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
        """Minimal line for `stock.move._get_forecast_availability_outgoing`.

        That caller reads back only `quantity`, `replenishment_filled`, `move_out` and
        `move_in`; resolving the source document of both moves, their display names, the
        formatted dates and the reservation data is all thrown away.
        """
        wanted_ids = self.env.context.get('forecast_availability_move_ids')
        if not move_out or (wanted_ids is not None and move_out.id not in wanted_ids):
            return {'quantity': 0.0, 'replenishment_filled': True, 'move_out': False, 'move_in': False}
        product = product or move_out.product_id
        return {
            'quantity': float_round(quantity, precision_rounding=product.uom_id.rounding),
            'replenishment_filled': replenishment_filled,
            'move_out': move_out,
            'move_in': move_in,
        }

    def _prepare_report_line(self, quantity, move_out=None, move_in=None, replenishment_filled=True, product=False, reserved_move=False, in_transit=False, read=True):
        if self.env.context.get('forecast_availability_only'):
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

    def _get_forecast_availability_lines(self, product_template_ids, product_ids, wh_location_ids, wh_stock_location):
        """Same reconciliation as `_get_report_lines`, run over plain scalars.

        Only used for the `forecast_availability_only` path; the report UI and the MO
        overview keep the generic implementation.

        The generic version walks every out move and every (out, linked move) pair
        through the ORM: each `move.state`, `move.product_id.uom_id.rounding` or
        `move.move_orig_ids.filtered(...)` rebuilds recordsets and re-reads them. Here
        each set of records is prefetched with `fetch()` and then read once into plain
        dicts, so the arithmetic below runs on ids and floats.
        """
        Move = self.env['stock.move']
        wanted_out_ids = self.env.context.get('forecast_availability_move_ids') or frozenset()

        in_domain, out_domain = self._move_confirmed_domain(product_template_ids, product_ids, wh_location_ids)
        past_domain = [('reservation_date', '<=', date.today())]
        future_domain = ['|', ('reservation_date', '>', date.today()), ('reservation_date', '=', False)]

        past_outs = Move.search(AND([out_domain, past_domain]), order='priority desc, date, id')
        future_outs = Move.search(AND([out_domain, future_domain]), order='reservation_date, priority desc, date, id')
        outs = past_outs | future_outs
        ins = Move.search(in_domain, order='priority desc, date, id')

        # Prewarm the cache with the rollups (these also pull the scalar fields).
        outs._rollup_move_origs_fetch()
        ins._rollup_move_dests_fetch()

        # ---- origin graph -----------------------------------------------------------
        # Each level is prefetched in one go, so the attribute access below is served
        # from the cache. Going through the ORM rather than reading the cache directly
        # also computes `move_orig_ids` where a recomputation is still pending.
        orig_map = {}
        frontier = outs
        while frontier:
            frontier.fetch(['move_orig_ids'])
            next_ids = set()
            for move in frontier:
                if move.id not in orig_map:
                    origs = move.move_orig_ids._ids
                    orig_map[move.id] = origs
                    next_ids.update(origs)
            frontier = Move.browse(next_ids - orig_map.keys())

        def rollup(move_id):
            """`_rollup_move_origs` on ids, preserving its visit order."""
            seen = OrderedSet()
            level = [move_id]
            while True:
                unseen = [i for i in level if i not in seen]
                if not unseen:
                    return seen
                seen.update(unseen)
                nxt, taken = [], set()
                for i in unseen:
                    for o in orig_map.get(i, ()):
                        if o not in taken:
                            taken.add(o)
                            nxt.append(o)
                level = nxt

        ins_ids = set(ins._ids)
        linked_ids_per_out = {}
        all_linked_ids = set()
        for out_id in outs._ids:
            linked = [i for i in rollup(out_id) if i not in ins_ids]
            linked_ids_per_out[out_id] = linked
            all_linked_ids.update(linked)

        # ---- scalar columns --------------------------------------------------------
        universe = Move.browse(all_linked_ids | set(outs._ids))
        universe.fetch(['state', 'quantity', 'product_uom', 'product_id', 'product_qty', 'location_id'])
        state_of, qty_of, uom_of = {}, {}, {}
        product_of, product_qty_of, location_of = {}, {}, {}
        # One pass over the recordset: iterating it once per field would build a
        # singleton for every move six times over.
        for move in universe:
            move_id = move.id
            state_of[move_id] = move.state
            qty_of[move_id] = move.quantity
            uom_of[move_id] = move.product_uom.id
            product_of[move_id] = move.product_id.id
            product_qty_of[move_id] = move.product_qty
            location_of[move_id] = move.location_id.id

        # Siblings: the dest moves of the origins, where only state/quantity is needed.
        sibling_ids = set()
        for move_id in all_linked_ids:
            sibling_ids.update(orig_map.get(move_id, ()))
        siblings = Move.browse(sibling_ids)
        siblings.fetch(['move_dest_ids'])
        dest_map = {move.id: move.move_dest_ids._ids for move in siblings}
        dest_ids = {d for dests in dest_map.values() for d in dests}
        # An origin may itself be an incoming move, which is excluded from the linked
        # ids and so absent from the maps above -- pull state/quantity for those too.
        extra = Move.browse((dest_ids | sibling_ids) - set(state_of))
        if extra:
            extra.fetch(['state', 'quantity'])
            for move in extra:
                state_of[move.id] = move.state
                qty_of[move.id] = move.quantity

        # ---- uom / product invariants ----------------------------------------------
        UoM = self.env['uom.uom']
        uoms = UoM.with_context(active_test=False).search([])
        uoms.fetch(['factor', 'rounding', 'category_id'])
        uom_factor = {u.id: u.factor for u in uoms}
        uom_rounding = {u.id: u.rounding for u in uoms}
        uom_category = {u.id: u.category_id.id for u in uoms}

        products = self.env['product.product'].browse({p for p in product_of.values() if p})
        products.fetch(['uom_id'])
        product_uom = {p.id: p.uom_id.id for p in products}
        product_rounding = {pid: uom_rounding.get(uid) for pid, uid in product_uom.items()}

        def convert(qty, from_uom, to_uom):
            """`uom._compute_quantity` on ids."""
            if not from_uom or not qty or not to_uom:
                return qty
            if from_uom != to_uom:
                if uom_category.get(from_uom) != uom_category.get(to_uom):
                    # Different categories: let the generic implementation raise.
                    return UoM.browse(from_uom)._compute_quantity(qty, UoM.browse(to_uom))
                qty = qty / uom_factor[from_uom] * uom_factor[to_uom]
            return float_round(qty, precision_rounding=uom_rounding[to_uom], rounding_method='UP')

        # ---- current stock ----------------------------------------------------------
        out_product_ids = [product_of[i] for i in outs._ids]
        qties = self.env['stock.quant']._read_group(
            [('location_id', 'in', wh_location_ids), ('quantity', '>', 0), ('product_id', 'in', out_product_ids)],
            ['product_id', 'location_id'], ['quantity:sum'])
        wh_stock_sub_location_ids = set(wh_stock_location.search([('id', 'child_of', wh_stock_location.id)])._ids)
        currents = defaultdict(float)
        for product, location, quantity in qties:
            location_id = location.id
            if location_id in wh_stock_sub_location_ids:
                location_id = wh_stock_location.id
            currents[product.id, location_id] += quantity

        # ---- allocation --------------------------------------------------------------
        outs_per_product = defaultdict(list)
        for out_id in outs._ids:
            outs_per_product[product_of[out_id]].append(out_id)

        reserved_of = {}
        taken_of = {}
        for product_id, out_ids in outs_per_product.items():
            used_reserved = defaultdict(float)
            for out_id in out_ids:
                out_qty = product_qty_of[out_id]
                reserved_out = 0
                for move_id in linked_ids_per_out[out_id]:
                    if state_of[move_id] not in ('partially_available', 'assigned'):
                        continue
                    move_product = product_of[move_id]
                    reserved = convert(qty_of[move_id], uom_of[move_id], product_uom.get(move_product))
                    reserved = min(reserved - used_reserved[move_id], out_qty)
                    reserved_out += reserved
                    used_reserved[move_id] += reserved
                    currents[(product_id, location_of[move_id])] -= reserved
                    if float_compare(reserved_out, out_qty, precision_rounding=product_rounding[move_product]) >= 0:
                        break
                reserved_of[out_id] = reserved_out

            for out_id in out_ids:
                demand_out = product_qty_of[out_id] - reserved_of[out_id]
                taken_from_stock_out = 0
                for move_id in linked_ids_per_out[out_id]:
                    if state_of[move_id] in ('draft', 'cancel', 'assigned', 'done'):
                        continue
                    move_product = product_of[move_id]
                    rounding = product_rounding[move_product]
                    reserved = convert(qty_of[move_id], uom_of[move_id], product_uom.get(move_product))
                    demand = max(product_qty_of[move_id] - reserved, 0)
                    demand = min(demand, demand_out)
                    if float_is_zero(demand, precision_rounding=rounding):
                        continue
                    stock_key = (product_id, location_of[move_id])
                    origs = orig_map.get(move_id, ())
                    if origs:
                        move_in_qty = sum(qty_of.get(o, 0.0) for o in origs if state_of.get(o) == 'done')
                        move_out_qty = 0
                        counted = set()
                        for orig in origs:
                            for dest in dest_map.get(orig, ()):
                                if dest in counted or dest == move_id:
                                    continue
                                counted.add(dest)
                                if state_of.get(dest) == 'done':
                                    move_out_qty += qty_of.get(dest, 0.0)
                        move_available_qty = move_in_qty - move_out_qty - reserved
                    else:
                        move_available_qty = currents[stock_key]
                    taken_from_stock = min(demand, move_available_qty, currents[stock_key])
                    if taken_from_stock > 0:
                        currents[stock_key] -= taken_from_stock
                        taken_from_stock_out += taken_from_stock
                    demand_out -= taken_from_stock
                taken_of[out_id] = taken_from_stock_out

        product_sum = defaultdict(float)
        for (product_id, _location_id), quantity in currents.items():
            product_sum[product_id] += quantity

        # ---- incoming moves ------------------------------------------------------------
        dest_ids_to_in_ids, in_id_to_in_data = defaultdict(OrderedSet), {}
        ins_per_product = defaultdict(OrderedSet)
        for in_ in ins:
            in_id_to_in_data[in_.id] = {
                'qty': in_.product_qty,
                'move': in_,
                'move_dests': in_._rollup_move_dests(),
            }
            ins_per_product[in_.product_id.id].add(in_.id)
            for dest in in_id_to_in_data[in_.id]['move_dests']:
                dest_ids_to_in_ids[dest].add(in_.id)

        # ---- lines ----------------------------------------------------------------------
        lines = []

        def add_line(quantity, out_id, move_in=None, replenishment_filled=True):
            if out_id not in wanted_out_ids:
                return
            lines.append({
                'quantity': float_round(quantity, precision_rounding=product_rounding[product_of[out_id]]),
                'replenishment_filled': replenishment_filled,
                'move_out': Move.browse(out_id),
                'move_in': move_in,
            })

        def reconcile_with_ins(out_id, in_ids, demand, rounding):
            to_remove = []
            for in_id in in_ids:
                in_data = in_id_to_in_data[in_id]
                if float_is_zero(in_data['qty'], precision_rounding=rounding):
                    to_remove.append(in_id)
                    continue
                taken_from_in = min(demand, in_data['qty'])
                demand -= taken_from_in
                add_line(taken_from_in, out_id, move_in=in_data['move'])
                in_data['qty'] -= taken_from_in
                if in_data['qty'] <= 0:
                    to_remove.append(in_id)
                if float_is_zero(demand, precision_rounding=rounding):
                    break
            for in_id in to_remove:
                in_data = in_id_to_in_data[in_id]
                product_id = in_data['move'].product_id.id
                for dest in in_data['move_dests']:
                    dest_ids_to_in_ids[dest].remove(in_id)
                ins_per_product[product_id].remove(in_id)
            return demand

        # Same product visit order as `(ins | outs).product_id`.
        product_order, seen_products = [], set()
        for move_id in list(ins._ids) + list(outs._ids):
            product_id = product_of.get(move_id) or ins.browse(move_id).product_id.id
            if product_id not in seen_products:
                seen_products.add(product_id)
                product_order.append(product_id)

        for product_id in product_order:
            rounding = product_rounding.get(product_id)
            if rounding is None:
                rounding = self.env['product.product'].browse(product_id).uom_id.rounding
                product_rounding[product_id] = rounding
            unreconciled_outs = []
            free_stock = currents[product_id, wh_stock_location.id]
            transit_stock = product_sum[product_id] - free_stock
            for out_id in outs_per_product[product_id]:
                reserved_out = reserved_of[out_id]
                taken_from_stock_out = taken_of[out_id]
                demand_out = product_qty_of[out_id]

                if reserved_out > 0:
                    demand_out = max(demand_out - reserved_out, 0)
                    add_line(reserved_out, out_id)
                if float_is_zero(demand_out, precision_rounding=rounding):
                    continue

                if taken_from_stock_out > 0:
                    demand_out = max(demand_out - taken_from_stock_out, 0)
                    add_line(taken_from_stock_out, out_id)
                if float_is_zero(demand_out, precision_rounding=rounding):
                    continue

                unreservable_qty = min(demand_out, transit_stock)
                if unreservable_qty > 0:
                    demand_out -= unreservable_qty
                    transit_stock -= unreservable_qty
                    add_line(unreservable_qty, out_id)
                if float_is_zero(demand_out, precision_rounding=rounding):
                    continue

                demand_out = reconcile_with_ins(out_id, dest_ids_to_in_ids[out_id], demand_out, rounding)
                if not float_is_zero(demand_out, precision_rounding=rounding):
                    unreconciled_outs.append((demand_out, out_id))

            for (demand, out_id) in unreconciled_outs:
                demand = reconcile_with_ins(out_id, ins_per_product[product_id], demand, rounding)
                if not float_is_zero(demand, precision_rounding=rounding):
                    add_line(demand, out_id, replenishment_filled=False)
            # Product-level and in-only lines carry no move_out; the caller skips them.
        return lines

    def _get_report_lines(self, product_template_ids, product_ids, wh_location_ids, wh_stock_location, read=True):
        if self.env.context.get('forecast_availability_only'):
            # An override may still decline the fast path by returning None.
            lines = self._get_forecast_availability_lines(product_template_ids, product_ids, wh_location_ids, wh_stock_location)
            if lines is not None:
                return lines

        def _get_out_move_reserved_data(out, linked_moves, used_reserved_moves, currents):
            reserved_out = 0
            # the move to show when qty is reserved
            reserved_move = self.env['stock.move']
            for move in linked_moves:
                if move.state not in ('partially_available', 'assigned'):
                    continue
                # count reserved stock.
                reserved = move.product_uom._compute_quantity(move.quantity, move.product_id.uom_id)
                # check if the move reserved qty was counted before (happens if multiple outs share pick/pack)
                reserved = min(reserved - used_reserved_moves[move], out.product_qty)
                if reserved and not reserved_move:
                    reserved_move = move
                # add to reserved line data
                reserved_out += reserved
                used_reserved_moves[move] += reserved
                currents[(out.product_id.id, move.location_id.id)] -= reserved
                if float_compare(reserved_out, out.product_qty, precision_rounding=move.product_id.uom_id.rounding) >= 0:
                    break

            return {
                'reserved': reserved_out,
                'reserved_move': reserved_move,
                'linked_moves': linked_moves,
            }

        def _get_out_move_taken_from_stock_data(out, currents, reserved_data):
            reserved_out = reserved_data['reserved']
            demand_out = out.product_qty - reserved_out
            linked_moves = reserved_data['linked_moves']
            taken_from_stock_out = 0
            for move in linked_moves:
                if move.state in ('draft', 'cancel', 'assigned', 'done'):
                    continue
                reserved = move.product_uom._compute_quantity(move.quantity, move.product_id.uom_id)
                demand = max(move.product_qty - reserved, 0)
                # to make sure we don't demand more than the out (useful when same pick/pack goes to multiple out)
                demand = min(demand, demand_out)
                if float_is_zero(demand, precision_rounding=move.product_id.uom_id.rounding):
                    continue
                # check available qty for move if chained, move available is what was move by orig moves
                if move.move_orig_ids:
                    move_in_qty = sum(move.move_orig_ids.filtered(lambda m: m.state == 'done').mapped('quantity'))
                    sibling_moves = (move.move_orig_ids.move_dest_ids - move)
                    move_out_qty = sum(sibling_moves.filtered(lambda m: m.state == 'done').mapped('quantity'))
                    move_available_qty = move_in_qty - move_out_qty - reserved
                else:
                    move_available_qty = currents[(out.product_id.id, move.location_id.id)]
                # count taken from stock, but avoid taking more than whats in stock in case of move origs,
                # this can happen if stock adjustment is done after orig moves are done
                taken_from_stock = min(demand, move_available_qty, currents[(out.product_id.id, move.location_id.id)])
                if taken_from_stock > 0:
                    currents[(out.product_id.id, move.location_id.id)] -= taken_from_stock
                    taken_from_stock_out += taken_from_stock
                demand_out -= taken_from_stock
            return {
                'taken_from_stock': taken_from_stock_out,
            }

        def _reconcile_out_with_ins(lines, out, ins, demand, product_rounding, in_id_to_in_data, ins_per_product, dest_ids_to_in_ids, read=True):
            ins_to_remove = []
            for in_id in ins:
                in_data = in_id_to_in_data[in_id]
                if float_is_zero(in_data['qty'], precision_rounding=product_rounding):
                    ins_to_remove.append(in_id)
                    continue
                taken_from_in = min(demand, in_data['qty'])
                demand -= taken_from_in
                lines.append(self._prepare_report_line(taken_from_in, move_in=in_data['move'], move_out=out, read=read))
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

        past_outs = self.env['stock.move'].search(AND([out_domain, past_domain]), order='priority desc, date, id')
        future_outs = self.env['stock.move'].search(AND([out_domain, future_domain]), order='reservation_date, priority desc, date, id')

        outs = past_outs | future_outs

        ins = self.env['stock.move'].search(in_domain, order='priority desc, date, id')
        # Prewarm cache with rollups
        outs._rollup_move_origs_fetch()
        ins._rollup_move_dests_fetch()

        linked_moves_per_out = {}
        ins_ids = set(ins._ids)
        for out in outs:
            linked_move_ids = out._rollup_move_origs() - ins_ids
            linked_moves_per_out[out] = self.env['stock.move'].browse(linked_move_ids)

        # Gather all linked moves
        all_linked_move_ids = {
            _id for _ids in linked_moves_per_out.values() for _id in _ids._ids
        }
        all_linked_moves = self.env['stock.move'].browse(all_linked_move_ids)

        # Prewarm cache with sibling move's state/quantity
        all_linked_moves.fetch(['move_orig_ids'])
        all_linked_moves.move_orig_ids.fetch(['move_dest_ids'])
        all_linked_moves.move_orig_ids.move_dest_ids.fetch(['state', 'quantity'])

        # Share prefetch ids among all linked moves for performance
        for out, linked_moves in linked_moves_per_out.items():
            linked_moves_per_out[out] = linked_moves.with_prefetch(
                all_linked_moves._prefetch_ids
            )

        outs_per_product = defaultdict(list)
        for out in outs:
            outs_per_product[out.product_id.id].append(out)

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

        qties = self.env['stock.quant']._read_group([('location_id', 'in', wh_location_ids), ('quantity', '>', 0), ('product_id', 'in', outs.product_id.ids)],
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
        for _, out_moves in outs_per_product.items():
            # to handle multiple out wtih same in (ex: same pick/pack for 2 outs)
            used_reserved_moves = defaultdict(float)
            # for all out moves, check for linked moves and count reserved quantity
            for out in out_moves:
                moves_data[out] = _get_out_move_reserved_data(
                    out, linked_moves_per_out[out], used_reserved_moves, currents
                )
            # another loop to remove qty from current stock after reserved is counted for
            for out in out_moves:
                data = _get_out_move_taken_from_stock_data(out, currents, moves_data[out])
                moves_data[out].update(data)
        product_sum = defaultdict(float)
        for product_loc, quantity in currents.items():
            product_sum[product_loc[0]] += quantity
        lines = []
        for product in (ins | outs).product_id:
            product_rounding = product.uom_id.rounding
            unreconciled_outs = []
            # remaining stock
            free_stock = currents[product.id, wh_stock_location.id]
            transit_stock = product_sum[product.id] - free_stock
            # add report lines and see if remaining demand can be reconciled by unreservable stock or ins
            for out in outs_per_product[product.id]:
                reserved_out = moves_data[out].get('reserved')
                taken_from_stock_out = moves_data[out].get('taken_from_stock')
                reserved_move = moves_data[out].get('reserved_move')
                demand_out = out.product_qty
                # Reconcile with the reserved stock.
                if reserved_out > 0:
                    demand_out = max(demand_out - reserved_out, 0)
                    in_transit = bool(reserved_move.move_orig_ids)
                    lines.append(self._prepare_report_line(reserved_out, move_out=out, reserved_move=reserved_move, in_transit=in_transit, read=read))

                if float_is_zero(demand_out, precision_rounding=product_rounding):
                    continue

                # Reconcile with the current stock.
                if taken_from_stock_out > 0:
                    demand_out = max(demand_out - taken_from_stock_out, 0)
                    lines.append(self._prepare_report_line(taken_from_stock_out, move_out=out, read=read))

                if float_is_zero(demand_out, precision_rounding=product_rounding):
                    continue

                # Reconcile with unreservable stock, quantities that are in stock but not in correct location to reserve from (in transit)
                unreservable_qty = min(demand_out, transit_stock)
                if unreservable_qty > 0:
                    demand_out -= unreservable_qty
                    transit_stock -= unreservable_qty
                    lines.append(self._prepare_report_line(unreservable_qty, move_out=out, in_transit=True, read=read))

                if float_is_zero(demand_out, precision_rounding=product_rounding):
                    continue

                # Reconcile with the ins.
                demand_out = _reconcile_out_with_ins(lines, out, dest_ids_to_in_ids[out.id], demand_out, product_rounding, in_id_to_in_data, ins_per_product, dest_ids_to_in_ids, read=read)

                if not float_is_zero(demand_out, precision_rounding=product_rounding):
                    unreconciled_outs.append((demand_out, out))

            # Another pass, in case there are some ins linked to a dest move but that still have some quantity available
            for (demand, out) in unreconciled_outs:
                demand = _reconcile_out_with_ins(lines, out, ins_per_product[product.id], demand, product_rounding, in_id_to_in_data, ins_per_product, dest_ids_to_in_ids, read=read)
                if not float_is_zero(demand, precision_rounding=product_rounding):
                    # Not reconciled
                    lines.append(self._prepare_report_line(demand, move_out=out, replenishment_filled=False, read=read))
            # Stock in transit
            if not float_is_zero(transit_stock, precision_rounding=product_rounding):
                lines.append(self._prepare_report_line(transit_stock, product=product, in_transit=True, read=read))

            # Unused remaining stock.
            if not float_is_zero(free_stock, precision_rounding=product_rounding):
                lines.append(self._prepare_report_line(free_stock, product=product, read=read))
            # In moves not used.
            for in_id in ins_per_product[product.id]:
                in_data = in_id_to_in_data[in_id]
                if float_is_zero(in_data['qty'], precision_rounding=product_rounding):
                    continue
                lines.append(self._prepare_report_line(in_data['qty'], move_in=in_data['move'], read=read))
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
