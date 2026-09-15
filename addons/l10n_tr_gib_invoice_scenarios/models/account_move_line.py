from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    l10n_tr_original_line_id = fields.Many2one("account.move.line", readonly=True)

    l10n_tr_original_quantity = fields.Float(
        string="Original Quantity",
        digits="Product Unit",
        help="The quantity originally sold for this product.",
    )

    l10n_tr_original_tax_without_withholding = fields.Monetary(
        string="Original Tax After Withholding",
        help="Taxes collected after deducting withholding taxes for this product on the original invoice.",
    )
