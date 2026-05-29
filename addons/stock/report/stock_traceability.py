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
    def _get_move_lines(self, move_lines):
        lines_seen = move_lines
        lines_todo = list(move_lines)
        while lines_todo:
            move_line = lines_todo.pop(0)
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
        return lines_seen - move_lines

    @api.model
    def get_lines(self, line_id=False, **kw):
        context = dict(self.env.context)
        model = kw and kw['model_name'] or context.get('model')
        record_id = kw and kw['record_id'] or context.get('active_id')
        level = kw and kw['level'] or 1
        lines = self.env['stock.move.line']
        if record_id and model == 'stock.lot':
            lines = self.env['stock.move.line'].search([
                ('lot_id', '=', context.get('lot_name') or record_id),
                ('state', '=', 'done'),
            ])
        elif record_id and model == 'stock.move.line' and context.get('lot_name'):
            record = self.env[model].browse(record_id)
            dummy, children_lines = self._get_linked_move_lines(record)
            if children_lines:
                lines = children_lines
        elif record_id and model in ('stock.picking', 'mrp.production'):
            record = self.env[model].browse(record_id)
            if model == 'stock.picking':
                lines = record.move_ids.move_line_ids.filtered(lambda m: m.lot_id and m.state == 'done')
            else:
                lines = record.move_finished_ids.move_line_ids.filtered(lambda m: m.state == 'done')
        return self._lines(line_id, record_id=record_id, model=model, level=level, move_lines=lines)

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
    def _make_dict_move(self, level, line_id, move_line, unfoldable=False):
        res_model, res_id, reference = self._get_reference(move_line)
        dummy, children_lines = self._get_linked_move_lines(move_line)
        source_name, destination_name = self._get_location_names(move_line)
        return {
            'id': autoIncrement(),
            'model': 'stock.move.line',
            'record_id': move_line.id,
            'parent_id': line_id,
            'has_children': bool(children_lines),
            'lot_name': move_line.lot_id.name,
            'lot_id': move_line.lot_id.id,
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
                self._make_column('date', format_datetime(self.env, move_line.move_id.date, tz=False, dt_format=False)),
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
    def _lines(self, line_id=False, record_id=False, model=False, level=0, move_lines=None, **kw):
        final_vals = []
        lines = move_lines or []
        if model and line_id:
            move_line = self.env[model].browse(record_id)
            parent_lines, dummy = self._get_linked_move_lines(move_line)
            if parent_lines:
                lines = parent_lines
            else:
                # Traceability in case of consumed in.
                lines = self._get_move_lines(move_line)
        for line in sorted(lines, key=lambda l: l.move_id.date, reverse=True):
            unfoldable = False
            if line.consume_line_ids or (model != "stock.lot" and line.lot_id and self._get_move_lines(line)):
                unfoldable = True
            final_vals.append(self._make_dict_move(level, line_id=line_id, move_line=line, unfoldable=unfoldable))
        return final_vals

    def get_pdf_lines(self, line_data=[]):
        lines = []
        for line in line_data:
            model = self.env[line['model_name']].browse(line['record_id'])
            unfoldable = False
            if line.get('unfoldable'):
                unfoldable = True
            lines.append(self._make_dict_move(line['level'], line_id=line['id'], move_line=model, unfoldable=unfoldable))
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
            return self.create({}).with_context(given_context).get_lines()
        return res.with_context(given_context).get_lines()
