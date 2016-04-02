# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import time

from openerp.osv import fields, osv

class hr_holidays_summary_employee(osv.osv_memory):
    _name = 'hr.holidays.summary.employee'
    _description = 'HR Leaves Summary Report By Employee'
    _columns = {
        'date_from': fields.date('From', required=True),
        'emp': fields.many2many('hr.employee', 'summary_emp_rel', 'sum_id', 'emp_id', 'Employee(s)'),
        'holiday_type': fields.selection([('Approved','Approved'),('Confirmed','Confirmed'),('both','Both Approved and Confirmed')], 'Select Leave Type', required=True)
    }

    _defaults = {
         'date_from': lambda *a: time.strftime('%Y-%m-01'),
         'holiday_type': 'Approved',
    }

    def print_report(self, cr, uid, ids, context=None):
        data = self.read(cr, uid, ids, context=context)[0]
        data['emp'] = context.get('active_ids',[])
        datas = {
             'ids': [],
             'model': 'hr.employee',
             'form': data
            }
        return self.pool['report'].get_action(cr, uid, data['emp'], 'hr_holidays.report_holidayssummary', data=datas, context=context)