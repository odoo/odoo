# custom_odooship_decanting_process/models/sales_order_inherit.py

from odoo import models, fields, api
from odoo.exceptions import UserError
import logging


_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def create(self, vals):
        sale_order = super(SaleOrder, self).create(vals)
        sale_order._assign_routes_to_order_lines()
        return sale_order

    def write(self, vals):
        res = super(SaleOrder, self).write(vals)
        if 'order_line' in vals:
            self._assign_routes_to_order_lines()
        return res

    def _assign_routes_to_order_lines(self):
        route_mapping = {
            'manual': "ALTWH6: transferOrders",
            'automation': "Automation Order: Pick-Pack-Deliver",
            'automation_bulk': "Bulk Automation Order: Pick-Pack-Deliver"
        }

        for order in self:
            for line in order.order_line:
                if line.product_id:
                    automation_manual_product = line.product_id.automation_manual_product or 'manual'
                    route_name = route_mapping.get(automation_manual_product, "ALTWH6: transferOrders")

                    # Search for the route
                    route = self.env['stock.route'].search([('name', '=', route_name)], limit=1)
                    if not route:
                        raise UserError(
                            f"Route '{route_name}' not found in the system. Please create it before processing orders.")

                    # Assign the route to the order line using Many2many field
                    line.route_id = route.id
