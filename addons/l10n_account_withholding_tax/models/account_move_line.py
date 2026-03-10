from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    is_withhold_line = fields.Boolean(
        string="Is Withhold Line",
    )
    l10n_withholding_tax_amount = fields.Monetary(
        string="Withholding Tax Amount",
        compute='_compute_l10n_withholding_tax_amount'
    )

    @api.depends('tax_ids')
    def _compute_l10n_withholding_tax_amount(self):
        # Compute the withhold tax amount for the withholding lines
        withholding_lines = self.filtered(lambda line: line.is_withhold_line and line.tax_ids)
        (self - withholding_lines).l10n_withholding_tax_amount = False
        for line in withholding_lines:
            line.l10n_withholding_tax_amount = abs(line.currency_id.round(line.price_total - line.price_subtotal))
