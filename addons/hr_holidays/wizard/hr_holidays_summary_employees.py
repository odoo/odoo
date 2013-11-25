# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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
        data['emp'] = context['active_ids']
        datas = {
             'ids': [],
             'model': 'hr.employee',
             'form': data
            }
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'holidays.summary',
            'datas': datas,
            }


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
