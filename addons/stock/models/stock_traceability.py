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
        StockQuant = self.env['stock.quant']
        context_ids = []
        if context.get('active_id') and not context.get('model') or context.get('model') == 'stock.production.lot':
            context_ids = StockQuant.search([['lot_id', '=', context.get('active_id')]])
        elif context.get('active_id') and context.get('model') == 'mrp.production':
            context_ids = self.env['mrp.production'].browse(context['active_id']).move_finished_ids.mapped('quant_ids')
        elif context.get('active_id') and context.get('model') == 'stock.picking':
            context_ids = self.env['stock.picking'].browse(context['active_id']).move_lines.mapped('quant_ids')
        context.update({
            'context_ids': context_ids or context.get('model') == 'stock.quant' and self.env[context.get('model')].browse(context.get('active_id')) or [],
            'stream': stream
        })
        res = self.with_context(context)._lines(line_id, model_id=model_id, model=model, level=level, parent_quant=parent_quant)
        return res

    @api.model
    def get_links(self, move):
        res_model = ''
        ref = ''
        res_id = False
        if move.picking_id:
            res_model = 'stock.picking'
            res_id = move.picking_id.id
            ref = move.picking_id.name
        elif move.raw_material_production_id or move.production_id:
            res_model = 'mrp.production'
            res_id = move.raw_material_production_id.id or move.production_id.id
            ref = move.raw_material_production_id.name or move.production_id.name
        elif move.unbuild_id or move.consume_unbuild_id:
            res_model = 'mrp.unbuild'
            res_id = move.consume_unbuild_id.id or move.unbuild_id.id
            ref = move.consume_unbuild_id.name or move.unbuild_id.name
        return res_model, res_id, ref

    def make_dict_move(self, level, line_id, move, stream=False, final_vals=None):
        res_model, res_id, ref = self.get_links(move)
        data = {
            'level': level,
            'unfoldable': False,
            'date': move.date,
            'parent_id': line_id,
            'model_id': move.id,
            'model':'stock.move',
            'product_id': move.product_id.display_name,
            'product_qty_uom': False,
            'location_source': move.location_id.name,
            'location_destination': move.location_dest_id.name,
            'reference_id': ref,
            'res_id': res_id,
            'stream': stream,
            'res_model': res_model}
        final_vals.append(data)
        return final_vals

    def make_dict_head(self, level, line_id, stream=False, move=False, quant=False, final_vals=None):
        if move:
            res_model, res_id, ref = self.get_links(move)
            final_vals.append({
                'level': level,
                'unfoldable': True,
                'model_id': move.id,
                'parent_id': line_id,
                'model': 'stock.move',
                'parent_quant': quant.id if quant else False,
                'product_id': move.product_id.display_name,
                'product_qty_uom': False,
                'location_source': move.location_id.name,
                'location_destination': move.location_dest_id.name,
                'reference_id': ref,
                'res_id': res_id,
                'stream': stream,
                'res_model': res_model})
        else:
            final_vals.append({
                'level': level,
                'unfoldable': True if quant.history_ids else False,
                'date': quant.lot_id.name,
                'model_id': quant.id,
                'parent_id': line_id,
                'model':'stock.quant',
                'product_id': quant.product_id.display_name,
                'product_qty_uom': str(quant.qty) + ' ' + quant.product_id.uom_id.name,
                'location_source': False,
                'location_destination': False,
                'stream': stream,
                'reference_id': False})
        return final_vals

    @api.model
    def upstream_traceability(self, level, stream=False, line_id=False, model=False, model_id=False, parent_quant=False, final_vals=None):
        model_obj = self.env[model].browse(model_id)
        if model == 'stock.quant':
            for move in model_obj.history_ids.sorted(key=lambda r: r.date, reverse=True):
                if move.production_id or move.unbuild_id:
                    final_vals = self.make_dict_head(level, stream=stream, line_id=line_id, move=move, quant=model_obj, final_vals=final_vals)
                else:
                    final_vals = self.make_dict_move(level, stream=stream, line_id=line_id, move=move, final_vals=final_vals)
        else:
            if model_obj.production_id or model_obj.unbuild_id:
                parent_quant = self.env['stock.quant'].browse(parent_quant)
                for quant in parent_quant.consumed_quant_ids.filtered(lambda x: x.qty > 0):
                    final_vals = self.make_dict_head(level, line_id=line_id, stream=stream, move=False, quant=quant, final_vals=final_vals)

    @api.model
    def downstream_traceability(self, level, stream=False, line_id=False, model=False, model_id=False, parent_quant=False, final_vals=None):
        model_obj = self.env[model].browse(model_id)
        if model == 'stock.quant':
            for move in model_obj.history_ids.sorted(key=lambda r: r.date):
                if move.raw_material_production_id or move.consume_unbuild_id:
                    final_vals = self.make_dict_head(level, stream=stream, line_id=line_id, move=move, quant=model_obj, final_vals=final_vals)
                else:
                    final_vals = self.make_dict_move(level, stream=stream, line_id=line_id, move=move, final_vals=final_vals)
        else:
            if model_obj.raw_material_production_id or model_obj.consume_unbuild_id:
                parent_quant = self.env['stock.quant'].browse(parent_quant)
                for quant in parent_quant.produced_quant_ids.filtered(lambda x: x.qty > 0):
                    final_vals = self.make_dict_head(level, stream=stream, line_id=line_id, move=False, quant=quant, final_vals=final_vals)
        return True

    @api.model
    def _lines(self, line_id=None, model_id=False, model=False, level=0, parent_quant=False, **kw):
        lines = []
        context = dict(self.env.context)
        final_vals = []
        if model:
            if context.get('stream') == "downstream" or context.get('stream') == 'downstream':
                self.downstream_traceability(level, stream='downstream', line_id=line_id, model=model, model_id=model_id, parent_quant=parent_quant, final_vals=final_vals)
            else:
                self.upstream_traceability(level, stream='upstream', line_id=line_id, model=model, model_id=model_id, parent_quant=parent_quant, final_vals=final_vals)
        else:
            for quant in context['context_ids']:
                final_vals = self.make_dict_head(level, stream=context.get('stream', False), line_id=line_id, move=False, quant=quant, final_vals=final_vals)
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
                            data.get('date', False),
                            data.get('product_qty_uom', 0),
                            data.get('location_source', False),
                            data.get('location_destination', False)],
                'level': level,
                'unfoldable': data['unfoldable'],
            })
        return lines

    @api.multi
    def get_pdf_lines(self, line_data=[]):
        final_vals = []
        lines = []
        for line in line_data:
            model = self.env[line['model_name']].browse(line['model_id'])
            if line.get('unfoldable'):
                if line['model_name'] == 'stock.quant':
                    final_vals = self.make_dict_head(line['level'], line_id=line['id'], move=False, quant=model, final_vals=final_vals)
                else:
                    final_vals = self.make_dict_head(line['level'], line_id=line['id'], move=model, quant=False, final_vals=final_vals)
            else:
                if line['model_name'] == 'stock.move':
                    final_vals = self.make_dict_move(line['level'], line_id=line['id'], move=model, final_vals=final_vals)
                else:
                    final_vals = self.make_dict_head(line['level'], line_id=line['id'], quant=model, final_vals=final_vals)
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
                            data.get('date'),
                            data.get('product_qty_uom', 0),
                            data.get('location_source'),
                            data.get('location_destination')],
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
            "mrp_workorder.report_stock_inventory_print",
            values=dict(rcontext, lines=lines, report=self, context=self),
        )

        header = self.env['ir.actions.report'].render_template("web.internal_layout", values=rcontext)
        header = self.env['ir.actions.report'].render_template("web.minimal_layout", values=dict(rcontext, subst=True, body=header))
        landscape = True

        return self.env['ir.actions.report']._run_wkhtmltopdf(
            [self.env['ir.actions.report'].create_wkhtmltopdf_obj(header, body, None)],
            landscape, self.env.user.company_id.paperformat_id,
            specific_paperformat_args={'data-report-margin-top': 10, 'data-report-header-spacing': 10}
        )

    def _get_html(self):
        result = {}
        rcontext = {}
        context = dict(self.env.context)
        rcontext['lines'] = self.with_context(context).get_lines()
        result['html'] = self.env.ref('mrp_workorder.report_stock_inventory').render(rcontext)
        return result

    @api.model
    def get_html(self, given_context=None):
        res = self.search([('create_uid', '=', self.env.uid)], limit=1)
        if not res:
            return self.create({}).with_context(given_context)._get_html()
        return res.with_context(given_context)._get_html()
