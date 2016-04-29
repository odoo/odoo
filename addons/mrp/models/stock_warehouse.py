# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from openerp import api
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
            'name': warehouse._format_routename(_(' Manufacture')),
            'location_id': warehouse.lot_stock_id.id,
            'route_id': manufacture_route_id,
            'action': 'manufacture',
            'picking_type_id': warehouse.int_type_id.id,
            'propagate': False, 
            'warehouse_id': warehouse.id,
        }

    def create_routes(self, cr, uid, ids, context=None):
        pull_obj = self.pool.get('procurement.rule')
        res = super(stock_warehouse, self).create_routes(cr, uid, ids, context=context)
        warehouse = self.browse(cr, uid, ids, context=context)[0]
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
        return super(stock_warehouse, self).write(cr, uid, ids, vals, context=context)

    @api.multi
    def _get_all_routes(self):
        routes = super(stock_warehouse, self).get_all_routes_for_wh()
        routes |= self.filtered(lambda self: self.manufacture_to_resupply and self.manufacture_pull_id and self.manufacture_pull_id.route_id).mapped('manufacture_pull_id').mapped('route_id')
        return routes

    def _handle_renaming(self, cr, uid, ids, name, code, context=None):
        res = super(stock_warehouse, self)._handle_renaming(cr, uid, ids, name, code, context=context)
        warehouse = self.browse(cr, uid, ids[0], context=context)
        pull_obj = self.pool.get('procurement.rule')
        #change the manufacture procurement rule name
        if warehouse.manufacture_pull_id:
            pull_obj.write(cr, uid, warehouse.manufacture_pull_id.id, {'name': warehouse.manufacture_pull_id.name.replace(warehouse.name, name, 1)}, context=context)
        return res
