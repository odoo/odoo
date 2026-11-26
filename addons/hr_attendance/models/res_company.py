# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import uuid

from odoo import fields, models, api
from odoo.tools import SQL
from odoo.tools.urls import urljoin as url_join

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'

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
    auto_check_out = fields.Boolean(string="Automatic Check Out", default=False)
    single_check_in = fields.Boolean(string="Single Check-In Attendance System")
    auto_check_out_mode = fields.Selection([('tolerance', 'Tolerance'), ('specific_time', 'Specific Time')], default='tolerance')
    auto_check_out_tolerance = fields.Float(default=2, export_string_translation=False)
    auto_check_out_specific_time = fields.Float(default=20.0, export_string_translation=False)
    attendance_validation = fields.Selection([
        ('manual_validation', 'Review everything'),
        ('exception_validation', 'Review exceptions only'),
    ], string="Attendance Validation", default='exception_validation', required=True)
    attendance_validation_tolerance = fields.Integer(
        string="Validation Tolerance (Minutes)",
        default=15,
    )

    attendance_tolerance = fields.Boolean(
        string="Check-In/Out Tolerance",
        help="A check-in or a check-out close enough to the planned time (the planning shift if any, else the working "
             "schedule) is recorded at the planned time.",
    )
    attendance_tolerance_early_check_in = fields.Integer(string="Early Arrivals (Minutes)", default=15)
    attendance_tolerance_late_check_in = fields.Integer(string="Late Arrivals (Minutes)", default=0)
    attendance_tolerance_early_check_out = fields.Integer(string="Early Departures (Minutes)", default=15)
    attendance_tolerance_late_check_out = fields.Integer(string="Late Departures (Minutes)", default=0)
    attendance_device_tracking = fields.Boolean(string="Precise Location Tracking", default=False)
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

    def _regenerate_attendance_kiosk_key(self):
        """Replace the kiosk key, which invalidates the current kiosk URL."""
        self.ensure_one()
        self.write({
            'attendance_kiosk_key': uuid.uuid4().hex
        })

    def _check_hr_presence_control(self, at_install):
        """Switch the presence control of the companies on install and uninstall.

        At install, the companies controlling presence by login also control it by attendance;
        at uninstall, the companies controlling it by attendance fall back to the login.

        :param bool at_install: ``True`` at install, ``False`` at uninstall
        """
        companies = self.env.companies
        for company in companies:
            if at_install and company.hr_presence_control_login:
                company.hr_presence_control_attendance = True
            if not at_install and company.hr_presence_control_attendance:
                company.hr_presence_control_login = True
                company.hr_presence_control_attendance = False

    def _action_open_kiosk_mode(self):
        """Return an action opening the kiosk of the current company, through the route that
        logs the user out first."""
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': f'/hr_attendance/kiosk_mode_menu/{self.env.company.id}',
        }
