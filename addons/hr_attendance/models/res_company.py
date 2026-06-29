# Part of Odoo. See LICENSE file for full copyright and licensing details.

import uuid

from odoo import fields, models, api
from odoo.tools.urls import urljoin as url_join


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _default_company_token(self):
        return str(uuid.uuid4())

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
    attendance_kiosk_key = fields.Char(default=lambda s: uuid.uuid4().hex, copy=False, groups='hr_attendance.group_hr_attendance_user')
    attendance_kiosk_url = fields.Char(compute="_compute_attendance_kiosk_url")
    attendance_kiosk_use_pin = fields.Boolean(string='Employee PIN Identification')
    attendance_from_systray = fields.Boolean(string='Attendance From Systray', default=True)
    auto_check_out = fields.Boolean(string="Automatic Check Out", default=False)
    single_check_in = fields.Boolean(string="Single Check-In Attendance System")
    auto_check_out_mode = fields.Selection([('tolerance', 'Tolerance'), ('specific_time', 'Specific Time')], default='tolerance')
    auto_check_out_tolerance = fields.Float(default=2, export_string_translation=False)
    auto_check_out_specific_time = fields.Float(default=20.0, export_string_translation=False)
    absence_management = fields.Boolean(string="Absence Management", default=False)
    attendance_validation = fields.Selection([
        ('no_validation', 'Worked days are automatically approved'),
        ('manual_validation', 'Worked days require manual approval'),
    ], string="Attendance Validation", default='no_validation')
    attendance_work_entry_type_id = fields.Many2one(
        'hr.work.entry.type',
        string="Attendance Work Entry Type",
        domain=[('count_as', '=', 'working_time')],
        store=True,
        compute='_compute_attendance_work_entry_type_id',
        groups="hr.group_hr_user",
        help="Work entry type assigned to attendances and read by the time rule engine.",
    )

    attendance_device_tracking = fields.Boolean(string="Device & Location Tracking", default=False)
    attendance_capture_check_in = fields.Boolean(string="Take Pictures on Check-In", default=False)
    attendance_based = fields.Boolean(default=False, required=True, groups="hr.group_hr_user")

    _check_auto_check_out_specific_time_range = models.Constraint(
        "CHECK (NOT (auto_check_out = true AND auto_check_out_mode = 'specific_time') OR (auto_check_out_specific_time >= 0 AND auto_check_out_specific_time < 24))",
        'Specific Time must be within a 24-hour range (0h 0m 0s to 23h 59m 59s).',
    )

    @api.depends("attendance_kiosk_key")
    def _compute_attendance_kiosk_url(self):
        for company in self:
            company.attendance_kiosk_url = url_join(self.env['res.company'].get_base_url(), '/hr_attendance/%s' % company.attendance_kiosk_key)
 
    def _compute_attendance_work_entry_type_id(self):
        fallback = self.env.ref('hr_work_entry.generic_work_entry_type_attendance', raise_if_not_found=False)
        country_codes = self.mapped('country_id.code')
        country_types = self.env['hr.work.entry.type'].search([
            ('count_as', '=', 'working_time'),
            ('code', '=', 'WORK100'),
            ('country_code', 'in', country_codes),
        ])
        type_by_country = {t.country_code: t for t in country_types}
        for company in self:
            if company.attendance_work_entry_type_id:
                continue
            company.attendance_work_entry_type_id = type_by_country.get(company.country_id.code) or fallback

    # ---------------------------------------------------------
    # ORM Overrides
    # ---------------------------------------------------------
    def _init_column(self, column_name):
        """ Initialize the value of the given column for existing rows.
            Overridden here because we need to generate different access tokens
            and by default _init_column calls the default method once and applies
            it for every record.
        """
        if column_name != 'attendance_kiosk_key':
            super(ResCompany, self)._init_column(column_name)
        else:
            self.env.cr.execute("SELECT id FROM %s WHERE attendance_kiosk_key IS NULL" % self._table)
            attendance_ids = self.env.cr.dictfetchall()
            values_args = [(attendance_id['id'], self._default_company_token()) for attendance_id in attendance_ids]
            query = """
                UPDATE {table}
                SET attendance_kiosk_key = vals.token
                FROM (VALUES %s) AS vals(id, token)
                WHERE {table}.id = vals.id
            """.format(table=self._table)
            self.env.cr.execute_values(query, values_args)

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
