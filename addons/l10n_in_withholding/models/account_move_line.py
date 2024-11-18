from odoo import fields, models, api


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    l10n_in_withhold_tax_amount = fields.Monetary(string="TDS Tax Amount", compute='_compute_withhold_tax_amount')
    l10n_in_tds_tcs_section_id = fields.Many2one(related="account_id.l10n_in_tds_tcs_section_id")

    @api.depends('tax_ids')
    def _compute_withhold_tax_amount(self):
        # Compute the withhold tax amount for the withholding lines
        withholding_lines = self.filtered(lambda rec: rec.move_id.l10n_in_is_withholding)
        (self - withholding_lines).l10n_in_withhold_tax_amount = False
        for line in withholding_lines:
            line.l10n_in_withhold_tax_amount = line.currency_id.round(abs(line.price_total - line.price_subtotal))
