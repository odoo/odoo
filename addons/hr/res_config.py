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

from openerp.osv import fields, osv

class hr_config_settings(osv.osv_memory):
    _name = 'hr.config.settings'
    _inherit = 'res.config.settings'

    _columns = {
        'module_hr_timesheet_sheet': fields.boolean('Allow timesheets validation by managers',
            help ="""This installs the module hr_timesheet_sheet."""),
        'module_hr_attendance': fields.boolean('Install attendances feature',
            help ="""This installs the module hr_attendance."""),
        'module_hr_timesheet': fields.boolean('Manage timesheets',
            help ="""This installs the module hr_timesheet."""),
        'module_hr_holidays': fields.boolean('Manage holidays, leaves and allocation requests',
            help ="""This installs the module hr_holidays."""),
        'module_hr_expense': fields.boolean('Manage employees expenses',
            help ="""This installs the module hr_expense."""),
        'module_hr_recruitment': fields.boolean('Manage the recruitment process',
            help ="""This installs the module hr_recruitment."""),
        'module_hr_contract': fields.boolean('Record contracts per employee',
            help ="""This installs the module hr_contract."""),
        'module_hr_evaluation': fields.boolean('Organize employees periodic evaluation',
            help ="""This installs the module hr_evaluation."""),
        'module_hr_gamification': fields.boolean('Drive engagement with challenges and badges',
            help ="""This installs the module hr_gamification."""),
        'module_account_analytic_analysis': fields.boolean('Allow invoicing based on timesheets (the sale application will be installed)',
            help ="""This installs the module account_analytic_analysis, which will install sales management too."""),
        'module_hr_payroll': fields.boolean('Manage payroll',
            help ="""This installs the module hr_payroll."""),
    }

    def onchange_hr_timesheet(self, cr, uid, ids, timesheet, context=None):
        """ module_hr_timesheet implies module_hr_attendance """
        if timesheet:
            return {'value': {'module_hr_attendance': True}}
        return {}

    def onchange_hr_attendance(self, cr, uid, ids, attendance, context=None):
        """ module_hr_timesheet implies module_hr_attendance """
        if not attendance:
            return {'value': {'module_hr_timesheet': False}}
        return {}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
