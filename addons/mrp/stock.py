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

import time

from openerp.osv import fields
from openerp.osv import osv
from openerp.tools.translate import _
from openerp import SUPERUSER_ID
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT

class StockMove(osv.osv):
    _inherit = 'stock.move'

    _columns = {
        'production_id': fields.many2one('mrp.production', 'Production Order for Produced Products', select=True, copy=False),
        'raw_material_production_id': fields.many2one('mrp.production', 'Production Order for Raw Materials', select=True),
        'consumed_for': fields.many2one('stock.move', 'Consumed for', help='Technical field used to make the traceability of produced products'),
    }

    def check_tracking(self, cr, uid, move, lot_id, context=None):
        super(StockMove, self).check_tracking(cr, uid, move, lot_id, context=context)
        if move.product_id.track_production and (move.location_id.usage == 'production' or move.location_dest_id.usage == 'production') and not lot_id:
            raise osv.except_osv(_('Warning!'), _('You must assign a serial number for the product %s') % (move.product_id.name))
        if move.raw_material_production_id and move.location_dest_id.usage == 'production' and move.raw_material_production_id.product_id.track_production and not move.consumed_for:
            raise osv.except_osv(_('Warning!'), _("Because the product %s requires it, you must assign a serial number to your raw material %s to proceed further in your production. Please use the 'Produce' button to do so.") % (move.raw_material_production_id.product_id.name, move.product_id.name))

    def _check_phantom_bom(self, cr, uid, move, context=None):
        """check if product associated to move has a phantom bom
            return list of ids of mrp.bom for that product """
        user_company = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
        #doing the search as SUPERUSER because a user with the permission to write on a stock move should be able to explode it
        #without giving him the right to read the boms.
        domain = [
            '|', ('product_id', '=', move.product_id.id),
            '&', ('product_id', '=', False), ('product_tmpl_id.product_variant_ids', '=', move.product_id.id),
            ('type', '=', 'phantom'),
            '|', ('date_start', '=', False), ('date_start', '<=', time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)),
            '|', ('date_stop', '=', False), ('date_stop', '>=', time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)),
            ('company_id', '=', user_company)]
        return self.pool.get('mrp.bom').search(cr, SUPERUSER_ID, domain, context=context)

    def _action_explode(self, cr, uid, move, context=None):
        """ Explodes pickings.
        @param move: Stock moves
        @return: True
        """
        bom_obj = self.pool.get('mrp.bom')
        move_obj = self.pool.get('stock.move')
        to_explode_again_ids = []
        processed_ids = []
        bis = self._check_phantom_bom(cr, uid, move, context=context)
        if bis:
            factor = move.product_qty
            bom_point = bom_obj.browse(cr, SUPERUSER_ID, bis[0], context=context)
            res = bom_obj._bom_explode(cr, SUPERUSER_ID, bom_point, move.product_id, factor, [])
            state = 'confirmed'
            if move.state == 'assigned':
                state = 'assigned'
            for line in res[0]:
                valdef = {
                    'picking_id': move.picking_id.id if move.picking_id else False,
                    'product_id': line['product_id'],
                    'product_uom': line['product_uom'],
                    'product_uom_qty': line['product_qty'],
                    'product_uos': line['product_uos'],
                    'product_uos_qty': line['product_uos_qty'],
                    'state': state,
                    'name': line['name'],
                }
                mid = move_obj.copy(cr, uid, move.id, default=valdef)
                to_explode_again_ids.append(mid)

            #delete the move with original product which is not relevant anymore
            move_obj.unlink(cr, SUPERUSER_ID, [move.id], context=context)
            #check if new moves needs to be exploded
            if to_explode_again_ids:
                for new_move in self.browse(cr, uid, to_explode_again_ids, context=context):
                    processed_ids.extend(self._action_explode(cr, uid, new_move, context=context))
        #return list of newly created move or the move id otherwise
        return processed_ids or [move.id]

    def action_confirm(self, cr, uid, ids, context=None):
        move_ids = []
        for move in self.browse(cr, uid, ids, context=context):
            #in order to explode a move, we must have a picking_type_id on that move because otherwise the move
            #won't be assigned to a picking and it would be weird to explode a move into several if they aren't
            #all grouped in the same picking.
            if move.picking_type_id:
                move_ids.extend(self._action_explode(cr, uid, move, context=context))
            else:
                move_ids.append(move.id)

        #we go further with the list of ids potentially changed by action_explode
        return super(StockMove, self).action_confirm(cr, uid, move_ids, context=context)

    def action_consume(self, cr, uid, ids, product_qty, location_id=False, restrict_lot_id=False, restrict_partner_id=False,
                       consumed_for=False, context=None):
        """ Consumed product with specific quantity from specific source location.
        @param product_qty: Consumed product quantity
        @param location_id: Source location
        @param restrict_lot_id: optionnal parameter that allows to restrict the choice of quants on this specific lot
        @param restrict_partner_id: optionnal parameter that allows to restrict the choice of quants to this specific partner
        @param consumed_for: optionnal parameter given to this function to make the link between raw material consumed and produced product, for a better traceability
        @return: Consumed lines
        """
        if context is None:
            context = {}
        res = []
        production_obj = self.pool.get('mrp.production')
        uom_obj = self.pool.get('product.uom')

        if product_qty <= 0:
            raise osv.except_osv(_('Warning!'), _('Please provide proper quantity.'))
        #because of the action_confirm that can create extra moves in case of phantom bom, we need to make 2 loops
        ids2 = []
        for move in self.browse(cr, uid, ids, context=context):
            if move.state == 'draft':
                ids2.extend(self.action_confirm(cr, uid, [move.id], context=context))
            else:
                ids2.append(move.id)

        for move in self.browse(cr, uid, ids2, context=context):
            move_qty = move.product_qty
            uom_qty = uom_obj._compute_qty(cr, uid, move.product_id.uom_id.id, product_qty, move.product_uom.id)
            if move_qty <= 0:
                raise osv.except_osv(_('Error!'), _('Cannot consume a move with negative or zero quantity.'))
            quantity_rest = move.product_qty - uom_qty
            if quantity_rest > 0:
                ctx = context.copy()
                if location_id:
                    ctx['source_location_id'] = location_id
                new_mov = self.split(cr, uid, move, move_qty - quantity_rest, restrict_lot_id=restrict_lot_id, restrict_partner_id=restrict_partner_id, context=ctx)
                self.write(cr, uid, new_mov, {'consumed_for': consumed_for}, context=context)
                res.append(new_mov)
            else:
                res.append(move.id)
                if location_id:
                    self.write(cr, uid, [move.id], {'location_id': location_id, 'restrict_lot_id': restrict_lot_id,
                                                    'restrict_partner_id': restrict_partner_id,
                                                    'consumed_for': consumed_for}, context=context)
            self.action_done(cr, uid, res, context=context)
            production_ids = production_obj.search(cr, uid, [('move_lines', 'in', [move.id])])
            production_obj.signal_button_produce(cr, uid, production_ids)
            for new_move in res:
                if new_move != move.id:
                    #This move is not already there in move lines of production order
                    production_obj.write(cr, uid, production_ids, {'move_lines': [(4, new_move)]})
        return res

    def action_scrap(self, cr, uid, ids, product_qty, location_id, restrict_lot_id=False, restrict_partner_id=False, context=None):
        """ Move the scrap/damaged product into scrap location
        @param product_qty: Scraped product quantity
        @param location_id: Scrap location
        @return: Scraped lines
        """
        res = []
        production_obj = self.pool.get('mrp.production')
        for move in self.browse(cr, uid, ids, context=context):
            new_moves = super(StockMove, self).action_scrap(cr, uid, [move.id], product_qty, location_id,
                                                            restrict_lot_id=restrict_lot_id,
                                                            restrict_partner_id=restrict_partner_id, context=context)
            #If we are not scrapping our whole move, tracking and lot references must not be removed
            production_ids = production_obj.search(cr, uid, [('move_lines', 'in', [move.id])])
            for prod_id in production_ids:
                production_obj.signal_button_produce(cr, uid, [prod_id])
            for new_move in new_moves:
                production_obj.write(cr, uid, production_ids, {'move_lines': [(4, new_move)]})
                res.append(new_move)
        return res

    def write(self, cr, uid, ids, vals, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        res = super(StockMove, self).write(cr, uid, ids, vals, context=context)
        from openerp import workflow
        for move in self.browse(cr, uid, ids, context=context):
            if move.raw_material_production_id and move.raw_material_production_id.state == 'confirmed':
                workflow.trg_trigger(uid, 'stock.move', move.id, cr)
        return res

class stock_warehouse(osv.osv):
    _inherit = 'stock.warehouse'
    _columns = {
        'manufacture_to_resupply': fields.boolean('Manufacture in this Warehouse', 
                                                  help="When products are manufactured, they can be manufactured in this warehouse."),
        'manufacture_pull_id': fields.many2one('procurement.rule', 'Manufacture Rule'),
    }

    def _get_manufacture_pull_rule(self, cr, uid, warehouse, context=None):
        route_obj = self.pool.get('stock.location.route')
        data_obj = self.pool.get('ir.model.data')
        try:
            manufacture_route_id = data_obj.get_object_reference(cr, uid, 'stock', 'route_warehouse0_manufacture')[1]
        except:
            manufacture_route_id = route_obj.search(cr, uid, [('name', 'like', _('Manufacture'))], context=context)
            manufacture_route_id = manufacture_route_id and manufacture_route_id[0] or False
        if not manufacture_route_id:
            raise osv.except_osv(_('Error!'), _('Can\'t find any generic Manufacture route.'))

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
        #change the manufacture pull rule name
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
