# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.exceptions import UserError

class stock_picking(osv.osv):
    _inherit = 'stock.picking'
    _columns = {
        'purchase_id': fields.related('move_lines', 'purchase_line_id', 'order_id', string="Purchase Orders",
            readonly=True, type="many2one", relation="purchase.order"),
    }

    def _prepare_values_extra_move(self, cr, uid, op, product, remaining_qty, context=None):
        res = super(stock_picking, self)._prepare_values_extra_move(cr, uid, op, product, remaining_qty, context=context)
        for m in op.linked_move_operation_ids:
            if m.move_id.purchase_line_id and m.move_id.product_id == product:
                res['purchase_line_id'] = m.move_id.purchase_line_id.id
                break
        return res


class stock_move(osv.osv):
    _inherit = 'stock.move'
    _columns = {
        'purchase_line_id': fields.many2one('purchase.order.line',
            'Purchase Order Line', ondelete='set null', select=True,
            readonly=True),
    }

    @api.multi
    def get_price_unit(self):
        """ Returns the unit price to store on the quant """
        if self.purchase_line_id:
            order = self.purchase_line_id.order_id
            #if the currency of the PO is different than the company one, the price_unit on the move must be reevaluated
            #(was created at the rate of the PO confirmation, but must be valuated at the rate of stock move execution)
            if order.currency_id != self.company_id.currency_id:
                #we don't pass the move.date in the compute() for the currency rate on purpose because
                # 1) get_price_unit() is supposed to be called only through move.action_done(),
                # 2) the move hasn't yet the correct date (currently it is the expected date, after
                #    completion of action_done() it will be now() )
                price_unit = self.purchase_line_id._get_stock_move_price_unit()
                self.write({'price_unit': price_unit})
                return price_unit
            return self.price_unit
        return super(stock_move, self).get_price_unit()

    def copy(self, cr, uid, id, default=None, context=None):
        default = default or {}
        context = context or {}
        if not default.get('split_from'):
            #we don't want to propagate the link to the purchase order line except in case of move split
            default['purchase_line_id'] = False
        return super(stock_move, self).copy(cr, uid, id, default, context)


class stock_warehouse(osv.osv):
    _inherit = 'stock.warehouse'
    _columns = {
        'buy_to_resupply': fields.boolean('Purchase to resupply this warehouse',
                                          help="When products are bought, they can be delivered to this warehouse"),
        'buy_pull_id': fields.many2one('procurement.rule', 'Buy rule'),
    }
    _defaults = {
        'buy_to_resupply': True,
    }

    def _get_buy_pull_rule(self, cr, uid, warehouse, context=None):
        route_obj = self.pool.get('stock.location.route')
        data_obj = self.pool.get('ir.model.data')
        try:
            buy_route_id = data_obj.get_object_reference(cr, uid, 'purchase', 'route_warehouse0_buy')[1]
        except:
            buy_route_id = route_obj.search(cr, uid, [('name', 'like', _('Buy'))], context=context)
            buy_route_id = buy_route_id and buy_route_id[0] or False
        if not buy_route_id:
            raise UserError(_('Can\'t find any generic Buy route.'))

        return {
            'name': warehouse._format_routename(_(' Buy')),
            'location_id': warehouse.in_type_id.default_location_dest_id.id,
            'route_id': buy_route_id,
            'action': 'buy',
            'picking_type_id': warehouse.in_type_id.id,
            'warehouse_id': warehouse.id,
            'group_propagation_option': 'none',
        }

    def create_routes(self, cr, uid, ids, context=None):
        pull_obj = self.pool.get('procurement.rule')
        res = super(stock_warehouse, self).create_routes(cr, uid, ids, context=context)
        warehouse = self.browse(cr, uid, ids, context=context)[0]
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

    @api.multi
    def _get_all_routes(self):
        routes = super(stock_warehouse, self).get_all_routes_for_wh()
        routes |= self.filtered(lambda self: self.buy_to_resupply and self.buy_pull_id and self.buy_pull_id.route_id).mapped('buy_pull_id').mapped('route_id')
        return routes

    def _update_name_and_code(self, cr, uid, ids, name, code, context=None):
        res = super(stock_warehouse, self)._update_name_and_code(cr, uid, ids, name, code, context=context)
        warehouse = self.browse(cr, uid, ids[0], context=context)
        pull_obj = self.pool.get('procurement.rule')
        #change the buy procurement rule name
        if name and warehouse.buy_pull_id:
            pull_obj.write(cr, uid, warehouse.buy_pull_id.id, {'name': warehouse.buy_pull_id.name.replace(warehouse.name, name, 1)}, context=context)
        return res

    def _update_routes(self, cr, uid, ids, context=None):
        res = super(stock_warehouse, self)._update_routes(cr, uid, ids, context=context)
        for warehouse in self.browse(cr, uid, ids[0], context=context):
            if warehouse.in_type_id.default_location_dest_id != warehouse.buy_pull_id.location_id:
                self.pool.get('procurement.rule').write(cr, uid, warehouse.buy_pull_id.id, {'location_id': warehouse.in_type_id.default_location_dest_id.id}, context=context)
        return res
