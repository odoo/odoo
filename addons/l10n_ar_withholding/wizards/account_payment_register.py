# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api, Command


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    @api.depends('can_edit_wizard', 'source_amount', 'source_amount_currency', 'source_currency_id', 'company_id', 'currency_id', 'payment_date', 'installments_mode', 'l10n_latam_move_check_ids.amount', 'l10n_latam_new_check_ids.amount', 'payment_method_code')
    def _compute_amount(self):
        # EXTENDS 'l10n_account_withholding_tax'
        super()._compute_amount()
        for wizard in self:
            if wizard.company_id.country_code != 'AR':
                continue
            checks = wizard.l10n_latam_new_check_ids if wizard.filtered(lambda x: x._is_latam_check_payment(check_subtype='new_check')) else wizard.l10n_latam_move_check_ids
            checks_amount = sum(checks.mapped('amount'))
            if all([
                not wizard.currency_id.is_zero(checks_amount),
                wizard.currency_id.compare_amounts(checks_amount, wizard.withholding_net_amount) != 0,
                wizard.partner_type == 'supplier',
            ]):
                original_amount = wizard.amount
                f_delta = checks_amount - wizard.withholding_net_amount
                if f_delta < 0:
                    wizard.amount = checks_amount
                    f_delta = checks_amount - wizard.withholding_net_amount
                d = f_delta
                f_previous = wizard.withholding_net_amount
                wizard.amount += d
                wizard._refresh_l10n_ar_withholding_net_amount()
                for i in range(201):
                    f_delta = checks_amount - wizard.withholding_net_amount
                    if wizard.currency_id.is_zero(f_delta):
                        break
                    der = ((wizard.withholding_net_amount - f_previous) / d) if abs(d) >= 0.01 else 1.0
                    if wizard.currency_id.is_zero(der):
                        i = 200
                        break
                    d = max(f_delta / der, 0.01)
                    f_previous = wizard.withholding_net_amount
                    wizard.amount += d
                    wizard._refresh_l10n_ar_withholding_net_amount()
                if i == 200:
                    wizard.amount = original_amount

    @api.depends('country_code', 'can_edit_wizard', 'can_group_payments', 'group_payment',
                 'amount', 'l10n_latam_move_check_ids.amount', 'l10n_latam_new_check_ids.amount',
                 'payment_method_code', 'withholding_net_amount')
    def _compute_alerts(self):
        # EXTENDS 'l10n_account_withholding_tax'
        super()._compute_alerts()
        for wizard in self:
            if wizard.country_code != 'AR':
                continue
            alerts = dict(wizard.alerts or {})
            # AR withholdings can't be used when paying invoices of different partners (or same partner without grouping)
            if not (wizard.can_edit_wizard and (not wizard.can_group_payments or wizard.group_payment)):
                alerts['l10n_ar_withholding_grouping'] = {
                    'message': self.env._("You can't register withholdings when paying invoices of different partners or same partner without grouping."),
                    'level': 'info',
                }
            # Check amount adjustment mismatch warning
            checks = wizard.l10n_latam_new_check_ids if wizard._is_latam_check_payment(check_subtype='new_check') else wizard.l10n_latam_move_check_ids
            checks_amount = sum(checks.mapped('amount'))
            if not wizard.currency_id.is_zero(checks_amount) and wizard.currency_id.compare_amounts(checks_amount, wizard.withholding_net_amount) != 0:
                alerts['l10n_ar_check_adjustment'] = {
                    'message': self.env._("Adjust total amount or withholdings amount so that the check amount is the correct one."),
                    'level': 'warning',
                }
            wizard.alerts = alerts

    @api.depends('partner_id', 'payment_date')
    def _compute_withholding_line_ids(self):
        # EXTENDS 'l10n_account_withholding_tax'
        ar_wizards = self.filtered(lambda w: w.company_id.country_code == 'AR')
        super(AccountPaymentRegister, self - ar_wizards)._compute_withholding_line_ids()
        for wizard in ar_wizards:
            if not wizard.display_withholding or not wizard.can_edit_wizard:
                wizard.withholding_line_ids = [Command.clear()]
                continue
            if wizard.withholding_line_ids:
                continue
            date = wizard.payment_date or fields.Date.context_today(self)
            partner_type_to_tax_use = {'supplier': 'purchase', 'customer': 'sale'}
            partner_taxes = self.env['l10n_ar.partner.tax'].search([
                *self.env['l10n_ar.partner.tax']._check_company_domain(wizard.company_id),
                '|', ('from_date', '>=', date), ('from_date', '=', False),
                '|', ('to_date', '<=', date), ('to_date', '=', False),
                ('partner_id', '=', wizard.partner_id.commercial_partner_id.id),
                ('tax_id.is_withholding_tax_on_payment', '=', True),
                ('tax_id.type_tax_use', '=', partner_type_to_tax_use.get(wizard.partner_type, '')),
                ('tax_id.active', '=', True)
            ])
            wizard.withholding_line_ids = [Command.clear()] + [Command.create({'tax_id': x.tax_id.id}) for x in partner_taxes]

    def _refresh_l10n_ar_withholding_net_amount(self):
        # Newton iteration in `_compute_amount` writes wizard.amount and then needs an up-to-date
        # withholding_net_amount. The framework's lazy-recompute does not propagate trigger marks
        # from a write that happens *inside* a compute method, so we explicitly invalidate and
        # recompute base_amount/amount on the lines and the wizard's net amount.
        self.ensure_one()
        self.withholding_line_ids.invalidate_recordset(['base_amount', 'amount'])
        # Force re-evaluation of base/amount via the recompute trigger graph.
        self.withholding_line_ids.mapped('amount')
        self._compute_withholding_net_amount()
