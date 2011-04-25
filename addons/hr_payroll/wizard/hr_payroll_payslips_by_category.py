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

from osv import fields, osv
import netsvc

class hr_payroll_payslip_groups(osv.osv_memory):

    _name ='hr.payroll.payslip.groups'
    _columns = {
            'employee_category': fields.many2one('hr.employee.category', 'Employee Category', required=True),
    }

    def compute_sheet(self, cr, uid, ids, context=None):
        emp_pool = self.pool.get('hr.employee')
        slip_pool = self.pool.get('hr.payslip')
        wf_service = netsvc.LocalService("workflow")
        if context is None:
            context = {}
        data = self.read(cr, uid, ids, context=context)[0]
        cr.execute('SELECT DISTINCT emp_id FROM employee_category_rel WHERE category_id = %s', (data['employee_category'][0], ))
        emp_ids = filter(None, map(lambda x:x[0], cr.fetchall()))
        for emp in emp_pool.browse(cr, uid, emp_ids, context=context):
            old_slips = slip_pool.search(cr, uid, [('employee_id','=', emp.id)], context=context)
            if old_slips:
                slip_pool.write(cr, uid, old_slips, {'payslip_group_id': context.get('active_id', False)}, context=context)
                for sid in old_slips:
                    wf_service.trg_validate(uid, 'hr.payslip', sid, 'compute_sheet', cr)
            else:
                res = {
                    'employee_id': emp.id,
                    'payslip_group_id': context.get('active_id', False),
                }
                slip_id = slip_pool.create(cr, uid, res, context=context)
                wf_service.trg_validate(uid, 'hr.payslip', slip_id, 'compute_sheet', cr)
        return {'type': 'ir.actions.act_window_close'}

hr_payroll_payslip_groups()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
