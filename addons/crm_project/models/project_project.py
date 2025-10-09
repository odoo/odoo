from odoo import api, fields, models


class ProjectProject(models.Model):
    _inherit = 'project.project'

    lead_id = fields.Many2one('crm.lead', index=True, export_string_translation=False)

    @api.model
    def _get_template_default_context_whitelist(self):
        return [
            *super()._get_template_default_context_whitelist(),
            'lead_id',
        ]
