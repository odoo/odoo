from odoo import models, fields


class PosOrder(models.Model):
    _inherit = "pos.order"

    it_fiscal_receipt_number = fields.Char(string="Fiscal Receipt Number")
    it_fiscal_receipt_date = fields.Char(string="Fiscal Receipt Date")
    it_z_rep_number = fields.Char(string="Z-Rep Number")
