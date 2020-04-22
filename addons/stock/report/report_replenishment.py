# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, models
from odoo.tools import format_datetime


class ReplenishmentReport(models.AbstractModel):
    _name = 'report.stock.report_product_product_replenishment'
    _description = "Stock Replenishment Report"

    @api.model
    def _move_domain(self, product_template_ids, product_variant_ids):
        move_domain = self._product_domain(product_template_ids, product_variant_ids)
        move_domain += [
            ('product_uom_qty', '!=', 0),
            ('state', 'not in', ['draft', 'cancel', 'done']),
        ]
        location_ids = False
        # Add locations in domain if user is using multi-warehouse config.
        if self.env.context.get('wh_location_id'):
            wh_location_id = self.env.context.get('wh_location_id')
            location_ids = self.env['stock.location'].search_read(
                [('id', 'child_of', wh_location_id)],
                ['id'],
            )
            location_ids = [loc['id'] for loc in location_ids]
            move_domain += [
                '|',
                ('location_id', 'in', location_ids),
                ('location_dest_id', 'in', location_ids),
            ]
        consuming_move_domain = move_domain + self.env['stock.move']._get_consuming_domain(location_ids)
        replenishing_move_domain = move_domain + self.env['stock.move']._get_replenishment_domain(location_ids)
        return consuming_move_domain, replenishing_move_domain

    @api.model
    def _product_domain(self, product_template_ids, product_variant_ids):
        domain = []
        if product_template_ids:
            domain += [('product_tmpl_id', 'in', product_template_ids)]
        elif product_variant_ids:
            domain += [('product_id', 'in', product_variant_ids)]
        return domain

    @api.model
    def _convert_date(self, lines):
        """ Convert the datetime into formated string. """
        timezone = self._context.get('tz')
        for line in lines:
            line['delivery_date'] = (line['delivery_date'] and format_datetime(self.env, line['delivery_date'], timezone, 'medium')) or ''
            line['receipt_date'] = (line['receipt_date'] and format_datetime(self.env, line['receipt_date'], timezone, 'medium')) or ''
        return lines

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self._get_report_data(product_variant_ids=docids)
        docargs = {
            'data': data,
            'doc_ids': docids,
            'doc_model': 'product.product',
            'docs': docs,
        }
        return docargs

    @api.model
    def _get_report_data(self, product_template_ids=False, product_variant_ids=False):
        """ Return all the report data, which include report lines (documents,
        quantity, expected date), quantity summary (On Hand Qty, Forecasted Qty
        and Forcasted + Pending Qty) and the number of pending documents.

        This method use the following context key:
            - `warehouse`: will restrict the search move for this warehouse.
              If missing, it will take the first company's warehouse.

        :param product_template_ids: list of `product.product` ids.
        :type product_template_ids: list
        :param product_variant_ids: list of `product.template` ids.
        :type product_variant_ids: list

        :return: a dict with all the report data.
        :rtype: dict
        """
        res = {
            'product_templates': False,
            'product_variants': False,
        }
        if self.user_has_groups('stock.group_stock_multi_warehouses') or len(self.env.companies) > 1:
            # Add warehouse id in the context to reuse it to filter data to make
            # the report warehouse specific.
            warehouse_id = self.env.context.get('warehouse', False)
            if warehouse_id:
                warehouse = self.env['stock.warehouse'].browse(warehouse_id)
            else:
                warehouse = self.env['stock.warehouse'].search([
                    ('company_id', '=', self.env.company.id)
                ], limit=1)
            self.env.context = dict(
                self.env.context,
                warehouse=warehouse.id,
                wh_location_id=warehouse.view_location_id.id,
            )
            res['active_warehouse'] = warehouse.display_name
        if product_template_ids:
            product_templates = self.env['product.template'].browse(product_template_ids)
            res['product_templates'] = product_templates
            res['product_variants'] = product_templates.product_variant_ids
        if product_variant_ids:
            product_variants = self.env['product.product'].browse(product_variant_ids)
            res['product_variants'] = product_variants

        # Generates report lines.
        consuming_lines, replenishing_lines = self._get_report_line_values(
            product_template_ids=product_template_ids,
            product_variant_ids=product_variant_ids,
        )
        replenishing_lines = self._merge_similar_replenishing_lines(replenishing_lines)
        # Updates report lines, to link replenishment lines with consuming lines when it's possible.
        # report_lines = consuming_lines + replenishing_lines
        report_lines = self._link_report_lines(consuming_lines, replenishing_lines)
        # Sorts lines to have:
        # - lines without consuming document at the end;
        # - nearest delivery date first;
        # - lines with replenishment unfilled at the end.
        report_lines.sort(key=lambda line: (
            line['document_out'] is False,
            line['replenishment_filled'] is False,
            line['delivery_date'],
            line['document_out'] and line['document_out'].id,
            line['document_in'] is not False,
            line['receipt_date'],
            line['document_in'] and line['document_in'].id,
        ))
        self._convert_date(report_lines)

        products = self.env['product.template']
        if product_template_ids:
            products = self.env['product.template'].browse(product_template_ids)
            res['multiple_product'] = len(products.product_variant_ids) > 1
        elif product_variant_ids:
            products = self.env['product.product'].browse(product_variant_ids)
            res['multiple_product'] = len(products) > 1
        else:
            res['multiple_product'] = True
        # If the report will display lines for multiple products, sorts them by product.
        if res['multiple_product']:
            report_lines.sort(key=lambda line: line['product']['id'])
        res['lines'] = report_lines
        res['uom'] = products[:1].uom_id.display_name

        # Computes quantities.
        res['quantity_on_hand'] = sum(products.mapped('qty_available'))
        res['virtual_available'] = sum(products.mapped('virtual_available'))

        # Will keep the track of all the incoming/outgoing quantity from pending documents.
        domain = [('state', '=', 'draft')]
        if product_template_ids:
            domain += [('product_tmpl_id', 'in', product_template_ids)]
        elif product_variant_ids:
            domain += [('product_id', 'in', product_variant_ids)]
        qty_in, qty_out = 0, 0
        location_ids = False
        if self.env.context.get('wh_location_id'):
            wh_location_id = self.env.context.get('wh_location_id')
            location_ids = self.env['stock.location'].search_read(
                [('id', 'child_of', wh_location_id)],
                ['id'],
            )
            location_ids = [loc['id'] for loc in location_ids]
        in_domain = [('picking_code', '=', 'incoming')] + domain
        if location_ids:
            in_domain += [('location_dest_id', 'in', location_ids)]
        incoming_moves = self.env['stock.move'].read_group(in_domain, ['product_qty'], 'product_id')
        if incoming_moves:
            qty_in = sum(move['product_qty'] for move in incoming_moves)
        out_domain = [('picking_code', '=', 'outgoing')] + domain
        if location_ids:
            out_domain += [('location_id', 'in', location_ids)]
        outgoing_moves = self.env['stock.move'].read_group(out_domain, ['product_qty'], 'product_id')
        if outgoing_moves:
            qty_out = sum(move['product_qty'] for move in outgoing_moves)

        res['qty'] = {
            'in': qty_in,
            'out': qty_out,
        }
        res['draft_picking_qty'] = {
            'in': qty_in,
            'out': qty_out,
        }
        return res

    @api.model
    def _get_report_line_values(self, product_template_ids, product_variant_ids):
        """ Fetch the moves (`stock.move`) to generate the report lines.
        Report lines are separate in two catgeory: consuming lines and replenishing lines

        :param product_template_ids: list of `product.product` ids.
        :type product_template_ids: list
        :param product_variant_ids: list of `product.template` ids.
        :type product_variant_ids: list

        :return: two lists: the first one about consuming documents, and the second one about
        replenishing documents.
        :rtype: tuple
        """
        def take_incoming_moves(move):
            return move.state not in ['cancel', 'done']

        def take_done_moves(move):
            return move.state == 'done'

        consuming_lines = []
        replenish_lines = []
        # `reported_quantity` is a dict who will keep the quantity used by a consuming
        # move from a replenishing move. Usefull when they aren't direclty linked.
        reported_quantity = defaultdict(lambda: 0)
        # Get consuming and replenishing moves and sorts them by expected date.
        consuming_move_domain, replenishing_move_domain = self._move_domain(product_template_ids, product_variant_ids)
        consuming_moves = self.env['stock.move'].search(consuming_move_domain)
        consuming_moves = consuming_moves.sorted(lambda move: move.date_expected)
        replenishing_moves = self.env['stock.move'].search(replenishing_move_domain)
        replenishing_moves = replenishing_moves.sorted(lambda move: move.date_expected)

        # Get the available quantity for each product (used for prevision on unreserved transfer).
        virtual_available = {}
        for product in (consuming_moves + replenishing_moves).product_id:
            # virtual_available[product.id] = product.qty_available
            product_moves = consuming_moves.filtered(lambda move: move.product_id.id == product.id)
            qty_reserved = sum(product_moves.mapped('reserved_availability'))
            virtual_available[product.id] = product.qty_available - qty_reserved

        # Creates a report line for each move linked to a consuming document.
        for move in consuming_moves:
            if move in replenishing_moves:
                continue
            move_data_common = {
                'document_in': False,
                'document_out': move._get_consuming_document(),
                'product': {
                    'id': move.product_id.id,
                    'display_name': move.product_id.display_name
                },
                'replenishment_filled': True,
                'uom_id': move.product_id.uom_id,
                'receipt_date': False,
                'delivery_date': move.date_expected,
                'is_late': False,
            }

            # Compute the quantity to report.
            qty_to_process = move.product_qty
            qty_reserved = move.reserved_availability
            # Decreases the already received quantities from done moves.
            qty_to_process -= move.quantity_done
            # done_move_origins = move.move_orig_ids.filtered(take_done_moves)
            # qty_to_process -= sum(done_move_origins.mapped('quantity_done'))

            incoming_move_origins = move.move_orig_ids.filtered(take_incoming_moves)
            # incoming_move_origins = move
            # Get back the end of chain origin move to avoid intermediate moves.
            while incoming_move_origins.move_orig_ids.filtered(take_incoming_moves).exists():
            # while incoming_move_origins.move_orig_ids.exists():
                incoming_move_origins = incoming_move_origins.move_orig_ids
            # Creates also a report line for each linked replenishment document.
            for move_origin in incoming_move_origins:
                quantity = min(qty_to_process, move_origin.product_qty)
                qty_to_process -= quantity
                qty_reserved -= quantity
                reported_quantity[move_origin.id] += quantity
                move_data = dict(move_data_common)
                move_data['quantity'] = quantity
                move_data['receipt_date'] = move_origin.date_expected
                move_data['is_late'] = move_origin.date_expected > move.date_expected
                move_data['document_in'] = move_origin._get_replenishment_document()
                consuming_lines.append(move_data)

            product_id = move.product_id.id
            # The move has still quantities who aren't fulfilled by a document.
            while qty_to_process > 0:
                move_data = dict(move_data_common)
                if qty_reserved > 0:
                    # Create a line for quantities reserved in stock.
                    move_data['quantity'] = qty_reserved
                    qty_to_process -= qty_reserved
                    qty_reserved = 0
                elif virtual_available[product_id] > 0:
                    # Create a line for quantities not reserved in stock, but available.
                    qty_from_stock = min(virtual_available[product_id], qty_to_process)
                    move_data['quantity'] = qty_from_stock
                    virtual_available[product_id] -= qty_from_stock
                    qty_to_process -= qty_from_stock
                else:
                    # Create a line for remaining unreseved quantities.
                    move_data['quantity'] = qty_to_process
                    move_data['replenishment_filled'] = False
                    qty_to_process = 0
                consuming_lines.append(move_data)

        # Creates a report line for each move linked to a replenishing document.
        for move in replenishing_moves:
            origin_filter = take_incoming_moves
            quantity = move.product_qty
            receipt_date = move.date_expected
            if move.state == 'partially_available':
                origin_filter = take_done_moves
                move_orig_done = move.move_orig_ids.filtered(origin_filter)
                quantity = sum(move_orig_done.mapped('product_qty'))
            move_origin = move
            while move_origin.move_orig_ids.exists():
                # Avoid to take done or cancel origin moves in account.
                new_move_origin = move_origin.move_orig_ids.filtered(origin_filter)
                if new_move_origin.exists():
                    move_origin = new_move_origin
                else:
                    break

            quantity -= reported_quantity[move_origin.id]
            if quantity <= 0:
                continue
            move_data = {
                'document_in': move_origin._get_replenishment_document(),
                'document_out': False,
                'product': {
                    'id': move.product_id.id,
                    'display_name': move.product_id.display_name
                },
                'replenishment_filled': True,
                'uom_id': move.product_id.uom_id,
                'receipt_date': receipt_date,
                'delivery_date': False,
                'is_late': False,
                'quantity': quantity,
            }
            replenish_lines.append(move_data)
        return consuming_lines, replenish_lines

    @api.model
    def _link_report_lines(self, consuming_lines, replenishing_lines):
        """ Try to link consuming lines without replenishment with replenishing
        lines who have unreserved quantity.

        :param consuming_lines: a list of report lines about documents using product qty.
        :type consuming_lines: list
        :param replenishing_lines: a list of report lines about documents who will restock.
        :type replenishing_lines: list

        :return: consuming lines and replenishing lines after they are eventually linked.
        :rtype: list
        """
        consuming_lines.sort(key=lambda line: line['delivery_date'])
        replenishing_lines.sort(key=lambda line: line['receipt_date'])
        linked_replenishing_lines = []
        for replenishing_line in replenishing_lines:
            qty_to_process = replenishing_line['quantity']
            for consuming_line in consuming_lines:
                if consuming_line['replenishment_filled'] or replenishing_line['product']['id'] != consuming_line['product']['id']:
                    continue
                if consuming_line['quantity'] <= qty_to_process:
                    # Enough quantity to fulfil the line.
                    # Updates the line's quantity and marks it as fulfilled.
                    consuming_line['document_in'] = replenishing_line['document_in']
                    consuming_line['replenishment_filled'] = True
                    consuming_line['receipt_date'] = replenishing_line['receipt_date']
                    if consuming_line['receipt_date'] and consuming_line['delivery_date']:
                        consuming_line['is_late'] = consuming_line['receipt_date'] > consuming_line['delivery_date']
                    qty_to_process -= min(consuming_line['quantity'], qty_to_process)
                    if qty_to_process <= 0:
                        break
                else:
                    # No enough quantity to fulfil the line. So:
                    # - Decreases the quantity on the line;
                    # - Creates an another fulfilled line with lesser quantity.
                    consuming_line['quantity'] -= qty_to_process
                    separate_consuming_line = consuming_line.copy()
                    separate_consuming_line.update(
                        quantity=qty_to_process,
                        replenishment_filled=True,
                        document_in=replenishing_line['document_in'],
                        receipt_date=replenishing_line['receipt_date'],
                    )
                    separate_consuming_line['is_late'] = separate_consuming_line['receipt_date'] > separate_consuming_line['delivery_date']
                    linked_replenishing_lines.append(separate_consuming_line)
                    qty_to_process = 0
                    break
            # If it still unassign quantity, create a report line for it.
            if qty_to_process:
                report_data = dict(replenishing_line)
                report_data['quantity'] = qty_to_process
                linked_replenishing_lines.append(report_data)

        return consuming_lines + linked_replenishing_lines

    @api.model
    def _merge_similar_replenishing_lines(self, lines):
        """ TODO SVS: I keep this method in case I could need it, but it's most
        likely I'll just delete it soon."""
        # Merge nothing if the report display intermediate moves.
        merged_lines = []
        while len(lines):
            current_line = lines.pop(0)
            for i in range(len(lines) - 1, -1, -1):
                line = lines[i]
                if current_line['product']['id'] == line['product']['id'] and\
                   current_line['document_in'] and line['document_in'] and\
                   current_line['document_in'].id == line['document_in'].id:
                    current_line['quantity'] += line['quantity']
                    # Take the most distant date.
                    if line['receipt_date'] > current_line['receipt_date']:
                        current_line['receipt_date'] = line['receipt_date']
                    del lines[i]
            merged_lines.append(current_line)
        return merged_lines

    @api.model
    def get_filter_state(self):
        res = {}
        res['warehouses'] = self.env['stock.warehouse'].search_read(fields=['id', 'name', 'code'])
        res['group_adv_location'] = self.env.user.has_group('stock.group_adv_location')
        res['active_warehouse'] = self.env.context.get('warehouse', False)
        if not res['active_warehouse']:
            res['active_warehouse'] = self.env.context.get('allowed_company_ids')[0]
        return res


class ReplenishmentTemplateReport(models.AbstractModel):
    _name = 'report.stock.report_product_template_replenishment'
    _description = "Stock Replenishment Report"
    _inherit = 'report.stock.report_product_product_replenishment'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self._get_report_data(product_template_ids=docids)
        docargs = {
            'data': data,
            'doc_ids': docids,
            'doc_model': 'product.product',
            'docs': docs,
        }
        return docargs
