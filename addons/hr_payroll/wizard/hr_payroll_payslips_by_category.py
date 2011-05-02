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
from datetime import datetime
from dateutil import relativedelta

from osv import fields, osv
from tools.translate import _

class hr_payslip_category(osv.osv_memory):

    _name ='hr.payslip.category'
    _description = 'Generate payslips for all employees within given category'
    _columns = {
        'employee_ids': fields.many2many('hr.employee', 'hr_employee_group_rel', 'struct_id', 'employee_id', 'Employees'),
    }

    def compute_sheet(self, cr, uid, ids, context=None):
        emp_pool = self.pool.get('hr.employee')
        slip_pool = self.pool.get('hr.payslip')
        input_line_pool = self.pool.get('hr.payslip.input')
        slip_ids = []
        if context is None:
            context = {}
        data = self.read(cr, uid, ids, context=context)[0]
        if not data['employee_ids']:
            raise osv.except_osv(_("Warning !"), _("You must select employees to generate payslip"))
        for emp in emp_pool.browse(cr, uid, data['employee_ids'], context=context):
            slip_data = slip_pool.onchange_employee_id(cr, uid, [], time.strftime('%Y-%m-01'), str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10], emp.id, contract_id=False, context=context)
            res = {
                'employee_id': emp.id,
                'name': slip_data['value'].get('name', False),
                'struct_id': slip_data['value'].get('struct_id', False),
                'contract_id': slip_data['value'].get('contract_id', False),
                'payslip_group_id': context.get('active_id', False),
            }
            slip_id = slip_pool.create(cr, uid, res, context=context)
            for input in slip_data['value']['input_line_ids']:
                input.update({'payslip_id': slip_id})
                input_line_pool.create(cr, uid, input, context=context)
            slip_ids.append(slip_id)
        slip_pool.compute_sheet(cr, uid, slip_ids, context=context)
        return {'type': 'ir.actions.act_window_close'}

hr_payslip_category()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
