from odoo import fields, models


class UomUom(models.Model):
    _inherit = "uom.uom"

    l10n_ar_afip_code = fields.Char(
        string="Code",
        help="Argentina: This code will be used on electronic invoice.",
    )
