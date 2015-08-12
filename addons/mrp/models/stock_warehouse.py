# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models, _
from openerp.exceptions import UserError


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    manufacture_to_resupply = fields.Boolean(string='Manufacture in this Warehouse', default=True, help="When products are manufactured, they can be manufactured in this warehouse.")
    manufacture_pull_id = fields.Many2one('procurement.rule', string='Manufacture Rule')

    @api.model
    def _get_manufacture_pull_rule(self, warehouse):
        try:
            manufacture_route_id = self.env.ref('mrp.route_warehouse0_manufacture').id
        except:
            manufacture_route_id = self.env['stock.location.route'].search([('name', 'like', _('Manufacture'))])
            manufacture_route_id = manufacture_route_id and manufacture_route_id[0] or False
        if not manufacture_route_id:
            raise UserError(_('Can\'t find any generic Manufacture route.'))

        return {
            'name': self._format_routename(warehouse, _(' Manufacture')),
            'location_id': warehouse.lot_stock_id.id,
            'route_id': manufacture_route_id,
            'action': 'manufacture',
            'picking_type_id': warehouse.int_type_id.id,
            'propagate': False, 
            'warehouse_id': warehouse.id,
        }

    @api.multi
    def create_routes(self, warehouse):
        res = super(StockWarehouse, self).create_routes(warehouse)
        if warehouse.manufacture_to_resupply:
            manufacture_pull_vals = self._get_manufacture_pull_rule(warehouse)
            self.manufacture_pull_id = self.env['procurement.rule'].create(manufacture_pull_vals)
        return res

    @api.multi
    def write(self, vals):
        if 'manufacture_to_resupply' in vals:
            if vals.get("manufacture_to_resupply"):
                for warehouse in self:
                    if not warehouse.manufacture_pull_id:
                        manufacture_pull_vals = self._get_manufacture_pull_rule(warehouse)
                        self.manufacture_pull_id = self.env['procurement.rule'].create(manufacture_pull_vals)
            else:
                for warehouse in self:
                    if warehouse.manufacture_pull_id:
                        self.env['procurement.rule'].browse(warehouse.manufacture_pull_id.id).unlink()
        return super(StockWarehouse, self).write(vals)

    @api.model
    def get_all_routes_for_wh(self, warehouse):
        all_routes = super(StockWarehouse, self).get_all_routes_for_wh(warehouse)
        if warehouse.manufacture_to_resupply and warehouse.manufacture_pull_id and warehouse.manufacture_pull_id.route_id:
            all_routes += [warehouse.manufacture_pull_id.route_id.id]
        return all_routes

    @api.model
    def _handle_renaming(self, warehouse, name, code):
        res = super(StockWarehouse, self)._handle_renaming(warehouse, name, code)
        #change the manufacture procurement rule name
        if warehouse.manufacture_pull_id:
            warehouse.manufacture_pull_id.write({'name': warehouse.manufacture_pull_id.name.replace(warehouse.name, name, 1)})
        return res

    def _get_all_products_to_resupply(self, warehouse):
        res = super(StockWarehouse, self)._get_all_products_to_resupply(warehouse)
        if warehouse.manufacture_pull_id and warehouse.manufacture_pull_id.route_id:
            for product_id in res:
                for route in self.env['product.product'].browse(product_id).route_ids:
                    if route.id == warehouse.manufacture_pull_id.route_id.id:
                        res.remove(product_id)
                        break
        return res
