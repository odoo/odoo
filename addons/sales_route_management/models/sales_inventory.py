from odoo import models, fields, api

class CustomerInventory(models.Model):
    _name = 'sales.inventory'
    _description = 'Customer Inventory'

    customer_id = fields.Many2one('res.partner', string="Customer", required=True)
    product_id = fields.Many2one('product.product', string="Product", required=True)
    stock_level = fields.Float(string="Stock Level")
    last_updated = fields.Datetime(string="Last Updated", default=fields.Datetime.now)

    def update_inventory(self):
        """ Update the inventory levels manually """
        self.last_updated = fields.Datetime.now()