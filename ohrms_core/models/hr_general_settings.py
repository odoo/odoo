# -*- coding: utf-8 -*-
from odoo import api, fields, models


class OHRMSConfiguration(models.TransientModel):
    _inherit = 'res.config.settings'

    module_hr_custody = fields.Boolean(
        string='Manage the company properties when it is in the custody of an employee',
        help='Helps you to manage Custody Requests.\n'
             '- This installs the module Custody Management.')
    module_oh_employee_check_list = fields.Boolean(
        string="Manages employee's entry & exit Process",
        help='Helps you to manage Employee Checklist.\n'
             '- This installs the module Employee Checklist.')
    module_hr_employee_shift = fields.Boolean(
        string='Manage different type of shifts',
        help='Helps you to manage Employee Shift.\n'
             '- This installs the module Employee Shift.')
    module_hr_insurance = fields.Boolean(
        string='Manage Insurance for employees',
        help='Helps you to manage Employee Insurance.\n'
             '- This installs the module Employee Insurance.')
    module_oh_hr_lawsuit_management = fields.Boolean(
        string='Manage legal actions',
        help='Helps you to manage Lawsuit Management.\n'
             '- This installs the module Lawsuit Management.')
    module_hr_resignation = fields.Boolean(
        string='Handle the resignation process of the employee',
        help='Helps you to manage Resignation Process.\n'
             '- This installs the module Resignation Process.')
    module_hr_vacation_mngmt = fields.Boolean(
        string='Manage employee vacation',
        help='Helps you to manage Vacation Management.\n'
             '- This installs the module Vacation Management.')
    module_oh_hr_zk_attendance = fields.Boolean(
        string='Manage biometric device (Model: ZKteco uFace 202) integration with HR attendance (Face + Thumb)',
        help='Helps you to manage Biometric Device Integration.\n'
             '- This installs the module Biometric Device Integration.')
    test_module_hr_custody = fields.Boolean(default=False, invisible=True)
    test_oh_employee_check_list = fields.Boolean(default=False, invisible=True)
    test_module_hr_employee_shift = fields.Boolean(default=False, invisible=True)
    test_module_hr_insurance = fields.Boolean(default=False, invisible=True)
    test_module_oh_hr_lawsuit_management = fields.Boolean(default=False, invisible=True)
    test_module_hr_resignation = fields.Boolean(default=False, invisible=True)
    test_module_hr_vacation_mngmt = fields.Boolean(default=False, invisible=True)
    test_module_oh_hr_zk_attendance = fields.Boolean(default=False, invisible=True)

    @api.onchange('module_hr_custody')
    def onchange_module_hr_custody(self):
        for each in self:
            if each.module_hr_custody:
                if not self.env['ir.module.module'].search([('name', '=', 'hr_custody')]):
                    each.test_module_hr_custody = True
                    each.module_hr_custody = False
                else:
                    each.test_module_hr_custody = False

    @api.onchange('module_oh_employee_check_list')
    def onchange_module_oh_employee_check_list(self):
        for each in self:
            if each.module_oh_employee_check_list:
                if not self.env['ir.module.module'].search([('name', '=', 'oh_employee_check_list')]):
                    each.test_oh_employee_check_list = True
                    each.module_oh_employee_check_list = False
                else:
                    each.test_oh_employee_check_list = False

    @api.onchange('module_hr_employee_shift')
    def onchange_module_hr_employee_shift(self):
        for each in self:
            if each.module_hr_employee_shift:
                if not self.env['ir.module.module'].search([('name', '=', 'hr_employee_shift')]):
                    each.test_module_hr_employee_shift = True
                    each.module_hr_employee_shift = False
                else:
                    each.test_module_hr_employee_shift = False

    @api.onchange('module_hr_insurance')
    def onchange_module_hr_insurance(self):
        for each in self:
            if each.module_hr_insurance:
                if not self.env['ir.module.module'].search([('name', '=', 'hr_insurance')]):
                    each.test_module_hr_insurance = True
                    each.module_hr_insurance = False
                else:
                    each.test_module_hr_insurance = False

    @api.onchange('module_oh_hr_lawsuit_management')
    def onchange_module_oh_hr_lawsuit_management(self):
        for each in self:
            if each.module_oh_hr_lawsuit_management:
                if not self.env['ir.module.module'].search([('name', '=', 'oh_hr_lawsuit_management')]):
                    each.test_module_oh_hr_lawsuit_management = True
                    each.module_oh_hr_lawsuit_management = False
                else:
                    each.test_module_oh_hr_lawsuit_management = False

    @api.onchange('module_hr_resignation')
    def onchange_module_hr_resignation(self):
        for each in self:
            if each.module_hr_resignation:
                if not self.env['ir.module.module'].search([('name', '=', 'hr_resignation')]):
                    each.test_module_hr_resignation = True
                    each.module_hr_resignation = False
                else:
                    each.test_module_hr_resignation = False

    @api.onchange('module_hr_vacation_mngmt')
    def onchange_module_hr_vacation_mngmt(self):
        for each in self:
            if each.module_hr_vacation_mngmt:
                if not self.env['ir.module.module'].search([('name', '=', 'hr_vacation_mngmt')]):
                    each.test_module_hr_vacation_mngmt = True
                    each.module_hr_vacation_mngmt = False
                else:
                    each.test_module_hr_vacation_mngmt = False

    @api.onchange('module_oh_hr_zk_attendance')
    def onchange_module_oh_hr_zk_attendance(self):
        for each in self:
            if each.module_oh_hr_zk_attendance:
                if not self.env['ir.module.module'].search([('name', '=', 'oh_hr_zk_attendance')]):
                    each.test_module_oh_hr_zk_attendance = True
                    each.module_oh_hr_zk_attendance = False
                else:
                    each.test_module_oh_hr_zk_attendance = False


