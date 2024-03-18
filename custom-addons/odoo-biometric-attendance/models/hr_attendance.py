# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    biometric_device_id = fields.Char(string="Biometric Device ID")
    worked_hours = fields.Float(
        compute="_compute_worked_hours",
        store=True,
        readonly=True,
    )

    # Override the default check_in
    check_in = fields.Datetime(default=False, required=False)

    @api.constrains("check_in", "check_out")
    def _check_validity_check_in_check_out(self):
        """
        Override the validations to receive any kind of data.
        """
        pass

    @api.constrains("check_in", "check_out", "employee_id")
    def _check_validity(self):
        """
        Override the validations to receive any kind of data.
        """
        pass

    @api.depends("employee_id.name")
    def _compute_display_name(self):
        """
        In Odoo 17, name_get() is deprecated in favor of display_name.
        Therefore, we need to override the display_name computation
        method.
        """
        for attendance in self:
            display_name = _("Attendance for %(empl_name)s") % {
                "empl_name": attendance.employee_id.name
            }
            if attendance.check_out:
                display_name += " "
            attendance.display_name = display_name

    @api.depends("check_in", "check_out")
    def _compute_worked_hours(self):
        for attendance in self:
            if attendance.check_in and attendance.check_out:
                delta = attendance.check_out - attendance.check_in
                attendance.worked_hours = delta.total_seconds() / 3600.0
            else:
                attendance.worked_hours = 0.0
