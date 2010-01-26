# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from osv import fields, osv

class hr_installer(osv.osv_memory):
    _name = 'hr.installer'
    _inherit = 'res.config.installer'

    _columns = {
        # Human Resources Management
        'hr_holidays':fields.boolean('Holidays / Leaves Management'),
        'hr_expense':fields.boolean('Expenses'),
        'hr_jobs':fields.boolean('Recruitement Process'),
        'hr_timesheet_sheet':fields.boolean('Timesheets'),
        'hr_contract':fields.boolean("Employee's Contracts"),
        'hr_evaluation':fields.boolean('Periodic Evaluations'),
        'hr_attendance':fields.boolean('Attendances (Sign In/Out)'),
        }
    _defaults = {
        'hr_holidays': True,
        'hr_expense': True,
        }
hr_installer()
