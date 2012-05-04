# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (C) 2004-2012 OpenERP S.A. (<http://openerp.com>).
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

class hr_config_settings(osv.osv_memory):
    _name = 'hr.config.settings'
    _inherit = 'res.config.settings'

    _columns = {
        'module_hr_timesheet_sheet': fields.boolean('Timesheet Validation by Manager',
            help ="""This installs the module hr_timesheet_sheet."""),
        'module_hr_attendance': fields.boolean('Track Attendances',
            help ="""This installs the module hr_attendance."""),
        'module_hr_timesheet': fields.boolean('Manage Timesheets',
            help ="""This installs the module hr_timesheet."""),                                
        'module_hr_holidays': fields.boolean('Leaves & Holidays',
            help ="""This installs the module hr_holidays."""),
        'module_hr_expense': fields.boolean('Expenses',
            help ="""This installs the module hr_expense."""),
        'module_hr_recruitment': fields.boolean('Recruitment',
            help ="""This installs the module hr_recruitment."""),
        'module_hr_contract': fields.boolean('Employees Contracts',
            help ="""This installs the module hr_contract."""),
        'module_hr_evaluation': fields.boolean('Periodic Appraisals',
            help ="""This installs the module hr_evaluation."""),
                
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
