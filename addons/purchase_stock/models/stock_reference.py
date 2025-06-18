from odoo import fields, models


class StockReference(models.Model):
    _inherit = 'stock.reference'

    purchase_ids = fields.Many2many(
        'purchase.order', 'stock_reference_purchase_rel', 'reference_id',
        'purchase_id', string="Purchases", copy=False)
