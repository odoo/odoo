# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import date

from odoo import api, models
from odoo.osv.expression import AND
from odoo.tools import float_is_zero, format_date, float_round, float_compare, OrderedSet

class StockForecasted(models.AbstractModel):
    _name = 'stock.forecasted_product_product'
    _description = "Stock Replenishment Report"

    @api.model
    def get_report_values(self, docids, data=None):
        return {
            'data': data,
            'doc_ids': docids,
            'doc_model': 'product.product',
            'docs': self._get_report_data(product_ids=docids),
            'precision': self.env['decimal.precision'].precision_get('Product Unit of Measure'),
        }

    def _product_domain(self, product_template_ids, product_ids):
        if product_template_ids:
            return [('product_tmpl_id', 'in', product_template_ids)]
        return [('product_id', 'in', product_ids)]

    def _move_domain(self, product_template_ids, product_ids, wh_location_ids):
        move_domain = self._product_domain(product_template_ids, product_ids)
        move_domain += [('product_uom_qty', '!=', 0)]
        out_domain = move_domain + [
            '&',
            ('location_id', 'in', wh_location_ids),
            '|',
            ('location_dest_id', 'not in', wh_location_ids),
            '&',
            ('location_final_id', '!=', False),
            ('location_final_id', 'not in', wh_location_ids),
        ]
        in_domain = move_domain + [
            '&',
            ('location_id', 'not in', wh_location_ids),
            ('location_dest_id', 'in', wh_location_ids),
        ]
        return in_domain, out_domain

    def _move_draft_domain(self, product_template_ids, product_ids, wh_location_ids):
        in_domain, out_domain = self._move_domain(product_template_ids, product_ids, wh_location_ids)
        in_domain += [('state', '=', 'draft')]
        out_domain += [('state', '=', 'draft')]
        return in_domain, out_domain

    def _move_confirmed_domain(self, product_template_ids, product_ids, wh_location_ids):
        in_domain, out_domain = self._move_domain(product_template_ids, product_ids, wh_location_ids)
        out_domain += [('state', 'in', ['waiting', 'confirmed', 'partially_available', 'assigned'])]
        in_domain += [('state', 'in', ['waiting', 'confirmed', 'partially_available', 'assigned'])]
        return in_domain, out_domain

    def _get_report_header(self, product_template_ids, product_ids, wh_location_ids):
        # Get the products we're working, fill the rendering context with some of their attributes.
        res = {}
        if product_template_ids:
            products = self.env['product.template'].browse(product_template_ids)
            res.update({
                'product_templates' : products.read(fields=['id', 'display_name']),
                'product_templates_ids' : products.ids,
                'product_variants' : [{
                        'id' : pv.id,
                        'combination_name' : pv.product_template_attribute_value_ids._get_combination_name(),
                    } for pv in products.product_variant_ids],
                'product_variants_ids' : products.product_variant_ids.ids,
                'multiple_product' : len(products.product_variant_ids) > 1,
            })
        elif product_ids:
            products = self.env['product.product'].browse(product_ids)
            res.update({
                'product_templates' : False,
                'product_variants' : products.read(fields=['id', 'display_name']),
                'product_variants_ids' : products.ids,
                'multiple_product' : len(products) > 1,
            })

        res['uom'] = products[:1].uom_id.display_name
        res['quantity_on_hand'] = sum(products.mapped('qty_available'))
        res['virtual_available'] = sum(products.mapped('virtual_available'))
        res['incoming_qty'] = sum(products.mapped('incoming_qty'))
        res['outgoing_qty'] = sum(products.mapped('outgoing_qty'))

        in_domain, out_domain = self._move_draft_domain(product_template_ids, product_ids, wh_location_ids)
        [in_sum] = self.env['stock.move']._read_group(in_domain, aggregates=['product_qty:sum'])[0]
        [out_sum] = self.env['stock.move']._read_group(out_domain, aggregates=['product_qty:sum'])[0]

        res.update({
            'draft_picking_qty': {
                'in': in_sum,
                'out': out_sum
            },
            'qty': {
                'in': in_sum,
                'out': out_sum
            }
        })
        return res

    def _get_reservation_data(self, move):
        return {
            '_name': move.picking_id._name,
            'name': move.picking_id.name,
            'id': move.picking_id.id
        }

    def _get_report_data(self, product_template_ids=False, product_ids=False):
        assert product_template_ids or product_ids
        res = {}

        warehouse = self.env['stock.warehouse'].browse(self.env['stock.warehouse']._get_warehouse_id_from_context()) or self.env['stock.warehouse'].search([['active', '=', True]])[0]
        wh_location_ids = [loc['id'] for loc in self.env['stock.location'].search_read(
            [('id', 'child_of', warehouse.view_location_id.id)],
            ['id'],
        )]
        # any quantities in this location will be considered free stock, others are free stock in transit
        wh_stock_location = warehouse.lot_stock_id

        res.update(self._get_report_header(product_template_ids, product_ids, wh_location_ids))

        res['lines'] = self._get_report_lines(product_template_ids, product_ids, wh_location_ids, wh_stock_location)
        res['user_can_edit_pickings'] = self.env.user.has_group('stock.group_stock_user')
        return res

    def _prepare_forecast_availability_line(self, quantity, move_out, move_in, replenishment_filled, product=False):
        """Report line holding only the values needed to compute an availability.

        Everything a full line adds for display purposes (source documents, display
        names, formatted dates, reservation data) is left out.
        """
        product = product or move_out.product_id
        return {
            'quantity': float_round(quantity, precision_rounding=product.uom_id.rounding),
            'replenishment_filled': replenishment_filled,
            'move_out': move_out,
            'move_in': move_in,
        }

    def _prepare_report_line(self, quantity, move_out=None, move_in=None, replenishment_filled=True, product=False, reserved_move=False, in_transit=False, read=True):
        if move_out and self.env.context.get('forecast_availability_move_ids') is not None:
            return self._prepare_forecast_availability_line(quantity, move_out, move_in, replenishment_filled, product)
        product = product or (move_out.product_id if move_out else move_in.product_id)
        is_late = move_out.date < move_in.date if (move_out and move_in) else False

        move_to_match_ids = self.env.context.get('move_to_match_ids') or []
        move_in_id = move_in.id if move_in else None
        move_out_id = move_out.id if move_out else None
        line = {
            'document_in': False,
            'document_out': False,
            'receipt_date': False,
            'delivery_date': False,
            'product': {
                'id': product.id,
                'display_name': product.display_name,
            },
            'replenishment_filled': replenishment_filled,
            'is_late': is_late,
            'quantity': float_round(quantity, precision_rounding=product.uom_id.rounding),
            'move_out': move_out,
            'move_in': move_in,
            'reservation': self._get_reservation_data(reserved_move) if reserved_move else False,
            'in_transit': in_transit,
            'is_matched': any(move_id in [move_in_id, move_out_id] for move_id in move_to_match_ids),
            'uom_id' : product.uom_id.read()[0] if read else product.uom_id,
        }
        if move_in:
            document_in = move_in.sudo()._get_source_document()
            line.update({
                'move_in': move_in.read(fields=self._get_report_moves_fields())[0] if read else move_in,
                'document_in' : {
                    '_name' : document_in._name,
                    'id' : document_in.id,
                    'name' : document_in.display_name,
                } if document_in else False,
                'receipt_date': format_date(self.env, move_in.date),
            })

        if move_out:
            document_out = move_out.sudo()._get_source_document()
            line.update({
                'move_out': move_out.read(fields=self._get_report_moves_fields())[0] if read else move_out,
                'document_out' : {
                    '_name' : document_out._name,
                    'id' : document_out.id,
                    'name' : document_out.display_name,
                } if document_out else False,
                'delivery_date': format_date(self.env, move_out.date),
            })
            if move_out.picking_id and read:
                line['move_out'].update({
                    'picking_id': move_out.picking_id.read(fields=['id', 'priority'])[0],
                })
        return line

    def _get_report_moves_fields(self):
        return ['id', 'date']

    def _get_report_lines(self, product_template_ids, product_ids, wh_location_ids, wh_stock_location, read=True):

        # The helpers below read the plain dicts built further down rather than the
        # records themselves: the allocation walks every move chained to every outgoing
        # move, and at that scale each field access costs a new singleton recordset.
        def _move_rounding(move_id):
            """Rounding of the move product's reference uom."""
            return uom_rounding[product_uom_id[product_of[move_id]]]

        def _move_reserved_qty(move_id):
            """Quantity of the move, converted to its product's reference uom."""
            qty, from_uom = qty_of[move_id], uom_of[move_id]
            to_uom = product_uom_id.get(product_of[move_id])
            if not (from_uom and qty and to_uom):
                return qty
            if from_uom != to_uom:
                if uom_category[from_uom] != uom_category[to_uom]:
                    # Different categories: leave the conversion to the ORM.
                    UoM = self.env['uom.uom']
                    return UoM.browse(from_uom)._compute_quantity(qty, UoM.browse(to_uom))
                qty = qty / uom_factor[from_uom] * uom_factor[to_uom]
            return float_round(qty, precision_rounding=uom_rounding[to_uom], rounding_method='UP')

        def _move_chain_qty(move_id):
            """What the origin moves brought in, minus what their other dests took."""
            origs = orig_map.get(move_id, ())
            move_in_qty = sum(qty_of.get(orig, 0.0) for orig in origs if state_of.get(orig) == 'done')
            move_out_qty, counted = 0, set()
            for orig in origs:
                for dest in dest_map.get(orig, ()):
                    if dest in counted or dest == move_id:
                        continue
                    counted.add(dest)
                    if state_of.get(dest) == 'done':
                        move_out_qty += qty_of.get(dest, 0.0)
            return move_in_qty - move_out_qty

        def _get_out_move_reserved_data(out_id, linked_ids, used_reserved_moves, currents):
            reserved_out = 0
            # the move to show when qty is reserved
            reserved_move_id = False
            out_qty, out_product = product_qty_of[out_id], product_of[out_id]
            for move_id in linked_ids:
                if state_of[move_id] not in ('partially_available', 'assigned'):
                    continue
                # count reserved stock.
                reserved = _move_reserved_qty(move_id)
                # check if the move reserved qty was counted before (happens if multiple outs share pick/pack)
                reserved = min(reserved - used_reserved_moves[move_id], out_qty)
                if reserved and not reserved_move_id:
                    reserved_move_id = move_id
                # add to reserved line data
                reserved_out += reserved
                used_reserved_moves[move_id] += reserved
                currents[(out_product, location_of[move_id])] -= reserved
                if float_compare(reserved_out, out_qty, precision_rounding=_move_rounding(move_id)) >= 0:
                    break

            return {
                'reserved': reserved_out,
                'reserved_move_id': reserved_move_id,
                'linked_ids': linked_ids,
            }

        def _get_out_move_taken_from_stock_data(out_id, currents, reserved_data):
            reserved_out = reserved_data['reserved']
            demand_out = product_qty_of[out_id] - reserved_out
            out_product = product_of[out_id]
            taken_from_stock_out = 0
            for move_id in reserved_data['linked_ids']:
                if state_of[move_id] in ('draft', 'cancel', 'assigned', 'done'):
                    continue
                reserved = _move_reserved_qty(move_id)
                demand = max(product_qty_of[move_id] - reserved, 0)
                # to make sure we don't demand more than the out (useful when same pick/pack goes to multiple out)
                demand = min(demand, demand_out)
                if float_is_zero(demand, precision_rounding=_move_rounding(move_id)):
                    continue
                stock_key = (out_product, location_of[move_id])
                # check available qty for move if chained, move available is what was move by orig moves
                if orig_map.get(move_id):
                    move_available_qty = _move_chain_qty(move_id) - reserved
                else:
                    move_available_qty = currents[stock_key]
                # count taken from stock, but avoid taking more than whats in stock in case of move origs,
                # this can happen if stock adjustment is done after orig moves are done
                taken_from_stock = min(demand, move_available_qty, currents[stock_key])
                if taken_from_stock > 0:
                    currents[stock_key] -= taken_from_stock
                    taken_from_stock_out += taken_from_stock
                demand_out -= taken_from_stock
            return {
                'taken_from_stock': taken_from_stock_out,
            }

        # A caller may only care about some outgoing moves. The allocation still has to
        # run over all of them, but building a line is the expensive part, so only build
        # the lines that will be read back.
        wanted_out_ids = self.env.context.get('forecast_availability_move_ids')
        lines = []

        def _add_line(quantity, out_id=None, **kwargs):
            if wanted_out_ids is not None and (out_id is None or out_id not in wanted_out_ids):
                return
            # `browse()` alone would reduce the prefetch set to this single id, while
            # the line still reads related fields off the record.
            move_out = Move.browse(out_id).with_prefetch(outs._ids) if out_id else None
            lines.append(self._prepare_report_line(quantity, move_out=move_out, read=read, **kwargs))

        def _reconcile_out_with_ins(out_id, ins, demand, product_rounding, in_id_to_in_data, ins_per_product, dest_ids_to_in_ids):
            ins_to_remove = []
            for in_id in ins:
                in_data = in_id_to_in_data[in_id]
                if float_is_zero(in_data['qty'], precision_rounding=product_rounding):
                    ins_to_remove.append(in_id)
                    continue
                taken_from_in = min(demand, in_data['qty'])
                demand -= taken_from_in
                _add_line(taken_from_in, out_id, move_in=in_data['move'])
                in_data['qty'] -= taken_from_in
                if in_data['qty'] <= 0:
                    ins_to_remove.append(in_id)
                if float_is_zero(demand, precision_rounding=product_rounding):
                    break

            for in_id in ins_to_remove:
                in_data = in_id_to_in_data[in_id]
                product_id = in_data['move'].product_id.id
                for dest in in_data['move_dests']:
                    dest_ids_to_in_ids[dest].remove(in_id)
                ins_per_product[product_id].remove(in_id)
            return demand

        in_domain, out_domain = self._move_confirmed_domain(
            product_template_ids, product_ids, wh_location_ids
        )
        past_domain = [('reservation_date', '<=', date.today())]
        future_domain = ['|', ('reservation_date', '>', date.today()), ('reservation_date', '=', False)]

        Move = self.env['stock.move']
        past_outs = Move.search(AND([out_domain, past_domain]), order='priority desc, date, id')
        future_outs = Move.search(AND([out_domain, future_domain]), order='reservation_date, priority desc, date, id')

        outs = past_outs | future_outs

        ins = Move.search(in_domain, order='priority desc, date, id')
        # Prewarm cache with rollups
        outs._rollup_move_origs_fetch()
        ins._rollup_move_dests_fetch()

        # Walk the origin graph once on ids instead of rolling up each outgoing move
        # separately: the chains overlap, so a single level-by-level prefetch of
        # `move_orig_ids` is enough to serve every rollup.
        orig_map = {}
        frontier = outs
        while frontier:
            frontier.fetch(['move_orig_ids'])
            next_ids = set()
            for move in frontier:
                if move.id not in orig_map:
                    orig_map[move.id] = move.move_orig_ids._ids
                    next_ids.update(orig_map[move.id])
            frontier = Move.browse(next_ids - orig_map.keys())

        def _rollup_origs(move_id):
            """Same as `stock.move._rollup_move_origs`, on ids and in the same order."""
            seen = OrderedSet()
            level = [move_id]
            while True:
                unseen = [i for i in level if i not in seen]
                if not unseen:
                    return seen
                seen.update(unseen)
                nxt, taken = [], set()
                for i in unseen:
                    for orig in orig_map.get(i, ()):
                        if orig not in taken:
                            taken.add(orig)
                            nxt.append(orig)
                level = nxt

        linked_ids_per_out = {}
        ins_ids = set(ins._ids)
        all_linked_move_ids = set()
        for out_id in outs._ids:
            linked = [_id for _id in _rollup_origs(out_id) if _id not in ins_ids]
            linked_ids_per_out[out_id] = linked
            all_linked_move_ids.update(linked)

        # Read every move the allocation touches once, into plain dicts.
        universe = Move.browse(all_linked_move_ids | set(outs._ids))
        universe.fetch(['state', 'quantity', 'product_uom', 'product_id', 'product_qty', 'location_id'])
        state_of, qty_of, uom_of = {}, {}, {}
        product_of, product_qty_of, location_of = {}, {}, {}
        # All fields in a single pass: one loop per field would rebuild a singleton
        # recordset for every move as many times as there are fields.
        for move in universe:
            move_id = move.id
            state_of[move_id] = move.state
            qty_of[move_id] = move.quantity
            uom_of[move_id] = move.product_uom.id
            product_of[move_id] = move.product_id.id
            product_qty_of[move_id] = move.product_qty
            location_of[move_id] = move.location_id.id

        # The origins' other destination moves, of which only state and quantity is read.
        sibling_ids = set()
        for move_id in all_linked_move_ids:
            sibling_ids.update(orig_map.get(move_id, ()))
        siblings = Move.browse(sibling_ids)
        siblings.fetch(['move_dest_ids'])
        dest_map = {move.id: move.move_dest_ids._ids for move in siblings}
        # An origin may itself be an incoming move, excluded from the linked ids and so
        # missing from the maps above; read state and quantity for those too.
        extra = Move.browse((sibling_ids | {d for dests in dest_map.values() for d in dests}) - set(state_of))
        if extra:
            extra.fetch(['state', 'quantity'])
            for move in extra:
                state_of[move.id] = move.state
                qty_of[move.id] = move.quantity

        # Factors and roundings of the products and uoms actually referenced above.
        products = self.env['product.product'].browse({p for p in product_of.values() if p})
        products.fetch(['uom_id'])
        product_uom_id = {product.id: product.uom_id.id for product in products}
        uoms = products.uom_id | self.env['uom.uom'].browse({u for u in uom_of.values() if u})
        uoms.fetch(['factor', 'rounding', 'category_id'])
        uom_factor, uom_rounding, uom_category = {}, {}, {}
        for uom in uoms:
            uom_factor[uom.id] = uom.factor
            uom_rounding[uom.id] = uom.rounding
            uom_category[uom.id] = uom.category_id.id

        outs_per_product = defaultdict(list)
        for out_id in outs._ids:
            outs_per_product[product_of[out_id]].append(out_id)

        dest_ids_to_in_ids, in_id_to_in_data = defaultdict(OrderedSet), {}
        ins_per_product = defaultdict(OrderedSet)
        for in_ in ins:
            in_id_to_in_data[in_.id] = {
                'qty': in_.product_qty,
                'move': in_,
                'move_dests': in_._rollup_move_dests(),
            }
            product_id = in_.product_id.id
            ins_per_product[product_id].add(in_.id)
            for dest in in_id_to_in_data[in_.id]['move_dests']:
                dest_ids_to_in_ids[dest].add(in_.id)

        qties = self.env['stock.quant']._read_group([('location_id', 'in', wh_location_ids), ('quantity', '>', 0), ('product_id', 'in', [product_of[i] for i in outs._ids])],
                                                    ['product_id', 'location_id'], ['quantity:sum'])
        wh_stock_sub_location_ids = set(
            wh_stock_location.search([('id', 'child_of', wh_stock_location.id)])._ids
        )
        currents = defaultdict(float)
        for product, location, quantity in qties:
            location_id = location.id
            # any sublocation qties will be added to the main stock location qty
            if location_id in wh_stock_sub_location_ids:
                location_id = wh_stock_location.id
            currents[(product.id, location_id)] += quantity
        moves_data = {}
        for _, out_ids in outs_per_product.items():
            # to handle multiple out wtih same in (ex: same pick/pack for 2 outs)
            used_reserved_moves = defaultdict(float)
            # for all out moves, check for linked moves and count reserved quantity
            for out_id in out_ids:
                moves_data[out_id] = _get_out_move_reserved_data(
                    out_id, linked_ids_per_out[out_id], used_reserved_moves, currents
                )
            # another loop to remove qty from current stock after reserved is counted for
            for out_id in out_ids:
                data = _get_out_move_taken_from_stock_data(out_id, currents, moves_data[out_id])
                moves_data[out_id].update(data)
        product_sum = defaultdict(float)
        for product_loc, quantity in currents.items():
            product_sum[product_loc[0]] += quantity
        for product in (ins | outs).product_id:
            product_rounding = product.uom_id.rounding
            unreconciled_outs = []
            # remaining stock
            free_stock = currents[product.id, wh_stock_location.id]
            transit_stock = product_sum[product.id] - free_stock
            # add report lines and see if remaining demand can be reconciled by unreservable stock or ins
            for out_id in outs_per_product[product.id]:
                reserved_out = moves_data[out_id].get('reserved')
                taken_from_stock_out = moves_data[out_id].get('taken_from_stock')
                reserved_move_id = moves_data[out_id].get('reserved_move_id')
                demand_out = product_qty_of[out_id]
                # Reconcile with the reserved stock.
                if reserved_out > 0:
                    demand_out = max(demand_out - reserved_out, 0)
                    reserved_move = Move.browse(reserved_move_id).with_prefetch(universe._ids)
                    in_transit = bool(orig_map.get(reserved_move_id))
                    _add_line(reserved_out, out_id, reserved_move=reserved_move, in_transit=in_transit)

                if float_is_zero(demand_out, precision_rounding=product_rounding):
                    continue

                # Reconcile with the current stock.
                if taken_from_stock_out > 0:
                    demand_out = max(demand_out - taken_from_stock_out, 0)
                    _add_line(taken_from_stock_out, out_id)

                if float_is_zero(demand_out, precision_rounding=product_rounding):
                    continue

                # Reconcile with unreservable stock, quantities that are in stock but not in correct location to reserve from (in transit)
                unreservable_qty = min(demand_out, transit_stock)
                if unreservable_qty > 0:
                    demand_out -= unreservable_qty
                    transit_stock -= unreservable_qty
                    _add_line(unreservable_qty, out_id, in_transit=True)

                if float_is_zero(demand_out, precision_rounding=product_rounding):
                    continue

                # Reconcile with the ins.
                demand_out = _reconcile_out_with_ins(out_id, dest_ids_to_in_ids[out_id], demand_out, product_rounding, in_id_to_in_data, ins_per_product, dest_ids_to_in_ids)

                if not float_is_zero(demand_out, precision_rounding=product_rounding):
                    unreconciled_outs.append((demand_out, out_id))

            # Another pass, in case there are some ins linked to a dest move but that still have some quantity available
            for (demand, out_id) in unreconciled_outs:
                demand = _reconcile_out_with_ins(out_id, ins_per_product[product.id], demand, product_rounding, in_id_to_in_data, ins_per_product, dest_ids_to_in_ids)
                if not float_is_zero(demand, precision_rounding=product_rounding):
                    # Not reconciled
                    _add_line(demand, out_id, replenishment_filled=False)
            # Stock in transit
            if not float_is_zero(transit_stock, precision_rounding=product_rounding):
                _add_line(transit_stock, product=product, in_transit=True)

            # Unused remaining stock.
            if not float_is_zero(free_stock, precision_rounding=product_rounding):
                _add_line(free_stock, product=product)
            # In moves not used.
            for in_id in ins_per_product[product.id]:
                in_data = in_id_to_in_data[in_id]
                if float_is_zero(in_data['qty'], precision_rounding=product_rounding):
                    continue
                _add_line(in_data['qty'], move_in=in_data['move'])
        return lines

    @api.model
    def action_reserve_linked_picks(self, move_id):
        move_id = self.env['stock.move'].browse(move_id)
        move_ids = move_id.browse(move_id._rollup_move_origs()).filtered(lambda m: m.state not in ['draft', 'cancel', 'assigned', 'done'])
        if move_ids:
            move_ids._action_assign()
        return move_ids

    @api.model
    def action_unreserve_linked_picks(self, move_id):
        move_id = self.env['stock.move'].browse(move_id)
        move_ids = move_id.browse(move_id._rollup_move_origs()).filtered(lambda m: m.state not in ['draft', 'cancel', 'done'])
        if move_ids:
            move_ids._do_unreserve()
            move_ids.picking_id.package_level_ids.filtered(lambda p: not p.move_ids).unlink()
        return move_ids


class StockForecastedTemplate(models.AbstractModel):
    _name = 'stock.forecasted_product_template'
    _description = "Stock Replenishment Report"
    _inherit = 'stock.forecasted_product_product'

    @api.model
    def get_report_values(self, docids, data=None):
        return {
            'data': data,
            'doc_ids': docids,
            'doc_model': 'product.template',
            'docs': self._get_report_data(product_template_ids=docids),
            'precision': self.env['decimal.precision'].precision_get('Product Unit of Measure'),
        }
