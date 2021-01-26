# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"

    hr_attendance_overtime = fields.Boolean(related='company_id.hr_attendance_overtime')
