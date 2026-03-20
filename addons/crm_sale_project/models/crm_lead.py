from odoo import api, fields, models


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    project_ids = fields.One2many('project.project', inverse_name='lead_id', groups="project.group_project_user", export_string_translation=False)
    project_count = fields.Integer(compute='_compute_project_count', groups="project.group_project_user", export_string_translation=False)
    task_count = fields.Integer(compute='_compute_task_count', groups="project.group_project_user", export_string_translation=False)

    @api.depends('project_ids')
    def _compute_project_count(self):
        project_count_per_lead = dict(
            self.env['project.project']._read_group(
                domain=[('lead_id', 'in', self.ids)],
                groupby=['lead_id'],
                aggregates=['__count'],
            ),
        )

        for lead in self:
            lead.project_count = project_count_per_lead.get(lead, 0)

    @api.depends('project_ids.task_ids')
    def _compute_task_count(self):
        task_count_per_lead = dict(
            self.env['project.task']._read_group(
                domain=[('project_id', 'in', self.project_ids.ids)],
                groupby=['project_id.lead_id'],
                aggregates=['__count'],
            ),
        )

        for lead in self:
            lead.task_count = task_count_per_lead.get(lead, 0)

    def _get_project_create_from_lead_context(self):
        """Return the context for creating a project from a lead."""
        self.ensure_one()
        return dict(
            default_company_id=self.company_id.id,
            default_lead_id=self.id,
            default_partner_id=self.partner_id.id,
            default_allow_billable=True,
        )

    def action_create_project(self):
        self.ensure_one()
        view_id = self.env.ref('crm_sale_project.crm_project_view_form_simplified_template', raise_if_not_found=False)
        return {
            **self.env['project.template.create.wizard'].action_open_template_view(),
            'name': self.env._('Create a Project'),
            'views': [(view_id.id, 'form')],
            'context': {
                **self._get_project_create_from_lead_context(),
                'default_name': self.name,
            },
        }

    def action_view_project_ids(self):
        self.ensure_one()

        if self.project_count == 1:
            action = self.project_ids.action_view_tasks()
            action['context'].update(self._get_project_create_from_lead_context())
        else:
            action = {
                **self.env['ir.actions.actions']._for_xml_id('project.open_view_project_all'),
                'domain': [
                    '|',
                    ('lead_id', '=', self.id),
                    ('id', 'in', self.project_ids.ids),
                ],
                'context': self._get_project_create_from_lead_context(),
            }
        return action
