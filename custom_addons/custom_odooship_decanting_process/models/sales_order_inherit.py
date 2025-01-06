# custom_odooship_decanting_process/models/sales_order_inherit.py

from odoo import models, fields, api
from odoo.exceptions import UserError
import logging


_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    tenant_code_id = fields.Many2one(
        'tenant.code.configuration',
        string='Tenant Code',
        related='partner_id.tenant_code_id',
        readonly=True,
        store=True
    )

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
        """
        Assign routes to sales order lines based on the warehouse_id and automation/manual product setting.
        Route names dynamically include the warehouse name.
        """
        route_mapping = {
            'manual': "{warehouse} Manual Orders",
            'automation': "{warehouse} Automation Order: Pick-Pack-Deliver",
            'automation_bulk': "{warehouse} Bulk Automation Order: Pick-Pack-Deliver"
        }

        for order in self:
            if not order.warehouse_id:
                raise UserError("Please specify a warehouse on the Sales Order before confirming the order.")

            warehouse_name = order.warehouse_id.name

            for line in order.order_line:
                if line.product_id and line.auto_assign_route:  # Execute only if auto_assign_route is True
                    automation_manual_product = line.product_id.automation_manual_product or 'manual'
                    route_template = route_mapping.get(automation_manual_product)

                    if not route_template:
                        raise UserError(f"No route mapping found for product type '{automation_manual_product}'.")

                    # Dynamically construct the route name using the warehouse name
                    route_name = route_template.format(warehouse=warehouse_name)

                    # Search for the route matching the name
                    route = self.env['stock.route'].search([
                        ('name', '=', route_name),
                        ('supplied_wh_id', '=', order.warehouse_id.id)
                    ], limit=1)

                    if not route:
                        raise UserError(
                            f"Route '{route_name}' for Warehouse '{warehouse_name}' not found. "
                            f"Please create the route before processing orders."
                        )

                    # Assign the route to the order line
                    line.route_id = route.id


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    auto_assign_route = fields.Boolean(
        string="Auto Assign Route",
        default=False,
        help="If checked, the route for this line will be assigned automatically. "
             "Otherwise, you can manually select a route."
    )