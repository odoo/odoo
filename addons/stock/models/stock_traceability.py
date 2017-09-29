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
    def get_move_lines_upstream(self, move_lines):
        res = self.env['stock.move.line']
        for move_line in move_lines:
            # if MTO
            if move_line.move_id.move_orig_ids:
                res |= move_line.move_id.move_orig_ids.mapped('move_line_ids').filtered(
                    lambda m: m.lot_id.id == move_line.lot_id.id)
            # if MTS
            else:
                if move_line.location_id.usage == 'internal':
                    res |= self.env['stock.move.line'].search([
                        ('product_id', '=', move_line.product_id.id),
                        ('lot_id', '=', move_line.lot_id.id),
                        ('location_dest_id', '=', move_line.location_id.id),
                        ('id', '!=', move_line.id),
                        ('date', '<', move_line.date),
                    ])
        if res:
            res |= self.get_move_lines_upstream(res)
        return res

    @api.model
    def get_move_lines_downstream(self, move_lines):
        res = self.env['stock.move.line']
        for move_line in move_lines:
            # if MTO
            if move_line.move_id.move_dest_ids:
                res |= move_line.move_id.move_dest_ids.mapped('move_line_ids').filtered(
                    lambda m: m.lot_id.id == move_line.lot_id.id)
            # if MTS
            else:
                if move_line.location_dest_id.usage == 'internal':
                    res |= self.env['stock.move.line'].search([
                        ('product_id', '=', move_line.product_id.id),
                        ('lot_id', '=', move_line.lot_id.id),
                        ('location_id', '=', move_line.location_dest_id.id),
                        ('id', '!=', move_line.id),
                        ('date', '>', move_line.date),
                    ])
        if res:
            res |= self.get_move_lines_downstream(res)
        return res

    @api.model
    def get_lines(self, line_id=None, **kw):
        context = dict(self.env.context)
        stream = context.get('ttype')
        model = False
        model_id = False
        level = 1
        parent_quant = False
        if kw:
            level = kw['level']
            model = kw['model_name']
            model_id = kw['model_id']
            stream = kw['stream']
            parent_quant = kw['parent_quant']
        res = []
        if context.get('active_id') and not context.get('model') or context.get('model') == 'stock.production.lot':
            if stream == "downstream":
                move_ids = self.env['stock.move.line'].search([
                    ('lot_id', '=', context.get('active_id')),
                    ('location_id.usage', '!=', 'internal'),
                    ('state', '=', 'done'),
                    ('move_id.returned_move_ids', '=', False),
                ])
                res += self._lines(line_id, model_id=model_id, model='stock.move.line', level=level, parent_quant=parent_quant,
                                  stream=stream, obj_ids=move_ids)
                quant_ids = self.env['stock.quant'].search([
                    ('lot_id', '=', context.get('active_id')),
                    ('quantity', '<', 0),
                    ('location_id.usage', '=', 'internal'),
                ])
                res += self._lines(line_id, model_id=model_id, model='stock.quant', level=level,
                                   parent_quant=parent_quant, stream=stream, obj_ids=quant_ids)
            else:
                move_ids = self.env['stock.move.line'].search([
                    ('lot_id', '=', context.get('active_id')),
                    ('location_dest_id.usage', '!=', 'internal'),
                    ('state', '=', 'done'),
                    ('move_id.returned_move_ids', '=', False),
                ])
                res += self._lines(line_id, model_id=model_id, model='stock.move.line', level=level, parent_quant=parent_quant,
                                  stream=stream, obj_ids=move_ids)
                quant_ids = self.env['stock.quant'].search([
                    ('lot_id', '=', context.get('active_id')),
                    ('quantity', '>', 0),
                    ('location_id.usage', '=', 'internal'),
                ])
                res += self._lines(line_id, model_id=model_id, model='stock.quant', level=level,
                                   parent_quant=parent_quant, stream=stream, obj_ids=quant_ids)
        elif context.get('active_id') and context.get('model') == 'stock.picking':
            move_ids = self.env['stock.picking'].browse(context['active_id']).move_lines.mapped('move_line_ids').filtered(lambda m: m.lot_id and m.state == 'done')
            res = self._lines(line_id, model_id=model_id, model='stock.move.line', level=level, parent_quant=parent_quant, stream=stream, obj_ids=move_ids)
        elif context.get('active_id') and context.get('model') == 'stock.move.line':
            move_line_ids = self.env['stock.move.line'].browse(context.get('active_id'))
            res = self._lines(line_id, model_id=context.get('active_id'), model=context.get('model'), level=level, parent_quant=parent_quant, stream=stream, obj_ids=move_line_ids)
        else:
            res = self._lines(line_id,  model_id=model_id, model=model, level=level, parent_quant=parent_quant, stream=stream)
        reverse_sort = True
        if stream == "downstream":
            reverse_sort = False
        final_vals = sorted(res, key=lambda v: v['date'], reverse=reverse_sort)
        lines = self.final_vals_to_lines(final_vals, level)
        return lines

    @api.model
    def get_links(self, move_line):
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

    def make_dict_move(self, level, parent_id, move_line, stream=False, unfoldable=False):
        res_model, res_id, ref = self.get_links(move_line)
        data = [{
            'level': level,
            'unfoldable': unfoldable,
            'date': move_line.move_id.date,
            'parent_id': parent_id,
            'model_id': move_line.id,
            'model':'stock.move.line',
            'product_id': move_line.product_id.display_name,
            'product_qty_uom': str(move_line.product_uom_id._compute_quantity(move_line.qty_done, move_line.product_id.uom_id, rounding_method='HALF-UP')) + ' ' + move_line.product_id.uom_id.name,
            'location': move_line.location_id.name + ' -> ' + move_line.location_dest_id.name,
            'reference_id': ref,
            'res_id': res_id,
            'stream': stream,
            'res_model': res_model}]
        return data

    def make_dict_head(self, level, parent_id, model=False, stream=False, move_line=False):
        data = []
        if model == 'stock.move.line':
            data = [{
                'level': level,
                'unfoldable': True,
                'date': move_line.move_id.date,
                'model_id': move_line.id,
                'parent_id': parent_id,
                'model': model or 'stock.move.line',
                'product_id': move_line.product_id.display_name,
                'lot_id': move_line.lot_id.name,
                'product_qty_uom': str(move_line.product_uom_id._compute_quantity(move_line.qty_done, move_line.product_id.uom_id, rounding_method='HALF-UP')) + ' ' + move_line.product_id.uom_id.name,
                'location': move_line.location_dest_id.name,
                'stream': stream,
                'reference_id': False}]
        elif model == 'stock.quant':
            data = [{
                'level': level,
                'unfoldable': True,
                'date': move_line.write_date,
                'model_id': move_line.id,
                'parent_id': parent_id,
                'model': model or 'stock.quant',
                'product_id': move_line.product_id.display_name,
                'lot_id': move_line.lot_id.name,
                'product_qty_uom': str(move_line.quantity) + ' ' + move_line.product_id.uom_id.name,
                'location': move_line.location_id.name,
                'stream': stream,
                'reference_id': False}]
        return data

    @api.model
    def upstream_traceability(self, level, stream=False, line_id=False, model=False, model_obj=False, parent_quant=False):
        final_vals =[]
        if model == 'stock.move.line':
            moves = self.get_move_lines_upstream(model_obj)
        elif model == 'stock.quant':
            moves = self.env['stock.move.line'].search([
                ('location_dest_id', '=', model_obj.location_id.id),
                ('lot_id', '=', model_obj.lot_id.id),
                ('date', '<=', model_obj.write_date),
                ('state', '=', 'done'),
            ])
            moves |= self.get_move_lines_upstream(moves)
        for move in moves:
            unfoldable = False
            if move.consume_line_ids:
                unfoldable = True
            final_vals += self.make_dict_move(level, stream=stream, parent_id=line_id, move_line=move, unfoldable=unfoldable)
        return final_vals

    @api.model
    def downstream_traceability(self, level, stream=False, line_id=False, model=False, model_obj=False, parent_quant=False):
        final_vals = []
        if model == 'stock.move.line':
            moves = self.get_move_lines_downstream(model_obj)
        elif model == 'stock.quant':
            moves = self.env['stock.move.line'].search([
                ('location_id', '=', model_obj.location_id.id),
                ('lot_id', '=', model_obj.lot_id.id),
                ('date', '>=', model_obj.write_date),
                ('state', '=', 'done'),
            ])
            moves |= self.get_move_lines_downstream(moves)
        for move in moves:
            unfoldable = False
            if move.produce_line_ids:
                unfoldable = True
            final_vals += self.make_dict_move(level, stream=stream, parent_id=line_id, move_line=move, unfoldable=unfoldable)
        return final_vals

    @api.model
    def final_vals_to_lines(self, final_vals, level):
        lines = []
        for data in final_vals:
            lines.append({
                'id': autoIncrement(),
                'model': data['model'],
                'model_id': data['model_id'],
                'stream': data['stream'] or 'upstream',
                'parent_id': data['parent_id'],
                'parent_quant': data.get('parent_quant', False),
                'type': 'line',
                'reference': data.get('reference_id', False),
                'res_id': data.get('res_id', False),
                'res_model': data.get('res_model', False),
                'name': _(data.get('lot_id', False)),
                'columns': [data.get('reference_id', False) or data.get('product_id', False),
                            data.get('lot_id', False),
                            data.get('date', False),
                            data.get('product_qty_uom', 0),
                            data.get('location', False)],
                'level': level,
                'unfoldable': data['unfoldable'],
            })
        return lines

    @api.model
    def _lines(self, line_id=None, model_id=False, model=False, level=0, parent_quant=False, stream=False, obj_ids=[], **kw):
        final_vals = []
        if model and line_id:
            model_obj = self.env[model].browse(model_id)
            if stream == "downstream":
                final_vals += self.downstream_traceability(level, stream='downstream', line_id=line_id, model=model, model_obj=model_obj, parent_quant=parent_quant)
                if model == 'stock.move.line':
                    if model_obj.produce_line_ids:
                        final_vals += self.get_produced_or_consumed_vals(model_obj.produce_line_ids, level, model=model, stream=stream, parent_id=line_id)
                    else:
                        final_vals = self.make_dict_move(level, stream=stream, parent_id=line_id,move_line=model_obj) + final_vals
            else:
                final_vals += self.upstream_traceability(level, stream='upstream', line_id=line_id, model=model, model_obj=model_obj, parent_quant=parent_quant)
                if model == 'stock.move.line':
                    if model_obj.consume_line_ids:
                        final_vals += self.get_produced_or_consumed_vals(model_obj.consume_line_ids, level, model=model, stream=stream, parent_id=line_id)
                    else:
                        final_vals = self.make_dict_move(level, stream=stream, parent_id=line_id, move_line=model_obj) + final_vals
        else:
            for move_line in obj_ids:
                final_vals += self.make_dict_head(level, stream=stream, parent_id=line_id, model=model or 'stock.pack.operation', move_line=move_line)
        return final_vals

    @api.model
    def get_produced_or_consumed_vals(self, move_lines, level, model, stream, parent_id):
        final_vals = []
        for line in move_lines:
            final_vals += self.make_dict_head(level, model=model, stream=stream, parent_id=parent_id, move_line=line)
        return final_vals

    def get_pdf_lines(self, line_data=[]):
        final_vals = []
        lines = []
        for line in line_data:
            model = self.env[line['model_name']].browse(line['model_id'])
            if line.get('unfoldable'):
                    final_vals += self.make_dict_head(line['level'], model=line['model_name'], parent_id=line['id'], move_line=model)
            else:
                if line['model_name'] == 'stock.move.line':
                    final_vals += self.make_dict_move(line['level'], parent_id=line['id'], move_line=model)
        for data in final_vals:
            lines.append({
                'id': autoIncrement(),
                'model': data['model'],
                'model_id': data['model_id'],
                'parent_id': data['parent_id'],
                'stream': "%s" % (data['stream']),
                'type': 'line',
                'name': _(data.get('lot_id')),
                'columns': [data.get('reference_id') or data.get('product_id'),
                            data.get('lot_id'),
                            data.get('date'),
                            data.get('product_qty_uom', 0),
                            data.get('location')],
                'level': data['level'],
                'unfoldable': data['unfoldable'],
            })

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
