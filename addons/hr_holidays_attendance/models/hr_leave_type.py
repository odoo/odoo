# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HRLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    hr_attendance_overtime = fields.Boolean(related='company_id.hr_attendance_overtime')
    overtime_deductible = fields.Boolean("Deduct Extra Hours", default=False,
                                         help="""Once a time off of this type is approved, extra hours in attendances
                                         will be deducted.""")
