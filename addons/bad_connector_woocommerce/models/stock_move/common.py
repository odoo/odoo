from odoo import fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    external_move = fields.Char(string="WooCommerce External ID for Stock Move")
