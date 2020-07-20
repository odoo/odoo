# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HRLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    deduct_from_extra_hours = fields.Boolean("Deduct From Extra Hours", default=False,
        help="""Once a time off of this type is approved, extra hours in attendances will be deducted.
                The deduction mechanism has to be activated in Attendance Settings.
             """
    )
