# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    attendance_kiosk_mode = fields.Selection(related='company_id.attendance_kiosk_mode', readonly=False)
    attendance_barcode_source = fields.Selection(related='company_id.attendance_barcode_source', readonly=False)
    attendance_kiosk_delay = fields.Integer(related='company_id.attendance_kiosk_delay', readonly=False)
    attendance_kiosk_url = fields.Char(related='company_id.attendance_kiosk_url')
    attendance_kiosk_use_pin = fields.Boolean(related='company_id.attendance_kiosk_use_pin', readonly=False)
    attendance_from_systray = fields.Boolean(related="company_id.attendance_from_systray", readonly=False)
    auto_check_out = fields.Boolean(related="company_id.auto_check_out", readonly=False)
    single_check_in = fields.Boolean(related="company_id.single_check_in", readonly=False)
    auto_check_out_mode = fields.Selection(related="company_id.auto_check_out_mode", readonly=False)
    auto_check_out_tolerance = fields.Float(related="company_id.auto_check_out_tolerance", readonly=False)
    auto_check_out_specific_time = fields.Float(related="company_id.auto_check_out_specific_time", readonly=False)
    absence_management = fields.Boolean(related="company_id.absence_management", readonly=False)
    attendance_validation = fields.Selection(related="company_id.attendance_validation", readonly=False)
    attendance_work_entry_type_id = fields.Many2one(
        related='company_id.attendance_work_entry_type_id',
        readonly=False,
    )
    attendance_device_tracking = fields.Boolean(related="company_id.attendance_device_tracking", readonly=False)
    attendance_capture_check_in = fields.Boolean(related="company_id.attendance_capture_check_in", readonly=False)
    attendance_based = fields.Boolean(string="Default Tracking", related='company_id.attendance_based', groups="hr.group_hr_user", readonly=False)

    def set_values(self):
        super().set_values()
        company = self.env.company
        if not company.auto_check_out and company.single_check_in:
            company.single_check_in = False

    def regenerate_kiosk_key(self):
        if self.env.user.has_group("hr_attendance.group_hr_attendance_user"):
            self.company_id._regenerate_attendance_kiosk_key()
