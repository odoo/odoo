from datetime import datetime, time

import pytz

from odoo import api, fields, models

VISIT_STATE_LABELS = {
    "draft": "Draft",
    "waiting": "Waiting",
    "in_consultation": "In Consultation",
    "done": "Done",
    "cancelled": "Cancelled",
}

GROUP_RECEPTIONIST = "clinic_visit_manager.group_clinic_receptionist"
GROUP_DOCTOR = "clinic_visit_manager.group_clinic_doctor"
GROUP_MANAGER = "clinic_visit_manager.group_clinic_manager"


class ClinicVisitDashboard(models.Model):
    _name = "clinic.visit.dashboard"
    _description = "Clinic Visit Dashboard"

    name = fields.Char(default="Clinic Dashboard")

    @api.model
    def get_owl_dashboard_data(self):
        Visit = self.env["clinic.visit"]
        Patient = self.env["clinic.patient"]
        today_domain = self._get_today_domain()
        active_domain = [("state", "in", ("waiting", "in_consultation"))]

        waiting_visits = Visit.search(
            [("state", "=", "waiting")],
            order="queued_at asc, visit_date asc, id asc",
        )
        current_visit = Visit.search(
            [("state", "=", "in_consultation")],
            order="consultation_started_at asc, id asc",
            limit=1,
        )
        next_visit = waiting_visits[:1]
        today_done_visits = Visit.search(today_domain + [("state", "=", "done")])

        return {
            "updated_at": fields.Datetime.to_string(fields.Datetime.now()),
            "metrics": {
                "today_visits": Visit.search_count(today_domain),
                "active_queue": Visit.search_count(active_domain),
                "completed_today": len(today_done_visits),
                "total_patients": Patient.search_count([]),
            },
            "state_counts": [
                {
                    "state": state,
                    "label": label,
                    "count": Visit.search_count([("state", "=", state)]),
                }
                for state, label in VISIT_STATE_LABELS.items()
            ],
            "focus": {
                "current": self._serialize_visit(current_visit),
                "next": self._serialize_visit(next_visit),
            },
            "permissions": self._get_permissions(),
        }

    def _get_permissions(self):
        user = self.env.user
        is_manager = user.has_group(GROUP_MANAGER)
        is_receptionist = user.has_group(GROUP_RECEPTIONIST)
        is_doctor = user.has_group(GROUP_DOCTOR)
        return {
            "can_create_visit": is_receptionist or is_manager,
            "can_create_patient": is_receptionist or is_manager,
            "can_queue": is_receptionist or is_manager,
            "can_start": is_doctor or is_manager,
            "can_complete": is_doctor or is_manager,
            "can_cancel": is_receptionist or is_manager,
        }

    def _get_today_domain(self):
        today = fields.Date.context_today(self)
        timezone = pytz.timezone(self.env.context.get("tz") or self.env.user.tz or "UTC")
        start = timezone.localize(datetime.combine(today, time.min))
        end = timezone.localize(datetime.combine(today, time.max))
        return [
            (self._visit_date_field(), ">=", self._to_utc_string(start)),
            (self._visit_date_field(), "<=", self._to_utc_string(end)),
        ]

    @staticmethod
    def _visit_date_field():
        return "visit_date"

    @staticmethod
    def _to_utc_string(value):
        return fields.Datetime.to_string(value.astimezone(pytz.UTC).replace(tzinfo=None))

    def _serialize_visit(self, visit):
        if not visit:
            return False
        return {
            "id": visit.id,
            "name": visit.name,
            "token_number": visit.token_number,
            "patient_name": visit.patient_name,
            "doctor_name": visit.doctor_name,
            "queue_wait_minutes": visit.queue_wait_minutes,
        }
