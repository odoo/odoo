from odoo import fields, models


class UoM(models.Model):
    _inherit = "uom.uom"

    ro_saft_code = fields.Char(string="RO SAF-T Code", help="Romanian SAF-T code used for e-Factura.", store=True)
