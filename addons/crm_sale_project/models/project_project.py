from odoo import api, fields, models


class ProjectProject(models.Model):
    _inherit = 'project.project'

    lead_id = fields.Many2one('crm.lead', index=True, export_string_translation=False)

    @api.model
    def default_get(self, fields):
        defaults = super().default_get(fields)
        if self.env.context.get('default_lead_id'):
            defaults['allow_billable'] = True
        return defaults

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
