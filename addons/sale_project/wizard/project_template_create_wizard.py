from odoo import fields, models


class ProjectTemplateCreateWizard(models.TransientModel):
    _inherit = 'project.template.create.wizard'

    partner_id = fields.Many2one("res.partner")
    allow_billable = fields.Boolean(related="template_id.allow_billable")

    def _get_template_whitelist_fields(self):
        res = super()._get_template_whitelist_fields()
        if self.allow_billable:
            res.append("partner_id")
        return res

    def action_create_project_from_so(self):
        self.ensure_one()
        project_vals = {
            'name': self.name,
        }
        if self.template_id:
            project = self.template_id.action_create_from_template(values=project_vals)
        else:
            project = self.env['project.project'].create(project_vals)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'project.project',
            'res_id': project.id,
            'view_mode': 'form',
        }
