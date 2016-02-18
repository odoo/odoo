# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models, _
from openerp.exceptions import UserError


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    manufacture_to_resupply = fields.Boolean(string='Manufacture in this Warehouse', default=True, help="When products are manufactured, they can be manufactured in this warehouse.")
    manufacture_pull_id = fields.Many2one('procurement.rule', string='Manufacture Rule')

    def _get_manufacture_pull_rule(self):
        try:
            manufacture_route = self.env.ref('mrp.route_warehouse0_manufacture')
        except:
            manufacture_route = self.env['stock.location.route'].search([('name', 'like', _('Manufacture'))])
            manufacture_route = manufacture_route and manufacture_route[0] or False
        if not manufacture_route:
            raise UserError(_('Can\'t find any generic Manufacture route.'))

        return {
            'name': self._format_routename(self, _(' Manufacture')),
            'location_id': self.lot_stock_id.id,
            'route_id': manufacture_route.id,
            'action': 'manufacture',
            'picking_type_id': self.int_type_id.id,
            'propagate': False,
            'warehouse_id': self.id,
        }

    @api.multi
    def create_routes(self, warehouse):
        res = super(StockWarehouse, self).create_routes(warehouse)
        if warehouse.manufacture_to_resupply:
            manufacture_pull_vals = warehouse._get_manufacture_pull_rule()
            self.manufacture_pull_id = self.env['procurement.rule'].create(manufacture_pull_vals)
        return res

    @api.multi
    def write(self, vals):
        if 'manufacture_to_resupply' in vals:
            if vals.get("manufacture_to_resupply"):
                for warehouse in self:
                    if not warehouse.manufacture_pull_id:
                        manufacture_pull_vals = warehouse._get_manufacture_pull_rule()
                        warehouse.manufacture_pull_id = self.env['procurement.rule'].create(manufacture_pull_vals)
            else:
                for warehouse in self:
                    if warehouse.manufacture_pull_id:
                        warehouse.manufacture_pull_id.unlink()
        return super(StockWarehouse, self).write(vals)

    @api.multi
    def get_all_routes_for_wh(self):
        all_routes = super(StockWarehouse, self).get_all_routes_for_wh()
        if self.manufacture_to_resupply and self.manufacture_pull_id and self.manufacture_pull_id.route_id:
            all_routes += [self.manufacture_pull_id.route_id.id]
        return all_routes

    @api.multi
    def _handle_renaming(self, name, code):
        res = super(StockWarehouse, self)._handle_renaming(name, code)
        # change the manufacture procurement rule name
        if self.manufacture_pull_id:
            self.manufacture_pull_id.write({'name': self.manufacture_pull_id.name.replace(self.name, name, 1)})
        return res

    def _get_all_products_to_resupply(self):
        ProductProduct = self.env['product.product']
        res = super(StockWarehouse, self)._get_all_products_to_resupply()
        if self.manufacture_pull_id and self.manufacture_pull_id.route_id:
            for product_id in res:
                for route in ProductProduct.browse(product_id).route_ids:
                    if route.id == self.manufacture_pull_id.route_id.id:
                        res.remove(product_id)
                        break
        return res
