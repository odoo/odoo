# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#    $Id: account.py 1005 2005-07-25 08:41:42Z nicoe $
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

from osv import osv, fields
from tools.translate import _

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
        data = self.read(cr, uid, ids, [], context=context)[0]
        if not data['depts']:
            raise osv.except_osv(_('Error'), _('You have to select at least 1 Department. And try again.'))
        datas = {
             'ids': [],
             'model': 'ir.ui.menu',
             'form': data
            }
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'holidays.summary',
            'datas': datas,
            }

hr_holidays_summary_dept()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
