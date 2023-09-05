from odoo import api, fields, models


class DerriHospitalPatient(models.Model):
    _name = "hospital.patient"
    _description = "patient recors"
    name = fields.Char(string="Name", required=True)
    age = fields.Integer(string="Age")
    is_child = fields.Boolean(string="is child ?")
    notes = fields.Text(string="Notes")
    gender = fields.Selection(
        [("male", "Male"), ("female", "Female"), ("others", "Others")], string="Gender")
