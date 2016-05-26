# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv


class hr_employee(osv.osv):
    '''
    Employee
    '''

    _inherit = 'hr.employee'
    _description = 'Employee'

    def _timesheet_count(self, cr, uid, ids, field_name, arg, context=None):
        Sheet = self.pool['hr_timesheet_sheet.sheet']
        return {
            employee_id: Sheet.search_count(cr,uid, [('employee_id', '=', employee_id)], context=context)
            for employee_id in ids
        }

    _columns = {
        'timesheet_count': fields.function(_timesheet_count, type='integer', string='Timesheets'),
    }
