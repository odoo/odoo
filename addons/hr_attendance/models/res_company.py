# Part of Odoo. See LICENSE file for full copyright and licensing details.

import uuid

from odoo import fields, models, api
from odoo.fields import Domain
from odoo.tools.urls import urljoin as url_join


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _default_company_token(self):
        return str(uuid.uuid4())

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
    attendance_kiosk_key = fields.Char(default=lambda s: uuid.uuid4().hex, copy=False, groups='hr_attendance.group_hr_attendance_user')
    attendance_kiosk_url = fields.Char(compute="_compute_attendance_kiosk_url")
    attendance_kiosk_use_pin = fields.Boolean(string='Employee PIN Identification')
    attendance_from_systray = fields.Boolean(string='Attendance From Systray', default=False)
    attendance_overtime_validation = fields.Selection([
        ('no_validation', 'Automatically Approved'),
        ('by_manager', 'Approved by Manager'),
    ], string='Extra Hours Validation', default='no_validation')
    auto_check_out = fields.Boolean(string="Automatic Check Out", default=False)
    auto_check_out_tolerance = fields.Float(default=2, export_string_translation=False)
    absence_management = fields.Boolean(string="Absence Management", default=False)
    attendance_device_tracking = fields.Boolean(string="Device & Location Tracking", default=False)

    @api.depends("attendance_kiosk_key")
    def _compute_attendance_kiosk_url(self):
        for company in self:
            company.attendance_kiosk_url = url_join(self.env['res.company'].get_base_url(), '/hr_attendance/%s' % company.attendance_kiosk_key)

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
        search_domain = Domain.FALSE  # Overtime to generate
        # Also recompute if the threshold have changed
        if 'overtime_company_threshold' in vals or 'overtime_employee_threshold' in vals:
            # If we modify the thresholds only
            search_domain = Domain.OR(
                Domain('employee_id.company_id', '=', company.id)
                for company in self
                if (vals.get('overtime_company_threshold') != company.overtime_company_threshold)
                or (vals.get('overtime_employee_threshold') != company.overtime_employee_threshold)
            )

        res = super().write(vals)
        if not search_domain.is_false():
            self.env['hr.attendance'].search(search_domain)._update_overtime()

        return res

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

    def _action_open_kiosk_mode(self):
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': f'/hr_attendance/kiosk_mode_menu/{self.env.company.id}',
        }
