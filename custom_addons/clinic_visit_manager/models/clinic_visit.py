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
            vals = {"state": "waiting"}
            if not record.token_number:
                vals["token_number"] = self.env["ir.sequence"].next_by_code(
                    "clinic.visit.token"
                )
            record.write(vals)

    def action_start_consultation(self):
        for record in self:
            if record.state != "waiting":
                raise UserError("Only waiting visits can start consultation.")
            record.state = "in_consultation"

    def action_done(self):
        for record in self:
            if record.state not in ("waiting", "in_consultation"):
                raise UserError("Only active visits can be marked as done.")
            record.state = "done"

    def action_cancel(self):
        for record in self:
            if record.state == "done":
                raise UserError("Done visits cannot be cancelled.")
            record.state = "cancelled"
