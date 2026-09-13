from odoo import _, api, fields, models


class UomUom(models.Model):
    _inherit = "uom.uom"

    l10n_cl_sii_code = fields.Char(string="SII Code")
