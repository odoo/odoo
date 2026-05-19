# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    attendance_based = fields.Boolean(default=False, required=True, groups="hr.group_hr_user")

    attendance_work_entry_type_id = fields.Many2one(
        'hr.work.entry.type',
        string="Attendance Work Entry Type",
        domain=[('requires_allocation', '=', False)],
        default=lambda self: self._get_default_attendance_work_entry_type(),
        help="Work entry type assigned to leaves generated from attendance records "
             "and read by the time rule engine.",
    )

    @api.model
    def _init_attendance_work_entry_type(self):
        for company in self.search([('attendance_work_entry_type_id', '=', False)]):
            company.attendance_work_entry_type_id = company._get_default_attendance_work_entry_type()
