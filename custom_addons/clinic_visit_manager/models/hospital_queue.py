from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


QUEUE_STATES = [
    ("waiting", "Waiting"),
    ("serving", "Serving"),
    ("done", "Done"),
    ("skipped", "Skipped"),
]

GROUP_RECEPTIONIST = "clinic_visit_manager.group_clinic_receptionist"
GROUP_DOCTOR = "clinic_visit_manager.group_clinic_doctor"
GROUP_MANAGER = "clinic_visit_manager.group_clinic_manager"


class HospitalQueue(models.Model):
    _name = "hospital.queue"
    _description = "Hospital Token Queue"
    _order = "queue_number asc, id asc"

    token = fields.Char(
        string="Token",
        readonly=True,
        copy=False,
        index=True,
    )
    patient_name = fields.Char(
        string="Patient Name",
        required=True,
    )
    doctor_id = fields.Many2one(
        "res.users",
        string="Doctor",
        required=True,
        default=lambda self: self.env.user,
        ondelete="restrict",
    )
    state = fields.Selection(
        QUEUE_STATES,
        string="Status",
        default="waiting",
        required=True,
        index=True,
    )
    queue_number = fields.Integer(
        string="Queue Number",
        readonly=True,
        copy=False,
        index=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        next_number = self._next_queue_number()
        for vals in vals_list:
            vals.setdefault("token", self.env["ir.sequence"].next_by_code("hospital.queue") or _("New"))
            if not vals.get("queue_number"):
                vals["queue_number"] = next_number
                next_number += 1
        records = super().create(vals_list)
        records._broadcast_queue_update("created")
        return records

    def write(self, vals):
        result = super().write(vals)
        if {"state", "doctor_id", "patient_name", "queue_number"} & set(vals):
            self._broadcast_queue_update("updated")
        return result

    @api.constrains("doctor_id", "state")
    def _check_one_serving_per_doctor(self):
        for record in self.filtered(lambda queue: queue.state == "serving"):
            duplicate = self.search(
                [
                    ("id", "!=", record.id),
                    ("doctor_id", "=", record.doctor_id.id),
                    ("state", "=", "serving"),
                ],
                limit=1,
            )
            if duplicate:
                raise ValidationError(
                    _("Only one patient can be serving for doctor %(doctor)s.")
                    % {"doctor": record.doctor_id.display_name}
                )

    @api.model
    def get_queue_data(self, doctor_id=False):
        doctor = self._resolve_doctor(doctor_id)
        domain = [("doctor_id", "=", doctor.id)]
        current = self.search(domain + [("state", "=", "serving")], limit=1)
        waiting = self.search(domain + [("state", "=", "waiting")], limit=20)
        skipped = self.search(
            domain + [("state", "=", "skipped")],
            order="write_date desc, id desc",
            limit=10,
        )
        doctors = self._queue_doctors()
        return {
            "doctor": self._serialize_doctor(doctor),
            "doctors": doctors,
            "current": self._serialize_queue(current),
            "waiting": [self._serialize_queue(queue) for queue in waiting],
            "skipped": [self._serialize_queue(queue) for queue in skipped],
            "can_add_queue": self._can_add_queue(),
            "updated_at": fields.Datetime.to_string(fields.Datetime.now()),
        }

    @api.model
    def get_patient_display_data(self):
        queue_current = self.search(
            [("state", "=", "serving")],
            order="write_date desc, queue_number asc, id asc",
            limit=8,
        )
        queue_waiting = self.search(
            [("state", "=", "waiting")],
            order="queue_number asc, id asc",
            limit=24,
        )
        visit_model = self.env["clinic.visit"]
        visit_current = visit_model.search(
            [("state", "=", "in_consultation")],
            order="write_date desc, queued_at asc, id asc",
            limit=8,
        )
        visit_waiting = visit_model.search(
            [("state", "=", "waiting")],
            order="queued_at asc, visit_date asc, id asc",
            limit=24,
        )
        current = sorted(
            [self._serialize_queue_display(queue) for queue in queue_current]
            + [self._serialize_visit_display(visit) for visit in visit_current],
            key=lambda item: item["called_at"] or "",
            reverse=True,
        )[:8]
        waiting = (
            [self._serialize_queue_display(queue) for queue in queue_waiting]
            + [self._serialize_visit_display(visit) for visit in visit_waiting]
        )[:24]
        return {
            "current": current,
            "waiting": waiting,
            "updated_at": fields.Datetime.to_string(fields.Datetime.now()),
        }

    @api.model
    def action_add_patient(self, patient_name, doctor_id=False):
        patient_name = (patient_name or "").strip()
        if not patient_name:
            raise UserError(_("Patient name is required."))
        doctor = self._resolve_doctor(doctor_id)
        self.create(
            {
                "patient_name": patient_name,
                "doctor_id": doctor.id,
                "state": "waiting",
            }
        )
        return self.get_queue_data(doctor.id)

    @api.model
    def action_call_next(self, doctor_id=False):
        doctor = self._resolve_doctor(doctor_id)
        current = self._current_for_doctor(doctor)
        if current:
            current.write({"state": "done"})
        next_queue = self._next_waiting_for_doctor(doctor)
        if next_queue:
            next_queue.write({"state": "serving"})
            next_queue._broadcast_queue_update("called")
        else:
            self._broadcast_queue_update("called")
        return self.get_queue_data(doctor.id)

    def action_complete(self):
        for record in self:
            if record.state not in ("waiting", "serving", "skipped"):
                raise UserError(_("Only active queue tokens can be completed."))
            was_serving = record.state == "serving"
            record.write({"state": "done"})
            if was_serving:
                next_queue = self._next_waiting_for_doctor(record.doctor_id)
                if next_queue:
                    next_queue.write({"state": "serving"})
        return self.get_queue_data(self[:1].doctor_id.id if self else False)

    def action_skip(self):
        doctors = self.mapped("doctor_id")
        for record in self:
            if record.state not in ("waiting", "serving"):
                raise UserError(_("Only waiting or serving patients can be skipped."))
            was_serving = record.state == "serving"
            record.write({"state": "skipped"})
            if was_serving:
                next_queue = self._next_waiting_for_doctor(record.doctor_id)
                if next_queue:
                    next_queue.write({"state": "serving"})
        return self.get_queue_data(doctors[:1].id if doctors else False)

    def action_recall(self):
        for record in self:
            if record.state == "serving":
                record._broadcast_queue_update("recalled")
                continue
            if record.state != "skipped":
                raise UserError(_("Only skipped or serving patients can be recalled."))
            current = self._current_for_doctor(record.doctor_id)
            if current:
                current.write({"state": "waiting"})
            record.write({"state": "serving"})
            record._broadcast_queue_update("recalled")
        return self.get_queue_data(self[:1].doctor_id.id if self else False)

    @api.model
    def _next_queue_number(self):
        last_queue = self.search([], order="queue_number desc", limit=1)
        return (last_queue.queue_number or 0) + 1

    @api.model
    def _resolve_doctor(self, doctor_id=False):
        if doctor_id:
            doctor = self.env["res.users"].browse(doctor_id).exists()
            if doctor:
                return doctor
        return self.env.user

    @api.model
    def _queue_doctors(self):
        doctor_group = self.env.ref(
            "clinic_visit_manager.group_clinic_doctor",
            raise_if_not_found=False,
        )
        queue_doctors = self.search([]).mapped("doctor_id")
        group_doctors = doctor_group.user_ids if doctor_group else self.env["res.users"]
        doctors = (queue_doctors | self.env.user).sorted("name")
        doctors = (doctors | group_doctors).sorted("name")
        return [self._serialize_doctor(doctor) for doctor in doctors]

    def _can_add_queue(self):
        user = self.env.user
        return any(
            user.has_group(group_xmlid)
            for group_xmlid in (GROUP_RECEPTIONIST, GROUP_DOCTOR, GROUP_MANAGER)
        )

    @staticmethod
    def _serialize_doctor(doctor):
        return {"id": doctor.id, "name": doctor.display_name}

    def _serialize_queue(self, queue):
        if not queue:
            return False
        return {
            "id": queue.id,
            "token": queue.token,
            "patient_name": queue.patient_name,
            "doctor_id": queue.doctor_id.id,
            "doctor_name": queue.doctor_id.display_name,
            "state": queue.state,
            "queue_number": queue.queue_number,
        }

    def _serialize_queue_display(self, queue):
        data = self._serialize_queue(queue)
        data.update(
            {
                "id": f"queue-{queue.id}",
                "source": "queue",
                "called_at": fields.Datetime.to_string(queue.write_date)
                if queue.write_date
                else False,
            }
        )
        return data

    @staticmethod
    def _serialize_visit_display(visit):
        return {
            "id": f"visit-{visit.id}",
            "source": "visit",
            "token": visit.token_number or visit.name,
            "patient_name": visit.patient_name,
            "doctor_id": False,
            "doctor_name": visit.doctor_name or "",
            "state": visit.state,
            "queue_number": visit.token_number or "-",
            "called_at": fields.Datetime.to_string(
                visit.consultation_started_at or visit.write_date
            )
            if visit.consultation_started_at or visit.write_date
            else False,
        }

    def _current_for_doctor(self, doctor):
        return self.search(
            [("doctor_id", "=", doctor.id), ("state", "=", "serving")],
            limit=1,
        )

    def _next_waiting_for_doctor(self, doctor):
        return self.search(
            [("doctor_id", "=", doctor.id), ("state", "=", "waiting")],
            limit=1,
        )

    def _broadcast_queue_update(self, action):
        doctor_ids = self.mapped("doctor_id").ids if self else []
        self.env["bus.bus"]._sendone(
            "hospital_queue",
            "hospital_queue_update",
            {
                "action": action,
                "doctor_ids": doctor_ids,
                "updated_at": fields.Datetime.to_string(fields.Datetime.now()),
            },
        )
