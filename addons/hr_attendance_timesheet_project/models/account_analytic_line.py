# -*- coding: utf-8 -*-

from odoo import models, fields


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    attendance_id = fields.Many2one(
        'hr.attendance',
        string='Attendance',
        index=True,
        help="Link to the attendance record that generated this timesheet entry",
        ondelete='cascade',
    )
