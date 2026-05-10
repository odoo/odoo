from odoo import api, fields, models


class ClinicVisitDashboard(models.Model):
    _name = "clinic.visit.dashboard"
    _description = "Clinic Visit Dashboard"

    name = fields.Char(
        string="Name",
        default="Clinic Dashboard",
    )
    draft_count = fields.Integer(
        string="Draft",
        compute="_compute_visit_counts",
    )
    waiting_count = fields.Integer(
        string="Waiting",
        compute="_compute_visit_counts",
    )
    in_consultation_count = fields.Integer(
        string="In Consultation",
        compute="_compute_visit_counts",
    )
    done_count = fields.Integer(
        string="Done",
        compute="_compute_visit_counts",
    )
    cancelled_count = fields.Integer(
        string="Cancelled",
        compute="_compute_visit_counts",
    )

    @api.depends_context("uid")
    def _compute_visit_counts(self):
        Visit = self.env["clinic.visit"]
        counts = {
            "draft": Visit.search_count([("state", "=", "draft")]),
            "waiting": Visit.search_count([("state", "=", "waiting")]),
            "in_consultation": Visit.search_count(
                [("state", "=", "in_consultation")]
            ),
            "done": Visit.search_count([("state", "=", "done")]),
            "cancelled": Visit.search_count([("state", "=", "cancelled")]),
        }
        for dashboard in self:
            dashboard.draft_count = counts["draft"]
            dashboard.waiting_count = counts["waiting"]
            dashboard.in_consultation_count = counts["in_consultation"]
            dashboard.done_count = counts["done"]
            dashboard.cancelled_count = counts["cancelled"]

    def _get_visit_action(self, state, name):
        return {
            "type": "ir.actions.act_window",
            "name": name,
            "res_model": "clinic.visit",
            "view_mode": "list,form",
            "domain": [("state", "=", state)],
        }

    def action_open_draft(self):
        return self._get_visit_action("draft", "Draft Visits")

    def action_open_waiting(self):
        return self._get_visit_action("waiting", "Waiting Visits")

    def action_open_in_consultation(self):
        return self._get_visit_action(
            "in_consultation",
            "Visits In Consultation",
        )

    def action_open_done(self):
        return self._get_visit_action("done", "Done Visits")

    def action_open_cancelled(self):
        return self._get_visit_action("cancelled", "Cancelled Visits")
