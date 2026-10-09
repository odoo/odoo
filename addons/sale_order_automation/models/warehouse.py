from odoo import api, fields, models


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    is_delivery_set_to_done = fields.Boolean(string="Is Delivery Set to Done")
    create_invoice=fields.Boolean(string='Create Invoice?')
    validate_invoice = fields.Boolean(string='Validate invoice?')
