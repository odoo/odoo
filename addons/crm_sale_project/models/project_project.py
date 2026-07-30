from odoo import api, models


class ProjectProject(models.Model):
    _inherit = 'project.project'

    @api.model
    def default_get(self, fields):
        defaults = super().default_get(fields)
        if self.env.context.get('default_lead_id'):
            defaults['allow_billable'] = True
        return defaults

    # The dependencies of the overridden compute have to be restated, as only the
    # decorator of the resolved method is taken into account.
    @api.depends('lead_id', 'allow_billable')
    def _compute_is_opportunity_button_visible(self):
        super()._compute_is_opportunity_button_visible()
        for project in self:
            if not project.allow_billable:
                project.is_opportunity_button_visible = False
