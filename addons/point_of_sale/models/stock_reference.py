from odoo import fields, models


class StockReference(models.Model):
    _inherit = 'stock.reference'

    pos_order_ids = fields.Many2many(
        'pos.order', 'stock_reference_pos_order_rel', 'reference_id',
        'pos_order_id', string="PoS Orders")
