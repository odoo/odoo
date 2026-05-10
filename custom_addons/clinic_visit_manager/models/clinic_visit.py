# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
from odoo import api, fields, models
from odoo.exceptions import UserError

VISIT_STATES = [
    ("draft", "Draft"),
    ("waiting", "Waiting"),
    ("in_consultation", "In Consultation"),
    ("done", "Done"),
    ("cancelled", "Cancelled"),
]


class ClinicVisit(models.Model):
    _name = "clinic.visit"
    _description = "Clinic Visit"
    _order = "visit_date desc, id desc"

    name = fields.Char(
        string="Visit Reference",
        required=True,
        default="New Visit",
    )

    patient_name = fields.Char(
        string="Patient Name",
        required=True,
    )

    patient_id = fields.Many2one(
        "clinic.patient",
        string="Patient Card",
        ondelete="restrict",
    )

    token_number = fields.Char(
        string="Token",
        readonly=True,
        copy=False,
        index=True,
    )

    doctor_name = fields.Char(
        string="Doctor Name",
    )

    visit_date = fields.Datetime(
        string="Visit Date",
        default=fields.Datetime.now,
    )

    queued_at = fields.Datetime(
        string="Queued At",
        readonly=True,
        copy=False,
    )

    consultation_started_at = fields.Datetime(
        string="Consultation Started At",
        readonly=True,
        copy=False,
    )

    completed_at = fields.Datetime(
        string="Completed At",
        readonly=True,
        copy=False,
    )

    symptoms = fields.Text(
        string="Symptoms",
    )

    temperature_celsius = fields.Float(
        string="Temperature (C)",
        digits=(4, 1),
    )

    blood_pressure_systolic = fields.Integer(
        string="Systolic BP",
    )

    blood_pressure_diastolic = fields.Integer(
        string="Diastolic BP",
    )

    pulse_rate = fields.Integer(
        string="Pulse Rate",
    )

    respiratory_rate = fields.Integer(
        string="Respiratory Rate",
    )

    oxygen_saturation = fields.Float(
        string="Oxygen Saturation (%)",
        digits=(5, 2),
    )

    weight_kg = fields.Float(
        string="Weight (kg)",
        digits=(6, 2),
    )

    height_cm = fields.Float(
        string="Height (cm)",
        digits=(6, 2),
    )

    bmi = fields.Float(
        string="BMI",
        compute="_compute_bmi",
        digits=(5, 2),
        store=True,
    )

    fee = fields.Float(
        string="Consultation Fee",
    )

    state = fields.Selection(
        VISIT_STATES,
        string="Status",
        default="draft",
        required=True,
    )

    notes = fields.Text(
        string="Doctor Notes",
    )

    queue_wait_minutes = fields.Integer(
        string="Wait Minutes",
        compute="_compute_timing_minutes",
    )

    consultation_minutes = fields.Integer(
        string="Consultation Minutes",
        compute="_compute_timing_minutes",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._sync_patient_values(vals)
        return super().create(vals_list)

    def write(self, vals):
        vals = dict(vals)
        if "patient_name" in vals or "patient_id" in vals:
            self._sync_patient_values(vals)
        return super().write(vals)

    @api.depends("weight_kg", "height_cm")
    def _compute_bmi(self):
        for record in self:
            height_m = record.height_cm / 100
            record.bmi = (
                record.weight_kg / (height_m * height_m)
                if record.weight_kg and height_m
                else 0.0
            )

    @api.depends("queued_at", "consultation_started_at", "completed_at")
    def _compute_timing_minutes(self):
        now = fields.Datetime.now()
        for record in self:
            queue_end = record.consultation_started_at or record.completed_at or now
            consultation_end = record.completed_at or now
            record.queue_wait_minutes = self._minutes_between(
                record.queued_at,
                queue_end,
            )
            record.consultation_minutes = self._minutes_between(
                record.consultation_started_at,
                consultation_end,
            )

    @staticmethod
    def _minutes_between(start, end):
        if not start or not end or end < start:
            return 0
        return int((end - start).total_seconds() // 60)

    def _sync_patient_values(self, vals):
        patient_id = vals.get("patient_id")
        patient_name = (vals.get("patient_name") or "").strip()

        if patient_id and not patient_name:
            patient = self.env["clinic.patient"].browse(patient_id)
            vals["patient_name"] = getattr(patient, "name", "")
            return

        if patient_name and not patient_id:
            vals["patient_id"] = self._get_or_create_patient(patient_name).id

    def _get_or_create_patient(self, patient_name):
        patient_name = patient_name.strip()
        patient = self.env["clinic.patient"].search(
            [("name", "=ilike", patient_name)],
            limit=1,
        )
        if patient:
            return patient
        return self.env["clinic.patient"].create({"name": patient_name})

    def action_confirm(self):
        for record in self:
            if not record.patient_name:
                raise UserError("Patient name is required.")
            vals = {"state": "waiting"}
            if not record.queued_at:
                vals["queued_at"] = fields.Datetime.now()
            if not record.token_number:
                vals["token_number"] = self.env["ir.sequence"].next_by_code(
                    "clinic.visit.token"
                )
            record.write(vals)

    def action_start_consultation(self):
        for record in self:
            if record.state != "waiting":
                raise UserError("Only waiting visits can start consultation.")
            vals = {"state": "in_consultation"}
            if not record.consultation_started_at:
                vals["consultation_started_at"] = fields.Datetime.now()
            record.write(vals)

    def action_done(self):
        for record in self:
            if record.state not in ("waiting", "in_consultation"):
                raise UserError("Only active visits can be marked as done.")
            vals = {"state": "done"}
            if not record.completed_at:
                vals["completed_at"] = fields.Datetime.now()
            if record.state == "waiting" and not record.consultation_started_at:
                vals["consultation_started_at"] = vals["completed_at"]
            record.write(vals)

    def action_cancel(self):
        for record in self:
            if record.state == "done":
                raise UserError("Done visits cannot be cancelled.")
            record.state = "cancelled"
