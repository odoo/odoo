from odoo import models, fields, api

class StockAlert(models.Model):
    _name = 'sales.stock.alert'
    _description = 'Stock Alert'

    inventory_id = fields.Many2one('sales.inventory', string="Inventory Record", required=True)
    threshold = fields.Float(string="Stock Threshold", default=5)
    alert_sent = fields.Boolean(string="Alert Sent", default=False)

    @api.model
    def check_stock_levels(self):
        """ Auto-check stock levels and create alerts if below threshold """
        inventories = self.env['sales.inventory'].search([])
        for inventory in inventories:
            if inventory.stock_level < 5:  # Threshold value
                self.create({'inventory_id': inventory.id, 'threshold': 5, 'alert_sent': False})