from odoo import api, fields, models


class ProjectTemplateCreateWizard(models.TransientModel):
    _name = 'project.template.create.wizard'
    _description = 'Project Template create Wizard'

    name = fields.Char(string="Name", required=True)
    date_start = fields.Date(string="Start Date")
    date = fields.Date(string='Expiration Date')
    alias_name = fields.Char(string="Alias Name")
    alias_domain_id = fields.Many2one("mail.alias.domain", string="Alias Domain")
    partner_id = fields.Many2one("res.partner")
    template_id = fields.Many2one("project.project", default=lambda self: self._context.get('template_id'))

    def create_project_from_template(self):
        # Dictionary with all fields and their values
        field_values = self._convert_to_write(
            {
                fname: self[fname]
                for fname in self._fields.keys() - ["id", "template_id"]
            }
        )
        project = self.template_id.action_create_from_template(field_values)
        # Opening project task views after creation of project from template
        return project.action_view_tasks()

    @api.model
    def action_open_template_view(self):
        view = self.env.ref('project.project_project_view_form_simplified_template', raise_if_not_found=False)
        if not view:
            return {}
        return {
            'name': self.env._('Create a Project from Template %s', self._context.get('template_name')),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'views': [(view.id, 'form')],
            'res_model': 'project.template.create.wizard',
            'res_id': self.id,
            'target': 'new',
            'context': self.env.context,
        }
