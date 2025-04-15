# hospital_patient.py

from odoo import models, fields, api
from odoo.exceptions import ValidationError

class HospitalPatient(models.Model):
    _name = 'hospital.patient'
    _description = 'Hospital Patient'

    # Fields
    name = fields.Char(string='Patient Name', required=True)
    age = fields.Integer(string='Age')
    gender = fields.Selection([('male', 'Male'), ('female', 'Female')], string='Gender')
    diagnosis = fields.Text(string='Diagnosis')

    # Constraints to ensure that age cannot be negative
    @api.constrains('age')
    def _check_age(self):
        for record in self:
            if record.age < 0:
                raise ValidationError("Age cannot be negative.")
