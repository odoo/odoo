# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields
from openerp.osv import osv
from openerp.tools.translate import _
from openerp.exceptions import UserError


class stock_warehouse(osv.osv):
    _inherit = 'stock.warehouse'
    _columns = {
        'manufacture_to_resupply': fields.boolean('Manufacture in this Warehouse', 
                                                  help="When products are manufactured, they can be manufactured in this warehouse."),
        'manufacture_pull_id': fields.many2one('procurement.rule', 'Manufacture Rule'),
    }

    _defaults = {
        'manufacture_to_resupply': True,
    }

    def _get_manufacture_pull_rule(self, cr, uid, warehouse, context=None):
        route_obj = self.pool.get('stock.location.route')
        data_obj = self.pool.get('ir.model.data')
        try:
            manufacture_route_id = data_obj.get_object_reference(cr, uid, 'mrp', 'route_warehouse0_manufacture')[1]
        except:
            manufacture_route_id = route_obj.search(cr, uid, [('name', 'like', _('Manufacture'))], context=context)
            manufacture_route_id = manufacture_route_id and manufacture_route_id[0] or False
        if not manufacture_route_id:
            raise UserError(_('Can\'t find any generic Manufacture route.'))

        return {
            'name': self._format_routename(cr, uid, warehouse, _(' Manufacture'), context=context),
            'location_id': warehouse.lot_stock_id.id,
            'route_id': manufacture_route_id,
            'action': 'manufacture',
            'picking_type_id': warehouse.int_type_id.id,
            'propagate': False, 
            'warehouse_id': warehouse.id,
        }

    def create_routes(self, cr, uid, ids, warehouse, context=None):
        pull_obj = self.pool.get('procurement.rule')
        res = super(stock_warehouse, self).create_routes(cr, uid, ids, warehouse, context=context)
        if warehouse.manufacture_to_resupply:
            manufacture_pull_vals = self._get_manufacture_pull_rule(cr, uid, warehouse, context=context)
            manufacture_pull_id = pull_obj.create(cr, uid, manufacture_pull_vals, context=context)
            res['manufacture_pull_id'] = manufacture_pull_id
        return res

    def write(self, cr, uid, ids, vals, context=None):
        pull_obj = self.pool.get('procurement.rule')
        if isinstance(ids, (int, long)):
            ids = [ids]

        if 'manufacture_to_resupply' in vals:
            if vals.get("manufacture_to_resupply"):
                for warehouse in self.browse(cr, uid, ids, context=context):
                    if not warehouse.manufacture_pull_id:
                        manufacture_pull_vals = self._get_manufacture_pull_rule(cr, uid, warehouse, context=context)
                        manufacture_pull_id = pull_obj.create(cr, uid, manufacture_pull_vals, context=context)
                        vals['manufacture_pull_id'] = manufacture_pull_id
            else:
                for warehouse in self.browse(cr, uid, ids, context=context):
                    if warehouse.manufacture_pull_id:
                        pull_obj.unlink(cr, uid, warehouse.manufacture_pull_id.id, context=context)
        return super(stock_warehouse, self).write(cr, uid, ids, vals, context=None)

    def get_all_routes_for_wh(self, cr, uid, warehouse, context=None):
        all_routes = super(stock_warehouse, self).get_all_routes_for_wh(cr, uid, warehouse, context=context)
        if warehouse.manufacture_to_resupply and warehouse.manufacture_pull_id and warehouse.manufacture_pull_id.route_id:
            all_routes += [warehouse.manufacture_pull_id.route_id.id]
        return all_routes

    def _handle_renaming(self, cr, uid, warehouse, name, code, context=None):
        res = super(stock_warehouse, self)._handle_renaming(cr, uid, warehouse, name, code, context=context)
        pull_obj = self.pool.get('procurement.rule')
        #change the manufacture procurement rule name
        if warehouse.manufacture_pull_id:
            pull_obj.write(cr, uid, warehouse.manufacture_pull_id.id, {'name': warehouse.manufacture_pull_id.name.replace(warehouse.name, name, 1)}, context=context)
        return res

    def _get_all_products_to_resupply(self, cr, uid, warehouse, context=None):
        res = super(stock_warehouse, self)._get_all_products_to_resupply(cr, uid, warehouse, context=context)
        if warehouse.manufacture_pull_id and warehouse.manufacture_pull_id.route_id:
            for product_id in res:
                for route in self.pool.get('product.product').browse(cr, uid, product_id, context=context).route_ids:
                    if route.id == warehouse.manufacture_pull_id.route_id.id:
                        res.remove(product_id)
                        break
        return res
