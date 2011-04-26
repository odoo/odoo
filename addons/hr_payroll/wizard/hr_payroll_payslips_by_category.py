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
from tools.translate import _

class hr_payslip_category(osv.osv_memory):

    _name ='hr.payslip.category'
    _columns = {
            'category_id': fields.many2one('hr.employee.category', 'Employee Category', required=True),
    }

    def compute_sheet(self, cr, uid, ids, context=None):
        emp_pool = self.pool.get('hr.employee')
        slip_pool = self.pool.get('hr.payslip')
        if context is None:
            context = {}
        data = self.read(cr, uid, ids, context=context)[0]
        cr.execute('SELECT DISTINCT emp_id FROM employee_category_rel WHERE category_id = %s', (data['category_id'][0], ))
        emp_ids = [x[0] for x in cr.fetchall()]
        if not emp_ids:
            raise osv.except_osv(_("Warning !"), _("No employee(s) found for '%s' category!") % (data['category_id'][1]))
        slip_ids = []
        for emp in emp_pool.browse(cr, uid, emp_ids, context=context):
            old_slips = slip_pool.search(cr, uid, [('employee_id', '=', emp.id),('state', '=', 'draft')], context=context)
            if old_slips:
                for id in context.get('active_ids'):
                    slip_pool.write(cr, uid, old_slips, {'payslip_group_id': id}, context=context)
                    slip_ids.extend(old_slips)
            else:
                for id in context.get('active_ids'):
                    res = {
                        'employee_id': emp.id,
                        'payslip_group_id': id,
                    }
                    slip_id = slip_pool.create(cr, uid, res, context=context)
                    slip_ids.append(slip_id)
        slip_pool.compute_sheet(cr, uid, slip_ids, context=context)
        return {'type': 'ir.actions.act_window_close'}

hr_payslip_category()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
