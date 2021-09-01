from odoo import models, fields


class StockWarehouseOrderpoint(models.Model):
    _inherit = 'stock.warehouse.orderpoint'
    payment_method = fields.Many2one("aumet.payment_method", string="payment method")
