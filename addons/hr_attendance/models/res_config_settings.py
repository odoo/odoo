# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    hr_attendance_overtime = fields.Boolean(
        string="Count Extra Hours", readonly=False)
    overtime_start_date = fields.Date(string="Extra Hours Starting Date", readonly=False)
    overtime_company_threshold = fields.Integer(
        string="Tolerance Time In Favor Of Company", readonly=False)
    overtime_employee_threshold = fields.Integer(
        string="Tolerance Time In Favor Of Employee", readonly=False)
    hr_attendance_display_overtime = fields.Boolean(related='company_id.hr_attendance_display_overtime', readonly=False)
    attendance_kiosk_mode = fields.Selection(related='company_id.attendance_kiosk_mode', readonly=False)
    attendance_barcode_source = fields.Selection(related='company_id.attendance_barcode_source', readonly=False)
    attendance_kiosk_delay = fields.Integer(related='company_id.attendance_kiosk_delay', readonly=False)
    attendance_kiosk_url = fields.Char(related='company_id.attendance_kiosk_url')
    attendance_kiosk_use_pin = fields.Boolean(related='company_id.attendance_kiosk_use_pin', readonly=False)
    attendance_from_systray = fields.Boolean(related="company_id.attendance_from_systray", readonly=False)

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        company = self.env.company
        res.update({
            'hr_attendance_overtime': company.hr_attendance_overtime,
            'overtime_start_date': company.overtime_start_date,
            'overtime_company_threshold': company.overtime_company_threshold,
            'overtime_employee_threshold': company.overtime_employee_threshold,
        })
        return res

    def set_values(self):
        super().set_values()
        company = self.env.company
        # Done this way to have all the values written at the same time,
        # to avoid recomputing the overtimes several times with
        # invalid company configurations
        fields_to_check = [
            'hr_attendance_overtime',
            'overtime_start_date',
            'overtime_company_threshold',
            'overtime_employee_threshold',
        ]
        if any(self[field] != company[field] for field in fields_to_check):
            company.write({field: self[field] for field in fields_to_check})

    def regenerate_kiosk_key(self):
        if self.user_has_groups("hr_attendance.group_hr_attendance_manager"):
            self.company_id._regenerate_attendance_kiosk_key()
