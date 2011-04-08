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

class hr_timesheet_invoice_installer(osv.osv_memory):
    _name = "hr.timesheet.invoice.installer"
    _description = "Employee Invoice Data"
    _columns = {
        'employee_id': fields.many2one('hr.employee', 'Employee', domain="['|',('product_id','=',False),('journal_id','=',False)]" ,required=True),
        'product_id': fields.many2one('product.product', 'Product', domain="[('type','=','service')]"),
        'journal_id': fields.many2one('account.analytic.journal', 'Analytic Journal',domain="[('type','=','general')]"),
        'wizard_id': fields.many2one('hr.timesheet.invoice.wizard','Employee', required=True),
    }


hr_timesheet_invoice_installer()

class hr_timesheet_invoice_wizard(osv.osv_memory):
    _name = "hr.timesheet.invoice.wizard"
    _description = "Timesheet Invoice"
    _columns = {
        'emp_ids':fields.one2many('hr.timesheet.invoice.installer', 'wizard_id', 'Wizard Reference'),
    }

    def default_get(self, cr, uid, fields, context=None):
        """
         To get default values for the object.
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param fields: List of fields for which we want default values
         @param context: A standard dictionary
         @return: A dictionary with default values for all field in ``fields``
        """
        if context is None:
            context = {}
        res = super(hr_timesheet_invoice_wizard, self).default_get(cr, uid, fields, context=context)
        emp_obj = self.pool.get('hr.employee')
        emp_id = emp_obj.search(cr, uid, ['|',('user_id', '=', uid),('product_id','=',False),('journal_id','=','')], context=context)
        result = []
        data = {}
        for emp in emp_obj.browse(cr, uid, emp_id, context=context):
            data = {'employee_id':emp.id,'product_id':emp.product_id.id,'journal_id':emp.journal_id.id}
            result.append(data)
            if 'emp_ids' in fields:
                res.update({'emp_ids': result})
        return res

    def employee_data(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        hr_obj = self.pool.get('hr.employee')
        for emp in self.browse(cr, uid, ids, context=context):
            for emp_data in emp.emp_ids:
                emp_id = hr_obj.search(cr, uid, [('id', '=', emp_data.employee_id.id)], context=context)
                hr_obj.write(cr, uid, emp_id, {'name': emp_data.employee_id.name,'product_id':emp_data.product_id.id or False, 'journal_id':emp_data.journal_id.id or ''})
        return {'type': 'ir.actions.act_window_close'}

hr_timesheet_invoice_wizard()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: