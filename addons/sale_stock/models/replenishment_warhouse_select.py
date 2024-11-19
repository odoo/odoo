# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import expression


class SaleStockReplenishmentWarehouseSelect(models.TransientModel):
    _name = 'sale_stock.replenishment.warehouse.select'
    _description = 'Replenishment Warehouse Select'
    _rec_name = 'sale_order_line_id'

    sale_order_line_id = fields.Many2one('sale.order.line')
    product_id = fields.Many2one('product.product', related='sale_order_line_id.product_id')
    qty_to_order = fields.Float(related='sale_order_line_id.product_uom_qty')

    route_ids = fields.One2many('stock.route', compute='_compute_route_ids')
    wh_replenishment_option_ids = fields.One2many('stock.replenishment.option', string='Warehouse Replenishment Options', compute='_compute_wh_replenishment_options')

    def _compute_route_ids(self):
        customer_location = self.sale_order_line_id.order_id.partner_shipping_id.property_stock_customer
        routes = self.env['stock.rule'].search(expression.AND([
            self.env['stock.rule']._check_company_domain(self.env.company),
            [
                ('location_dest_id', '=', customer_location.id),
                ('warehouse_id', '!=', False),
            ],
        ])).route_id
        for warehouse_select in self:
            warehouse_select.route_ids = routes

    @api.depends('sale_order_line_id')
    def _compute_wh_replenishment_options(self):
        for warehouse_select in self:
            warehouse_select.wh_replenishment_option_ids = self.env['stock.replenishment.option'].create([{
                'product_id': warehouse_select.product_id.id,
                'route_id': route_id.id,
                'warehouse_id': route_id.warehouse_ids[0].id,
                'location_id': route_id.warehouse_ids[0].lot_stock_id.id,
                'replenishment_info_id': '%s,%s' % (warehouse_select._name, warehouse_select.id),
            } for route_id in warehouse_select.route_ids]).sorted(lambda o: o.free_qty, reverse=True)

    def order_avbl(self, route_id, free_qty):
        so_line = self.sale_order_line_id
        if so_line.product_uom_qty > free_qty:
            so_line.copy({'product_uom_qty': so_line.product_uom_qty - free_qty, 'order_id': so_line.order_id.id})
        so_line.write({'route_id': route_id, 'product_uom_qty': free_qty})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': so_line.order_id.id,
        }

    def order_all(self, route_id):
        self.sale_order_line_id.write({'route_id': route_id})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': self.sale_order_line_id.order_id.id,
        }


class StockReplenishmentOption(models.TransientModel):
    _inherit = 'stock.replenishment.option'

    replenishment_info_id = fields.Reference(selection_add=[
        ('sale_stock.replenishment.warehouse.select', 'sale_stock.replenishment.warehouse.select'),
    ])
