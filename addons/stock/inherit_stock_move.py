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

class stock_move(osv.osv):
    _inherit = "stock.move"

    def action_confirm(self, cr, uid, ids, context=None):
        """ Confirms stock move or put it in waiting if it's linked to another move.
        @return: List of ids.
        """
        if not context:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        states = {
            'confirmed': [],
            'waiting': []
        }
        to_assign = {}
        for move in self.browse(cr, uid, ids, context=context):
            self.attribute_price(cr, uid, move, context=context)
            state = 'confirmed'
            #if the move is preceeded, then it's waiting (if preceeding move is done, then action_assign has been called already and its state is already available)
            if move.move_orig_ids:
                state = 'waiting'
            #if the move is split and some of the ancestor was preceeded, then it's waiting as well
            elif move.split_from:
                move2 = move.split_from
                while move2 and state != 'waiting':
                    if move2.move_orig_ids:
                        state = 'waiting'
                    move2 = move2.split_from
            states[state].append(move.id)

            if not move.picking_id and move.picking_type_id:
                key = (move.group_id.id, move.location_id.id, move.location_dest_id.id)
                if key not in to_assign:
                    to_assign[key] = []
                to_assign[key].append(move.id)
        moves = [move for move in self.browse(cr, uid, states['confirmed'], context=context) if move.procure_method == 'make_to_order']
        self._create_procurements(cr, uid, moves, context=context)
        for move in moves:
            states['waiting'].append(move.id)
            states['confirmed'].remove(move.id)

        for state, write_ids in states.items():
            if len(write_ids):
                self.write(cr, uid, write_ids, {'state': state})
        #assign picking in batch for all confirmed move that share the same details
        for key, move_ids in to_assign.items():
            self._picking_assign(cr, uid, move_ids, context=context)
        moves = self.browse(cr, uid, ids, context=context)
        self._push_apply(cr, uid, moves, context=context)
        return ids

    def force_assign(self, cr, uid, ids, context=None):
        """ Changes the state to assigned.
        @return: True
        """
        res = self.write(cr, uid, ids, {'state': 'assigned'}, context=context)
        self.check_recompute_pack_op(cr, uid, ids, context=context)
        return res

    def check_tracking(self, cr, uid, move, ops, context=None):
        """ Checks if serial number is assigned to stock move or not and raise an error if it had to.
        """
        if move.picking_id and (move.picking_id.picking_type_id.use_existing_lots or move.picking_id.picking_type_id.use_create_lots) and \
            move.product_id.tracking != 'none':
            if not (move.restrict_lot_id or (ops and ops.pack_lot_ids)):
                raise UserError(_('You need to provide a Lot/Serial Number for product %s') % move.product_id.name)

    def check_recompute_pack_op(self, cr, uid, ids, context=None):
        pickings = list(set([x.picking_id for x in self.browse(cr, uid, ids, context=context) if x.picking_id]))
        pickings_partial = []
        pickings_write = []
        pick_obj = self.pool['stock.picking']
        for pick in pickings:
            # Check if someone was treating the picking already
            if not any([x.qty_done > 0 for x in pick.pack_operation_ids]):
                pickings_partial.append(pick.id)
            else:
                pickings_write.append(pick.id)
        if pickings_partial:
            pick_obj.do_prepare_partial(cr, uid, pickings_partial, context=context)
        if pickings_write:
            pick_obj.write(cr, uid, pickings_write, {'recompute_pack_op': True}, context=context)

    def action_assign(self, cr, uid, ids, no_prepare=False, context=None):
        """ Checks the product type and accordingly writes the state.
        """
        context = context or {}
        quant_obj = self.pool.get("stock.quant")
        uom_obj = self.pool['product.uom']
        to_assign_moves = []
        main_domain = {}
        todo_moves = []
        operations = set()
        for move in self.browse(cr, uid, ids, context=context):
            if move.state not in ('confirmed', 'waiting', 'assigned'):
                continue
            if move.location_id.usage in ('supplier', 'inventory', 'production'):
                to_assign_moves.append(move.id)
                #in case the move is returned, we want to try to find quants before forcing the assignment
                if not move.origin_returned_move_id:
                    continue
            if move.product_id.type == 'consu':
                to_assign_moves.append(move.id)
                continue
            else:
                todo_moves.append(move)

                #we always keep the quants already assigned and try to find the remaining quantity on quants not assigned only
                main_domain[move.id] = [('reservation_id', '=', False), ('qty', '>', 0)]

                #if the move is preceeded, restrict the choice of quants in the ones moved previously in original move
                ancestors = self.find_move_ancestors(cr, uid, move, context=context)
                if move.state == 'waiting' and not ancestors:
                    #if the waiting move hasn't yet any ancestor (PO/MO not confirmed yet), don't find any quant available in stock
                    main_domain[move.id] += [('id', '=', False)]
                elif ancestors:
                    main_domain[move.id] += [('history_ids', 'in', ancestors)]

                #if the move is returned from another, restrict the choice of quants to the ones that follow the returned move
                if move.origin_returned_move_id:
                    main_domain[move.id] += [('history_ids', 'in', move.origin_returned_move_id.id)]
                for link in move.linked_move_operation_ids:
                    operations.add(link.operation_id)
        # Check all ops and sort them: we want to process first the packages, then operations with lot then the rest
        operations = list(operations)
        operations.sort(key=lambda x: ((x.package_id and not x.product_id) and -4 or 0) + (x.package_id and -2 or 0) + (x.pack_lot_ids and -1 or 0))
        for ops in operations:
            #first try to find quants based on specific domains given by linked operations for the case where we want to rereserve according to existing pack operations
            if not (ops.product_id and ops.pack_lot_ids):
                for record in ops.linked_move_operation_ids:
                    move = record.move_id
                    if move.id in main_domain:
                        qty = record.qty
                        domain = main_domain[move.id]
                        if qty:
                            quants = quant_obj.quants_get_preferred_domain(cr, uid, qty, move, ops=ops, domain=domain, preferred_domain_list=[], context=context)
                            quant_obj.quants_reserve(cr, uid, quants, move, record, context=context)
            else:
                lot_qty = {}
                rounding = ops.product_id.uom_id.rounding
                for pack_lot in ops.pack_lot_ids:
                    lot_qty[pack_lot.lot_id.id] = uom_obj._compute_qty(cr, uid, ops.product_uom_id.id, pack_lot.qty, ops.product_id.uom_id.id)
                for record in ops.linked_move_operation_ids:
                    move_qty = record.qty
                    domain = main_domain[move.id]
                    for lot in lot_qty:
                        if float_compare(lot_qty[lot], 0, precision_rounding=rounding) > 0 and float_compare(move_qty, 0, precision_rounding=rounding) > 0:
                            qty = min(lot_qty[lot], move_qty)
                            quants = quant_obj.quants_get_preferred_domain(cr, uid, qty, move, ops=ops, lot_id=lot, domain=domain, preferred_domain_list=[], context=context)
                            quants_to_reserve = [x for x in quants if x[0] and x[0].lot_id]
                            quant_obj.quants_reserve(cr, uid, quants_to_reserve, move, record, context=context)

        for move in todo_moves:
            if move.linked_move_operation_ids:
                continue
            #then if the move isn't totally assigned, try to find quants without any specific domain
            if move.state != 'assigned':
                qty_already_assigned = move.reserved_availability
                qty = move.product_qty - qty_already_assigned
                quants = quant_obj.quants_get_preferred_domain(cr, uid, qty, move, domain=main_domain[move.id], preferred_domain_list=[], context=context)
                quant_obj.quants_reserve(cr, uid, quants, move, context=context)

        #force assignation of consumable products and incoming from supplier/inventory/production
        # Do not take force_assign as it would create pack operations
        if to_assign_moves:
            self.write(cr, uid, to_assign_moves, {'state': 'assigned'}, context=context)
        if not no_prepare:
            self.check_recompute_pack_op(cr, uid, ids, context=context)

    def action_cancel(self, cr, uid, ids, context=None):
        """ Cancels the moves and if all moves are cancelled it cancels the picking.
        @return: True
        """
        procurement_obj = self.pool.get('procurement.order')
        context = context or {}
        procs_to_check = []
        for move in self.browse(cr, uid, ids, context=context):
            if move.state == 'done':
                raise UserError(_('You cannot cancel a stock move that has been set to \'Done\'.'))
            if move.reserved_quant_ids:
                self.pool.get("stock.quant").quants_unreserve(cr, uid, move, context=context)
            if context.get('cancel_procurement'):
                if move.propagate:
                    procurement_ids = procurement_obj.search(cr, uid, [('move_dest_id', '=', move.id)], context=context)
                    procurement_obj.cancel(cr, uid, procurement_ids, context=context)
            else:
                if move.move_dest_id:
                    if move.propagate:
                        self.action_cancel(cr, uid, [move.move_dest_id.id], context=context)
                    elif move.move_dest_id.state == 'waiting':
                        #If waiting, the chain will be broken and we are not sure if we can still wait for it (=> could take from stock instead)
                        self.write(cr, uid, [move.move_dest_id.id], {'state': 'confirmed'}, context=context)
                if move.procurement_id:
                    # Does the same as procurement check, only eliminating a refresh
                    procs_to_check.append(move.procurement_id.id)

        res = self.write(cr, uid, ids, {'state': 'cancel', 'move_dest_id': False}, context=context)
        if procs_to_check:
            procurement_obj.check(cr, uid, procs_to_check, context=context)
        return res

    def _check_package_from_moves(self, cr, uid, ids, context=None):
        pack_obj = self.pool.get("stock.quant.package")
        packs = set()
        for move in self.browse(cr, uid, ids, context=context):
            packs |= set([q.package_id for q in move.quant_ids if q.package_id and q.qty > 0])
        return pack_obj._check_location_constraint(cr, uid, list(packs), context=context)

    def find_move_ancestors(self, cr, uid, move, context=None):
        '''Find the first level ancestors of given move '''
        ancestors = []
        move2 = move
        while move2:
            ancestors += [x.id for x in move2.move_orig_ids]
            #loop on the split_from to find the ancestor of split moves only if the move has not direct ancestor (priority goes to them)
            move2 = not move2.move_orig_ids and move2.split_from or False
        return ancestors

    @api.cr_uid_ids_context
    def recalculate_move_state(self, cr, uid, move_ids, context=None):
        '''Recompute the state of moves given because their reserved quants were used to fulfill another operation'''
        for move in self.browse(cr, uid, move_ids, context=context):
            vals = {}
            reserved_quant_ids = move.reserved_quant_ids
            if len(reserved_quant_ids) > 0 and not move.partially_available:
                vals['partially_available'] = True
            if len(reserved_quant_ids) == 0 and move.partially_available:
                vals['partially_available'] = False
            if move.state == 'assigned':
                if self.find_move_ancestors(cr, uid, move, context=context):
                    vals['state'] = 'waiting'
                else:
                    vals['state'] = 'confirmed'
            if vals:
                self.write(cr, uid, [move.id], vals, context=context)

    def _move_quants_by_lot(self, cr, uid, ops, lot_qty, quants_taken, false_quants, lot_move_qty, quant_dest_package_id, context=None):
        quant_obj = self.pool['stock.quant']
        move_quants_dict = {}
        domain = [('qty', '>', 0)]
        fallback_domain = [('reservation_id', '=', False)]
        fallback_domain2 = ['&', ('reservation_id', 'not in', [x for x in lot_move_qty.keys()]), ('reservation_id', '!=', False)]
        preferred_domain_list = [fallback_domain] + [fallback_domain2]
        rounding = ops.product_id.uom_id.rounding
        # Iterate for every move through the different lots taken
        # Take the reserved quants with the correct lot first
        # Afterwards take the not reserved quants (or reserved on another move) with the correct lot
        # If nothing found, take first the quants reserved with False lots before taking others
        for move in lot_move_qty:
            move_quants_dict[move] = {}
            move_rec = self.pool['stock.move'].browse(cr, uid, move, context=context)
            #Needs to be divided by lot still
            for quant in quants_taken:
                move_quants_dict[move].setdefault(quant[0].lot_id.id, [])
                move_quants_dict[move][quant[0].lot_id.id] += [quant]
            false_quants_move = [x for x in false_quants if x[0].reservation_id.id == move]
            for lot in lot_qty:
                move_quants_dict[move].setdefault(lot, [])
                if float_compare(lot_move_qty[move], 0, precision_rounding=rounding) > 0 and float_compare(lot_qty[lot], 0, precision_rounding=rounding) > 0:
                    # Search if we can find quants with that lot
                    quants = quant_obj.quants_get_preferred_domain(cr, uid, lot_move_qty[move], move_rec, ops=ops, lot_id=lot, domain=domain,
                                                        preferred_domain_list=preferred_domain_list, context=context)
                    while quants and float_compare(lot_qty[lot], 0, precision_rounding=rounding) > 0 and float_compare(lot_move_qty[move], 0, precision_rounding=rounding) > 0:
                        quant = quants.pop(0)
                        if quant[0] and quant[0].lot_id:
                            qty = min (lot_qty[lot], lot_move_qty[move], quant[1])
                            move_quants_dict[move][lot] += [(quant[0], qty)]
                            lot_qty[lot] -= qty
                            lot_move_qty[move] -= qty
                        else:
                            #Take reserved False quants first if no quants with lot anymore
                            while false_quants_move and float_compare(lot_qty[lot], 0, precision_rounding=rounding) > 0 and float_compare(lot_move_qty[move], 0, precision_rounding=rounding) > 0:
                                qty_min = min(lot_qty[lot], lot_move_qty[move])
                                if false_quants_move[0][1] > qty_min:
                                    false_quants_move[0][1] -= qty_min
                                    move_quants_dict[move][lot] += [(false_quants_move[0][0], qty_min)]
                                    qty = qty_min
                                else:
                                    move_quants_dict[move][lot] += [false_quants_move[0]]
                                    qty = false_quants_move[0][1]
                                    false_quants_move.pop(0)
                                lot_qty[lot] -= qty
                                lot_move_qty[move] -= qty
                            if float_compare(lot_qty[lot], 0, precision_rounding=rounding) > 0 and float_compare(lot_move_qty[move], 0,precision_rounding=rounding) > 0:
                                qty = min (lot_qty[lot], lot_move_qty[move], quant[1])
                                move_quants_dict[move][lot] += [(quant[0], qty)]
                                lot_qty[lot] -= qty
                                lot_move_qty[move] -= qty

                #Move all the quants related to that lot/move
                quant_obj.quants_move(cr, uid, move_quants_dict[move][lot], move_rec, ops.location_dest_id, location_from=ops.location_id,
                                                    lot_id=lot, owner_id=ops.owner_id.id, src_package_id=ops.package_id.id,
                                                    dest_package_id=quant_dest_package_id, context=context)

    def action_done(self, cr, uid, ids, context=None):
        """ Process completely the moves given as ids and if all moves are done, it will finish the picking.
        """
        context = context or {}
        picking_obj = self.pool.get("stock.picking")
        quant_obj = self.pool.get("stock.quant")
        uom_obj = self.pool.get("product.uom")
        todo = [move.id for move in self.browse(cr, uid, ids, context=context) if move.state == "draft"]
        if todo:
            ids = self.action_confirm(cr, uid, todo, context=context)
        pickings = set()
        procurement_ids = set()
        #Search operations that are linked to the moves
        operations = set()
        move_qty = {}
        for move in self.browse(cr, uid, ids, context=context):
            move_qty[move.id] = move.product_qty
            for link in move.linked_move_operation_ids:
                operations.add(link.operation_id)

        #Sort operations according to entire packages first, then package + lot, package only, lot only
        operations = list(operations)
        operations.sort(key=lambda x: ((x.package_id and not x.product_id) and -4 or 0) + (x.package_id and -2 or 0) + (x.pack_lot_ids and -1 or 0))

        for ops in operations:
            if ops.picking_id:
                pickings.add(ops.picking_id.id)
            main_domain = [('qty', '>', 0)]
            entire_pack=False
            if ops.product_id:
                #If a product is given, the result is always put immediately in the result package (if it is False, they are without package)
                quant_dest_package_id  = ops.result_package_id.id
            else:
                # When a pack is moved entirely, the quants should not be written anything for the destination package
                quant_dest_package_id = False
                entire_pack=True
            lot_qty = {}
            tot_qty = 0.0
            for pack_lot in ops.pack_lot_ids:
                qty = uom_obj._compute_qty(cr, uid, ops.product_uom_id.id, pack_lot.qty, ops.product_id.uom_id.id)
                lot_qty[pack_lot.lot_id.id] = qty
                tot_qty += pack_lot.qty
            if ops.pack_lot_ids and ops.product_id and float_compare(tot_qty, ops.product_qty, precision_rounding=ops.product_uom_id.rounding) != 0.0:
                raise UserError(_('You have a difference between the quantity on the operation and the quantities specified for the lots. '))
            quants_taken = []
            false_quants = []
            lot_move_qty = {}
            for record in ops.linked_move_operation_ids:
                move = record.move_id
                self.check_tracking(cr, uid, move, ops, context=context)
                preferred_domain = [('reservation_id', '=', move.id)]
                fallback_domain = [('reservation_id', '=', False)]
                fallback_domain2 = ['&', ('reservation_id', '!=', move.id), ('reservation_id', '!=', False)]
                dom = main_domain
                if not ops.pack_lot_ids:
                    preferred_domain_list = [preferred_domain] + [fallback_domain] + [fallback_domain2]
                    quants = quant_obj.quants_get_preferred_domain(cr, uid, record.qty, move, ops=ops, domain=dom,
                                                        preferred_domain_list=preferred_domain_list, context=context)
                    quant_obj.quants_move(cr, uid, quants, move, ops.location_dest_id, location_from=ops.location_id,
                                          lot_id=False, owner_id=ops.owner_id.id, src_package_id=ops.package_id.id,
                                          dest_package_id=quant_dest_package_id, entire_pack=entire_pack, context=context)
                else:
                    # Check what you can do with reserved quants already
                    qty_on_link = record.qty
                    rounding = ops.product_id.uom_id.rounding
                    for reserved_quant in move.reserved_quant_ids:
                        if not reserved_quant.lot_id:
                            false_quants += [reserved_quant]
                        elif float_compare(lot_qty.get(reserved_quant.lot_id.id, 0), 0, precision_rounding=rounding) > 0:
                            if float_compare(lot_qty[reserved_quant.lot_id.id], reserved_quant.qty, precision_rounding=rounding) >= 0:
                                lot_qty[reserved_quant.lot_id.id] -= reserved_quant.qty
                                quants_taken += [(reserved_quant, reserved_quant.qty)]
                                qty_on_link -= reserved_quant.qty
                            else:
                                quants_taken += [(reserved_quant, lot_qty[reserved_quant.lot_id.id])]
                                lot_qty[reserved_quant.lot_id.id] = 0
                                qty_on_link -= lot_qty[reserved_quant.lot_id.id]
                    lot_move_qty[move.id] = qty_on_link

                if not move_qty.get(move.id):
                    raise UserError(_("The roundings of your Unit of Measures %s on the move vs. %s on the product don't allow to do these operations or you are not transferring the picking at once. ") % (move.product_uom.name, move.product_id.uom_id.name))
                move_qty[move.id] -= record.qty

            #Handle lots separately
            if ops.pack_lot_ids:
                self._move_quants_by_lot(cr, uid, ops, lot_qty, quants_taken, false_quants, lot_move_qty, quant_dest_package_id, context=context)

            # Handle pack in pack
            if not ops.product_id and ops.package_id and ops.result_package_id.id != ops.package_id.parent_id.id:
                self.pool.get('stock.quant.package').write(cr, SUPERUSER_ID, [ops.package_id.id], {'parent_id': ops.result_package_id.id}, context=context)
        #Check for remaining qtys and unreserve/check move_dest_id in
        move_dest_ids = set()
        for move in self.browse(cr, uid, ids, context=context):
            move_qty_cmp = float_compare(move_qty[move.id], 0, precision_rounding=move.product_id.uom_id.rounding)
            if move_qty_cmp > 0:  # (=In case no pack operations in picking)
                main_domain = [('qty', '>', 0)]
                preferred_domain = [('reservation_id', '=', move.id)]
                fallback_domain = [('reservation_id', '=', False)]
                fallback_domain2 = ['&', ('reservation_id', '!=', move.id), ('reservation_id', '!=', False)]
                preferred_domain_list = [preferred_domain] + [fallback_domain] + [fallback_domain2]
                self.check_tracking(cr, uid, move, False, context=context)
                qty = move_qty[move.id]
                quants = quant_obj.quants_get_preferred_domain(cr, uid, qty, move, domain=main_domain, preferred_domain_list=preferred_domain_list, context=context)
                quant_obj.quants_move(cr, uid, quants, move, move.location_dest_id, lot_id=move.restrict_lot_id.id, owner_id=move.restrict_partner_id.id, context=context)

            # If the move has a destination, add it to the list to reserve
            if move.move_dest_id and move.move_dest_id.state in ('waiting', 'confirmed'):
                move_dest_ids.add(move.move_dest_id.id)

            if move.procurement_id:
                procurement_ids.add(move.procurement_id.id)

            #unreserve the quants and make them available for other operations/moves
            quant_obj.quants_unreserve(cr, uid, move, context=context)
        # Check the packages have been placed in the correct locations
        self._check_package_from_moves(cr, uid, ids, context=context)
        #set the move as done
        self.write(cr, uid, ids, {'state': 'done', 'date': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)}, context=context)
        self.pool.get('procurement.order').check(cr, uid, list(procurement_ids), context=context)
        #assign destination moves
        if move_dest_ids:
            self.action_assign(cr, uid, list(move_dest_ids), context=context)
        #check picking state to set the date_done is needed
        done_picking = []
        for picking in picking_obj.browse(cr, uid, list(pickings), context=context):
            if picking.state == 'done' and not picking.date_done:
                done_picking.append(picking.id)
        if done_picking:
            picking_obj.write(cr, uid, done_picking, {'date_done': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)}, context=context)
        return True

    def unlink(self, cr, uid, ids, context=None):
        context = context or {}
        for move in self.browse(cr, uid, ids, context=context):
            if move.state not in ('draft', 'cancel'):
                raise UserError(_('You can only delete draft moves.'))
        return super(stock_move, self).unlink(cr, uid, ids, context=context)

    def action_scrap(self, cr, uid, ids, quantity, location_id, restrict_lot_id=False, restrict_partner_id=False, context=None):
        """ Move the scrap/damaged product into scrap location
        @param cr: the database cursor
        @param uid: the user id
        @param ids: ids of stock move object to be scrapped
        @param quantity : specify scrap qty
        @param location_id : specify scrap location
        @param context: context arguments
        @return: Scraped lines
        """
        quant_obj = self.pool.get("stock.quant")
        #quantity should be given in MOVE UOM
        if quantity <= 0:
            raise UserError(_('Please provide a positive quantity to scrap.'))
        res = []
        for move in self.browse(cr, uid, ids, context=context):
            source_location = move.location_id
            if move.state == 'done':
                source_location = move.location_dest_id
            #Previously used to prevent scraping from virtual location but not necessary anymore
            #if source_location.usage != 'internal':
                #restrict to scrap from a virtual location because it's meaningless and it may introduce errors in stock ('creating' new products from nowhere)
                #raise UserError(_('Forbidden operation: it is not allowed to scrap products from a virtual location.'))
            move_qty = move.product_qty
            default_val = {
                'location_id': source_location.id,
                'product_uom_qty': quantity,
                'state': move.state,
                'scrapped': True,
                'location_dest_id': location_id,
                'restrict_lot_id': restrict_lot_id,
                'restrict_partner_id': restrict_partner_id,
            }
            new_move = self.copy(cr, uid, move.id, default_val)

            res += [new_move]
            product_obj = self.pool.get('product.product')
            for product in product_obj.browse(cr, uid, [move.product_id.id], context=context):
                if move.picking_id:
                    uom = product.uom_id.name if product.uom_id else ''
                    message = _("%s %s %s has been <b>moved to</b> scrap.") % (quantity, uom, product.name)
                    move.picking_id.message_post(body=message)

            # We "flag" the quant from which we want to scrap the products. To do so:
            #    - we select the quants related to the move we scrap from
            #    - we reserve the quants with the scrapped move
            # See self.action_done, et particularly how is defined the "preferred_domain" for clarification
            scrap_move = self.browse(cr, uid, new_move, context=context)
            if move.state == 'done' and scrap_move.location_id.usage not in ('supplier', 'inventory', 'production'):
                domain = [('qty', '>', 0), ('history_ids', 'in', [move.id])]
                # We use scrap_move data since a reservation makes sense for a move not already done
                quants = quant_obj.quants_get_preferred_domain(cr, uid, scrap_move.location_id,
                        scrap_move.product_id, quantity, domain=domain, preferred_domain_list=[],
                        restrict_lot_id=scrap_move.restrict_lot_id.id, restrict_partner_id=scrap_move.restrict_partner_id.id, context=context)
                quant_obj.quants_reserve(cr, uid, quants, scrap_move, context=context)
        self.action_done(cr, uid, res, context=context)
        return res

    def split(self, cr, uid, move, qty, restrict_lot_id=False, restrict_partner_id=False, context=None):
        """ Splits qty from move move into a new move
        :param move: browse record
        :param qty: float. quantity to split (given in product UoM)
        :param restrict_lot_id: optional production lot that can be given in order to force the new move to restrict its choice of quants to this lot.
        :param restrict_partner_id: optional partner that can be given in order to force the new move to restrict its choice of quants to the ones belonging to this partner.
        :param context: dictionay. can contains the special key 'source_location_id' in order to force the source location when copying the move

        returns the ID of the backorder move created
        """
        if move.state in ('done', 'cancel'):
            raise UserError(_('You cannot split a move done'))
        if move.state == 'draft':
            #we restrict the split of a draft move because if not confirmed yet, it may be replaced by several other moves in
            #case of phantom bom (with mrp module). And we don't want to deal with this complexity by copying the product that will explode.
            raise UserError(_('You cannot split a draft move. It needs to be confirmed first.'))

        if move.product_qty <= qty or qty == 0:
            return move.id

        uom_obj = self.pool.get('product.uom')
        context = context or {}

        #HALF-UP rounding as only rounding errors will be because of propagation of error from default UoM
        uom_qty = uom_obj._compute_qty_obj(cr, uid, move.product_id.uom_id, qty, move.product_uom, rounding_method='HALF-UP', context=context)
        defaults = {
            'product_uom_qty': uom_qty,
            'procure_method': 'make_to_stock',
            'restrict_lot_id': restrict_lot_id,
            'restrict_partner_id': restrict_partner_id,
            'split_from': move.id,
            'procurement_id': move.procurement_id.id,
            'move_dest_id': move.move_dest_id.id,
            'origin_returned_move_id': move.origin_returned_move_id.id,
        }
        if context.get('source_location_id'):
            defaults['location_id'] = context['source_location_id']
        new_move = self.copy(cr, uid, move.id, defaults, context=context)

        ctx = context.copy()
        ctx['do_not_propagate'] = True
        self.write(cr, uid, [move.id], {
            'product_uom_qty': move.product_uom_qty - uom_qty,
        }, context=ctx)

        if move.move_dest_id and move.propagate and move.move_dest_id.state not in ('done', 'cancel'):
            new_move_prop = self.split(cr, uid, move.move_dest_id, qty, context=context)
            self.write(cr, uid, [new_move], {'move_dest_id': new_move_prop}, context=context)
        #returning the first element of list returned by action_confirm is ok because we checked it wouldn't be exploded (and
        #thus the result of action_confirm should always be a list of 1 element length)
        return self.action_confirm(cr, uid, [new_move], context=context)[0]


    def get_code_from_locs(self, cr, uid, move, location_id=False, location_dest_id=False, context=None):
        """
        Returns the code the picking type should have.  This can easily be used
        to check if a move is internal or not
        move, location_id and location_dest_id are browse records
        """
        code = 'internal'
        src_loc = location_id or move.location_id
        dest_loc = location_dest_id or move.location_dest_id
        if src_loc.usage == 'internal' and dest_loc.usage != 'internal':
            code = 'outgoing'
        if src_loc.usage != 'internal' and dest_loc.usage == 'internal':
            code = 'incoming'
        return code

    def show_picking(self, cr, uid, ids, context=None):
        assert len(ids) > 0
        picking_id = self.browse(cr, uid, ids[0], context=context).picking_id.id
        if picking_id:
            data_obj = self.pool['ir.model.data']
            view = data_obj.xmlid_to_res_id(cr, uid, 'stock.view_picking_form')
            return {
                 'name': _('Transfer'),
                 'type': 'ir.actions.act_window',
                 'view_type': 'form',
                 'view_mode': 'form',
                 'res_model': 'stock.picking',
                 'views': [(view, 'form')],
                 'view_id': view,
                 'target': 'new',
                 'res_id': picking_id,
            }
