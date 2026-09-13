from odoo import api, fields, models


class ProjectWorkflowStep(models.Model):
    _inherit = "project.workflow.step"

    show_rating_active = fields.Boolean(
        export_string_translation=False,
        compute="_compute_show_rating_active",
    )

    @api.depends("project_ids.allow_billable")
    def _compute_show_rating_active(self):
        for stage in self:
            stage.show_rating_active = any(stage.project_ids.mapped("allow_billable"))

    @api.onchange("project_ids")
    def _onchange_project_ids(self):
        if not any(self.project_ids.mapped("allow_billable")):
            self.rating_active = False
