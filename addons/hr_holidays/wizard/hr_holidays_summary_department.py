# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import time

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.exceptions import UserError

class hr_holidays_summary_dept(osv.osv_memory):
    _name = 'hr.holidays.summary.dept'
    _description = 'HR Leaves Summary Report By Department'
    _columns = {
        'date_from': fields.date('From', required=True),
        'depts': fields.many2many('hr.department', 'summary_dept_rel', 'sum_id', 'dept_id', 'Department(s)'),
        'holiday_type': fields.selection([('Approved','Approved'),('Confirmed','Confirmed'),('both','Both Approved and Confirmed')], 'Leave Type', required=True)
    }

    _defaults = {
         'date_from': lambda *a: time.strftime('%Y-%m-01'),
         'holiday_type': 'Approved'
    }

    def print_report(self, cr, uid, ids, context=None):
        data = self.read(cr, uid, ids, context=context)[0]
        if not data['depts']:
            raise UserError(_('You have to select at least one Department. And try again.'))
        datas = {
             'ids': [],
             'model': 'hr.department',
             'form': data
            }
        return self.pool['report'].get_action(cr, uid, data['depts'], 'hr_holidays.report_holidayssummary', data=datas, context=context)