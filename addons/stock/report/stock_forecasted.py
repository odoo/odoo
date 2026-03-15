# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import date, datetime

from odoo import api, models
from odoo.fields import Domain
from odoo.tools import float_is_zero, format_date, OrderedSet


class StockForecasted_Product_Product(models.AbstractModel):
    _name = 'stock.forecasted_product_product'
    _description = "Stock Replenishment Report"

    @api.model
    def get_report_values(self, docids, data=None):
        return {
            'data': data,
            'doc_ids': docids,
            'doc_model': 'product.product',
            'docs': self._get_report_data(product_ids=docids),
            'precision': self.env['decimal.precision'].precision_get('Product Unit'),
        }

    def _product_domain(self, product_template_ids, product_ids):
        if product_template_ids:
            return [('product_tmpl_id', 'in', product_template_ids), ('product_id.active', '=', True)]
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

    def _get_products(self, product_template_ids, product_ids):
        """Return a list of product.product records based on the provided product_template_ids or product_ids."""
        if product_template_ids:
            return self.env['product.template'].browse(product_template_ids).product_variant_ids
        if product_ids:
            return self.env['product.product'].browse(product_ids)
        return self.env['product.product']

    def _get_product_quantities(self, res, product_template_ids, product_ids):
        if 'product' not in res:
            res['product'] = dict()
        products = self._get_products(product_template_ids, product_ids)
        for product in products:
            if product.id not in res['product']:
                res['product'][product.id] = {
                    'uom': product.uom_id.display_name,
                    'quantity_on_hand': product.qty_available,
                    'virtual_available': product.virtual_available,
                    'free_qty': product.free_qty,
                    'incoming_qty': product.incoming_qty,
                    'outgoing_qty': product.outgoing_qty,
                    'qty': {
                        'in':  0.0,
                        'out':  0.0,
                    },
                }

    def _add_product_quantities(self, res, product_template_ids, product_ids, var_name, qty_in={}, qty_out={}):
        products = self._get_products(product_template_ids, product_ids)
        for product in products:
            res['product'][product.id][var_name] = {
                'in': qty_in.get(product.id, 0.0),
                'out': qty_out.get(product.id, 0.0),
            }
            res['product'][product.id]['qty']['in'] += qty_in.get(product.id, 0.0)
            res['product'][product.id]['qty']['out'] += qty_out.get(product.id, 0.0)

    def _get_product_leadtime(self, res, product_template_ids, product_ids):
        """Return a dictionary with product lead times."""
        products = self._get_products(product_template_ids, product_ids)
        location = self._get_warehouse().lot_stock_id
        for product in products:
            rule = product._get_rules_from_location(location)
            leadtime = rule._get_lead_days(product)
            if not leadtime:
                leadtime = [{'total_delay': 0}, {}]
            res['product'][product.id]['leadtime'] = {
                'total_delay': leadtime[0].get('total_delay', 0),
                'details': leadtime[1]
            }

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

        in_domain, out_domain = self._move_draft_domain(product_template_ids, product_ids, wh_location_ids)
        in_sum = {k.id: v for k, v in self.env['stock.move']._read_group(in_domain, aggregates=['product_qty:sum'], groupby=['product_id'])}
        out_sum = {k.id: v for k, v in self.env['stock.move']._read_group(out_domain, aggregates=['product_qty:sum'], groupby=['product_id'])}

        self._get_product_quantities(res, product_template_ids, product_ids)
        self._add_product_quantities(res, product_template_ids, product_ids, 'draft_picking_qty', in_sum, out_sum)
        self._get_product_leadtime(res, product_template_ids, product_ids)

        return res

    def _get_reservation_data(self, move):
        return {
            '_name': move.picking_id._name,
            'name': move.picking_id.name,
            'id': move.picking_id.id
        }

    def _get_warehouse(self):
        return self.env['stock.warehouse'].browse(self.env.context.get('warehouse_id', False)) or self.env['stock.warehouse'].search([['active', '=', True]])[0]

    def _get_report_data(self, product_template_ids=False, product_ids=False):
        assert product_template_ids or product_ids
        res = {}

        warehouse = self._get_warehouse()
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

    def _prepare_report_line(self, quantity, move_out=None, move_in=None, replenishment_filled=True, product=False, reserved_move=False, in_transit=False, read=True):
        product = product or (move_out.product_id if move_out else move_in.product_id)
        is_late = move_out.date < move_in.date if (move_out and move_in) else False
        delivery_late = move_out.state != 'done' and move_out.date < datetime.now() if move_out else False
        receipt_late = move_in.state != 'done' and move_in.date < datetime.now() if move_in else False

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
            'delivery_late': delivery_late,
            'receipt_late': receipt_late,
            'quantity': product.uom_id.round(quantity),
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

    def _get_quant_domain(self, location_ids, products):
        return [('location_id', 'in', location_ids), ('quantity', '>', 0), ('product_id', 'in', products.ids)]

    def _get_report_lines(self, product_template_ids, product_ids, wh_location_ids, wh_stock_location, read=True):

        def _get_out_move_reserved_data(out, linked_moves, used_reserved_moves, currents, wh_stock_location, wh_stock_sub_location_ids):
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
                # any sublocation qties needs to be reserved to the main stock location qty as well
                if move.location_id.id in wh_stock_sub_location_ids:
                    currents[out.product_id.id, wh_stock_location.id] -= reserved
                currents[(out.product_id.id, move.location_id.id)] -= reserved
                if move.product_id.uom_id.compare(reserved_out, out.product_qty) >= 0:
                    break

            return {
                'reserved': reserved_out,
                'reserved_move': reserved_move,
                'linked_moves': linked_moves,
            }

        def _get_out_move_taken_from_stock_data(out, currents, reserved_data, wh_stock_location, wh_stock_sub_location_ids):
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
                if move.product_id.uom_id.is_zero(demand):
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
                    # any sublocation qties needs to be removed to the main stock location qty as well
                    if move.location_id.id in wh_stock_sub_location_ids:
                        currents[out.product_id.id, wh_stock_location.id] -= taken_from_stock
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

        past_outs = self.env['stock.move'].search(Domain.AND([out_domain, past_domain]), order='priority desc, date, id')
        future_outs = self.env['stock.move'].search(Domain.AND([out_domain, future_domain]), order='reservation_date, priority desc, date, id')

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

        qties = self.env['stock.quant']._read_group(
            self._get_quant_domain(wh_location_ids, outs.product_id | self._get_products(product_template_ids, product_ids)),
            ['product_id', 'location_id'], ['quantity:sum']
        )
        wh_stock_sub_location_ids = set(
            (wh_stock_location.search([('id', 'child_of', wh_stock_location.id)]) - wh_stock_location)._ids
        )
        currents = defaultdict(float)
        for product, location, quantity in qties:
            location_id = location.id
            # any sublocation qties will be added to the main stock location qty as well
            if location_id in wh_stock_sub_location_ids:
                currents[product.id, wh_stock_location.id] += quantity
            currents[(product.id, location_id)] += quantity
        moves_data = {}
        for out_moves in outs_per_product.values():
            # to handle multiple out wtih same in (ex: same pick/pack for 2 outs)
            used_reserved_moves = defaultdict(float)
            # for all out moves, check for linked moves and count reserved quantity
            for out in out_moves:
                moves_data[out] = _get_out_move_reserved_data(
                    out, linked_moves_per_out[out], used_reserved_moves, currents, wh_stock_location, wh_stock_sub_location_ids
                )
            # another loop to remove qty from current stock after reserved is counted for
            for out in out_moves:
                data = _get_out_move_taken_from_stock_data(out, currents, moves_data[out], wh_stock_location, wh_stock_sub_location_ids)
                moves_data[out].update(data)
        product_sum = defaultdict(float)
        for product_loc, quantity in currents.items():
            if product_loc[1] not in wh_stock_sub_location_ids:
                product_sum[product_loc[0]] += quantity
        lines = []
        for product in (ins | outs).product_id | self._get_products(product_template_ids, product_ids):
            lines_init_count = len(lines)
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
            if not float_is_zero(free_stock, precision_rounding=product.uom_id.rounding) or lines_init_count == len(lines):
                lines += self._free_stock_lines(product, free_stock, moves_data, wh_location_ids, read)

            # In moves not used.
            for in_id in ins_per_product[product.id]:
                in_data = in_id_to_in_data[in_id]
                if float_is_zero(in_data['qty'], precision_rounding=product_rounding):
                    continue
                lines.append(self._prepare_report_line(in_data['qty'], move_in=in_data['move'], read=read))
        return lines

    def _free_stock_lines(self, product, free_stock, moves_data, wh_location_ids, read):
            return [self._prepare_report_line(free_stock, product=product, read=read)]

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
        return move_ids


class StockForecasted_Product_Template(models.AbstractModel):
    _name = 'stock.forecasted_product_template'
    _description = "Stock Replenishment Report"
    _inherit = ['stock.forecasted_product_product']

    @api.model
    def get_report_values(self, docids, data=None):
        return {
            'data': data,
            'doc_ids': docids,
            'doc_model': 'product.template',
            'docs': self._get_report_data(product_template_ids=docids),
            'precision': self.env['decimal.precision'].precision_get('Product Unit'),
        }
