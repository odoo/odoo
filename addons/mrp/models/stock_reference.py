from odoo import fields, models


class StockReference(models.Model):
    _inherit = 'stock.reference'

    production_ids = fields.Many2many(
        'mrp.production', 'stock_reference_production_rel', 'reference_id',
        'production_id', string="Productions")
