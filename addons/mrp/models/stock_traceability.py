from odoo import models, api


class StockTraceabilityReport(models.TransientModel):
    _inherit = 'stock.traceability.report'

    @api.model
    def _get_reference(self, move_line):
        res_model, res_id, ref = super()._get_reference(move_line)
        if move_line.move_id.production_id and move_line.move_id.location_dest_usage != 'inventory':
            res_model = 'mrp.production'
            res_id = move_line.move_id.production_id.id
            ref = move_line.move_id.production_id.name
        if move_line.move_id.raw_material_production_id and move_line.move_id.location_dest_usage != 'inventory':
            res_model = 'mrp.production'
            res_id = move_line.move_id.raw_material_production_id.id
            ref = move_line.move_id.raw_material_production_id.name
        if move_line.move_id.unbuild_id:
            res_model = 'mrp.unbuild'
            res_id = move_line.move_id.unbuild_id.id
            ref = move_line.move_id.unbuild_id.name
        if move_line.move_id.consume_unbuild_id:
            res_model = 'mrp.unbuild'
            res_id = move_line.move_id.consume_unbuild_id.id
            ref = move_line.move_id.consume_unbuild_id.name
        return res_model, res_id, ref

    @api.model
    def _get_linked_move_lines(self, move_line):
        """ Return all the move lines linked to move_line.
        parent_lines are the move lines that happen first in the production chain. We go towards the raw components.
        children_lines are the move lines that happen later in the production chain. We go towards the final products. """
        parent_lines, children_lines = super()._get_linked_move_lines(move_line)
        if not parent_lines:
            parent_lines = (move_line.move_id.consume_unbuild_id and move_line.produce_line_ids) or (move_line.move_id.production_id and move_line.consume_line_ids)
        if not children_lines:
            children_lines = (move_line.move_id.unbuild_id and move_line.consume_line_ids) or (move_line.move_id.raw_material_production_id and move_line.produce_line_ids)
        return parent_lines, children_lines

    @api.model
    def get_lines(self, line_type=False, **kw):
        context = dict(self.env.context)
        model = kw and kw['model_name'] or context.get('model')
        record_id = kw and kw['record_id'] or context.get('active_id')
        level = kw and kw['level'] or 1
        if record_id and model == 'mrp.production':
            record = self.env[model].browse(record_id)
            lines = (record.move_raw_ids + record.move_finished_ids).move_line_ids.filtered(lambda m: m.state == 'done')
            return self._production_lines(move_lines=lines, level=level)
        return super().get_lines(line_type=line_type, **kw)

    @api.model
    def _production_lines(self, move_lines=None, level=0):
        """ If we come from a production order, the component lines are processed as parent
        lines and the final product lines are processed as child lines. """
        final_vals = []
        lines = move_lines or []
        for line in lines:
            line_type = 'child' if line.consume_line_ids else 'parent'
            unfoldable = self._is_unfoldable(line, line_type)
            final_vals.append(self._make_dict_move(move_line=line, line_type=line_type, level=level, unfoldable=unfoldable))
        return sorted(final_vals, key=lambda l: (l['date'], l['id']), reverse=True)
