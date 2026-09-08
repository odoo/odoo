from odoo import models, api


class StockTraceabilityReport(models.TransientModel):
    _inherit = 'stock.traceability.report'

    @api.model
    def _get_reference(self, move_line):
        res_model, res_id, ref = super()._get_reference(move_line)
        move = move_line.move_id
        if move.production_id and move.location_dest_usage != 'inventory':
            res_model = 'mrp.production'
            res_id = move.production_id.id
            ref = move.production_id.name
        elif move.raw_material_production_id and move.location_dest_usage != 'inventory':
            res_model = 'mrp.production'
            res_id = move.raw_material_production_id.id
            ref = move.raw_material_production_id.name
        elif move.unbuild_id:
            res_model = 'mrp.unbuild'
            res_id = move.unbuild_id.id
            ref = move.unbuild_id.name
        elif move.consume_unbuild_id:
            res_model = 'mrp.unbuild'
            res_id = move.consume_unbuild_id.id
            ref = move.consume_unbuild_id.name
        return res_model, res_id, ref

    @api.model
    def _get_linked_move_lines(self, move_line):
        """ Return all the move lines linked to move_line.
        parent_lines are the move lines that happen first in the production chain. We go towards the raw components.
        children_lines are the move lines that happen later in the production chain. We go towards the final products. """
        parent_lines, children_lines = super()._get_linked_move_lines(move_line)
        move = move_line.move_id
        if not parent_lines:
            parent_lines = (move.consume_unbuild_id and move_line.produce_line_ids) or (move.production_id and move_line.consume_line_ids)
        if not children_lines:
            children_lines = (move.unbuild_id and move_line.consume_line_ids) or (move.raw_material_production_id and move_line.produce_line_ids)
        return parent_lines, children_lines

    @api.model
    def get_lines(self, line_type=None, **kw):
        context = dict(self.env.context)
        model = kw and kw['model_name'] or context.get('model')
        record_id = kw and kw['record_id'] or context.get('active_id')
        level = kw and kw['level'] or 1
        if record_id and model == 'mrp.production':
            return self._get_production_lines(record_id=record_id, level=level)
        return super().get_lines(line_type=line_type, **kw)

    @api.model
    def _get_production_lines(self, record_id=0, level=0):
        """ If we come from a production order, the component lines are processed as parent
        lines and the final product lines are processed as child lines. """
        final_vals = []
        production = self.env['mrp.production'].browse(record_id)
        lines = (production.move_raw_ids + production.move_finished_ids).move_line_ids.filtered(lambda m: m.state == 'done')
        for line in lines:
            line_type = 'child' if line.consume_line_ids else 'parent'
            unfoldable = self._is_unfoldable(line, line_type)
            final_vals.append(self._make_dict_move(move_line=line, line_type=line_type, level=level, unfoldable=unfoldable))
        return sorted(final_vals, key=lambda l: (l['date'], l['id']), reverse=True)
