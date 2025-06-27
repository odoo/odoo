# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import api, fields, models
from odoo.tools.translate import _


class CrmLead(models.Model):
    _inherit = "crm.lead"

    linked_project_ids = fields.One2many("project.project", inverse_name="lead_id", help="Projects linked to this lead.")
    linked_project_count = fields.Integer(compute="_compute_linked_project_count", help="Number of projects linked to this lead.")

    @api.depends("linked_project_ids")
    def _compute_linked_project_count(self):
        self.linked_project_count = 0
        for lead, count in self.env["project.project"]._read_group(
            domain=[("lead_id", "in", self.ids)],
            groupby=["lead_id"],
            aggregates=["__count"],
        ):
            lead.linked_project_count = count

    def open_linked_projects(self):
        self.ensure_one()

        action = {
            "type": "ir.actions.act_window",
            "name": _("Lead Projects"),
            "res_model": "project.project",
            "view_mode": "kanban,form",
            "context": dict(self.env.context, default_company_id=self.company_id.id, default_lead_id=self.id),
            "domain": [("id", "in", self.linked_project_ids.ids)],
            "help": """
                <p class="o_view_nocontent_smiling_face">
                    No projects found. Let"s create one!
                </p>
                <p>
                    Create projects to organize your tasks. Define a different workflow for each project.
                </p>
            """,
        }
        if self.linked_project_count == 1:
            action.update({
                "view_mode": "form",
                "res_id": self.linked_project_ids.id,
            })
        return action
