# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SaleConfiguration(models.TransientModel):
    _inherit = 'sale.config.settings'

    security_lead = fields.Float(related='company_id.security_lead', string="Sales Safety Days *")
    module_delivery = fields.Selection([
        (0, 'No shipping costs on sales orders'),
        (1, 'Allow adding shipping costs')
        ], "Shipping")
    default_picking_policy = fields.Selection([
        (0, 'Ship products when some are available, and allow back orders'),
        (1, 'Ship all products at once, without back orders')
        ], "Default Shipping Policy")
    group_mrp_properties = fields.Selection([
        (0, "Don't use manufacturing properties (recommended as its easier)"),
        (1, 'Allow setting manufacturing order properties per order line (advanced)')
        ], "Properties on SO Lines",
        implied_group='sale.group_mrp_properties',
        help="Allows you to tag sales order lines with properties.")
    group_route_so_lines = fields.Selection([
        (0, 'No order specific routes like MTO or drop shipping'),
        (1, 'Choose specific routes on sales order lines (advanced)')
        ], "Order Routing",
        implied_group='sale_stock.group_route_so_lines')
    module_sale_order_dates = fields.Selection([
        (0, 'Procurements and deliveries dates are based on the sales order dates'),
        (1, 'Allow to modify the sales order dates to postpone deliveries and procurements')
        ], "Date")

    @api.model
    def get_default_sale_config(self, fields):
        default_picking_policy = self.env['ir.values'].get_default('sale.order', 'picking_policy')
        return {
            'default_picking_policy': 1 if default_picking_policy == 'one' else 0,
        }

    @api.multi
    def set_sale_defaults(self):
        default_picking_policy = 'one' if self.default_picking_policy else 'direct'
        self.env['ir.values'].sudo().set_default('sale.order', 'picking_policy', default_picking_policy)
        return super(SaleConfiguration, self).set_sale_defaults()
