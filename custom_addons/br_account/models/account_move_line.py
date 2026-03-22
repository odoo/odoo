from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    cfop = fields.Char(size=5)
    cst_icms = fields.Char(size=3)
    cst_pis = fields.Char(size=2)
    cst_cofins = fields.Char(size=2)
    ncm = fields.Char(size=8)

