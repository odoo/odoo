# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict, OrderedDict

from odoo import _, api, models
from odoo.tools import float_compare, float_is_zero, format_date


class ReceptionReport(models.AbstractModel):
    _name = 'report.stock.report_reception'
    _description = "Stock Reception Report"

    @api.model
    def get_report_data(self, docids, data):
        report_values = self._get_report_values(docids, data)
        report_values['docs'] = self._format_html_docs(report_values.get('docs', False))
        report_values['sources_info'] = self._format_html_sources_info(report_values.get('sources_to_lines', {}))
        report_values['sources_to_lines'] = self._format_html_sources_to_lines(report_values.get('sources_to_lines', {}))
        report_values['sources_to_formatted_scheduled_date'] = self._format_html_sources_to_date(report_values.get('sources_to_formatted_scheduled_date', {}))
        report_values['show_uom'] = self.env.user.has_group('uom.group_uom')
        return report_values

    @api.model
    def _get_report_values(self, docids, data=None):
        ''' This report is flexibly designed to work with both individual and batch pickings.
        '''
        docs = self._get_docs(docids)
        doc_states = docs.mapped('state')
        # unsupported cases
        doc_types = self._get_doc_types()
        if not docs:
            msg = _("No %s selected or a delivery order selected", doc_types)
        elif 'done' in doc_states and len(set(doc_states)) > 1:
            docs = False
            msg = _("This report cannot be used for done and not done %s at the same time", doc_types)
        if not docs:
            return {'pickings': False, 'reason': msg}

        # incoming move qtys
        product_to_qty_draft = defaultdict(float)
        product_to_qty_to_assign = defaultdict(list)
        product_to_total_assigned = defaultdict(lambda: [0.0, []])

        # to support batch pickings we need to track the total already assigned
        move_ids = self._get_moves(docs)
        assigned_moves = move_ids.mapped('move_dest_ids')
        product_to_assigned_qty = defaultdict(float)
        for assigned in assigned_moves:
            product_to_assigned_qty[assigned.product_id] += assigned.product_qty

        for move in move_ids:
            qty_already_assigned = 0
            if move.move_dest_ids:
                qty_already_assigned = min(product_to_assigned_qty[move.product_id], move.product_qty)
                product_to_assigned_qty[move.product_id] -= qty_already_assigned
            if qty_already_assigned:
                product_to_total_assigned[move.product_id][0] += qty_already_assigned
                product_to_total_assigned[move.product_id][1].append(move.id)
            if move.product_qty != qty_already_assigned:
                if move.state == 'draft':
                    product_to_qty_draft[move.product_id] += move.product_qty - qty_already_assigned
                else:
                    quantity_to_assign = move.product_qty
                    if not move.product_qty:
                        # if immediate transfer is not Done and quantity_done hasn't been edited, then move.product_qty will incorrectly = 1 (due to default)
                        quantity_to_assign = move.product_uom._compute_quantity(move.quantity, move.product_id.uom_id, rounding_method='HALF-UP')
                    product_to_qty_to_assign[move.product_id].append((quantity_to_assign - qty_already_assigned, move))

        # only match for non-mto moves in same warehouse
        warehouse = docs[0].picking_type_id.warehouse_id
        wh_location_ids = self.env['stock.location']._search([('id', 'child_of', warehouse.view_location_id.id), ('usage', '!=', 'supplier')])

        allowed_states = ['confirmed', 'partially_available', 'waiting']
        if 'done' in doc_states:
            # only done moves are allowed to be assigned to already reserved moves
            allowed_states += ['assigned']

        outs = self.env['stock.move'].search(
            [
                ('state', 'in', allowed_states),
                ('product_qty', '>', 0),
                ('location_id', 'in', wh_location_ids),
                ('move_orig_ids', '=', False),
                ('product_id', 'in',
                    [p.id for p in list(product_to_qty_to_assign.keys()) + list(product_to_qty_draft.keys())]),
            ] + self._get_extra_domain(docs),
            order='reservation_date, priority desc, date, id')

        products_to_outs = defaultdict(list)
        for out in outs:
            products_to_outs[out.product_id].append(out)

        sources_to_lines = defaultdict(list)  # group by source so we can print them together
        # show potential moves that can be assigned
        for product_id, outs in products_to_outs.items():
            for out in outs:
                # we expect len(source) = 2 when picking + origin [e.g. SO] and len() = 1 otherwise [e.g. MO]
                source = (out._get_source_document(),)
                if not source:
                    continue
                if out.picking_id and source[0] != out.picking_id:
                    source = (out.picking_id, source[0])

                qty_to_reserve = out.product_qty
                product_uom = out.product_id.uom_id
                if 'done' not in doc_states and out.state == 'partially_available':
                    qty_to_reserve -= out.product_uom._compute_quantity(out.quantity, product_uom)
                moves_in_ids = []
                quantity = 0
                for move_in_qty, move_in in product_to_qty_to_assign[out.product_id]:
                    moves_in_ids.append(move_in.id)
                    if float_compare(quantity + move_in_qty, qty_to_reserve, precision_rounding=product_uom.rounding) <= 0:
                        qty_to_add = move_in_qty
                        move_in_qty = 0
                    else:
                        qty_to_add = qty_to_reserve - quantity
                        move_in_qty -= qty_to_add
                    quantity += qty_to_add
                    if move_in_qty:
                        product_to_qty_to_assign[out.product_id][0] = (move_in_qty, move_in)
                    else:
                        product_to_qty_to_assign[out.product_id] = product_to_qty_to_assign[out.product_id][1:]
                    if float_compare(qty_to_reserve, quantity, precision_rounding=product_uom.rounding) == 0:
                        break

                if not float_is_zero(quantity, precision_rounding=product_uom.rounding):
                    sources_to_lines[source].append(self._prepare_report_line(quantity, product_id, out, source[0], move_ins=self.env['stock.move'].browse(moves_in_ids)))

                # draft qtys can be shown but not assigned
                qty_expected = product_to_qty_draft.get(product_id, 0)
                if float_compare(qty_to_reserve, quantity, precision_rounding=product_uom.rounding) > 0 and\
                        not float_is_zero(qty_expected, precision_rounding=product_uom.rounding):
                    to_expect = min(qty_expected, qty_to_reserve - quantity)
                    sources_to_lines[source].append(self._prepare_report_line(to_expect, product_id, out, source[0], is_qty_assignable=False))
                    product_to_qty_draft[product_id] -= to_expect

        # show already assigned moves
        for product_id, qty_and_ins in product_to_total_assigned.items():
            total_assigned = qty_and_ins[0]
            moves_in = self.env['stock.move'].browse(qty_and_ins[1])
            out_moves = moves_in.move_dest_ids

            for out_move in out_moves:
                if float_is_zero(total_assigned, precision_rounding=out_move.product_id.uom_id.rounding):
                    # it is possible there are different in moves linked to the same out moves due to batch
                    # => we guess as to which outs correspond to this report...
                    continue
                source = (out_move._get_source_document(),)
                if not source:
                    continue
                if out_move.picking_id and source[0] != out_move.picking_id:
                    source = (out_move.picking_id, source[0])
                qty_assigned = min(total_assigned, out_move.product_qty)
                sources_to_lines[source].append(
                    self._prepare_report_line(qty_assigned, product_id, out_move, source[0], is_assigned=True, move_ins=moves_in))

        # dates aren't auto-formatted when printed in report :(
        sources_to_formatted_scheduled_date = defaultdict(list)
        for source, dummy in sources_to_lines.items():
            sources_to_formatted_scheduled_date[source] = self._get_formatted_scheduled_date(source[0])

        return {
            'data': data,
            'doc_ids': docids,
            'doc_model': self._get_doc_model(),
            'sources_to_lines': sources_to_lines,
            'precision': self.env['decimal.precision'].precision_get('Product Unit of Measure'),
            'docs': docs,
            'sources_to_formatted_scheduled_date': sources_to_formatted_scheduled_date,
        }

    def _prepare_report_line(self, quantity, product, move_out, source=False, is_assigned=False, is_qty_assignable=True, move_ins=False):
        return {
            'source': source,
            'product': {
                'id': product.id,
                'display_name': product.display_name
            },
            'uom': product.uom_id.display_name,
            'quantity': quantity,
            'is_qty_assignable': is_qty_assignable,
            'move_out': move_out,
            'is_assigned': is_assigned,
            'move_ins': move_ins and move_ins.ids or False,
        }

    def _get_docs(self, docids):
        docids = self.env.context.get('default_picking_ids', docids)
        return self.env['stock.picking'].search([('id', 'in', docids), ('picking_type_code', '!=', 'outgoing'), ('state', '!=', 'cancel')])

    def _get_doc_model(self):
        return 'stock.picking'

    def _get_doc_types(self):
        return "transfers"

    def _get_moves(self, docs):
        return docs.move_ids.filtered(lambda m: m.product_id.type == 'product' and m.state != 'cancel')

    def _get_extra_domain(self, docs):
        return [('picking_id', 'not in', docs.ids)]

    def _get_formatted_scheduled_date(self, source):
        """ Unfortunately different source record types have different field names for their "Scheduled Date"
        Therefore an extendable method is needed.
        """
        if source._name == 'stock.picking':
            return format_date(self.env, source.scheduled_date)
        return False

    def action_assign(self, move_ids, qtys, in_ids):
        """ Assign picking move(s) [i.e. link] to other moves (i.e. make them MTO)
        :param move_id ids: the ids of the moves to make MTO
        :param qtys list: the quantities that are being assigned to the move_ids (in same order as move_ids)
        :param in_ids ids: the ids of the moves that are to be assigned to move_ids
        """
        outs = self.env['stock.move'].browse(move_ids)
        # Split outs with only part of demand assigned to prevent reservation problems later on.
        # We do this first so we can create their split moves in batch
        out_to_new_out = OrderedDict()
        new_move_vals = []
        for out, qty_to_link in zip(outs, qtys):
            if float_compare(out.product_qty, qty_to_link, precision_rounding=out.product_id.uom_id.rounding) == 1:
                new_move = out._split(out.product_qty - qty_to_link)
                if new_move:
                    new_move[0]['reservation_date'] = out.reservation_date
                new_move_vals += new_move
                out_to_new_out[out.id] = self.env['stock.move']
        new_outs = self.env['stock.move'].create(new_move_vals)
        # don't do action confirm to avoid creating additional unintentional reservations
        new_outs.write({'state': 'confirmed'})
        for i, k in enumerate(out_to_new_out.keys()):
            out_to_new_out[k] = new_outs[i]

        for out, qty_to_link, ins in zip(outs, qtys, in_ids):
            potential_ins = self.env['stock.move'].browse(ins)
            if out.id in out_to_new_out:
                new_out = out_to_new_out[out.id]
                if potential_ins[0].state != 'done' and out.quantity:
                    # let's assume if 1 of the potential_ins isn't done, then none of them are => we are only assigning the not-reserved
                    # qty and the new move should have all existing reserved quants (i.e. move lines) assigned to it
                    out.move_line_ids.move_id = new_out
                elif potential_ins[0].state == 'done' and out.quantity > qty_to_link:
                    # let's assume if 1 of the potential_ins is done, then all of them are => we can link them to already reserved moves, but we
                    # need to make sure the reserved qtys still match the demand amount the move (we're assigning).
                    out.move_line_ids.move_id = new_out
                    assigned_amount = 0
                    for move_line_id in new_out.move_line_ids:
                        if assigned_amount + move_line_id.reserved_qty > qty_to_link:
                            new_move_line = move_line_id.copy({'reserved_uom_qty': 0, 'quantity': 0})
                            new_move_line.reserved_uom_qty = move_line_id.reserved_uom_qty
                            move_line_id.reserved_uom_qty = out.product_id.uom_id._compute_quantity(qty_to_link - assigned_amount, out.product_uom, rounding_method='HALF-UP')
                            new_move_line.reserved_uom_qty -= out.product_id.uom_id._compute_quantity(move_line_id.reserved_qty, out.product_uom, rounding_method='HALF-UP')
                        move_line_id.move_id = out
                        assigned_amount += move_line_id.reserved_qty
                        if float_compare(assigned_amount, qty_to_link, precision_rounding=out.product_id.uom_id.rounding) == 0:
                            break

            for in_move in reversed(potential_ins):
                quantity_remaining = in_move.product_qty - sum(in_move.move_dest_ids.mapped('product_qty'))
                if in_move.product_id != out.product_id or float_compare(0, quantity_remaining, precision_rounding=in_move.product_id.uom_id.rounding) >= 0:
                    # in move is already completely linked (e.g. during another assign click) => don't count it again
                    potential_ins = potential_ins[1:]
                    continue

                linked_qty = min(in_move.product_qty, qty_to_link)
                in_move.move_dest_ids |= out
                self._action_assign(in_move, out)
                out.procure_method = 'make_to_order'
                quantity_remaining -= linked_qty
                qty_to_link -= linked_qty
                if float_is_zero(qty_to_link, precision_rounding=out.product_id.uom_id.rounding):
                    break  # we have satistfied the qty_to_link

        (outs | new_outs)._recompute_state()

        # always try to auto-assign to prevent another move from reserving the quant if incoming move is done
        self.env['stock.move'].browse(move_ids)._action_assign()

    def action_unassign(self, move_id, qty, in_ids):
        """ Unassign moves [i.e. unlink] from a move (i.e. make non-MTO)
        :param move_id id: the id of the move to make non-MTO
        :param qty float: the total quantity that is being unassigned from move_id
        :param in_ids ids: the ids of the moves that are to be unassigned from move_id
        """
        out = self.env['stock.move'].browse(move_id)
        ins = self.env['stock.move'].browse(in_ids)

        amount_unassigned = 0
        for in_move in ins:
            if out.id not in in_move.move_dest_ids.ids:
                continue
            in_move.move_dest_ids -= out
            self._action_unassign(in_move, out)
            amount_unassigned += min(qty, in_move.product_qty)
            if float_compare(qty, amount_unassigned, precision_rounding=out.product_id.uom_id.rounding) <= 0:
                break
        if out.move_orig_ids and out.state != 'done':
            # annoying use cases where we need to split the out move:
            # 1. batch reserved + individual picking unreserved
            # 2. moves linked from backorder generation
            total_still_linked = sum(out.move_orig_ids.mapped('product_qty'))
            new_move_vals = out._split(out.product_qty - total_still_linked)
            if new_move_vals:
                new_move_vals[0]['procure_method'] = 'make_to_order'
                new_move_vals[0]['reservation_date'] = out.reservation_date
                new_out = self.env['stock.move'].create(new_move_vals)
                # don't do action confirm to avoid creating additional unintentional reservations
                new_out.write({'state': 'confirmed'})
                out.move_line_ids.move_id = new_out
                (out | new_out)._compute_quantity()
                if new_out.quantity > new_out.product_qty:
                    # extra reserved amount goes to no longer linked out
                    reserved_amount_to_remain = new_out.quantity - new_out.product_qty
                    for move_line_id in new_out.move_line_ids:
                        if reserved_amount_to_remain <= 0:
                            break
                        if move_line_id.reserved_qty > reserved_amount_to_remain:
                            new_move_line = move_line_id.copy({'reserved_uom_qty': 0, 'quantity': 0})
                            new_move_line.reserved_uom_qty = out.product_id.uom_id._compute_quantity(move_line_id.reserved_qty - reserved_amount_to_remain, move_line_id.product_uom_id, rounding_method='HALF-UP')
                            move_line_id.reserved_uom_qty -= new_move_line.reserved_uom_qty
                            new_move_line.move_id = out
                            break
                        else:
                            move_line_id.move_id = out
                            reserved_amount_to_remain -= move_line_id.reserved_qty
                    (out | new_out)._compute_quantity()
                out.move_orig_ids = False
                new_out._recompute_state()
        out.procure_method = 'make_to_stock'
        out._recompute_state()
        return True

    def _action_assign(self, in_move, out_move):
        """ For extension purposes only """
        return

    def _action_unassign(self, in_move, out_move):
        """ For extension purposes only """
        return

    def _format_html_docs(self, docs):
        """ Format docs to be sent in an html request. """
        return [{
            'id': doc.id,
            'name': doc.display_name,
            'state': doc.state,
            'display_state': dict(doc._fields['state']._description_selection(self.env)).get(doc.state),
        } for doc in docs] if docs else docs

    def _format_html_sources_to_date(self, sources_to_dates):
        """ Format sources_to_formatted_scheduled_date to be sent in an html request. """
        return {str(source): date for (source, date) in sources_to_dates.items()}

    def _format_html_sources_to_lines(self, sources_to_lines):
        """ Format sources_to_lines to be sent in an html request, while adding an index for OWL's t-foreach. """
        return {
            str(source): [{**line, 'index': i, 'move_out_id': line['move_out'].id} for i, line in enumerate(lines)]
            for source, lines in sources_to_lines.items()
        }

    def _format_html_sources_info(self, sources_to_lines):
        """ Format used info from sources of sources_to_lines to be sent in an html request. """
        return {str(source): [self._format_html_source(s, s._name == 'stock.picking')for s in source] for source in sources_to_lines.keys()}

    def _format_html_source(self, source, is_picking=False):
        """ Format used info from a single source to be sent in an html request. """
        formatted = {
            'id': source.id,
            'model': source._name,
            'name': source.display_name,
        }
        if is_picking:
            formatted.update({
                'priority': source.priority,
                'partner_id': source.partner_id.id if source.partner_id else False,
                'partner_name': source.partner_id.name if source.partner_id else False,
            })
        return formatted
