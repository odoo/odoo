from datetime import datetime, time

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
    total_visit_count = fields.Integer(
        string="Total Visits",
        compute="_compute_visit_counts",
    )
    total_patient_count = fields.Integer(
        string="Total Patients",
        compute="_compute_visit_counts",
    )
    today_visit_count = fields.Integer(
        string="Today's Visits",
        compute="_compute_visit_counts",
    )
    today_done_count = fields.Integer(
        string="Completed Today",
        compute="_compute_visit_counts",
    )
    today_revenue = fields.Float(
        string="Revenue Today",
        compute="_compute_visit_counts",
    )
    active_queue_count = fields.Integer(
        string="Queue Count",
        compute="_compute_visit_counts",
    )
    average_wait_minutes = fields.Integer(
        string="Average Wait",
        compute="_compute_active_visit_ids",
    )
    longest_wait_minutes = fields.Integer(
        string="Longest Wait",
        compute="_compute_active_visit_ids",
    )
    current_visit_id = fields.Many2one(
        "clinic.visit",
        string="Current Consultation",
        compute="_compute_active_visit_ids",
    )
    next_visit_id = fields.Many2one(
        "clinic.visit",
        string="Next Patient",
        compute="_compute_active_visit_ids",
    )
    longest_waiting_visit_id = fields.Many2one(
        "clinic.visit",
        string="Longest Waiting",
        compute="_compute_active_visit_ids",
    )
    active_visit_ids = fields.Many2many(
        "clinic.visit",
        string="Active Queue",
        compute="_compute_active_visit_ids",
    )
    today_completed_visit_ids = fields.Many2many(
        "clinic.visit",
        string="Recently Completed",
        compute="_compute_active_visit_ids",
    )

    @api.depends_context("uid")
    def _compute_visit_counts(self):
        Visit = self.env["clinic.visit"]
        Patient = self.env["clinic.patient"]
        today_domain = self._get_today_domain()
        counts = {
            "draft": Visit.search_count([("state", "=", "draft")]),
            "waiting": Visit.search_count([("state", "=", "waiting")]),
            "in_consultation": Visit.search_count(
                [("state", "=", "in_consultation")]
            ),
            "done": Visit.search_count([("state", "=", "done")]),
            "cancelled": Visit.search_count([("state", "=", "cancelled")]),
            "total_visit": Visit.search_count([]),
            "total_patient": Patient.search_count([]),
            "today_visit": Visit.search_count(today_domain),
            "today_done": Visit.search_count(
                today_domain + [("state", "=", "done")]
            ),
            "active_queue": Visit.search_count(
                [("state", "in", ("waiting", "in_consultation"))]
            ),
            "today_revenue": sum(
                Visit.search(today_domain + [("state", "=", "done")]).mapped("fee")
            ),
        }
        for dashboard in self:
            dashboard.draft_count = counts["draft"]
            dashboard.waiting_count = counts["waiting"]
            dashboard.in_consultation_count = counts["in_consultation"]
            dashboard.done_count = counts["done"]
            dashboard.cancelled_count = counts["cancelled"]
            dashboard.total_visit_count = counts["total_visit"]
            dashboard.total_patient_count = counts["total_patient"]
            dashboard.today_visit_count = counts["today_visit"]
            dashboard.today_done_count = counts["today_done"]
            dashboard.active_queue_count = counts["active_queue"]
            dashboard.today_revenue = counts["today_revenue"]

    def _compute_active_visit_ids(self):
        Visit = self.env["clinic.visit"]
        visits = Visit.search(
            [("state", "in", ("waiting", "in_consultation"))],
            order="queued_at asc, visit_date asc, id asc",
            limit=20,
        )
        waiting_visits = visits.filtered(lambda visit: visit.state == "waiting")
        next_visit = Visit.search(
            [("state", "=", "waiting")],
            order="queued_at asc, visit_date asc, id asc",
            limit=1,
        )
        current_visit = Visit.search(
            [("state", "=", "in_consultation")],
            order="consultation_started_at asc, id asc",
            limit=1,
        )
        completed_today = Visit.search(
            self._get_today_domain() + [("state", "=", "done")],
            order="completed_at desc, id desc",
            limit=10,
        )
        wait_minutes = waiting_visits.mapped("queue_wait_minutes")
        longest_wait_minutes = max(wait_minutes, default=0)
        longest_waiting_visit = waiting_visits.filtered(
            lambda visit: visit.queue_wait_minutes == longest_wait_minutes
        )[:1]
        for dashboard in self:
            dashboard.active_visit_ids = visits
            dashboard.next_visit_id = next_visit
            dashboard.current_visit_id = current_visit
            dashboard.today_completed_visit_ids = completed_today
            dashboard.average_wait_minutes = (
                int(sum(wait_minutes) / len(wait_minutes)) if wait_minutes else 0
            )
            dashboard.longest_wait_minutes = longest_wait_minutes
            dashboard.longest_waiting_visit_id = longest_waiting_visit

    def _get_today_domain(self):
        today = fields.Date.context_today(self)
        start = datetime.combine(today, time.min)
        end = datetime.combine(today, time.max)
        return [
            ("visit_date", ">=", fields.Datetime.to_string(start)),
            ("visit_date", "<=", fields.Datetime.to_string(end)),
        ]

    def _get_visit_action(self, name, domain):
        action = {
            "type": "ir.actions.act_window",
            "name": name,
            "res_model": "clinic.visit",
            "view_mode": "list,form",
            "domain": domain,
        }
        return action

    def action_open_draft(self):
        return self._get_visit_action("Draft Visits", [("state", "=", "draft")])

    def action_open_waiting(self):
        return self._get_visit_action("Waiting Visits", [("state", "=", "waiting")])

    def action_open_in_consultation(self):
        return self._get_visit_action(
            "Visits In Consultation",
            [("state", "=", "in_consultation")],
        )

    def action_open_done(self):
        return self._get_visit_action("Done Visits", [("state", "=", "done")])

    def action_open_cancelled(self):
        return self._get_visit_action(
            "Cancelled Visits",
            [("state", "=", "cancelled")],
        )

    def action_open_active_queue(self):
        return self._get_visit_action(
            "Active Queue",
            [("state", "in", ("waiting", "in_consultation"))],
        )

    def action_open_next_visit(self):
        self.ensure_one()
        if not self.next_visit_id:
            return self.action_open_active_queue()
        return {
            "type": "ir.actions.act_window",
            "name": self.next_visit_id.display_name,
            "res_model": "clinic.visit",
            "res_id": self.next_visit_id.id,
            "view_mode": "form",
        }

    def action_start_next_visit(self):
        self.ensure_one()
        if not self.next_visit_id:
            return self.action_open_active_queue()
        self.next_visit_id.action_start_consultation()
        return self.action_open_next_visit()

    def action_open_current_visit(self):
        self.ensure_one()
        if not self.current_visit_id:
            return self.action_open_active_queue()
        return {
            "type": "ir.actions.act_window",
            "name": self.current_visit_id.display_name,
            "res_model": "clinic.visit",
            "res_id": self.current_visit_id.id,
            "view_mode": "form",
        }

    def action_done_current_visit(self):
        self.ensure_one()
        if not self.current_visit_id:
            return self.action_open_active_queue()
        self.current_visit_id.action_done()
        return self.action_open_active_queue()

    def action_open_longest_waiting_visit(self):
        self.ensure_one()
        if not self.longest_waiting_visit_id:
            return self.action_open_active_queue()
        return {
            "type": "ir.actions.act_window",
            "name": self.longest_waiting_visit_id.display_name,
            "res_model": "clinic.visit",
            "res_id": self.longest_waiting_visit_id.id,
            "view_mode": "form",
        }

    def action_open_today_visits(self):
        return self._get_visit_action("Today's Visits", self._get_today_domain())

    def action_open_today_done(self):
        return self._get_visit_action(
            "Completed Today",
            self._get_today_domain() + [("state", "=", "done")],
        )

    def action_open_all_visits(self):
        return self._get_visit_action("All Visits", [])

    def action_open_patients(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Patients",
            "res_model": "clinic.patient",
            "view_mode": "kanban,list,form",
        }
