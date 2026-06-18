# In hr_employee.py
from odoo import models, fields

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    biometric_user_id = fields.Integer(string='Biometric User ID', help='ID from ZKTeco device')