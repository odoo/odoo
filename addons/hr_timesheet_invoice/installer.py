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

class hr_timesheet_invoice_installer(osv.osv):
    _name = "hr.timesheet.invoice.installer"
    _description = "Employee Invoice Data"
    _columns = {
        'employee_id': fields.many2one('hr.employee', 'Employee', domain="['|',('product_id','=',False),('journal_id','=',False)]" ,required=True),
        'type': fields.many2one('product.product', 'Product',domain="[('type','=','service')]"),
        'timesheet_journal': fields.many2one('account.analytic.journal', 'Analytic Journal',domain="[('type','=','general')]"),
    }

    def _get_user(self, cr, uid, context=None):

        emp_obj = self.pool.get('hr.employee')
        emp_id = emp_obj.search(cr, uid, ['|',('user_id', '=', uid),('product_id','=',False),('journal_id','=',False)], context=context)
        if not emp_id:
            raise osv.except_osv(_("Warning"), _("No employee defined for this user"))
        return emp_id and emp_id[0] or False

    _defaults = {
        'employee_id': _get_user
    }

hr_timesheet_invoice_installer()

class hr_timesheet_invoice_wizard(osv.osv):
    _name = "hr.timesheet.invoice.wizard"
    _description = "Timesheet Invoice"
    _columns = {
        'emp_ids':fields.one2many('hr.timesheet.invoice.installer', 'timesheet_journal', 'Employee details'),
    }

hr_timesheet_invoice_wizard()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: