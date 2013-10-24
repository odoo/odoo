# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import fields, osv
from openerp.tools.translate import _

class stock_move(osv.osv):
    _inherit = 'stock.move'
    _columns = {
        'purchase_line_id': fields.many2one('purchase.order.line',
            'Purchase Order Line', ondelete='set null', select=True,
            readonly=True),
    }

    def write(self, cr, uid, ids, vals, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        res = super(stock_move, self).write(cr, uid, ids, vals, context=context)
        from openerp import workflow
        for id in ids:
            workflow.trg_trigger(uid, 'stock.move', id, cr)
        return res

class stock_picking(osv.osv):
    _inherit = 'stock.picking'

    def _get_to_invoice(self, cr, uid, ids, name, args, context=None):
        res = {}
        for picking in self.browse(cr, uid, ids, context=context):
            res[picking.id] = False
            for move in picking.move_lines:
                if move.purchase_line_id and move.purchase_line_id.order_id.invoice_method == 'picking':
                    if not move.move_orig_ids:
                        res[picking.id] = True
        return res

    def _get_picking_to_recompute(self, cr, uid, ids, context=None):
        picking_ids = set()
        for move in self.pool.get('stock.move').browse(cr, uid, ids, context=context):
            if move.picking_id:
                picking_ids.add(move.picking_id.id)
        return list(picking_ids)

    _columns = {
        'reception_to_invoice': fields.function(_get_to_invoice, type='boolean', string='Invoiceable on incoming shipment?',
               help='Does the picking contains some moves related to a purchase order invoiceable on the reception?',
               store={
                   'stock.picking': (lambda self, cr, uid, ids, c={}: ids, ['move_lines'], 10),
                   'stock.move': (_get_picking_to_recompute, ['purchase_line_id', 'picking_id'], 10),
               }),
    }


    # TODO: Invoice based on receptions
    # Here is how it should work:
    #   On a draft invoice, allows to select purchase_orders (many2many_tags)
    # This fills in automatically PO lines or from related receptions if any

class stock_warehouse(osv.osv):
    _inherit = 'stock.warehouse'
    _columns = {
        'buy_to_resupply': fields.boolean('Purchase to resupply this warehouse'),
        'buy_pull_id': fields.many2one('procurement.rule', 'BUY rule'),
    }
    _defaults = {
        'buy_to_resupply': True,
    }

    def _get_buy_pull_rule(self, cr, uid, warehouse, context=None):
        route_obj = self.pool.get('stock.location.route')
        data_obj = self.pool.get('ir.model.data')
        try:
            buy_route_id = data_obj.get_object_reference(cr, uid, 'stock', 'route_warehouse0_buy')[1]
        except:
            buy_route_id = route_obj.search(cr, uid, [('name', 'like', _('Buy'))], context=context)
            buy_route_id = buy_route_id and buy_route_id[0] or False
        if not buy_route_id:
            raise osv.except_osv(_('Error!'), _('Can\'t find any generic Buy route.'))

        return {
            'name': self._format_routename(cr, uid, warehouse, _(' Buy'), context=context),
            'location_id': warehouse.in_type_id.default_location_dest_id.id,
            'route_id': buy_route_id,
            'action': 'buy',
            'picking_type_id': warehouse.in_type_id.id,
            'procure_method': 'make_to_order',
            'warehouse_id': warehouse.id,
        }

    def create_routes(self, cr, uid, ids, warehouse, context=None):
        pull_obj = self.pool.get('procurement.rule')
        res = super(stock_warehouse, self).create_routes(cr, uid, ids, warehouse, context=context)
        if warehouse.buy_to_resupply:
            buy_pull_vals = self._get_buy_pull_rule(cr, uid, warehouse, context=context)
            buy_pull_id = pull_obj.create(cr, uid, buy_pull_vals, context=context)
            res['buy_pull_id'] = buy_pull_id
        return res

    def write(self, cr, uid, ids, vals, context=None):
        pull_obj = self.pool.get('procurement.rule')
        if isinstance(ids, (int, long)):
            ids = [ids]

        if 'buy_to_resupply' in vals:
            if vals.get("buy_to_resupply"):
                for warehouse in self.browse(cr, uid, ids, context=context):
                    if not warehouse.buy_pull_id:
                        buy_pull_vals = self._get_buy_pull_rule(cr, uid, warehouse, context=context)
                        buy_pull_id = pull_obj.create(cr, uid, buy_pull_vals, context=context)
                        vals['buy_pull_id'] = buy_pull_id
            else:
                for warehouse in self.browse(cr, uid, ids, context=context):
                    if warehouse.buy_pull_id:
                        buy_pull_id = pull_obj.unlink(cr, uid, warehouse.buy_pull_id.id, context=context)
        return super(stock_warehouse, self).write(cr, uid, ids, vals, context=None)

    def get_all_routes_for_wh(self, cr, uid, warehouse, context=None):
        all_routes = super(stock_warehouse, self).get_all_routes_for_wh(cr, uid, warehouse, context=context)
        if warehouse.buy_to_resupply and warehouse.buy_pull_id and warehouse.buy_pull_id.route_id:
            all_routes += [warehouse.buy_pull_id.route_id.id]
        return all_routes

    def _get_all_products_to_resupply(self, cr, uid, warehouse, context=None):
        res = super(stock_warehouse, self)._get_all_products_to_resupply(cr, uid, warehouse, context=context)
        if warehouse.buy_pull_id and warehouse.buy_pull_id.route_id:
            for product_id in res:
                for route in self.pool.get('product.product').browse(cr, uid, product_id, context=context).route_ids:
                    if route.id == warehouse.buy_pull_id.route_id.id:
                        res.remove(product_id)
                        break
        return res

    def change_route(self, cr, uid, ids, warehouse, new_reception_step=False, new_delivery_step=False, context=None):
        res = super(stock_warehouse, self).change_route(cr, uid, ids, warehouse, new_reception_step=new_reception_step, new_delivery_step=new_delivery_step, context=context)
        if warehouse.in_type_id.default_location_dest_id != warehouse.buy_pull_id.location_id:
            self.pool.get('procurement.rule').write(cr, uid, warehouse.buy_pull_id.id, {'location_id': warehouse.in_type_id.default_location_dest_id.id}, context=context)
        return res
