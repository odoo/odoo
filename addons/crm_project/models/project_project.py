from odoo import api, fields, models


class ProjectProject(models.Model):
    _inherit = 'project.project'

    lead_id = fields.Many2one('crm.lead', index=True, export_string_translation=False)
    is_opportunity_button_visible = fields.Boolean(compute='_compute_is_opportunity_button_visible', export_string_translation=False)

    @api.depends('lead_id')
    def _compute_is_opportunity_button_visible(self):
        for project in self:
            project.is_opportunity_button_visible = bool(project.lead_id)

    @api.model
    def _get_template_default_context_whitelist(self):
        return [
            *super()._get_template_default_context_whitelist(),
            'lead_id',
        ]

    def action_view_lead(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead',
            'view_mode': 'form',
            'res_id': self.lead_id.id,
            'context': {'create': False},
        }
