from odoo import api, models


class ProjectTemplateCreateWizard(models.TransientModel):
    _inherit = 'project.template.create.wizard'

    @api.model
    def action_open_template_view(self):
        action = super().action_open_template_view()
        if self.env.context.get("default_lead_id"):
            action['context']['default_lead_id'] = self.env.context.get("default_lead_id")
        return action

    def action_create_project_from_lead(self):
        """Create a project either from template or directly if no template is set."""
        self.ensure_one()
        if self.template_id:
            project = self._create_project_from_template()
        else:
            lead_id = self.env['crm.lead'].browse(self.env.context.get("default_lead_id"))
            values = {
                'partner_id': lead_id.partner_id.id,
                'company_id': lead_id.company_id.id,
            }
            project = self.env['project.project'].create(values)
        if project.lead_id:
            project.lead_id.message_post(body=self.env._('%s Project created', project._get_html_link()))
        return project.action_view_tasks()
