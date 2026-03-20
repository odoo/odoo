from odoo import api, fields, models


class ProjectTemplateCreateWizard(models.TransientModel):
    _inherit = 'project.template.create.wizard'

    customer_action = fields.Selection([
        ('create', 'Create a new customer'),
        ('exist', 'Link to an existing customer'),
        ('nothing', 'Do not link to a customer'),
    ], string='Project Customer', default='create')
    is_customer_action_visible = fields.Boolean(compute='_compute_customer_action_visibility', export_string_translation=False)

    def _compute_customer_action_visibility(self):
        for wizard in self:
            wizard.is_customer_action_visible = not bool(self.env.context.get("default_partner_id"))

    @api.model
    def action_open_template_view(self):
        action = super().action_open_template_view()
        if self.env.context.get("default_lead_id"):
            action['context']['default_lead_id'] = self.env.context.get("default_lead_id")
            action['context']['default_partner_id'] = self.env.context.get("default_partner_id")
        return action

    def action_create_project_from_lead(self):
        """Create a project either from template or directly if no template is set."""
        self.ensure_one()
        lead = self.env['crm.lead'].browse(self.env.context.get("default_lead_id"))

        if self.customer_action == 'create':
            lead._handle_partner_assignment(create_missing=True)
            self.partner_id = lead.partner_id
        elif self.customer_action == 'exist':
            lead._handle_partner_assignment(force_partner_id=self.partner_id.id, create_missing=False)

        if self.template_id:
            project = self._create_project_from_template()
        else:
            values = {
                'partner_id': self.partner_id.id,
                'company_id': lead.company_id.id,
            }
            project = self.env['project.project'].create(values)
        return project.action_view_tasks()
