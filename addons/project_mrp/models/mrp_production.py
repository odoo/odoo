from odoo import api, fields, models


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    project_id = fields.Many2one(
        comodel_name="project.project",
        compute="_compute_project_id",
        store=True,
        readonly=False,
        domain=[("is_template", "=", False)],
    )

    @api.depends("bom_id")
    def _compute_project_id(self):
        if not self.env.context.get("from_project_action"):
            for production in self:
                production.project_id = production.bom_id.project_id

    def action_generate_bom(self):
        action = super().action_generate_bom()
        action["context"]["default_project_id"] = self.project_id.id
        return action

    def action_view_project(self):
        self.check_singleton()
        return {
            "type": "ir.actions.act_window",
            "res_model": "project.project",
            "view_mode": "form",
            "res_id": self.project_id.id,
        }
