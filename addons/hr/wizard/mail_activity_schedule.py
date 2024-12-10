# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from odoo import api, fields, models
from odoo.osv import expression


class MailActivitySchedule(models.TransientModel):
    _inherit = 'mail.activity.schedule'

    department_id = fields.Many2one('hr.department', compute='_compute_department_id')
    plan_department_filterable = fields.Boolean(compute='_compute_plan_department_filterable')

    @api.depends('department_id')
    def _compute_plan_available_ids(self):
        todo = self.filtered(lambda s: s.plan_department_filterable)
        for scheduler in todo:
            base_domain = scheduler._get_plan_available_base_domain()
            if not scheduler.department_id:
                final_domain = expression.AND([base_domain, [('department_id', '=', False)]])
            else:
                final_domain = expression.AND([base_domain, ['|', ('department_id', '=', False), ('department_id', '=', scheduler.department_id.id)]])
            scheduler.plan_available_ids = self.env['mail.activity.plan'].search(final_domain)
        super(MailActivitySchedule, self - todo)._compute_plan_available_ids()

    @api.depends('res_model')
    def _compute_plan_department_filterable(self):
        for wizard in self:
            wizard.plan_department_filterable = wizard.res_model == 'hr.employee'

    @api.depends('plan_date', 'plan_id')
    def _compute_plan_summary(self):
        if not self.env.context.get('sort_by_responsible', False) and self.env.context.get('active_model', False) != 'hr.employee':
            return super()._compute_plan_summary()
        self.plan_summary = False
        responsible_value_to_label = dict(
            self.env['mail.activity.plan.template']._fields['responsible_type']._description_selection(self.env)
        )
        for scheduler in self:
            templates_by_responsible_type = scheduler.plan_id.template_ids.grouped('responsible_type')
            scheduler.plan_summary = Markup('<ul>%(summary_by_responsible)s</ul>') % {
                'summary_by_responsible': Markup().join(
                    Markup("%(responsible)s %(summary_lines)s") % {
                        'responsible': responsible_value_to_label[key],
                        'summary_lines': scheduler._get_summary_lines(templates)
                    } for key, templates in templates_by_responsible_type.items()
                )}

    def action_schedule_plan(self):
        result = super().action_schedule_plan()
        if result.get('res_model') == 'hr.employee':
            applied_on = self._get_applied_on_records()
            if len(applied_on) == 1:
                return None  #don't want to open multiple form view
            result.pop('domain', None)
            if 'context' in result:
                result['context'].update({'search_default_group_activity_plans_ids': 1})
            else:
                result['context'] = {'search_default_group_activity_plans_ids': 1}
        return result

    @api.depends('res_model_id', 'res_ids')
    def _compute_department_id(self):
        for wizard in self:
            if wizard.plan_department_filterable:
                applied_on = wizard._get_applied_on_records()
                all_departments = applied_on.department_id
                wizard.department_id = False if len(all_departments) > 1 else all_departments
            else:
                wizard.department_id = False

    def _create_activity(self, record, template, responsible, date_deadline):
        if self.res_model == 'hr.employee' and template.plan_id:
            record.activity_plans_ids |= self.plan_id
            kwargs = {
                'summary': f"{template.plan_id.name} - {template.summary if template.summary else template.activity_type_id.name}",
            }
            activity = super()._create_activity(record, template, responsible, date_deadline, **kwargs)
            activity.plan_id = self.plan_id
            return activity
        super()._create_activity(record, template, responsible, date_deadline)
