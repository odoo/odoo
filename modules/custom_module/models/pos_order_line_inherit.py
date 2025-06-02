from odoo import models, fields

class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    menupro_id = fields.Char(string='Menu Pro ID')
