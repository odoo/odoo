# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _


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


class MrpStockReport(models.TransientModel):
    _name = 'stock.traceability.report'

    @api.model
    def _get_move_lines(self, move_lines):
        res = self.env['stock.move.line']
        for move_line in move_lines:
            # if MTO
            if move_line.move_id.move_orig_ids:
                res |= move_line.move_id.move_orig_ids.mapped('move_line_ids').filtered(
                    lambda m: m.lot_id.id == move_line.lot_id.id)
            # if MTS
            else:
                if move_line:
                    res |= self.env['stock.move.line'].search([
                        ('product_id', '=', move_line.product_id.id),
                        ('lot_id', '=', move_line.lot_id.id),
                        ('id', '!=', move_line.id),
                        ('date', '<', move_line.date),
                    ])
        if res:
            res |= self._get_move_lines(res)
        return res

    @api.model
    def get_lines(self, line_id=None, **kw):
        context = dict(self.env.context)
        model = kw and kw['model_name'] or context.get('model')
        rec_id = kw and kw['model_id'] or context.get('active_id')
        level = kw and kw['level'] or 1
        lines = []
        move_line = self.env['stock.move.line']
        if rec_id and model in ('stock.production.lot', 'stock.move.line'):
            lines = move_line.search([
                ('lot_id', '=', context.get('lot_name') or rec_id),
                ('state', '=', 'done'),
                ('move_id.returned_move_ids', '=', False),
            ])
            if model == 'stock.move.line':
                for line in lines:
                    dummy, is_used = self._get_linked_move_lines(line)
                    if is_used:
                        move_line |= is_used
                lines = move_line
        elif rec_id and model in ('stock.picking', 'mrp.production'):
            record = self.env[model].browse(rec_id)
            if model == 'stock.picking':
                lines = record.move_lines.mapped('move_line_ids').filtered(lambda m: m.lot_id and m.state == 'done')
            else:
                lines = record.move_finished_ids.mapped('move_line_ids').filtered(lambda m: m.lot_id and m.state == 'done')
        move_line_vals = self._lines(line_id, model_id=rec_id, model=model, level=level, move_lines=lines)
        final_vals = sorted(move_line_vals, key=lambda v: v['date'], reverse=True)
        lines = self._final_vals_to_lines(final_vals, level)
        return lines

    @api.model
    def _get_reference(self, move_line):
        res_model = ''
        ref = ''
        res_id = False
        if move_line.picking_id:
            res_model = 'stock.picking'
            res_id = move_line.picking_id.id
            ref = move_line.picking_id.name
        elif move_line.move_id.inventory_id:
            res_model = 'stock.inventory'
            res_id = move_line.move_id.inventory_id.id
            ref = 'Inv. Adj.: ' + move_line.move_id.inventory_id.name
        elif move_line.move_id.scrapped and move_line.move_id.scrap_ids:
            res_model = 'stock.scrap'
            res_id = move_line.move_id.scrap_ids[0].id
            ref = move_line.move_id.scrap_ids[0].name
        return res_model, res_id, ref

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
        unfoldable = False if not move_line.lot_id else unfoldable
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
            'lot_name': move_line.lot_id.name,
            'lot_id': move_line.lot_id.id,
            'product_qty_uom': str(move_line.product_uom_id._compute_quantity(move_line.qty_done, move_line.product_id.uom_id, rounding_method='HALF-UP')) + ' ' + move_line.product_id.uom_id.name,
            'location_source': move_line.location_id.name if not unfoldable or level == 1 else False,
            'location_destination': move_line.location_dest_id.name if not unfoldable or level == 1 else False,
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
                            data.get('date', False),
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
    def _lines(self, line_id=None, model_id=False, model=False, level=0, move_lines=[], **kw):
        final_vals = []
        lines = move_lines or []
        if model and line_id:
            move_line = self.env[model].browse(model_id)
            move_lines, is_used = self._get_linked_move_lines(move_line)
            if move_lines:
                lines = move_lines
            else:
                if is_used:
                    # Traceability in case of consumed in.
                    move_line |= self._get_move_lines(move_line)
                for line in move_line:
                    final_vals += self._make_dict_move(level, parent_id=line_id, move_line=line)
        for line in lines:
            unfoldable = bool(line.produce_line_ids or line.consume_line_ids)
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

    def get_pdf(self, line_data=[]):
        lines = self.with_context(print_mode=True).get_pdf_lines(line_data)
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        rcontext = {
            'mode': 'print',
            'base_url': base_url,
        }

        body = self.env['ir.ui.view'].render_template(
            "stock.report_stock_inventory_print",
            values=dict(rcontext, lines=lines, report=self, context=self),
        )

        header = self.env['ir.actions.report'].render_template("web.internal_layout", values=rcontext)
        header = self.env['ir.actions.report'].render_template("web.minimal_layout", values=dict(rcontext, subst=True, body=header))

        return self.env['ir.actions.report']._run_wkhtmltopdf(
            [body],
            header=header,
            landscape=True,
            specific_paperformat_args={'data-report-margin-top': 10, 'data-report-header-spacing': 10}
        )

    def _get_html(self):
        result = {}
        rcontext = {}
        context = dict(self.env.context)
        rcontext['lines'] = self.with_context(context).get_lines()
        result['html'] = self.env.ref('stock.report_stock_inventory').render(rcontext)
        return result

    @api.model
    def get_html(self, given_context=None):
        res = self.search([('create_uid', '=', self.env.uid)], limit=1)
        if not res:
            return self.create({}).with_context(given_context)._get_html()
        return res.with_context(given_context)._get_html()
