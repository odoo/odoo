# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.tools import format_datetime
from markupsafe import Markup


rec = 0
def autoIncrement():
    global rec
    pStart = 1
    pInterval = 1
    if rec == 0:
        rec = pStart
    else:
        rec += pInterval
    return rec


class StockTraceabilityReport(models.TransientModel):
    _name = 'stock.traceability.report'
    _description = 'Traceability Report'

    @api.model
    def _get_related_move_lines(self, move_lines, line_type=False):
        lines_seen = move_lines
        lines_todo = list(move_lines)
        while lines_todo:
            move_line = lines_todo.pop(0)
            if line_type == 'parent':
                # if MTO
                if move_line.move_id.move_orig_ids:
                    lines = move_line.move_id.move_orig_ids.move_line_ids.filtered(
                        lambda m: m.lot_id == move_line.lot_id and m.state == 'done'
                    ) - lines_seen
                # if MTS
                elif move_line.location_id.usage in ('internal', 'transit'):
                    lines = self.env['stock.move.line'].search([
                        ('product_id', '=', move_line.product_id.id),
                        ('lot_id', '=', move_line.lot_id.id),
                        ('location_dest_id', '=', move_line.location_id.id),
                        ('id', 'not in', lines_seen.ids),
                        ('date', '<=', move_line.date),
                        ('state', '=', 'done')
                    ])
                else:
                    continue
                lines_seen |= lines
            elif line_type == 'child':
                if move_line.move_id.move_dest_ids:
                    lines = move_line.move_id.move_dest_ids.move_line_ids.filtered(
                        lambda m: m.lot_id == move_line.lot_id and m.state == 'done'
                    ) - lines_seen
                elif move_line.location_dest_id.usage in ('internal', 'transit'):
                    lines = self.env['stock.move.line'].search([
                        ('product_id', '=', move_line.product_id.id),
                        ('lot_id', '=', move_line.lot_id.id),
                        ('location_id', '=', move_line.location_dest_id.id),
                        ('id', 'not in', lines_seen.ids),
                        ('date', '>=', move_line.date),
                        ('state', '=', 'done')
                    ])
                else:
                    continue
                lines_seen |= lines
        return lines_seen - move_lines

    @api.model
    def get_lines(self, line_type=False, **kw):
        context = dict(self.env.context)
        model = kw and kw['model_name'] or context.get('model')
        record_id = kw and kw['record_id'] or context.get('active_id')
        level = kw and kw['level'] or 1
        lines = self.env['stock.move.line']
        if record_id and model == 'stock.lot':
            main_location_ids = self.env['stock.warehouse'].search([]).lot_stock_id.ids
            lines = self.env['stock.move.line'].search([
                ('lot_id', '=', record_id),
                ('state', '=', 'done'),
                '|',
                ('location_id', 'in', main_location_ids),
                ('location_dest_id', 'in', main_location_ids)
            ])
            return self._lot_lines(move_lines=lines, level=level, main_loc_ids=main_location_ids)
        elif record_id and model == 'stock.move.line' and line_type:
            move_line = self.env[model].browse(record_id)
            parent_lines, children_lines = self._get_linked_move_lines(move_line)
            if line_type == 'parent':
                lines = parent_lines or self._get_related_move_lines(move_line, line_type)
            elif line_type == 'child':
                lines = children_lines or self._get_related_move_lines(move_line, line_type)
            return self._move_lines(move_lines=lines, level=level, line_type=line_type)
        elif record_id and model == 'stock.picking':
            record = self.env[model].browse(record_id)
            lines = record.move_ids.move_line_ids.filtered(lambda m: m.state == 'done')
            return self._picking_lines(move_lines=lines, level=level)
        return []

    @api.model
    def _get_reference(self, move_line):
        res_model = ''
        ref = ''
        res_id = False
        picking_id = move_line.picking_id or move_line.move_id.picking_id
        if picking_id:
            res_model = 'stock.picking'
            res_id = picking_id.id
            ref = picking_id.name
        elif move_line.move_id.is_inventory:
            res_model = 'stock.move'
            res_id = move_line.move_id.id
            ref = 'Inventory Adjustment'
        elif move_line.move_id.is_scrap:
            res_model = 'stock.move'
            res_id = move_line.move_id.id
            ref = move_line.move_id.origin
        return res_model, res_id, ref

    @api.model
    def _quantity_to_str(self, from_uom, to_uom, qty):
        """ workaround to apply the float rounding logic of t-out on data prepared server side """
        qty = from_uom._compute_quantity(qty, to_uom, rounding_method='HALF-UP')
        return self.env['ir.qweb.field.float'].value_to_html(qty, {'decimal_precision': 'Product Unit'})

    @api.model
    def _get_location_names(self, move_line):
        """ Return partner name instead of source or destination location based on
            whether the product is incoming or outgoing.
        """
        partner_name = move_line.picking_partner_id.name
        source_name = move_line.location_id.display_name
        destination_name = move_line.location_dest_id.display_name

        if (picking_code := move_line.picking_id.picking_type_code) == 'incoming':
            return partner_name, destination_name
        elif picking_code == 'outgoing':
            return source_name, partner_name
        else:
            return source_name, destination_name

    @api.model
    def _make_dict_move(self, move_line, line_type, level, unfoldable=False):
        res_model, res_id, reference = self._get_reference(move_line)
        source_name, destination_name = self._get_location_names(move_line)
        date = format_datetime(self.env, move_line.move_id.date)
        return {
            'id': autoIncrement(),
            'model_name': 'stock.move.line',
            'record_id': move_line.id,
            'line_type': line_type,
            'lot_name': move_line.lot_id.name,
            'lot_id': move_line.lot_id.id,
            'date': date,
            'reference': reference,
            'source_name': source_name,
            'destination_name': destination_name,
            'partner_id': move_line.picking_partner_id.id,
            'picking_type_code': move_line.picking_id.picking_type_code,
            'res_id': res_id,
            'res_model': res_model,
            'columns': [
                self._make_column('reference', reference),
                self._make_column('product', move_line.product_id.display_name),
                self._make_column('date', date),
                self._make_column('lot_name', move_line.lot_id.name),
                self._make_column('source_name', source_name),
                self._make_column('destination_name', destination_name),
                self._make_column('quantity', "%s %s" % (self._quantity_to_str(move_line.uom_id, move_line.product_id.uom_id, move_line.quantity), move_line.product_id.uom_id.name)),
            ],
            'level': level,
            'unfoldable': unfoldable,
        }

    def _make_column(self, name, value):
        return {
            'name': name,
            'value': value,
        }

    @api.model
    def _get_linked_move_lines(self, move_line):
        """ This method will return the consumed line or produced line for this operation."""
        return False, False

    @api.model
    def _is_unfoldable(self, move_line, line_type=False):
        """ To be unfoldable, a line must:
        - have a lot or serial number
        - go from one location to another different location
        - have linked move lines based on line_type """
        return bool(
            move_line.lot_id and move_line.location_id != move_line.location_dest_id
            and (
                (line_type == 'parent' and (
                        move_line.consume_line_ids
                        or self._get_related_move_lines(move_line, line_type)
                ))
                or (line_type == 'child' and (
                    move_line.produce_line_ids
                    or self._get_related_move_lines(move_line, line_type)
                ))
            )
        )

    @api.model
    def _lot_lines(self, move_lines=None, level=0, main_loc_ids=None):
        final_vals = []
        lines = move_lines or []
        main_location_ids = main_loc_ids or []
        for line in lines:
            line_type = 'child' if line.location_id.id in main_location_ids else 'parent'
            if line.location_id == line.location_dest_id:
                line_type = False
            unfoldable = self._is_unfoldable(line, line_type)
            final_vals.append(self._make_dict_move(move_line=line, line_type=line_type, level=level, unfoldable=unfoldable))
        return sorted(final_vals, key=lambda l: (l['date'], l['id']), reverse=True)

    @api.model
    def _picking_lines(self, move_lines=None, level=0):
        """ If we come from a picking and it's a non-return incoming picking, we just process
        the lines of the picking as child lines because incoming lines should not have parents.
        In all other cases, the SMLs are considered parents and we check if there's a next line
        in the chain. Any line found will be processed as a child line. """
        final_vals = []
        line_type = 'child' if move_lines.picking_id.picking_type_code == 'incoming' and not move_lines.move_id.origin_returned_move_id else 'parent'
        initial_lines = move_lines or []
        for line in initial_lines:
            unfoldable = self._is_unfoldable(line, line_type)
            final_vals.append(self._make_dict_move(move_line=line, line_type=line_type, level=level, unfoldable=unfoldable))
        if line_type == 'parent':
            children_lines = self._get_related_move_lines(initial_lines, 'child')
            for line in children_lines:
                unfoldable = self._is_unfoldable(line, 'child')
                final_vals.append(self._make_dict_move(move_line=line, line_type='child', level=level, unfoldable=unfoldable))
        return sorted(final_vals, key=lambda l: (l['date'], l['id']), reverse=True)

    @api.model
    def _move_lines(self, move_lines=None, level=0, line_type=False):
        final_vals = []
        lines = move_lines or []
        for line in lines:
            unfoldable = self._is_unfoldable(line, line_type)
            final_vals.append(self._make_dict_move(move_line=line, line_type=line_type, level=level, unfoldable=unfoldable))
        return sorted(final_vals, key=lambda l: (l['date'], l['id']), reverse=True)

    def get_pdf_lines(self, line_data=[]):
        lines = []
        for line in line_data:
            move_line = self.env[line['model_name']].browse(line['record_id'])
            unfoldable = line.get('unfoldable')
            lines.append(self._make_dict_move(move_line=move_line, line_type=line['line_type'], level=line['level'], unfoldable=unfoldable))
        return lines

    def get_pdf(self, line_data=None):
        line_data = [] if line_data is None else line_data
        lines = self.with_context(print_mode=True).get_pdf_lines(line_data)
        base_url = self.env['ir.config_parameter'].sudo().get_str('web.base.url')
        rcontext = {
            'mode': 'print',
            'base_url': base_url,
        }

        context = dict(self.env.context)
        if context.get('active_id') and context.get('active_model'):
            rcontext['reference'] = self.env[context.get('active_model')].browse(int(context.get('active_id'))).display_name

        body = self.env['ir.ui.view'].with_context(context)._render_template(
            "stock.report_stock_inventory_print",
            values=dict(rcontext, lines=lines, report=self, context=self),
        )

        header = self.env['ir.actions.report']._render_template("web.internal_layout", values=rcontext)
        header = self.env['ir.actions.report']._render_template("web.minimal_layout", values=dict(rcontext, subst=True, body=Markup(header.decode())))

        report_service = self.env['ir.actions.report']
        return report_service._run_pdf_engine_without_processing(
            report_service._get_pdf_engine(),
            [body],
            header=header.decode(),
            landscape=True,
            specific_paperformat_args={'data-report-margin-top': 30, 'data-report-header-spacing': 25}
        )

    @api.model
    def get_main_lines(self, given_context=None):
        res = self.search([('create_uid', '=', self.env.uid)], limit=1)
        if not res:
            res = self.create({})
        return res.with_context(given_context).get_lines()

    @api.model
    def get_expanded_lines(self, given_context=None):
        expanded_lines = self.get_main_lines(given_context)
        lines_todo = list(filter(lambda l: l['unfoldable'], expanded_lines))
        while lines_todo:
            line = lines_todo.pop(0)
            sub_lines = self.get_lines(**line)
            line['lines'] = sub_lines
            for sub_line in sub_lines:
                sub_line['lines'] = []
                sub_line['level'] += 30
                if sub_line.get('unfoldable'):
                    lines_todo.append(sub_line)
        return expanded_lines
