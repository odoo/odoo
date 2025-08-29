# Copyright (C) 2019 - TODAY, Patrick Wilson
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class FSMLocation(models.Model):
    _inherit = "fsm.location"

    project_count = fields.Integer(
        compute="_compute_project_count", string="# Projects"
    )

    def _compute_project_count(self):
        for location in self:
            location.project_count = self.env["project.project"].search_count(
                [("fsm_location_id", "=", location.id)]
            )

    def action_view_project(self):
        for location in self:
            project_ids = self.env["project.project"].search(
                [("fsm_location_id", "=", location.id)]
            )
            action = self.env.ref(
                "fieldservice_project.action_fsm_location_project"
            ).read()[0]
            action["context"] = {}
            if len(project_ids) == 1:
                action["views"] = [(self.env.ref("project.edit_project").id, "form")]
                action["res_id"] = project_ids.ids[0]
            else:
                action["domain"] = [("id", "in", project_ids.ids)]
            return action
