# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
from odoo import api, fields, models


class ClinicPatient(models.Model):
    _name = "clinic.patient"
    _description = "Clinic Patient"
    _order = "name"

    name = fields.Char(
        string="Patient Name",
        required=True,
    )
    phone = fields.Char(
        string="Phone",
    )
    email = fields.Char(
        string="Email",
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Odoo Customer",
        ondelete="restrict",
    )
    doctor_id = fields.Many2one(
        "res.users",
        string="Registered Doctor",
        ondelete="set null",
    )
    age = fields.Integer(
        string="Age",
    )
    gender = fields.Selection(
        [
            ("male", "Male"),
            ("female", "Female"),
            ("other", "Other"),
        ],
        string="Gender",
    )
    blood_group = fields.Selection(
        [
            ("a_positive", "A+"),
            ("a_negative", "A-"),
            ("b_positive", "B+"),
            ("b_negative", "B-"),
            ("ab_positive", "AB+"),
            ("ab_negative", "AB-"),
            ("o_positive", "O+"),
            ("o_negative", "O-"),
        ],
        string="Blood Group",
    )
    notes = fields.Text(
        string="Notes",
    )
    visit_ids = fields.One2many(
        "clinic.visit",
        "patient_id",
        string="Visits",
    )
    visit_count = fields.Integer(
        string="Visit Count",
        compute="_compute_visit_count",
    )

    @api.depends("visit_ids")
    def _compute_visit_count(self):
        for patient in self:
            patient.visit_count = len(patient.visit_ids)
