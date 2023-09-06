from odoo import api, fields, models


class DerriHospitalPatient(models.Model):
    _name = "hospital.patient"
    _description = "patient recors"
    _inherit = "mail.thread"
    name = fields.Char(string="Name", required=True, tracking=True)
    age = fields.Integer(string="Age", tracking=True)
    is_child = fields.Boolean(string="is child ?", tracking=True)
    notes = fields.Text(string="Notes", tracking=True)
    gender = fields.Selection(
        [("male", "Male"), ("female", "Female"), ("others", "Others")], string="Gender", tracking=True)
