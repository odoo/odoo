# -*- coding: utf-8 -*-
from odoo import models, fields

class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    # Add biometric_user_id field to public employee model
    biometric_user_id = fields.Integer(
        string='Biometric User ID',
        help='ID from ZKTeco device',
        related='employee_id.biometric_user_id',
        readonly=True
    )
