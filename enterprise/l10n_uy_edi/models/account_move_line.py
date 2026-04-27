from odoo import models, fields


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    l10n_uy_edi_addenda_ids = fields.Many2many(
        "l10n_uy_edi.addenda",
        string="Mandatory Disclosures",
        domain="[('type', '=', 'item')]",
        ondelete="restrict",
    )
