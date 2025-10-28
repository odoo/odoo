# -*- coding: utf-8 -*-
#############################################################################
#    A part of Open HRMS Project <https://www.openhrms.com>
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import api, fields, models


class OHRMSConfiguration(models.TransientModel):
    """Inheriting res_config settings form some fields for employee
        data management"""
    _inherit = 'res.config.settings'

    module_hr_custody = fields.Boolean(
        string='Manage the company properties when it is in the custody '
               'of an employee',
        help='Helps you to manage Custody Requests.\n'
             '- This installs the module Custody Management.')
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
        string='Manage biometric device (Model: ZKteco uFace 202) integration '
               'with HR attendance (Face + Thumb)',
        help='Helps you to manage Biometric Device Integration.\n'
             '- This installs the module Biometric Device Integration.')
    test_module_hr_custody = fields.Boolean(string="HR Custody Module",
                                            help="HR Custody module installed or not",
                                            default=False, invisible=True)
    test_module_hr_employee_shift = fields.Boolean(string="HR Employee Shift",
                                                   help="HR Employee Shift module installed or not",
                                                   default=False,
                                                   invisible=True)
    test_module_hr_insurance = fields.Boolean(string="HR Insurance",
                                              help="HR Insurance module installed or not",
                                              default=False, invisible=True)
    test_module_oh_hr_lawsuit_management = fields.Boolean(
        string="HR Lawsuit Management",
        help="HR Lawsuit Management module installed or not", default=False,
        invisible=True)
    test_module_hr_resignation = fields.Boolean(string="HR Resignation",
                                                help="HR Resignation module installed or not",
                                                default=False, invisible=True)
    test_module_hr_vacation_mngmt = fields.Boolean(string="Vacation Management",
                                                   help="Vacation Management module installed or not",
                                                   default=False,
                                                   invisible=True)
    test_module_oh_hr_zk_attendance = fields.Boolean(string="Attendance",
                                                     help="Attendance module installed or not",
                                                     default=False,
                                                     invisible=True)

    @api.onchange('module_hr_custody')
    def onchange_module_hr_custody(self):
        """Return hr_custody module exist or not"""
        for each in self:
            if each.module_hr_custody:
                if not self.env['ir.module.module'].search(
                        [('name', '=', 'hr_custody')]):
                    each.test_module_hr_custody = True
                    each.module_hr_custody = False
                else:
                    each.test_module_hr_custody = False

    @api.onchange('module_hr_employee_shift')
    def onchange_module_hr_employee_shift(self):
        """Return hr_employee_shift module exist or not"""
        for each in self:
            if each.module_hr_employee_shift:
                if not self.env['ir.module.module'].search(
                        [('name', '=', 'hr_employee_shift')]):
                    each.test_module_hr_employee_shift = True
                    each.module_hr_employee_shift = False
                else:
                    each.test_module_hr_employee_shift = False

    @api.onchange('module_hr_insurance')
    def onchange_module_hr_insurance(self):
        """Return hr_insurance module exist or not"""
        for each in self:
            if each.module_hr_insurance:
                if not self.env['ir.module.module'].search(
                        [('name', '=', 'hr_insurance')]):
                    each.test_module_hr_insurance = True
                    each.module_hr_insurance = False
                else:
                    each.test_module_hr_insurance = False

    @api.onchange('module_oh_hr_lawsuit_management')
    def onchange_module_oh_hr_lawsuit_management(self):
        """Return oh_hr_lawsuit_management module exist or not"""
        for each in self:
            if each.module_oh_hr_lawsuit_management:
                if not self.env['ir.module.module'].search(
                        [('name', '=', 'oh_hr_lawsuit_management')]):
                    each.test_module_oh_hr_lawsuit_management = True
                    each.module_oh_hr_lawsuit_management = False
                else:
                    each.test_module_oh_hr_lawsuit_management = False

    @api.onchange('module_hr_resignation')
    def onchange_module_hr_resignation(self):
        """Return hr_resignation module exist or not"""
        for each in self:
            if each.module_hr_resignation:
                if not self.env['ir.module.module'].search(
                        [('name', '=', 'hr_resignation')]):
                    each.test_module_hr_resignation = True
                    each.module_hr_resignation = False
                else:
                    each.test_module_hr_resignation = False

    @api.onchange('module_hr_vacation_mngmt')
    def onchange_module_hr_vacation_mngmt(self):
        """Return hr_vacation_mngmt module exist or not"""
        for each in self:
            if each.module_hr_vacation_mngmt:
                if not self.env['ir.module.module'].search(
                        [('name', '=', 'hr_vacation_mngmt')]):
                    each.test_module_hr_vacation_mngmt = True
                    each.module_hr_vacation_mngmt = False
                else:
                    each.test_module_hr_vacation_mngmt = False

    @api.onchange('module_oh_hr_zk_attendance')
    def onchange_module_oh_hr_zk_attendance(self):
        """Return oh_hr_zk_attendance module exist or not"""
        for each in self:
            if each.module_oh_hr_zk_attendance:
                if not self.env['ir.module.module'].search(
                        [('name', '=', 'oh_hr_zk_attendance')]):
                    each.test_module_oh_hr_zk_attendance = True
                    each.module_oh_hr_zk_attendance = False
                else:
                    each.test_module_oh_hr_zk_attendance = False
