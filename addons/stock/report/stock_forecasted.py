# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
import copy

from odoo import api, models
from odoo.tools import float_is_zero, format_date, float_round


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
                'reservation': line['reservation'],
                'is_matched': line['is_matched'],
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

        res['lines'] = self._get_report_lines(product_template_ids, product_variant_ids, wh_location_ids)
        return res

    def _prepare_report_line(self, quantity, move_out=None, move_in=None, replenishment_filled=True, product=False, reservation=False):
        product = product or (move_out.product_id if move_out else move_in.product_id)
        is_late = move_out.date < move_in.date if (move_out and move_in) else False

        move_to_match_ids = self.env.context.get('move_to_match_ids') or []
        move_in_id = move_in.id if move_in else None
        move_out_id = move_out.id if move_out else None

        return {
            'document_in': move_in._get_source_document() if move_in else False,
            'document_out': move_out._get_source_document() if move_out else False,
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
            'reservation': reservation,
            'is_matched': any(move_id in [move_in_id, move_out_id] for move_id in move_to_match_ids),
        }

    def _get_report_lines(self, product_template_ids, product_variant_ids, wh_location_ids):

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
        reserved_outs = self.env['stock.move'].search(
            out_domain + [('state', 'in', ('partially_available', 'assigned'))],
            order='priority desc, date, id')
        outs_per_product = defaultdict(list)
        reserved_outs_per_product = defaultdict(list)
        for out in outs:
            outs_per_product[out.product_id.id].append(out)
        for out in reserved_outs:
            reserved_outs_per_product[out.product_id.id].append(out)
        ins = self.env['stock.move'].search(in_domain, order='priority desc, date, id')
        ins_per_product = defaultdict(list)
        for in_ in ins:
            ins_per_product[in_.product_id.id].append({
                'qty': in_.product_qty,
                'move': in_,
                'move_dests': in_._rollup_move_dests(set())
            })
        currents = outs.product_id._get_only_qty_available()

        lines = []
        for product in (ins | outs).product_id:
            product_rounding = product.uom_id.rounding
            for out in reserved_outs_per_product[product.id]:
                # Reconcile with reserved stock.
                current = currents[product.id]
                reserved = out.product_uom._compute_quantity(out.reserved_availability, product.uom_id)
                currents[product.id] -= reserved
                lines.append(self._prepare_report_line(reserved, move_out=out, reservation=True))

            unreconciled_outs = []
            for out in outs_per_product[product.id]:
                # Reconcile with the current stock.
                reserved = 0.0
                if out.state in ('partially_available', 'assigned'):
                    reserved = out.product_uom._compute_quantity(out.reserved_availability, product.uom_id)
                demand = out.product_qty - reserved

                if float_is_zero(demand, precision_rounding=product_rounding):
                    continue
                current = currents[product.id]
                taken_from_stock = min(demand, current)
                if not float_is_zero(taken_from_stock, precision_rounding=product_rounding):
                    currents[product.id] -= taken_from_stock
                    demand -= taken_from_stock
                    lines.append(self._prepare_report_line(taken_from_stock, move_out=out))
                # Reconcile with the ins.
                if not float_is_zero(demand, precision_rounding=product_rounding):
                    demand = _reconcile_out_with_ins(lines, out, ins_per_product[product.id], demand, product_rounding, only_matching_move_dest=True)
                if not float_is_zero(demand, precision_rounding=product_rounding):
                    unreconciled_outs.append((demand, out))

            # Another pass, in case there are some ins linked to a dest move but that still have some quantity available
            for (demand, out) in unreconciled_outs:
                demand = _reconcile_out_with_ins(lines, out, ins_per_product[product.id], demand, product_rounding, only_matching_move_dest=False)
                if not float_is_zero(demand, precision_rounding=product_rounding):
                    # Not reconciled
                    lines.append(self._prepare_report_line(demand, move_out=out, replenishment_filled=False))
            # Unused remaining stock.
            free_stock = currents.get(product.id, 0)
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
