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
    def _get_move_lines(self, move_lines, line_id=None):
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
            if line_id is None or line_id in lines.ids:
                lines_todo += list(lines)
            lines_seen |= lines
        return lines_seen - move_lines

    @api.model
    def get_lines(self, line_id=False, **kw):
        context = dict(self.env.context)
        model = kw and kw['model_name'] or context.get('model')
        rec_id = kw and kw['model_id'] or context.get('active_id')
        level = kw and kw['level'] or 1
        lines = self.env['stock.move.line']
        move_line = self.env['stock.move.line']
        if rec_id and model == 'stock.lot':
            lines = move_line.search([
                ('lot_id', '=', context.get('lot_name') or rec_id),
                ('state', '=', 'done'),
            ])
        elif  rec_id and model == 'stock.move.line' and context.get('lot_name'):
            record = self.env[model].browse(rec_id)
            dummy, is_used = self._get_linked_move_lines(record)
            if is_used:
                lines = is_used
        elif rec_id and model in ('stock.picking', 'mrp.production'):
            record = self.env[model].browse(rec_id)
            if model == 'stock.picking':
                lines = record.move_ids.move_line_ids.filtered(lambda m: m.lot_id and m.state == 'done')
            else:
                lines = record.move_finished_ids.move_line_ids.filtered(lambda m: m.state == 'done')
        move_line_vals = self._lines(line_id, model_id=rec_id, model=model, level=level, move_lines=lines)
        final_vals = sorted(move_line_vals, key=lambda v: v['date'], reverse=True)
        lines = self._final_vals_to_lines(final_vals, level)
        return lines

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
        elif move_line.move_id.scrapped and move_line.move_id.scrap_id:
            res_model = 'stock.scrap'
            res_id = move_line.move_id.scrap_id.id
            ref = move_line.move_id.scrap_id.name
        return res_model, res_id, ref

    @api.model
    def _quantity_to_str(self, from_uom, to_uom, qty):
        """ workaround to apply the float rounding logic of t-esc on data prepared server side """
        qty = from_uom._compute_quantity(qty, to_uom, rounding_method='HALF-UP')
        return self.env['ir.qweb.field.float'].value_to_html(qty, {'decimal_precision': 'Product Unit of Measure'})

    def _get_usage(self, move_line):
        usage = ''
        if (move_line.location_id.usage == 'internal') and (move_line.location_dest_id.usage == 'internal'):
            usage = 'internal'
        elif (move_line.location_id.usage != 'internal') and (move_line.location_dest_id.usage == 'internal'):
            usage = 'in'
        else:
            usage = 'out'
        return usage

    def _make_dict_move(self, level, parent_id, move_line, unfoldable=False):
        res_model, res_id, ref = self._get_reference(move_line)
        dummy, is_used = self._get_linked_move_lines(move_line)
        data = [{
            'level': level,
            'unfoldable': unfoldable,
            'date': move_line.move_id.date,
            'parent_id': parent_id,
            'is_used': bool(is_used),
            'usage': self._get_usage(move_line),
            'model_id': move_line.id,
            'model': 'stock.move.line',
            'product_id': move_line.product_id.display_name,
            'product_qty_uom': "%s %s" % (self._quantity_to_str(move_line.product_uom_id, move_line.product_id.uom_id, move_line.quantity), move_line.product_id.uom_id.name),
            'lot_name': move_line.lot_id.name,
            'lot_id': move_line.lot_id.id,
            'location_source': move_line.location_id.name,
            'location_destination': move_line.location_dest_id.name,
            'reference_id': ref,
            'res_id': res_id,
            'res_model': res_model}]
        return data

    @api.model
    def _final_vals_to_lines(self, final_vals, level):
        lines = []
        for data in final_vals:
            lines.append({
                'id': autoIncrement(),
                'model': data['model'],
                'model_id': data['model_id'],
                'parent_id': data['parent_id'],
                'usage': data.get('usage', False),
                'is_used': data.get('is_used', False),
                'lot_name': data.get('lot_name', False),
                'lot_id': data.get('lot_id', False),
                'reference': data.get('reference_id', False),
                'res_id': data.get('res_id', False),
                'res_model': data.get('res_model', False),
                'columns': [data.get('reference_id', False),
                            data.get('product_id', False),
                            format_datetime(self.env, data.get('date', False), tz=False, dt_format=False),
                            data.get('lot_name', False),
                            data.get('location_source', False),
                            data.get('location_destination', False),
                            data.get('product_qty_uom', 0)],
                'level': level,
                'unfoldable': data['unfoldable'],
            })
        return lines

    def _get_linked_move_lines(self, move_line):
        """ This method will return the consumed line or produced line for this operation."""
        return False, False

    @api.model
    def _lines(self, line_id=False, model_id=False, model=False, level=0, move_lines=None, **kw):
        final_vals = []
        lines = move_lines or []
        if model and line_id:
            move_line = self.env[model].browse(model_id)
            move_lines, is_used = self._get_linked_move_lines(move_line)
            if move_lines:
                lines = move_lines
            else:
                # Traceability in case of consumed in.
                lines = self._get_move_lines(move_line, line_id=line_id)
        for line in lines:
            unfoldable = False
            if line.consume_line_ids or (model != "stock.lot" and line.lot_id and self._get_move_lines(line)):
                unfoldable = True
            final_vals += self._make_dict_move(level, parent_id=line_id, move_line=line, unfoldable=unfoldable)
        return final_vals

    def get_pdf_lines(self, line_data=[]):
        lines = []
        for line in line_data:
            model = self.env[line['model_name']].browse(line['model_id'])
            unfoldable = False
            if line.get('unfoldable'):
                unfoldable = True
            final_vals = self._make_dict_move(line['level'], parent_id=line['id'], move_line=model, unfoldable=unfoldable)
            lines.append(self._final_vals_to_lines(final_vals, line['level'])[0])
        return lines

    def get_pdf(self, line_data=None):
        line_data = [] if line_data is None else line_data
        lines = self.with_context(print_mode=True).get_pdf_lines(line_data)
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
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

        return self.env['ir.actions.report']._run_wkhtmltopdf(
            [body],
            header=header.decode(),
            landscape=True,
            specific_paperformat_args={'data-report-margin-top': 17, 'data-report-header-spacing': 12}
        )

    def _get_main_lines(self):
        context = dict(self.env.context)
        return self.with_context(context).get_lines()

    @api.model
    def get_main_lines(self, given_context=None):
        res = self.search([('create_uid', '=', self.env.uid)], limit=1)
        if not res:
            return self.create({}).with_context(given_context)._get_main_lines()
        return res.with_context(given_context)._get_main_lines()
