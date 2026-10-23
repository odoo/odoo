# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    @api.model
    def _get_default_withhold(self, moves):
        """ EXTENDS 'l10n_account_withholding_tax' """
        if not moves or any(move.country_code != 'GT' for move in moves):
            return super()._get_default_withhold(moves)

        net_residual = sum(moves.mapped('withholding_net_residual_amount_currency'))
        return 'withhold_pay' if net_residual > 0 else 'withhold'

    def _compute_amount(self):
        super()._compute_amount()
        for wizard in self:
            if wizard.country_code == 'GT' and wizard.withhold == 'withhold' and wizard.can_edit_wizard:
                # The generic module fills a withholding-only payment from the withholding taxes declared
                # on the invoice, which Guatemala never declares, so fill it from the lines instead.
                wizard._l10n_gt_set_amount_from_withholdings()

    @api.onchange('withholding_line_ids')
    def _onchange_withholding_line_ids(self):
        """ A withholding-only payment is worth what it withholds. """
        super()._onchange_withholding_line_ids()
        if self.country_code != 'GT' or self.withhold != 'withhold' or not self.can_edit_wizard:
            return

        self._l10n_gt_set_amount_from_withholdings()

    def _l10n_gt_set_amount_from_withholdings(self):
        self.ensure_one()
        lines = self.withholding_line_ids
        with self.env.protecting([lines._fields['base_amount']], lines):
            self.amount = sum(lines.mapped('amount'))

    def _compute_withholding_line_ids(self):
        """ EXTENDS 'l10n_account_withholding_tax'
        Guatemala declares no withholding tax on the invoice, the SAT rules define them from the untaxed amount of each invoice.
        """
        super()._compute_withholding_line_ids()
        for wizard in self:
            if (
                wizard.country_code != 'GT'
                or not wizard.display_withholding
                or not wizard.can_edit_wizard
                or wizard.withholding_line_ids
            ):
                continue

            base_lines = []
            for move in wizard._get_batches()[0]['lines'].move_id:
                base_lines += wizard._l10n_gt_get_withholding_base_lines(move)

            if base_lines:
                wizard.withholding_line_ids = wizard.withholding_line_ids._prepare_withholding_lines_commands(
                    base_lines=base_lines,
                    company=wizard.company_id,
                )

    def _l10n_gt_get_withholding_base_lines(self, move):
        """ Return one base line per withholding tax due on the move, levied on its untaxed amount in company currency. """
        # SAT withholdings don't apply to POS orders
        if 'pos_order_ids' in move._fields and move.sudo().pos_order_ids:
            return []

        base_lines, _tax_lines = move._get_rounded_base_and_tax_lines()
        merged_base_lines = {}
        total_untaxed_amount = 0.0
        for base_line in base_lines:
            line = base_line['record']
            if not isinstance(line, models.Model) or line.display_type != 'product':
                continue

            tax_details = base_line['tax_details']
            untaxed_amount = tax_details['total_excluded'] + tax_details['delta_total_excluded']
            total_untaxed_amount += untaxed_amount
            for tax in line._l10n_gt_get_withholding_taxes():
                merged = merged_base_lines.setdefault(tax, {'base_line': base_line, 'untaxed_amount': 0.0})
                merged['untaxed_amount'] += untaxed_amount

        AccountTax = self.env['account.tax']
        withholding_base_lines = []
        for tax, merged in merged_base_lines.items():
            if total_untaxed_amount < tax.l10n_gt_minimum_base_threshold:
                continue

            taxable_amount = merged['untaxed_amount']
            if tax.l10n_gt_max_taxable_base:
                taxable_amount = min(taxable_amount, tax.l10n_gt_max_taxable_base)
            taxable_amount -= tax.l10n_gt_nontaxable_base
            base_line = AccountTax._prepare_base_line_for_taxes_computation(
                merged['base_line'],
                tax_ids=tax,
                price_unit=taxable_amount,
                quantity=1.0,
                discount=0.0,
                currency_id=move.company_currency_id,
                rate=1.0,
            )
            if self._l10n_gt_get_withholding_amount(base_line):
                withholding_base_lines.append(base_line)
        return withholding_base_lines

    def _l10n_gt_get_withholding_amount(self, base_line):
        """ Return the sum of the base line's withholding taxes. """
        self.ensure_one()
        AccountTax = self.env['account.tax']
        evaluated_base_line = {**base_line, 'calculate_withholding_taxes': True}
        AccountTax._add_tax_details_in_base_line(evaluated_base_line, self.company_id)
        AccountTax._round_base_lines_tax_details([evaluated_base_line], self.company_id)
        return sum(
            tax_data['tax_amount_currency']
            for tax_data in evaluated_base_line['tax_details']['taxes_data']
        )
