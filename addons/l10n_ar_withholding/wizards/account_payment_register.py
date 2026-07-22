# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api
from odoo.fields import Command


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    @api.model
    def _get_default_withhold(self, moves):
        """ EXTENDS 'l10n_account_withholding_tax' """
        if not moves or any(move.country_code != 'AR' for move in moves):
            return super()._get_default_withhold(moves)

        net_residual = sum(moves.mapped('withholding_net_residual_amount_currency'))
        return 'withhold_pay' if net_residual > 0 else 'withhold'

    def _compute_amount(self):
        super()._compute_amount()
        for wizard in self:
            if wizard.country_code != 'AR':
                continue

            if wizard.withhold == 'withhold' and wizard.can_edit_wizard:
                # The generic module fills a withholding-only payment from the withholding taxes declared
                # on the invoice, which Argentina never declares: fill it from the lines instead.
                wizard._l10n_ar_set_amount_from_withholdings()
                continue

            checks_amount = wizard.l10n_latam_checks_amount
            currency_id = wizard.currency_id or wizard.company_currency_id
            if (
                wizard.partner_type != 'supplier'
                or currency_id.is_zero(checks_amount)
                or currency_id.compare_amounts(checks_amount, wizard.withholding_net_amount) == 0
            ):
                continue

            # The withholdings derive from the amount, so the amount whose net matches a fixed
            # check total cannot be set directly: look for it with a secant method.
            original_amount = wizard.amount
            residual = checks_amount - wizard.withholding_net_amount
            if residual < 0:
                # Removing withholdings can result in an overshoot of the initial amount
                wizard.amount = checks_amount
                residual = checks_amount - wizard.withholding_net_amount

            step = residual
            previous_net = wizard.withholding_net_amount
            wizard._l10n_ar_set_amount_and_recompute_withholdings(wizard.amount + step)

            converged = False
            for _ in range(200):
                residual = checks_amount - wizard.withholding_net_amount
                if currency_id.is_zero(residual):
                    converged = True
                    break
                # A step below the currency precision tells nothing about the slope: assume 1.
                slope = ((wizard.withholding_net_amount - previous_net) / step) if not currency_id.is_zero(step) else 1.0
                if currency_id.is_zero(slope):
                    break
                step = max(residual / slope, 0.01)
                previous_net = wizard.withholding_net_amount
                wizard._l10n_ar_set_amount_and_recompute_withholdings(wizard.amount + step)

            if not converged:
                # Adjustment failed, resetting
                wizard.amount = original_amount

    @api.onchange('withholding_line_ids')
    def _onchange_withholding_line_ids(self):
        """ A withholding-only payment is worth what it withholds. """
        super()._onchange_withholding_line_ids()
        if self.country_code != 'AR' or self.withhold != 'withhold' or not self.can_edit_wizard:
            return

        self._l10n_ar_set_amount_from_withholdings()

    def _l10n_ar_set_amount_from_withholdings(self):
        self.ensure_one()
        lines = self.withholding_line_ids
        with self.env.protecting([lines._fields['base_amount']], lines):
            self.amount = sum(lines.mapped('amount'))

    def _l10n_ar_set_amount_and_recompute_withholdings(self, amount):
        """ Set the payment amount and refresh what derives from it: the withholding lines are
        computed from the amount, and the net amount from those lines.
        """
        self.ensure_one()
        self.amount = amount  # amount + step
        # The comodel_percentage_paid_factor the base derives from is not stored, cleaning the cache to force
        # recompute against the amount just set.
        self.withholding_line_ids.invalidate_recordset(['comodel_percentage_paid_factor'])
        self.env.add_to_compute(self.withholding_line_ids._fields['base_amount'], self.withholding_line_ids)
        self.env.add_to_compute(self.withholding_line_ids._fields['amount'], self.withholding_line_ids)
        self.env.add_to_compute(self._fields['withholding_net_amount'], self)

    @api.depends(
        'withholding_net_amount', 'l10n_latam_checks_amount', 'can_edit_wizard', 'can_group_payments', 'group_payment',
        'withholding_line_ids.withholding_sequence_id',
    )
    def _compute_actionable_errors(self):
        super()._compute_actionable_errors()
        for wizard in self:
            if wizard.country_code != 'AR':
                continue
            actionable_errors = wizard.actionable_errors or {}

            if not wizard.can_edit_wizard or (wizard.can_group_payments and not wizard.group_payment):
                actionable_errors['l10n_ar_withholding_grouping_warning'] = {
                    'message': wizard.env._("You can't register withholdings when paying invoices of different partners or same partner without grouping"),
                    'level': 'info',
                }

            lines_without_sequence = wizard.withholding_line_ids.filtered(
                lambda line: not line.name and not line.withholding_sequence_id
            )
            if lines_without_sequence:
                actionable_errors['l10n_ar_withholding_sequence_warning'] = {
                    'message': wizard.env._(
                        "Please enter Sequence Number for tax %(tax_names)s",
                        tax_names=", ".join(lines_without_sequence.tax_id.mapped('name')),
                    ),
                    'level': 'warning',
                }

            currency_id = wizard.currency_id or wizard.company_currency_id
            checks_amount = wizard.l10n_latam_checks_amount
            if not currency_id.is_zero(checks_amount) and currency_id.compare_amounts(checks_amount, wizard.withholding_net_amount) != 0:
                # This will only happen if the secant method doesn't resolve the amount correctly after the 200 rounds.
                # So, shouldn't happen that often.
                actionable_errors['l10n_ar_adjustment_warning'] = {
                    'message': wizard.env._("Adjust total amount or withholdings amount so that the check amount is the correct one."),
                    'level': 'warning',
                }
            wizard.actionable_errors = actionable_errors

    def _compute_withholding_outstanding_account_id(self):
        # EXTENDS 'l10n_account_withholding_tax' - AR default outstanding account
        super()._compute_withholding_outstanding_account_id()
        for wizard in self:
            if wizard.country_code == 'AR' and wizard.withhold != 'payment' and not wizard.withholding_outstanding_account_id and not wizard.withholding_payment_account_id:
                account_ref = 'account_journal_payment_debit_account_id' if wizard.payment_type == 'inbound' else 'account_journal_payment_credit_account_id'
                chart_template = wizard.with_context(allowed_company_ids=wizard.company_id.root_id.ids).env['account.chart.template']
                wizard.withholding_outstanding_account_id = (
                    chart_template.ref(account_ref, raise_if_not_found=False)
                    or wizard.company_id.transfer_account_id
                )

    @api.depends('payment_date')
    def _compute_withholding_line_ids(self):
        """ EXTENDS 'l10n_account_withholding_tax'
        The generic module builds the lines from the withholding taxes declared on the invoice.
        Argentina declares none: the tax regimes the partner is registered in, as of the payment date, will define what is owed.
        Any other withholding is added manually on the wizard.
        """
        super()._compute_withholding_line_ids()
        for wizard in self:
            if wizard.country_code != 'AR' or not wizard.display_withholding or not wizard.can_edit_wizard:
                continue

            type_tax_use = 'purchase' if wizard.partner_type == 'supplier' else 'sale'
            all_regime_taxes = wizard.partner_id._l10n_ar_get_withholding_taxes_from_regime(
                company=wizard.company_id,
                type_tax_use=type_tax_use,
            )
            if not all_regime_taxes:
                continue

            taxes_at_date = wizard.partner_id._l10n_ar_get_withholding_taxes_from_regime(
                company=wizard.company_id,
                type_tax_use=type_tax_use,
                date=wizard.payment_date or fields.Date.context_today(self),
            )
            outdated = wizard.withholding_line_ids.filtered(lambda line: line.tax_id in all_regime_taxes - taxes_at_date)
            missing = taxes_at_date - wizard.withholding_line_ids.tax_id
            if not outdated and not missing:
                continue

            wizard.withholding_line_ids = [
                *[Command.delete(line.id) for line in outdated],
                *[Command.create({'tax_id': tax.id}) for tax in missing],
            ]

    def _compute_withholding_hide_name(self):
        # EXTENDS 'l10n_account_withholding_tax' - always display sequence/name for AR
        ar_payment_wizard = self.filtered(lambda w: w.country_code == 'AR')
        ar_payment_wizard.withholding_hide_name = False
        super(AccountPaymentRegister, self - ar_payment_wizard)._compute_withholding_hide_name()
