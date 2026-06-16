# Part of Odoo. See LICENSE file for full copyright and licensing details.

import uuid

from odoo import fields, models, api
from odoo.tools.urls import urljoin as url_join


class ResCompany(models.Model):
    _inherit = 'res.company'

    # TODO: Remove in master
    overtime_company_threshold = fields.Integer(string="Tolerance Time In Favor Of Company", default=0)
    # TODO: Remove in master
    overtime_employee_threshold = fields.Integer(string="Tolerance Time In Favor Of Employee", default=0)
    hr_attendance_display_overtime = fields.Boolean(string="Display Extra Hours")
    attendance_kiosk_mode = fields.Selection([
        ('barcode', 'Barcode / RFID'),
        ('barcode_manual', 'Barcode / RFID and Manual Selection'),
        ('manual', 'Manual Selection'),
    ], string='Attendance Mode', default='barcode_manual')
    attendance_barcode_source = fields.Selection([
        ('scanner', 'Scanner'),
        ('front', 'Front Camera'),
        ('back', 'Back Camera'),
    ], string='Barcode Source', default='front')
    attendance_kiosk_delay = fields.Integer(default=10)
    attendance_kiosk_key = fields.Char(default=lambda s: uuid.uuid4().hex, copy=False, groups='hr_attendance.group_hr_attendance_user', init_storage='_init_column_attendance_kiosk_key')
    attendance_kiosk_url = fields.Char(compute="_compute_attendance_kiosk_url")
    attendance_kiosk_use_pin = fields.Boolean(string='Employee PIN Identification')
    attendance_from_systray = fields.Boolean(string='Attendance From Systray', default=True)
    attendance_overtime_validation = fields.Selection([
        ('no_validation', 'Automatically Approved'),
        ('by_manager', 'Approved by Manager'),
    ], string='Extra Hours Validation', default='no_validation')
    auto_check_out = fields.Boolean(string="Automatic Check Out", default=False)
    single_check_in = fields.Boolean(string="Single Check-In Attendance System")
    auto_check_out_mode = fields.Selection([('tolerance', 'Tolerance'), ('specific_time', 'Specific Time')], default='tolerance')
    auto_check_out_tolerance = fields.Float(default=2, export_string_translation=False)
    auto_check_out_specific_time = fields.Float(default=20.0, export_string_translation=False)
    absence_management = fields.Boolean(string="Absence Management", default=False)
    attendance_work_entry_type_id = fields.Many2one(
        'hr.work.entry.type',
        string="Attendance Work Entry Type",
        domain=[('requires_allocation', '=', False)],
        default=lambda self: self._get_default_attendance_work_entry_type(),
        help="Work entry type assigned to attendances and read by the time rule engine.",
    )

    attendance_device_tracking = fields.Boolean(string="Device & Location Tracking", default=False)
    attendance_capture_check_in = fields.Boolean(string="Take Pictures on Check-In", default=False)
    attendance_break_management = fields.Boolean(
        string="Break Management on Checkout",
        help="If enabled, employees can record their total break duration after checking out.",
    )

    _check_auto_check_out_specific_time_range = models.Constraint(
        "CHECK (NOT (auto_check_out = true AND auto_check_out_mode = 'specific_time') OR (auto_check_out_specific_time >= 0 AND auto_check_out_specific_time < 24))",
        'Specific Time must be within a 24-hour range (0h 0m 0s to 23h 59m 59s).',
    )

    @api.depends("attendance_kiosk_key")
    def _compute_attendance_kiosk_url(self):
        for company in self:
            company.attendance_kiosk_url = url_join(self.env['res.company'].get_base_url(), '/hr_attendance/%s' % company.attendance_kiosk_key)

    # ---------------------------------------------------------
    # ORM Overrides
    # ---------------------------------------------------------
    def _init_column_attendance_kiosk_key(self):
        """ Generate different access tokens. """
        self.env.execute_query(SQL("""
            UPDATE %s
            SET attendance_kiosk_key = gen_random_uuid()
            WHERE attendance_kiosk_key IS NULL
        """, SQL.identifier(self._table)))

    def write(self, vals):
        return super().write(vals)

    def _regenerate_attendance_kiosk_key(self):
        self.ensure_one()
        self.write({
            'attendance_kiosk_key': uuid.uuid4().hex
        })

    def _check_hr_presence_control(self, at_install):
        companies = self.env.companies
        for company in companies:
            if at_install and company.hr_presence_control_login:
                company.hr_presence_control_attendance = True
            if not at_install and company.hr_presence_control_attendance:
                company.hr_presence_control_login = True
                company.hr_presence_control_attendance = False

    def _action_open_kiosk_mode(self):
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': f'/hr_attendance/kiosk_mode_menu/{self.env.company.id}',
        }
