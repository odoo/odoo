# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrTimeRuleRegenerateWizard(models.TransientModel):
    _inherit = 'hr.time.rule.regenerate.wizard'

    source_model_filter = fields.Selection(
        selection_add=[('hr.leave', 'Time Off only')],
        ondelete={'hr.leave': 'set default'},
    )

    def _collect_pure_alloc_rule_sources(self, Model, source_field, span_start, extra, seen_ids):
        result = []
        model_name = Model._name
        for rule in self.rule_ids:
            if rule.work_entry_type_id or not rule.allocation_type_id:
                continue
            Log = self.env['hr.time.rule.allocation.log'].sudo()
            candidate_emps = self.employee_ids or self.env['hr.employee'].sudo().search([])
            applicable = rule._get_applicable_employees(candidate_emps)
            logs = Log.search([
                ('allocation_id.work_entry_type_id', '=', rule.allocation_type_id.id),
                ('allocation_id.employee_id', 'in', applicable.ids),
                ('res_model', '=', model_name),
            ])
            out_ids = [l.res_id for l in logs if l.res_id not in seen_ids]
            if out_ids:
                for out in Model.sudo().search(
                    [('id', 'in', out_ids), (source_field, '!=', False)]
                    + extra + self._date_domain(span_start)
                ):
                    if out.id not in seen_ids:
                        seen_ids.add(out.id)
                        original_id = out.with_context(active_test=False)[source_field].id or 0
                        result.append((model_name, out, True, original_id, rule))
        return result
