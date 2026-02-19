# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    hr_attendance_display_overtime = fields.Boolean(related='company_id.hr_attendance_display_overtime', readonly=False)
    attendance_kiosk_mode = fields.Selection(related='company_id.attendance_kiosk_mode', readonly=False)
    attendance_barcode_source = fields.Selection(related='company_id.attendance_barcode_source', readonly=False)
    attendance_kiosk_delay = fields.Integer(related='company_id.attendance_kiosk_delay', readonly=False)
    attendance_kiosk_url = fields.Char(related='company_id.attendance_kiosk_url')
    attendance_kiosk_use_pin = fields.Boolean(related='company_id.attendance_kiosk_use_pin', readonly=False)
    attendance_from_systray = fields.Boolean(related="company_id.attendance_from_systray", readonly=False)
    attendance_overtime_validation = fields.Selection(related="company_id.attendance_overtime_validation", readonly=False)
    auto_check_out = fields.Boolean(related="company_id.auto_check_out", readonly=False)
    single_check_in = fields.Boolean(related="company_id.single_check_in", readonly=False)
    auto_check_out_tolerance = fields.Float(related="company_id.auto_check_out_tolerance", readonly=False)
    attendance_device_tracking = fields.Boolean(related="company_id.attendance_device_tracking", readonly=False)

    def set_values(self):
        super().set_values()
        company = self.env.company
        # synchronize auto_check_out and single_check_in feature.
        if not company.auto_check_out and company.single_check_in:
            company.single_check_in = False

    def regenerate_kiosk_key(self):
        if self.env.user.has_group("hr_attendance.group_hr_attendance_user"):
            self.company_id._regenerate_attendance_kiosk_key()
