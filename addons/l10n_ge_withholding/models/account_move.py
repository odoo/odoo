from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_ge_wht_category_ids = fields.Many2many(related='commercial_partner_id.l10n_ge_wht_category_ids')
    l10n_ge_gross_withholding_amount_currency = fields.Monetary(
        string="Gross Withholding",
        compute='_compute_l10n_ge_gross_withholding_amount_currency',
        currency_field='currency_id',
        help="The part of the total withholding amount borne by the company (gross withholding taxes).",
    )

    @api.depends('line_ids.tax_ids.l10n_ge_is_gross')
    def _compute_withholding_total_amount(self):
        # Turning Gross on a tax changes the withholding amount of its draft bills.
        super()._compute_withholding_total_amount()

    @api.depends('country_code', 'currency_id', 'line_ids.tax_ids.l10n_ge_is_gross', 'line_ids.price_unit', 'line_ids.quantity', 'line_ids.discount')
    def _compute_l10n_ge_gross_withholding_amount_currency(self):
        AccountTax = self.env['account.tax']
        for move in self:
            gross_amount_currency = 0.0
            if move.country_code == 'GE' and move.is_invoice(include_receipts=True):
                for line in move.line_ids.filtered('tax_ids.l10n_ge_is_gross'):
                    base_line = AccountTax._prepare_base_line_for_taxes_computation(line, price_unit=line.price_unit, quantity=line.quantity, currency_id=move.currency_id, calculate_withholding_taxes=True)
                    AccountTax._add_tax_details_in_base_line(base_line, move.company_id)
                    AccountTax._round_base_lines_tax_details([base_line], move.company_id)
                    gross_amount_currency -= sum(tax_data['tax_amount_currency'] for tax_data in base_line['tax_details']['taxes_data'] if tax_data['tax'].l10n_ge_is_gross)
            move.l10n_ge_gross_withholding_amount_currency = move.currency_id.round(gross_amount_currency)

    @api.depends('l10n_ge_gross_withholding_amount_currency')
    def _compute_withholding_net_residual_amount(self):
        super()._compute_withholding_net_residual_amount()
        # Payments withhold every tax in proportion to the amount paid: the gross share of the total applies to what is still due.
        for move in self._l10n_ge_filter_gross_withholding_due():
            gross_share = move.l10n_ge_gross_withholding_amount_currency / move.withholding_total_amount_currency
            move.withholding_net_residual_amount_currency += move.currency_id.round(move.withholding_residual_amount_currency * gross_share)

    def _l10n_ge_filter_gross_withholding_due(self):
        return self.filtered(lambda move: move.l10n_ge_gross_withholding_amount_currency and move.withholding_residual_amount_currency > 0)

    def _prepare_product_base_line_for_taxes_computation(self, product_line):
        base_line = super()._prepare_product_base_line_for_taxes_computation(product_line)
        # The base of a withholding payment entry is already the grossed-up base.
        if self.origin_payment_id:
            base_line['l10n_ge_is_gross_base'] = True
        return base_line

    def _reverse_moves(self, default_values_list=None, cancel=False):
        reverse_moves = super()._reverse_moves(default_values_list=default_values_list, cancel=cancel)
        # account._reverse_moves only reverses the balance of an entry: reverse the base the withholding return reads too.
        for line in reverse_moves.filtered('reversed_entry_id.origin_payment_id').line_ids.filtered(lambda line: line.tax_line_id.is_withholding_tax and line.tax_line_id.country_code == 'GE'):
            line.tax_base_amount = -line.tax_base_amount
        return reverse_moves
