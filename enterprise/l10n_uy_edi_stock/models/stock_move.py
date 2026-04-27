from odoo import fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    l10n_uy_edi_addenda_ids = fields.Many2many(
        "l10n_uy_edi.addenda",
        string="Mandatory Disclosures",
        domain="[('type', '=', 'item')]",
        ondelete="restrict",
    )
