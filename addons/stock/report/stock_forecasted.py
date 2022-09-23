# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
import copy

from odoo import api, models
from odoo.tools import float_is_zero, format_date, float_round, float_compare


class ReplenishmentReport(models.AbstractModel):
    _name = 'report.stock.report_product_product_replenishment'
    _description = "Stock Replenishment Report"

    def _product_domain(self, product_template_ids, product_variant_ids):
        if product_template_ids:
            return [('product_tmpl_id', 'in', product_template_ids)]
        return [('product_id', 'in', product_variant_ids)]

    def _move_domain(self, product_template_ids, product_variant_ids, wh_location_ids):
        move_domain = self._product_domain(product_template_ids, product_variant_ids)
        move_domain += [('product_uom_qty', '!=', 0)]
        out_domain = move_domain + [
            '&',
            ('location_id', 'in', wh_location_ids),
            ('location_dest_id', 'not in', wh_location_ids),
        ]
        in_domain = move_domain + [
            '&',
            ('location_id', 'not in', wh_location_ids),
            ('location_dest_id', 'in', wh_location_ids),
        ]
        return in_domain, out_domain

    def _move_draft_domain(self, product_template_ids, product_variant_ids, wh_location_ids):
        in_domain, out_domain = self._move_domain(product_template_ids, product_variant_ids, wh_location_ids)
        in_domain += [('state', '=', 'draft')]
        out_domain += [('state', '=', 'draft')]
        return in_domain, out_domain

    def _move_confirmed_domain(self, product_template_ids, product_variant_ids, wh_location_ids):
        in_domain, out_domain = self._move_domain(product_template_ids, product_variant_ids, wh_location_ids)
        out_domain += [('state', 'in', ['waiting', 'assigned', 'confirmed', 'partially_available'])]
        in_domain += [('state', 'in', ['waiting', 'assigned', 'confirmed', 'partially_available'])]
        return in_domain, out_domain

    def _compute_draft_quantity_count(self, product_template_ids, product_variant_ids, wh_location_ids):
        in_domain, out_domain = self._move_draft_domain(product_template_ids, product_variant_ids, wh_location_ids)
        incoming_moves = self.env['stock.move']._read_group(in_domain, ['product_qty:sum'], 'product_id')
        outgoing_moves = self.env['stock.move']._read_group(out_domain, ['product_qty:sum'], 'product_id')
        in_sum = sum(move['product_qty'] for move in incoming_moves)
        out_sum = sum(move['product_qty'] for move in outgoing_moves)
        return {
            'draft_picking_qty': {
                'in': in_sum,
                'out': out_sum
            },
            'qty': {
                'in': in_sum,
                'out': out_sum
            }
        }

    @api.model
    def _fields_for_serialized_moves(self):
        return ['picking_id', 'state']

    def _get_reservation_data(self, move):
        return {
            '_name': move.picking_id._name,
            'name': move.picking_id.name,
            'id': move.picking_id.id
        }

    def _serialize_docs(self, docs, product_template_ids=False, product_variant_ids=False):
        """
        Since conversion from report to owl client_action, adapt/override this method to make records available from js code.
        """
        res = copy.copy(docs)
        if product_template_ids:
            res['product_templates'] = docs['product_templates'].read(fields=['id', 'display_name'])
            product_variants = []
            for pv in docs['product_variants']:
                product_variants.append({
                        'id' : pv.id,
                        'combination_name' : pv.product_template_attribute_value_ids._get_combination_name(),
                    })
            res['product_variants'] = product_variants
        elif product_variant_ids:
            res['product_variants'] = docs['product_variants'].read(fields=['id', 'display_name'])

        res['lines'] = []
        for index, line in enumerate(docs['lines']):
            res['lines'].append({
                'index': index,
                'document_in' : {
                    '_name' : line['document_in']._name,
                    'id' : line['document_in']['id'],
                    'name' : line['document_in']['name'],
                } if line['document_in'] else False,
                'document_out' : {
                    '_name' : line['document_out']._name,
                    'id' : line['document_out']['id'],
                    'name' : line['document_out']['name'],
                } if line['document_out'] else False,
                'uom_id' : line['uom_id'].read()[0],
                'move_out' : line['move_out'].read(self._fields_for_serialized_moves())[0] if line['move_out'] else False,
                'move_in' : line['move_in'].read(self._fields_for_serialized_moves())[0] if line['move_in'] else False,
                'product': line['product'],
                'replenishment_filled': line['replenishment_filled'],
                'receipt_date': line['receipt_date'],
                'delivery_date': line['delivery_date'],
                'is_late': line['is_late'],
                'quantity': line['quantity'],
                'reservation': self._get_reservation_data(line['reserved_move']) if line['reserved_move'] else False,
                'is_matched': line['is_matched'],
                'in_transit': line['in_transit'],
            })
            if line['move_out'] and line['move_out']['picking_id']:
                res['lines'][-1]['move_out'].update({
                    'picking_id' : line['move_out']['picking_id'].read(fields=['id', 'priority'])[0],
                    })

        return res

    @api.model
    def get_report_values(self, docids, data=None, serialize=False):
        docs = self._get_report_data(product_variant_ids=docids)
        if serialize:
            docs = self._serialize_docs(docs, product_variant_ids=docids)
        return {
            'data': data,
            'doc_ids': docids,
            'doc_model': 'product.product',
            'docs': docs,
            'precision': self.env['decimal.precision'].precision_get('Product Unit of Measure'),
        }

    def _get_report_data(self, product_template_ids=False, product_variant_ids=False):
        assert product_template_ids or product_variant_ids
        res = {}

        if self.env.context.get('warehouse'):
            warehouse = self.env['stock.warehouse'].browse(self.env.context.get('warehouse'))
        else:
            warehouse = self.env['stock.warehouse'].browse(self.get_warehouses()[0]['id'])

        wh_location_ids = [loc['id'] for loc in self.env['stock.location'].search_read(
            [('id', 'child_of', warehouse.view_location_id.id)],
            ['id'],
        )]
        # any quantities in this location will be considered free stock, others are free stock in transit
        wh_stock_location = warehouse.lot_stock_id

        # Get the products we're working, fill the rendering context with some of their attributes.
        if product_template_ids:
            product_templates = self.env['product.template'].browse(product_template_ids)
            res['product_templates'] = product_templates
            res['product_templates_ids'] = product_templates.ids
            res['product_variants'] = product_templates.product_variant_ids
            res['multiple_product'] = len(product_templates.product_variant_ids) > 1
            res['uom'] = product_templates[:1].uom_id.display_name
            res['quantity_on_hand'] = sum(product_templates.mapped('qty_available'))
            res['virtual_available'] = sum(product_templates.mapped('virtual_available'))
            res['incoming_qty'] = sum(product_templates.mapped('incoming_qty'))
            res['outgoing_qty'] = sum(product_templates.mapped('outgoing_qty'))
        elif product_variant_ids:
            product_variants = self.env['product.product'].browse(product_variant_ids)
            res['product_templates'] = False
            res['product_variants'] = product_variants
            res['product_variants_ids'] = product_variants.ids
            res['multiple_product'] = len(product_variants) > 1
            res['uom'] = product_variants[:1].uom_id.display_name
            res['quantity_on_hand'] = sum(product_variants.mapped('qty_available'))
            res['virtual_available'] = sum(product_variants.mapped('virtual_available'))
            res['incoming_qty'] = sum(product_variants.mapped('incoming_qty'))
            res['outgoing_qty'] = sum(product_variants.mapped('outgoing_qty'))
        res.update(self._compute_draft_quantity_count(product_template_ids, product_variant_ids, wh_location_ids))

        res['lines'] = self._get_report_lines(product_template_ids, product_variant_ids, wh_location_ids, wh_stock_location)
        return res

    def _prepare_report_line(self, quantity, move_out=None, move_in=None, replenishment_filled=True, product=False, reserved_move=False, in_transit=False):
        product = product or (move_out.product_id if move_out else move_in.product_id)
        is_late = move_out.date < move_in.date if (move_out and move_in) else False

        move_to_match_ids = self.env.context.get('move_to_match_ids') or []
        move_in_id = move_in.id if move_in else None
        move_out_id = move_out.id if move_out else None
        # move_out can be a move in a chain, to get the document we use the move_dest_ids
        last_move_out = move_out
        while last_move_out and last_move_out.move_dest_ids:
            last_move_out = last_move_out.move_dest_ids
        return {
            'document_in': move_in._get_source_document() if move_in else False,
            'document_out': last_move_out._get_source_document() if move_out else False,
            'product': {
                'id': product.id,
                'display_name': product.display_name
            },
            'replenishment_filled': replenishment_filled,
            'uom_id': product.uom_id,
            'receipt_date': format_date(self.env, move_in.date) if move_in else False,
            'delivery_date': format_date(self.env, move_out.date) if move_out else False,
            'is_late': is_late,
            'quantity': float_round(quantity, precision_rounding=product.uom_id.rounding),
            'move_out': move_out,
            'move_in': move_in,
            'reserved_move': reserved_move,
            'in_transit': in_transit,
            'is_matched': any(move_id in [move_in_id, move_out_id] for move_id in move_to_match_ids),
        }

    def _get_report_lines(self, product_template_ids, product_variant_ids, wh_location_ids, wh_stock_location):

        def _get_out_move_reserved_data(out, ins, used_reserved_moves):
            reserved_out = 0
            linked_moves = self.env['stock.move'].browse(out._rollup_move_origs()).filtered(lambda m: m.id not in ins.ids)
            # the move to show when qty is reserved
            reserved_move = self.env['stock.move']
            for move in linked_moves:
                if move.state not in ('partially_available', 'assigned'):
                    continue
                # count reserved stock.
                reserved = move.product_uom._compute_quantity(move.reserved_availability, move.product_id.uom_id)
                # check if the move reserved qty was counted before (happens if multiple outs share pick/pack)
                reserved = min(reserved - used_reserved_moves[move], out.product_qty)
                if reserved and not reserved_move:
                    reserved_move = move
                # add to reserved line data
                reserved_out += reserved
                used_reserved_moves[move] += reserved
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
                reserved = move.product_uom._compute_quantity(move.reserved_availability, move.product_id.uom_id)
                demand = max(move.product_qty - reserved, 0)
                # to make sure we don't demand more than the out (useful when same pick/pack goes to multiple out)
                demand = min(demand, demand_out)
                if float_is_zero(demand, precision_rounding=move.product_id.uom_id.rounding):
                    continue
                # check available qty for move if chained, move available is what was move by orig moves
                if move.move_orig_ids:
                    move_in_qty = sum(move.move_orig_ids.filtered(lambda m: m.state == 'done').mapped('quantity_done'))
                    sibling_moves = (move.move_orig_ids.move_dest_ids - move)
                    move_out_qty = sum(sibling_moves.filtered(lambda m: m.state == 'done').mapped('quantity_done'))
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

        def _reconcile_out_with_ins(lines, out, ins, demand, product_rounding, only_matching_move_dest=True):
            index_to_remove = []
            for index, in_ in enumerate(ins):
                if float_is_zero(in_['qty'], precision_rounding=product_rounding):
                    index_to_remove.append(index)
                    continue
                if only_matching_move_dest and in_['move_dests'] and out.id not in in_['move_dests']:
                    continue
                taken_from_in = min(demand, in_['qty'])
                demand -= taken_from_in
                lines.append(self._prepare_report_line(taken_from_in, move_in=in_['move'], move_out=out))
                in_['qty'] -= taken_from_in
                if in_['qty'] <= 0:
                    index_to_remove.append(index)
                if float_is_zero(demand, precision_rounding=product_rounding):
                    break
            for index in reversed(index_to_remove):
                del ins[index]
            return demand

        in_domain, out_domain = self._move_confirmed_domain(
            product_template_ids, product_variant_ids, wh_location_ids
        )

        outs = self.env['stock.move'].search(out_domain, order='reservation_date, priority desc, date, id')
        outs_per_product = defaultdict(list)
        for out in outs:
            outs_per_product[out.product_id.id].append(out)

        ins = self.env['stock.move'].search(in_domain, order='priority desc, date, id')
        ins_per_product = defaultdict(list)
        for in_ in ins:
            ins_per_product[in_.product_id.id].append({
                'qty': in_.product_qty,
                'move': in_,
                'move_dests': in_._rollup_move_dests()
            })

        qties = self.env['stock.quant']._read_group([('location_id', 'in', wh_location_ids), ('quantity', '>', 0), ('product_id', 'in', outs.product_id.ids)],
                                                    ['product_id', 'location_id', 'quantity:sum', 'reserved_quantity:sum'], ['product_id', 'location_id'], lazy=False)
        wh_stock_sub_location_ids = wh_stock_location.search([('id', 'child_of', wh_stock_location.id)]).ids
        currents = defaultdict(float)
        for qty in qties:
            location_id = qty['location_id'][0]
            # any sublocation qties will be added to the main stock location qty
            if location_id in wh_stock_sub_location_ids:
                location_id = wh_stock_location.id
            currents[(qty['product_id'][0], location_id)] += qty['quantity'] - qty['reserved_quantity']
        moves_data = {}
        for _, out_moves in outs_per_product.items():
            # to handle multiple out wtih same in (ex: same pick/pack for 2 outs)
            used_reserved_moves = defaultdict(float)
            # for all out moves, check for linked moves and remove qty from current stock
            for out in out_moves:
                moves_data[out] = _get_out_move_reserved_data(out, ins, used_reserved_moves)
                data = _get_out_move_taken_from_stock_data(out, currents, moves_data[out])
                moves_data[out].update(data)
        lines = []
        for product in (ins | outs).product_id:
            product_rounding = product.uom_id.rounding
            unreconciled_outs = []
            # remaining stock
            free_stock = currents[product.id, wh_stock_location.id]
            transit_stock = sum([v if k[0] == product.id else 0 for k, v in currents.items()]) - free_stock
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
                    lines.append(self._prepare_report_line(reserved_out, move_out=out, reserved_move=reserved_move, in_transit=in_transit))

                if float_is_zero(demand_out, precision_rounding=product_rounding):
                    continue

                # Reconcile with the current stock.
                if taken_from_stock_out > 0:
                    demand_out = max(demand_out - taken_from_stock_out, 0)
                    lines.append(self._prepare_report_line(taken_from_stock_out, move_out=out))

                if float_is_zero(demand_out, precision_rounding=product_rounding):
                    continue

                # Reconcile with unreservable stock, quantities that are in stock but not in correct location to reserve from (in transit)
                unreservable_qty = min(demand_out, transit_stock)
                if unreservable_qty > 0:
                    demand_out -= unreservable_qty
                    transit_stock -= unreservable_qty
                    lines.append(self._prepare_report_line(unreservable_qty, move_out=out, in_transit=True))

                if float_is_zero(demand_out, precision_rounding=product_rounding):
                    continue

                # Reconcile with the ins.
                if not float_is_zero(demand_out, precision_rounding=product_rounding):
                    demand_out = _reconcile_out_with_ins(lines, out, ins_per_product[product.id], demand_out, product_rounding, only_matching_move_dest=True)
                if not float_is_zero(demand_out, precision_rounding=product_rounding):
                    unreconciled_outs.append((demand_out, out))

            # Another pass, in case there are some ins linked to a dest move but that still have some quantity available
            for (demand, out) in unreconciled_outs:
                demand = _reconcile_out_with_ins(lines, out, ins_per_product[product.id], demand, product_rounding, only_matching_move_dest=False)
                if not float_is_zero(demand, precision_rounding=product_rounding):
                    # Not reconciled
                    lines.append(self._prepare_report_line(demand, move_out=out, replenishment_filled=False))
            # Stock in transit
            if not float_is_zero(transit_stock, precision_rounding=product_rounding):
                lines.append(self._prepare_report_line(transit_stock, product=product, in_transit=True))

            # Unused remaining stock.
            if not float_is_zero(free_stock, precision_rounding=product_rounding):
                lines.append(self._prepare_report_line(free_stock, product=product))
            # In moves not used.
            for in_ in ins_per_product[product.id]:
                if float_is_zero(in_['qty'], precision_rounding=product_rounding):
                    continue
                lines.append(self._prepare_report_line(in_['qty'], move_in=in_['move']))
        return lines

    @api.model
    def get_warehouses(self):
        return self.env['stock.warehouse'].search_read(fields=['id', 'name', 'code'])

    @api.model
    def action_reserve_linked_picks(self, move_id):
        move_id = self.env['stock.move'].browse(move_id)
        move_id.browse(move_id._rollup_move_origs()).picking_id.filtered(lambda p: p.state not in ['draft', 'cancel', 'done']).action_assign()

    @api.model
    def action_unreserve_linked_picks(self, move_id):
        move_id = self.env['stock.move'].browse(move_id)
        move_id.browse(move_id._rollup_move_origs()).picking_id.filtered(lambda p: p.state not in ['draft', 'cancel', 'done']).do_unreserve()


class ReplenishmentTemplateReport(models.AbstractModel):
    _name = 'report.stock.report_product_template_replenishment'
    _description = "Stock Replenishment Report"
    _inherit = 'report.stock.report_product_product_replenishment'

    @api.model
    def get_report_values(self, docids, data=None, serialize=False):
        docs = self._get_report_data(product_template_ids=docids)
        if serialize:
            docs = self._serialize_docs(docs, product_template_ids=docids)
        return {
            'data': data,
            'doc_ids': docids,
            'doc_model': 'product.template',
            'docs': docs,
            'precision': self.env['decimal.precision'].precision_get('Product Unit of Measure'),
        }
