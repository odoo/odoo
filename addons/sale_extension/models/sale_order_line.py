from odoo import api, fields, models
from datetime import timedelta

class SaleOrderLine(models.Model):
    #custom fields

    _inherit='sale.order.line'

    item_delivery_date = fields.Date(string="Fecha de entrega", compute="_compute_item_delivery_date")

    #custom cumpute
    @api.depends('product_id', 'product_uom_qty', 'product_uom', 'order_id.date_order')
    def _compute_item_delivery_date(self):
        for line in self:

            line.item_delivery_date = False

            if line.product_id:
                try:
                    available_stock = line.product_id.with_context(location=line.order_id.warehouse_id.lot_stock_id.id).qty_available
                    qty_to_order = line.product_uom_qty

                    if available_stock <  qty_to_order:
                        line.item_delivery_date = fields.Date.today()

                    else:
                        production_time = 15

                        if production_time:
                            line.item_delivery_date = fields.Date.today() + timedelta(days=production_time)
                        
                        else:
                            line.item_delivery_date = fields.Date.today() + timedelta(days=15)
                except Exception as e:
                    print(e)
