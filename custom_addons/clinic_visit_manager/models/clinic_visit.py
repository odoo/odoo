# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
from odoo import api, fields, models
from odoo.exceptions import UserError

VISIT_STATES = [
    ("draft", "Draft"),
    ("confirmed", "Confirmed"),
    ("done", "Done"),
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

    doctor_name = fields.Char(
        string="Doctor Name",
    )

    visit_date = fields.Datetime(
        string="Visit Date",
        default=fields.Datetime.now,
    )

    symptoms = fields.Text(
        string="Symptoms",
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
            record.state = "confirmed"

    def action_done(self):
        for record in self:
            if record.state != "confirmed":
                raise UserError("Only confirmed visits can be marked as done.")
            record.state = "done"
