from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_ge_wht_category_ids = fields.Many2many(related="commercial_partner_id.l10n_ge_wht_category_ids")
    l10n_ge_gross_withholding_amount_currency = fields.Monetary(
        string="Gross Withholding",
        compute="_compute_withholding_total_amount",
        store=True,
        currency_field="currency_id",
        help="The part of the total withholding amount borne by the company (gross withholding taxes).",
    )

    @api.depends("line_ids.tax_ids.l10n_ge_is_gross")
    def _compute_withholding_total_amount(self):
        super()._compute_withholding_total_amount()
        AccountTax = self.env["account.tax"]
        for move in self:
            gross_amount_currency = 0.0
            if move.country_code == "GE" and move.is_invoice(include_receipts=True):
                for line in move.line_ids.filtered(lambda aml: any(aml.tax_ids.mapped("l10n_ge_is_gross"))):
                    base_line = AccountTax._prepare_base_line_for_taxes_computation(line, price_unit=line.price_unit, quantity=line.quantity, currency_id=move.currency_id, calculate_withholding_taxes=True)
                    AccountTax._add_tax_details_in_base_line(base_line, move.company_id)
                    AccountTax._round_base_lines_tax_details([base_line], move.company_id)
                    gross_amount_currency -= sum(tax_data["tax_amount_currency"] for tax_data in base_line["tax_details"]["taxes_data"] if tax_data["tax"].l10n_ge_is_gross)
            move.l10n_ge_gross_withholding_amount_currency = move.currency_id.round(gross_amount_currency)

    @api.depends("l10n_ge_gross_withholding_amount_currency")
    def _compute_withholding_net_residual_amount(self):
        super()._compute_withholding_net_residual_amount()
        # Payments withhold every tax in proportion to the amount paid: the gross share of the total applies to what is still due.
        for move in self.filtered(lambda m: m.l10n_ge_gross_withholding_amount_currency and m.withholding_residual_amount_currency > 0):
            gross_share = move.l10n_ge_gross_withholding_amount_currency / move.withholding_total_amount_currency
            move.withholding_net_residual_amount_currency += move.currency_id.round(move.withholding_residual_amount_currency * gross_share)
