# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime
from dateutil import relativedelta
import json
import time
import sets

import openerp
from openerp.osv import fields, osv
from openerp.tools.float_utils import float_compare, float_round
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from openerp import SUPERUSER_ID, api, models
import openerp.addons.decimal_precision as dp
from openerp.addons.procurement import procurement
import logging
from openerp.exceptions import UserError

class stock_picking(models.Model):
    _inherit = "stock.picking"

    def create(self, cr, user, vals, context=None):
        context = context or {}
        if ('name' not in vals) or (vals.get('name') in ('/', False)):
            ptype_id = vals.get('picking_type_id', context.get('default_picking_type_id', False))
            sequence_id = self.pool.get('stock.picking.type').browse(cr, user, ptype_id, context=context).sequence_id.id
            vals['name'] = self.pool.get('ir.sequence').next_by_id(cr, user, sequence_id, context=context)
        # As the on_change in one2many list is WIP, we will overwrite the locations on the stock moves here
        # As it is a create the format will be a list of (0, 0, dict)
        if vals.get('move_lines') and vals.get('location_id') and vals.get('location_dest_id'):
            for move in vals['move_lines']:
                if len(move) == 3:
                    move[2]['location_id'] = vals['location_id']
                    move[2]['location_dest_id'] = vals['location_dest_id']
        return super(stock_picking, self).create(cr, user, vals, context)

    def write(self, cr, uid, ids, vals, context=None):
        res = super(stock_picking, self).write(cr, uid, ids, vals, context=context)
        after_vals = {}
        if vals.get('location_id'):
            after_vals['location_id'] = vals['location_id']
        if vals.get('location_dest_id'):
            after_vals['location_dest_id'] = vals['location_dest_id']
        # Change locations of moves if those of the picking change
        if after_vals:
            moves = []
            for pick in self.browse(cr, uid, ids, context=context):
                moves += [x.id for x in pick.move_lines if not x.scrapped]
            if moves:
                self.pool['stock.move'].write(cr, uid, moves, after_vals, context=context)
        return res

    def _state_get(self, cr, uid, ids, field_name, arg, context=None):
        '''The state of a picking depends on the state of its related stock.move
            draft: the picking has no line or any one of the lines is draft
            done, draft, cancel: all lines are done / draft / cancel
            confirmed, waiting, assigned, partially_available depends on move_type (all at once or partial)
        '''
        res = {}
        for pick in self.browse(cr, uid, ids, context=context):
            if not pick.move_lines:
                res[pick.id] = pick.launch_pack_operations and 'assigned' or 'draft'
                continue
            if any([x.state == 'draft' for x in pick.move_lines]):
                res[pick.id] = 'draft'
                continue
            if all([x.state == 'cancel' for x in pick.move_lines]):
                res[pick.id] = 'cancel'
                continue
            if all([x.state in ('cancel', 'done') for x in pick.move_lines]):
                res[pick.id] = 'done'
                continue

            order = {'confirmed': 0, 'waiting': 1, 'assigned': 2}
            order_inv = {0: 'confirmed', 1: 'waiting', 2: 'assigned'}
            lst = [order[x.state] for x in pick.move_lines if x.state not in ('cancel', 'done')]
            if pick.move_type == 'one':
                res[pick.id] = order_inv[min(lst)]
            else:
                #we are in the case of partial delivery, so if all move are assigned, picking
                #should be assign too, else if one of the move is assigned, or partially available, picking should be
                #in partially available state, otherwise, picking is in waiting or confirmed state
                res[pick.id] = order_inv[max(lst)]
                if not all(x == 2 for x in lst):
                    if any(x == 2 for x in lst):
                        res[pick.id] = 'partially_available'
                    else:
                        #if all moves aren't assigned, check if we have one product partially available
                        for move in pick.move_lines:
                            if move.partially_available:
                                res[pick.id] = 'partially_available'
                                break
        return res

    def _get_pickings(self, cr, uid, ids, context=None):
        res = set()
        for move in self.browse(cr, uid, ids, context=context):
            if move.picking_id:
                res.add(move.picking_id.id)
        return list(res)

    def _get_pickings_dates_priority(self, cr, uid, ids, context=None):
        res = set()
        for move in self.browse(cr, uid, ids, context=context):
            if move.picking_id and (not (move.picking_id.min_date < move.date_expected < move.picking_id.max_date) or move.priority > move.picking_id.priority):
                res.add(move.picking_id.id)
        return list(res)

    def action_assign_owner(self, cr, uid, ids, context=None):
        for picking in self.browse(cr, uid, ids, context=context):
            packop_ids = [op.id for op in picking.pack_operation_ids]
            self.pool.get('stock.pack.operation').write(cr, uid, packop_ids, {'owner_id': picking.owner_id.id}, context=context)

    def onchange_picking_type(self, cr, uid, ids, picking_type_id, partner_id):
        res = {}
        if picking_type_id:
            picking_type = self.pool['stock.picking.type'].browse(cr, uid, picking_type_id)
            if not picking_type.default_location_src_id and partner_id:
                partner = self.pool['res.partner'].browse(cr, uid, partner_id)
                location_id = partner.property_stock_supplier.id
            else:
                location_id = picking_type.default_location_src_id.id

            if not picking_type.default_location_dest_id and partner_id:
                partner = self.pool['res.partner'].browse(cr, uid, partner_id)
                location_dest_id = partner.property_stock_customer.id
            else:
                location_dest_id = picking_type.default_location_dest_id.id

            res['value'] = {'location_id': location_id,
                            'location_dest_id': location_dest_id,}
        return res

    _columns = {
        'state': fields.function(_state_get, type="selection", copy=False,
            store={
                'stock.picking': (lambda self, cr, uid, ids, ctx: ids, ['move_type', 'launch_pack_operations'], 20),
                'stock.move': (_get_pickings, ['state', 'picking_id', 'partially_available'], 20)},
            selection=[
                ('draft', 'Draft'),
                ('cancel', 'Cancelled'),
                ('waiting', 'Waiting Another Operation'),
                ('confirmed', 'Waiting Availability'),
                ('partially_available', 'Partially Available'),
                ('assigned', 'Available'),
                ('done', 'Done'),
                ], string='Status', readonly=True, select=True, track_visibility='onchange',
            help="""
                * Draft: not confirmed yet and will not be scheduled until confirmed\n
                * Waiting Another Operation: waiting for another move to proceed before it becomes automatically available (e.g. in Make-To-Order flows)\n
                * Waiting Availability: still waiting for the availability of products\n
                * Partially Available: some products are available and reserved\n
                * Ready to Transfer: products reserved, simply waiting for confirmation.\n
                * Transferred: has been processed, can't be modified or cancelled anymore\n
                * Cancelled: has been cancelled, can't be confirmed anymore"""
        ),
        'group_id': fields.related('move_lines', 'group_id', type='many2one', relation='procurement.group', string='Procurement Group', readonly=True,
              store={
                  'stock.picking': (lambda self, cr, uid, ids, ctx: ids, ['move_lines'], 10),
                  'stock.move': (_get_pickings, ['group_id', 'picking_id'], 10),
              }),
    }

    _defaults = {
        'state': 'draft',
    }

    def do_print_picking(self, cr, uid, ids, context=None):
        '''This function prints the picking list'''
        context = dict(context or {}, active_ids=ids)
        return self.pool.get("report").get_action(cr, uid, ids, 'stock.report_picking', context=context)

    def launch_packops(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'launch_pack_operations': True}, context=context)

    def action_confirm(self, cr, uid, ids, context=None):
        todo = []
        todo_force_assign = []
        for picking in self.browse(cr, uid, ids, context=context):
            if not picking.move_lines:
                self.launch_packops(cr, uid, [picking.id], context=context)
            if picking.location_id.usage in ('supplier', 'inventory', 'production'):
                todo_force_assign.append(picking.id)
            for r in picking.move_lines:
                if r.state == 'draft':
                    todo.append(r.id)
        if len(todo):
            self.pool.get('stock.move').action_confirm(cr, uid, todo, context=context)

        if todo_force_assign:
            self.force_assign(cr, uid, todo_force_assign, context=context)
        return True

    def action_assign(self, cr, uid, ids, context=None):
        """ Check availability of picking moves.
        This has the effect of changing the state and reserve quants on available moves, and may
        also impact the state of the picking as it is computed based on move's states.
        @return: True
        """
        for pick in self.browse(cr, uid, ids, context=context):
            if pick.state == 'draft':
                self.action_confirm(cr, uid, [pick.id], context=context)
            #skip the moves that don't need to be checked
            move_ids = [x.id for x in pick.move_lines if x.state not in ('draft', 'cancel', 'done')]
            if not move_ids:
                raise UserError(_('Nothing to check the availability for.'))
            self.pool.get('stock.move').action_assign(cr, uid, move_ids, context=context)
        return True

    def force_assign(self, cr, uid, ids, context=None):
        """ Changes state of picking to available if moves are confirmed or waiting.
        @return: True
        """
        pickings = self.browse(cr, uid, ids, context=context)
        for pick in pickings:
            move_ids = [x.id for x in pick.move_lines if x.state in ['confirmed', 'waiting']]
            self.pool.get('stock.move').force_assign(cr, uid, move_ids, context=context)
        return True

    def action_cancel(self, cr, uid, ids, context=None):
        for pick in self.browse(cr, uid, ids, context=context):
            ids2 = [move.id for move in pick.move_lines]
            self.pool.get('stock.move').action_cancel(cr, uid, ids2, context)
        return True

    def action_done(self, cr, uid, ids, context=None):
        """Changes picking state to done by processing the Stock Moves of the Picking

        Normally that happens when the button "Done" is pressed on a Picking view.
        @return: True
        """
        for pick in self.browse(cr, uid, ids, context=context):
            todo = []
            for move in pick.move_lines:
                if move.state == 'draft':
                    todo.extend(self.pool.get('stock.move').action_confirm(cr, uid, [move.id], context=context))
                elif move.state in ('assigned', 'confirmed'):
                    todo.append(move.id)
            if len(todo):
                self.pool.get('stock.move').action_done(cr, uid, todo, context=context)
        return True

    def unlink(self, cr, uid, ids, context=None):
        #on picking deletion, cancel its move then unlink them too
        move_obj = self.pool.get('stock.move')
        context = context or {}
        for pick in self.browse(cr, uid, ids, context=context):
            move_ids = [move.id for move in pick.move_lines]
            move_obj.action_cancel(cr, uid, move_ids, context=context)
            move_obj.unlink(cr, uid, move_ids, context=context)
        return super(stock_picking, self).unlink(cr, uid, ids, context=context)

    def _create_backorder(self, cr, uid, picking, backorder_moves=[], context=None):
        """ Move all non-done lines into a new backorder picking. If the key 'do_only_split' is given in the context, then move all lines not in context.get('split', []) instead of all non-done lines.
        """
        if not backorder_moves:
            backorder_moves = picking.move_lines
        backorder_move_ids = [x.id for x in backorder_moves if x.state not in ('done', 'cancel')]
        if 'do_only_split' in context and context['do_only_split']:
            backorder_move_ids = [x.id for x in backorder_moves if x.id not in context.get('split', [])]

        if backorder_move_ids:
            backorder_id = self.copy(cr, uid, picking.id, {
                'name': '/',
                'move_lines': [],
                'pack_operation_ids': [],
                'backorder_id': picking.id,
            })
            backorder = self.browse(cr, uid, backorder_id, context=context)
            self.message_post(cr, uid, picking.id, body=_("Back order <em>%s</em> <b>created</b>.") % (backorder.name), context=context)
            move_obj = self.pool.get("stock.move")
            move_obj.write(cr, uid, backorder_move_ids, {'picking_id': backorder_id}, context=context)

            if not picking.date_done:
                self.write(cr, uid, [picking.id], {'date_done': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)}, context=context)
            self.action_confirm(cr, uid, [backorder_id], context=context)
            self.action_assign(cr, uid, [backorder_id], context=context)
            return backorder_id
        return False

    @api.cr_uid_ids_context
    def recheck_availability(self, cr, uid, picking_ids, context=None):
        self.action_assign(cr, uid, picking_ids, context=context)
        self.do_prepare_partial(cr, uid, picking_ids, context=context)

    def _get_top_level_packages(self, cr, uid, quants_suggested_locations, context=None):
        """This method searches for the higher level packages that can be moved as a single operation, given a list of quants
           to move and their suggested destination, and returns the list of matching packages.
        """
        # Try to find as much as possible top-level packages that can be moved
        pack_obj = self.pool.get("stock.quant.package")
        quant_obj = self.pool.get("stock.quant")
        top_lvl_packages = set()
        quants_to_compare = quants_suggested_locations.keys()
        for pack in list(set([x.package_id for x in quants_suggested_locations.keys() if x and x.package_id])):
            loop = True
            test_pack = pack
            good_pack = False
            pack_destination = False
            while loop:
                pack_quants = pack_obj.get_content(cr, uid, [test_pack.id], context=context)
                all_in = True
                for quant in quant_obj.browse(cr, uid, pack_quants, context=context):
                    # If the quant is not in the quants to compare and not in the common location
                    if not quant in quants_to_compare:
                        all_in = False
                        break
                    else:
                        #if putaway strat apply, the destination location of each quant may be different (and thus the package should not be taken as a single operation)
                        if not pack_destination:
                            pack_destination = quants_suggested_locations[quant]
                        elif pack_destination != quants_suggested_locations[quant]:
                            all_in = False
                            break
                if all_in:
                    good_pack = test_pack
                    if test_pack.parent_id:
                        test_pack = test_pack.parent_id
                    else:
                        #stop the loop when there's no parent package anymore
                        loop = False
                else:
                    #stop the loop when the package test_pack is not totally reserved for moves of this picking
                    #(some quants may be reserved for other picking or not reserved at all)
                    loop = False
            if good_pack:
                top_lvl_packages.add(good_pack)
        return list(top_lvl_packages)

    def _prepare_pack_ops(self, cr, uid, picking, quants, forced_qties, context=None):
        """ returns a list of dict, ready to be used in create() of stock.pack.operation.

        :param picking: browse record (stock.picking)
        :param quants: browse record list (stock.quant). List of quants associated to the picking
        :param forced_qties: dictionary showing for each product (keys) its corresponding quantity (value) that is not covered by the quants associated to the picking
        """
        def _picking_putaway_apply(product):
            location = False
            # Search putaway strategy
            if product_putaway_strats.get(product.id):
                location = product_putaway_strats[product.id]
            else:
                location = self.pool.get('stock.location').get_putaway_strategy(cr, uid, picking.location_dest_id, product, context=context)
                product_putaway_strats[product.id] = location
            return location or picking.location_dest_id.id

        # If we encounter an UoM that is smaller than the default UoM or the one already chosen, use the new one instead.
        product_uom = {} # Determines UoM used in pack operations
        location_dest_id = None
        location_id = None
        for move in [x for x in picking.move_lines if x.state not in ('done', 'cancel')]:
            if not product_uom.get(move.product_id.id):
                product_uom[move.product_id.id] = move.product_id.uom_id
            if move.product_uom.id != move.product_id.uom_id.id and move.product_uom.factor > product_uom[move.product_id.id].factor:
                product_uom[move.product_id.id] = move.product_uom
            if not move.scrapped:
                if location_dest_id and move.location_dest_id.id != location_dest_id:
                    raise UserError(_('The destination location must be the same for all the moves of the picking.'))
                location_dest_id = move.location_dest_id.id
                if location_id and move.location_id.id != location_id:
                    raise UserError(_('The source location must be the same for all the moves of the picking.'))
                location_id = move.location_id.id

        pack_obj = self.pool.get("stock.quant.package")
        quant_obj = self.pool.get("stock.quant")
        vals = []
        qtys_grouped = {}
        lots_grouped = {}
        #for each quant of the picking, find the suggested location
        quants_suggested_locations = {}
        product_putaway_strats = {}
        for quant in quants:
            if quant.qty <= 0:
                continue
            suggested_location_id = _picking_putaway_apply(quant.product_id)
            quants_suggested_locations[quant] = suggested_location_id

        #find the packages we can movei as a whole
        top_lvl_packages = self._get_top_level_packages(cr, uid, quants_suggested_locations, context=context)
        # and then create pack operations for the top-level packages found
        for pack in top_lvl_packages:
            pack_quant_ids = pack_obj.get_content(cr, uid, [pack.id], context=context)
            pack_quants = quant_obj.browse(cr, uid, pack_quant_ids, context=context)
            vals.append({
                    'picking_id': picking.id,
                    'package_id': pack.id,
                    'product_qty': 1.0,
                    'location_id': pack.location_id.id,
                    'location_dest_id': quants_suggested_locations[pack_quants[0]],
                    'owner_id': pack.owner_id.id,
                })
            #remove the quants inside the package so that they are excluded from the rest of the computation
            for quant in pack_quants:
                del quants_suggested_locations[quant]
        # Go through all remaining reserved quants and group by product, package, owner, source location and dest location
        # Lots will go into pack operation lot object
        for quant, dest_location_id in quants_suggested_locations.items():
            key = (quant.product_id.id, quant.package_id.id, quant.owner_id.id, quant.location_id.id, dest_location_id)
            if qtys_grouped.get(key):
                qtys_grouped[key] += quant.qty
            else:
                qtys_grouped[key] = quant.qty
            if quant.product_id.tracking != 'none' and quant.lot_id:
                lots_grouped.setdefault(key, {}).setdefault(quant.lot_id.id, 0.0)
                lots_grouped[key][quant.lot_id.id] += quant.qty

        # Do the same for the forced quantities (in cases of force_assign or incomming shipment for example)
        for product, qty in forced_qties.items():
            if qty <= 0:
                continue
            suggested_location_id = _picking_putaway_apply(product)
            key = (product.id, False, picking.owner_id.id, picking.location_id.id, suggested_location_id)
            if qtys_grouped.get(key):
                qtys_grouped[key] += qty
            else:
                qtys_grouped[key] = qty

        # Create the necessary operations for the grouped quants and remaining qtys
        uom_obj = self.pool.get('product.uom')
        prevals = {}
        for key, qty in qtys_grouped.items():
            product = self.pool.get("product.product").browse(cr, uid, key[0], context=context)
            uom_id = product.uom_id.id
            qty_uom = qty
            if product_uom.get(key[0]):
                uom_id = product_uom[key[0]].id
                qty_uom = uom_obj._compute_qty(cr, uid, product.uom_id.id, qty, uom_id)
            pack_lot_ids = []
            if lots_grouped.get(key):
                for lot in lots_grouped[key].keys():
                    pack_lot_ids += [(0, 0, {'lot_id': lot, 'qty': 0.0, 'qty_todo': lots_grouped[key][lot]})]
            val_dict = {
                'picking_id': picking.id,
                'product_qty': qty_uom,
                'product_id': key[0],
                'package_id': key[1],
                'owner_id': key[2],
                'location_id': key[3],
                'location_dest_id': key[4],
                'product_uom_id': uom_id,
                'pack_lot_ids': pack_lot_ids,
            }
            if key[0] in prevals:
                prevals[key[0]].append(val_dict)
            else:
                prevals[key[0]] = [val_dict]
        # prevals var holds the operations in order to create them in the same order than the picking stock moves if possible
        processed_products = set()
        for move in [x for x in picking.move_lines if x.state not in ('done', 'cancel')]:
            if move.product_id.id not in processed_products:
                vals += prevals.get(move.product_id.id, [])
                processed_products.add(move.product_id.id)
        return vals

    @api.cr_uid_ids_context
    def do_prepare_partial(self, cr, uid, picking_ids, context=None):
        context = context or {}
        pack_operation_obj = self.pool.get('stock.pack.operation')

        #get list of existing operations and delete them
        existing_package_ids = pack_operation_obj.search(cr, uid, [('picking_id', 'in', picking_ids)], context=context)
        if existing_package_ids:
            pack_operation_obj.unlink(cr, uid, existing_package_ids, context)
        for picking in self.browse(cr, uid, picking_ids, context=context):
            forced_qties = {}  # Quantity remaining after calculating reserved quants
            picking_quants = []
            #Calculate packages, reserved quants, qtys of this picking's moves
            for move in picking.move_lines:
                if move.state not in ('assigned', 'confirmed', 'waiting'):
                    continue
                move_quants = move.reserved_quant_ids
                picking_quants += move_quants
                forced_qty = (move.state == 'assigned') and move.product_qty - sum([x.qty for x in move_quants]) or 0
                #if we used force_assign() on the move, or if the move is incoming, forced_qty > 0
                if float_compare(forced_qty, 0, precision_rounding=move.product_id.uom_id.rounding) > 0:
                    if forced_qties.get(move.product_id):
                        forced_qties[move.product_id] += forced_qty
                    else:
                        forced_qties[move.product_id] = forced_qty
            for vals in self._prepare_pack_ops(cr, uid, picking, picking_quants, forced_qties, context=context):
                vals['fresh_record'] = False
                pack_operation_obj.create(cr, uid, vals, context=context)
        #recompute the remaining quantities all at once
        self.do_recompute_remaining_quantities(cr, uid, picking_ids, context=context)
        self.write(cr, uid, picking_ids, {'recompute_pack_op': False}, context=context)

    @api.cr_uid_ids_context
    def do_unreserve(self, cr, uid, picking_ids, context=None):
        """
          Will remove all quants for picking in picking_ids
        """
        moves_to_unreserve = []
        pack_line_to_unreserve = []
        for picking in self.browse(cr, uid, picking_ids, context=context):
            moves_to_unreserve += [m.id for m in picking.move_lines if m.state not in ('done', 'cancel')]
            pack_line_to_unreserve += [p.id for p in picking.pack_operation_ids]
        if moves_to_unreserve:
            if pack_line_to_unreserve:
                self.pool.get('stock.pack.operation').unlink(cr, uid, pack_line_to_unreserve, context=context)
            self.pool.get('stock.move').do_unreserve(cr, uid, moves_to_unreserve, context=context)

    def recompute_remaining_qty(self, cr, uid, picking, done_qtys=False, context=None):
        def _create_link_for_index(operation_id, index, product_id, qty_to_assign, quant_id=False):
            move_dict = prod2move_ids[product_id][index]
            qty_on_link = min(move_dict['remaining_qty'], qty_to_assign)
            self.pool.get('stock.move.operation.link').create(cr, uid, {'move_id': move_dict['move'].id, 'operation_id': operation_id, 'qty': qty_on_link, 'reserved_quant_id': quant_id}, context=context)
            if move_dict['remaining_qty'] == qty_on_link:
                prod2move_ids[product_id].pop(index)
            else:
                move_dict['remaining_qty'] -= qty_on_link
            return qty_on_link

        def _create_link_for_quant(operation_id, quant, qty):
            """create a link for given operation and reserved move of given quant, for the max quantity possible, and returns this quantity"""
            if not quant.reservation_id.id:
                return _create_link_for_product(operation_id, quant.product_id.id, qty)
            qty_on_link = 0
            for i in range(0, len(prod2move_ids[quant.product_id.id])):
                if prod2move_ids[quant.product_id.id][i]['move'].id != quant.reservation_id.id:
                    continue
                qty_on_link = _create_link_for_index(operation_id, i, quant.product_id.id, qty, quant_id=quant.id)
                break
            return qty_on_link

        def _create_link_for_product(operation_id, product_id, qty):
            '''method that creates the link between a given operation and move(s) of given product, for the given quantity.
            Returns True if it was possible to create links for the requested quantity (False if there was not enough quantity on stock moves)'''
            qty_to_assign = qty
            prod_obj = self.pool.get("product.product")
            product = prod_obj.browse(cr, uid, product_id)
            rounding = product.uom_id.rounding
            qtyassign_cmp = float_compare(qty_to_assign, 0.0, precision_rounding=rounding)
            if prod2move_ids.get(product_id):
                while prod2move_ids[product_id] and qtyassign_cmp > 0:
                    qty_on_link = _create_link_for_index(operation_id, 0, product_id, qty_to_assign, quant_id=False)
                    qty_to_assign -= qty_on_link
                    qtyassign_cmp = float_compare(qty_to_assign, 0.0, precision_rounding=rounding)
            return qtyassign_cmp == 0

        uom_obj = self.pool.get('product.uom')
        package_obj = self.pool.get('stock.quant.package')
        quant_obj = self.pool.get('stock.quant')
        link_obj = self.pool.get('stock.move.operation.link')
        quants_in_package_done = set()
        prod2move_ids = {}
        still_to_do = []
        #make a dictionary giving for each product, the moves and related quantity that can be used in operation links
        for move in [x for x in picking.move_lines if x.state not in ('done', 'cancel')]:
            if not prod2move_ids.get(move.product_id.id):
                prod2move_ids[move.product_id.id] = [{'move': move, 'remaining_qty': move.product_qty}]
            else:
                prod2move_ids[move.product_id.id].append({'move': move, 'remaining_qty': move.product_qty})

        need_rereserve = False
        #sort the operations in order to give higher priority to those with a package, then a serial number
        operations = picking.pack_operation_ids
        operations = sorted(operations, key=lambda x: ((x.package_id and not x.product_id) and -4 or 0) + (x.package_id and -2 or 0) + (x.pack_lot_ids and -1 or 0))
        #delete existing operations to start again from scratch
        links = link_obj.search(cr, uid, [('operation_id', 'in', [x.id for x in operations])], context=context)
        if links:
            link_obj.unlink(cr, uid, links, context=context)
        #1) first, try to create links when quants can be identified without any doubt
        for ops in operations:
            lot_qty = {}
            for packlot in ops.pack_lot_ids:
                lot_qty[packlot.lot_id.id] = uom_obj._compute_qty(cr, uid, ops.product_uom_id.id, packlot.qty, ops.product_id.uom_id.id)
            #for each operation, create the links with the stock move by seeking on the matching reserved quants,
            #and deffer the operation if there is some ambiguity on the move to select
            if ops.package_id and not ops.product_id and (not done_qtys or ops.qty_done):
                #entire package
                quant_ids = package_obj.get_content(cr, uid, [ops.package_id.id], context=context)
                for quant in quant_obj.browse(cr, uid, quant_ids, context=context):
                    remaining_qty_on_quant = quant.qty
                    if quant.reservation_id:
                        #avoid quants being counted twice
                        quants_in_package_done.add(quant.id)
                        qty_on_link = _create_link_for_quant(ops.id, quant, quant.qty)
                        remaining_qty_on_quant -= qty_on_link
                    if remaining_qty_on_quant:
                        still_to_do.append((ops, quant.product_id.id, remaining_qty_on_quant))
                        need_rereserve = True
            elif ops.product_id.id:
                #Check moves with same product
                product_qty = ops.qty_done if done_qtys else ops.product_qty
                qty_to_assign = uom_obj._compute_qty_obj(cr, uid, ops.product_uom_id, product_qty, ops.product_id.uom_id, context=context)
                for move_dict in prod2move_ids.get(ops.product_id.id, []):
                    move = move_dict['move']
                    for quant in move.reserved_quant_ids:
                        if not qty_to_assign > 0:
                            break
                        if quant.id in quants_in_package_done:
                            continue

                        #check if the quant is matching the operation details
                        if ops.package_id:
                            flag = quant.package_id and bool(package_obj.search(cr, uid, [('id', 'child_of', [ops.package_id.id])], context=context)) or False
                        else:
                            flag = not quant.package_id.id
                        flag = flag and (ops.owner_id.id == quant.owner_id.id)
                        if flag:
                            if not lot_qty:
                                max_qty_on_link = min(quant.qty, qty_to_assign)
                                qty_on_link = _create_link_for_quant(ops.id, quant, max_qty_on_link)
                                qty_to_assign -= qty_on_link
                            else:
                                if lot_qty.get(quant.lot_id.id): #if there is still some qty left
                                    max_qty_on_link = min(quant.qty, qty_to_assign, lot_qty[quant.lot_id.id])
                                    qty_on_link = _create_link_for_quant(ops.id, quant, max_qty_on_link)
                                    qty_to_assign -= qty_on_link
                                    lot_qty[quant.lot_id.id] -= qty_on_link

                qty_assign_cmp = float_compare(qty_to_assign, 0, precision_rounding=ops.product_id.uom_id.rounding)
                if qty_assign_cmp > 0:
                    #qty reserved is less than qty put in operations. We need to create a link but it's deferred after we processed
                    #all the quants (because they leave no choice on their related move and needs to be processed with higher priority)
                    still_to_do += [(ops, ops.product_id.id, qty_to_assign)]
                    need_rereserve = True

        #2) then, process the remaining part
        all_op_processed = True
        for ops, product_id, remaining_qty in still_to_do:
            all_op_processed = _create_link_for_product(ops.id, product_id, remaining_qty) and all_op_processed
        return (need_rereserve, all_op_processed)

    def picking_recompute_remaining_quantities(self, cr, uid, picking, done_qtys=False, context=None):
        need_rereserve = False
        all_op_processed = True
        if picking.pack_operation_ids:
            need_rereserve, all_op_processed = self.recompute_remaining_qty(cr, uid, picking, done_qtys=done_qtys, context=context)
        return need_rereserve, all_op_processed

    @api.cr_uid_ids_context
    def do_recompute_remaining_quantities(self, cr, uid, picking_ids, done_qtys=False, context=None):
        for picking in self.browse(cr, uid, picking_ids, context=context):
            if picking.pack_operation_ids:
                self.recompute_remaining_qty(cr, uid, picking, done_qtys=done_qtys, context=context)

    def _prepare_values_extra_move(self, cr, uid, op, product, remaining_qty, context=None):
        """
        Creates an extra move when there is no corresponding original move to be copied
        """
        uom_obj = self.pool.get("product.uom")
        uom_id = product.uom_id.id
        qty = remaining_qty
        if op.product_id and op.product_uom_id and op.product_uom_id.id != product.uom_id.id:
            if op.product_uom_id.factor > product.uom_id.factor: #If the pack operation's is a smaller unit
                uom_id = op.product_uom_id.id
                #HALF-UP rounding as only rounding errors will be because of propagation of error from default UoM
                qty = uom_obj._compute_qty_obj(cr, uid, product.uom_id, remaining_qty, op.product_uom_id, rounding_method='HALF-UP')
        picking = op.picking_id
        ref = product.default_code
        name = '[' + ref + ']' + ' ' + product.name if ref else product.name
        res = {
            'picking_id': picking.id,
            'location_id': picking.location_id.id,
            'location_dest_id': picking.location_dest_id.id,
            'product_id': product.id,
            'product_uom': uom_id,
            'product_uom_qty': qty,
            'name': _('Extra Move: ') + name,
            'state': 'draft',
            'restrict_partner_id': op.owner_id,
            'group_id': picking.group_id.id,
            }
        return res

    def _create_extra_moves(self, cr, uid, picking, context=None):
        '''This function creates move lines on a picking, at the time of do_transfer, based on
        unexpected product transfers (or exceeding quantities) found in the pack operations.
        '''
        move_obj = self.pool.get('stock.move')
        operation_obj = self.pool.get('stock.pack.operation')
        moves = []
        for op in picking.pack_operation_ids:
            for product_id, remaining_qty in operation_obj._get_remaining_prod_quantities(cr, uid, op, context=context).items():
                product = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
                if float_compare(remaining_qty, 0, precision_rounding=product.uom_id.rounding) > 0:
                    vals = self._prepare_values_extra_move(cr, uid, op, product, remaining_qty, context=context)
                    moves.append(move_obj.create(cr, uid, vals, context=context))
        if moves:
            move_obj.action_confirm(cr, uid, moves, context=context)
        return moves

    def rereserve_pick(self, cr, uid, ids, context=None):
        """
        This can be used to provide a button that rereserves taking into account the existing pack operations
        """
        for pick in self.browse(cr, uid, ids, context=context):
            self.rereserve_quants(cr, uid, pick, move_ids = [x.id for x in pick.move_lines], context=context)

    def rereserve_quants(self, cr, uid, picking, move_ids=[], context=None):
        """ Unreserve quants then try to reassign quants."""
        stock_move_obj = self.pool.get('stock.move')
        if not move_ids:
            self.do_unreserve(cr, uid, [picking.id], context=context)
            self.action_assign(cr, uid, [picking.id], context=context)
        else:
            stock_move_obj.do_unreserve(cr, uid, move_ids, context=context)
            stock_move_obj.action_assign(cr, uid, move_ids, no_prepare=True, context=context)

    def do_new_transfer(self, cr, uid, ids, context=None):
        pack_op_obj = self.pool['stock.pack.operation']
        data_obj = self.pool['ir.model.data']
        for pick in self.browse(cr, uid, ids, context=context):
            to_delete = []
            if not pick.move_lines and not pick.pack_operation_ids:
                raise UserError(_('Please create some Initial Demand or Mark as Todo and create some Operations. '))
            # In draft or with no pack operations edited yet, ask if we can just do everything
            if pick.state == 'draft' or all([x.qty_done == 0.0 for x in pick.pack_operation_ids]):
                # If no lots when needed, raise error
                picking_type = pick.picking_type_id
                if (picking_type.use_create_lots or picking_type.use_existing_lots):
                    for pack in pick.pack_operation_ids:
                        if pack.product_id and pack.product_id.tracking != 'none':
                            raise UserError(_('Some products require lots, so you need to specify those first!'))

                view = data_obj.xmlid_to_res_id(cr, uid, 'stock.view_immediate_transfer')
                wiz_id = self.pool['stock.immediate.transfer'].create(cr, uid, {'pick_id': pick.id}, context=context)
                return {
                     'name': _('Immediate Transfer?'),
                     'type': 'ir.actions.act_window',
                     'view_type': 'form',
                     'view_mode': 'form',
                     'res_model': 'stock.immediate.transfer',
                     'views': [(view, 'form')],
                     'view_id': view,
                     'target': 'new',
                     'res_id': wiz_id,
                     'context': context,
                 }

            # Check backorder should check for other barcodes
            if self.check_backorder(cr, uid, pick, context=context):
                view = data_obj.xmlid_to_res_id(cr, uid, 'stock.view_backorder_confirmation')
                wiz_id = self.pool['stock.backorder.confirmation'].create(cr, uid, {'pick_id': pick.id}, context=context)
                return {
                         'name': _('Create Backorder?'),
                         'type': 'ir.actions.act_window',
                         'view_type': 'form',
                         'view_mode': 'form',
                         'res_model': 'stock.backorder.confirmation',
                         'views': [(view, 'form')],
                         'view_id': view,
                         'target': 'new',
                         'res_id': wiz_id,
                         'context': context,
                     }
            for operation in pick.pack_operation_ids:
                if operation.qty_done < 0:
                    raise UserError(_('No negative quantities allowed'))
                if operation.qty_done > 0:
                    pack_op_obj.write(cr, uid, operation.id, {'product_qty': operation.qty_done}, context=context)
                else:
                    to_delete.append(operation.id)
            if to_delete:
                pack_op_obj.unlink(cr, uid, to_delete, context=context)
        self.do_transfer(cr, uid, ids, context=context)
        return

    def check_backorder(self, cr, uid, picking, context=None):
        need_rereserve, all_op_processed = self.picking_recompute_remaining_quantities(cr, uid, picking, done_qtys=True, context=context)
        for move in picking.move_lines:
            if float_compare(move.remaining_qty, 0, precision_rounding = move.product_id.uom_id.rounding) != 0:
                return True
        return False

    def create_lots_for_picking(self, cr, uid, ids, context=None):
        lot_obj = self.pool['stock.production.lot']
        opslot_obj = self.pool['stock.pack.operation.lot']
        to_unlink = []
        for picking in self.browse(cr, uid, ids, context=context):
            for ops in picking.pack_operation_ids:
                for opslot in ops.pack_lot_ids:
                    if not opslot.lot_id:
                        lot_id = lot_obj.create(cr, uid, {'name': opslot.lot_name, 'product_id': ops.product_id.id}, context=context)
                        opslot_obj.write(cr, uid, [opslot.id], {'lot_id':lot_id}, context=context)
                #Unlink pack operations where qty = 0
                to_unlink += [x.id for x in ops.pack_lot_ids if x.qty == 0.0]
        opslot_obj.unlink(cr, uid, to_unlink, context=context)

    def do_transfer(self, cr, uid, ids, context=None):
        """
            If no pack operation, we do simple action_done of the picking
            Otherwise, do the pack operations
        """
        if not context:
            context = {}

        stock_move_obj = self.pool.get('stock.move')
        self.create_lots_for_picking(cr, uid, ids, context=context)
        for picking in self.browse(cr, uid, ids, context=context):
            if not picking.pack_operation_ids:
                self.action_done(cr, uid, [picking.id], context=context)
                continue
            else:
                need_rereserve, all_op_processed = self.picking_recompute_remaining_quantities(cr, uid, picking, context=context)
                #create extra moves in the picking (unexpected product moves coming from pack operations)
                todo_move_ids = []
                if not all_op_processed:
                    todo_move_ids += self._create_extra_moves(cr, uid, picking, context=context)

                #split move lines if needed
                toassign_move_ids = []
                for move in picking.move_lines:
                    remaining_qty = move.remaining_qty
                    if move.state in ('done', 'cancel'):
                        #ignore stock moves cancelled or already done
                        continue
                    elif move.state == 'draft':
                        toassign_move_ids.append(move.id)
                    if float_compare(remaining_qty, 0,  precision_rounding = move.product_id.uom_id.rounding) == 0:
                        if move.state in ('draft', 'assigned', 'confirmed'):
                            todo_move_ids.append(move.id)
                    elif float_compare(remaining_qty,0, precision_rounding = move.product_id.uom_id.rounding) > 0 and \
                                float_compare(remaining_qty, move.product_qty, precision_rounding = move.product_id.uom_id.rounding) < 0:
                        new_move = stock_move_obj.split(cr, uid, move, remaining_qty, context=context)
                        todo_move_ids.append(move.id)
                        #Assign move as it was assigned before
                        toassign_move_ids.append(new_move)
                if need_rereserve or not all_op_processed: 
                    if not picking.location_id.usage in ("supplier", "production", "inventory"):
                        self.rereserve_quants(cr, uid, picking, move_ids=todo_move_ids, context=context)
                    self.do_recompute_remaining_quantities(cr, uid, [picking.id], context=context)
                if todo_move_ids and not context.get('do_only_split'):
                    self.pool.get('stock.move').action_done(cr, uid, todo_move_ids, context=context)
                elif context.get('do_only_split'):
                    context = dict(context, split=todo_move_ids)
            self._create_backorder(cr, uid, picking, context=context)
        return True

    @api.cr_uid_ids_context
    def do_split(self, cr, uid, picking_ids, context=None):
        """ just split the picking (create a backorder) without making it 'done' """
        if context is None:
            context = {}
        ctx = context.copy()
        ctx['do_only_split'] = True
        return self.do_transfer(cr, uid, picking_ids, context=ctx)

    def put_in_pack(self, cr, uid, ids, context=None):
        stock_move_obj = self.pool["stock.move"]
        stock_operation_obj = self.pool["stock.pack.operation"]
        package_obj = self.pool["stock.quant.package"]
        package_id = False
        for pick in self.browse(cr, uid, ids, context=context):
            operations = [x for x in pick.pack_operation_ids if x.qty_done > 0 and (not x.result_package_id)]
            pack_operation_ids = []
            for operation in operations:
                #If we haven't done all qty in operation, we have to split into 2 operation
                op = operation
                if operation.qty_done < operation.product_qty:
                    new_operation = stock_operation_obj.copy(cr, uid, operation.id, {'product_qty': operation.qty_done,'qty_done': operation.qty_done}, context=context)

                    stock_operation_obj.write(cr, uid, operation.id, {'product_qty': operation.product_qty - operation.qty_done,'qty_done': 0}, context=context)
                    if operation.pack_lot_ids:
                        packlots_transfer = [(4, x.id) for x in operation.pack_lot_ids]
                        stock_operation_obj.write(cr, uid, [new_operation], {'pack_lot_ids': packlots_transfer}, context=context)

                    op = stock_operation_obj.browse(cr, uid, new_operation, context=context)
                pack_operation_ids.append(op.id)
            if operations:
                stock_operation_obj.check_tracking(cr, uid, pack_operation_ids, context=context)
                package_id = package_obj.create(cr, uid, {}, context=context)
                stock_operation_obj.write(cr, uid, pack_operation_ids, {'result_package_id': package_id}, context=context)
            else:
                raise UserError(_('Please process some quantities to put in the pack first!'))
        return package_id
