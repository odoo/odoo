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
        'module_hr_timesheet_sheet': fields.boolean('allow timesheets validation by managers',
            help ="""This installs the module hr_timesheet_sheet."""),
        'module_hr_attendance': fields.boolean('track attendances',
            help ="""This installs the module hr_attendance."""),
        'module_hr_timesheet': fields.boolean('manage timesheets',
            help ="""This installs the module hr_timesheet."""),
        'module_hr_holidays': fields.boolean('manage holidays, leaves and allocation requests',
            help ="""This installs the module hr_holidays."""),
        'module_hr_expense': fields.boolean('manage employees expenses',
            help ="""This installs the module hr_expense."""),
        'module_hr_recruitment': fields.boolean('manage the recruitment process',
            help ="""This installs the module hr_recruitment."""),
        'module_hr_contract': fields.boolean('record contracts per employee',
            help ="""This installs the module hr_contract."""),
        'module_hr_evaluation': fields.boolean('organize employees periodic evaluation',
            help ="""This installs the module hr_evaluation."""),
        'module_hr_payroll': fields.boolean('manage payroll',
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
