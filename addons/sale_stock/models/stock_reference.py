from odoo import fields, models


class StockReference(models.Model):
    _inherit = 'stock.reference'

    sale_ids = fields.Many2many(
        'sale.order', 'stock_reference_sale_rel', 'reference_id',
        'sale_id', string="Sales")
