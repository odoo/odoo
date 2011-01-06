# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time
from osv import fields
from osv import osv
from osv.orm import except_orm
from tools.translate import _

class hr_employee(osv.osv):
    _name = "hr.employee"
    _inherit = "hr.employee"
    _columns = {
        'product_id': fields.many2one('product.product', 'Product'),
        'journal_id': fields.many2one('account.analytic.journal', 'Analytic Journal')
    }
hr_employee()


class hr_analytic_timesheet(osv.osv):
    _name = "hr.analytic.timesheet"
    _table = 'hr_analytic_timesheet'
    _description = "Timesheet line"
    _inherits = {'account.analytic.line': 'line_id'}
    _order = "id desc"
    _columns = {
        'line_id' : fields.many2one('account.analytic.line', 'Analytic line', ondelete='cascade'),
    }

    def unlink(self, cr, uid, ids, context={}):
        toremove = {}
        for obj in self.browse(cr, uid, ids, context):
            toremove[obj.line_id.id] = True
        self.pool.get('account.analytic.line').unlink(cr, uid, toremove.keys(), context)
        return super(hr_analytic_timesheet, self).unlink(cr, uid, ids, context)


    def on_change_unit_amount(self, cr, uid, id, prod_id, unit_amount, unit, context={}):
        res = {}
#        if prod_id and unit_amount:
        if prod_id:
            res = self.pool.get('account.analytic.line').on_change_unit_amount(cr, uid, id, prod_id, unit_amount,unit, context)
        return res

    def _getEmployeeProduct(self, cr, uid, context):
        emp_obj = self.pool.get('hr.employee')
        emp_id = emp_obj.search(cr, uid, [('user_id', '=', context.get('user_id', uid))])
        if emp_id:
            emp = emp_obj.browse(cr, uid, emp_id[0], context)
            if emp.product_id:
                return emp.product_id.id
        return False

    def _getEmployeeUnit(self, cr, uid, context):
        emp_obj = self.pool.get('hr.employee')
        emp_id = emp_obj.search(cr, uid, [('user_id', '=', context.get('user_id', uid))])
        if emp_id:
            emp = emp_obj.browse(cr, uid, emp_id[0], context)
            if emp.product_id:
                return emp.product_id.uom_id.id
        return False

    def _getGeneralAccount(self, cr, uid, context):
        emp_obj = self.pool.get('hr.employee')
        emp_id = emp_obj.search(cr, uid, [('user_id', '=', context.get('user_id', uid))])
        if emp_id:
            emp = self.pool.get('hr.employee').browse(cr, uid, emp_id[0], context=context)
            if bool(emp.product_id):
                a = emp.product_id.product_tmpl_id.property_account_expense.id
                if not a:
                    a = emp.product_id.categ_id.property_account_expense_categ.id
                if a:
                    return a
        return False

    def _getAnalyticJournal(self, cr, uid, context):
        emp_obj = self.pool.get('hr.employee')
        emp_id = emp_obj.search(cr, uid, [('user_id', '=', context.get('user_id', uid))])
        if emp_id:
            emp = self.pool.get('hr.employee').browse(cr, uid, emp_id[0], context=context)
            if emp.journal_id:
                return emp.journal_id.id
        return False


    _defaults = {
        'product_uom_id' : _getEmployeeUnit,
        'product_id' : _getEmployeeProduct,
        'general_account_id' : _getGeneralAccount,
        'journal_id' : _getAnalyticJournal,
        'date' : lambda self,cr,uid,ctx: ctx.get('date', time.strftime('%Y-%m-%d')),
        'user_id' : lambda obj, cr, uid, ctx : ctx.get('user_id', uid),
    }
    def on_change_account_id(self, cr, uid, ids, account_id):
        return {'value':{}}
    
    def on_change_date(self, cr, uid, ids, date):
        if ids:
            new_date = self.read(cr,uid,ids[0],['date'])['date']
            if date != new_date:
                warning = {'title':'User Alert!','message':'Changing the date will let this entry appear in the timesheet of the new date.'}
                return {'value':{},'warning':warning}
        return {'value':{}}
    
    def create(self, cr, uid, vals, context={}):
        try:
            res = super(hr_analytic_timesheet, self).create(cr, uid, vals, context)
            return res
        except Exception,e:
            if '"journal_id" viol' in e.args[0]:
                raise except_orm(_('ValidateError'),
                     _('No analytic journal available for this employee.\nDefine an employee for the selected user and assign an analytic journal.'))
            elif '"account_id" viol' in e.args[0]:
                raise except_orm(_('ValidateError'),
                     _('No analytic account defined on the project.\nPlease set one or we can not automatically fill the timesheet.'))
            else:
                raise except_orm(_('UnknownError'), str(e))

    def on_change_user_id(self, cr, uid, ids, user_id):
        if not user_id:
            return {}
        context = {'user_id': user_id}
        return {'value' : {
            'product_id' : self._getEmployeeProduct(cr, uid, context),
            'product_uom_id' : self._getEmployeeUnit(cr, uid, context),
            'general_account_id' :self._getGeneralAccount(cr, uid, context),
            'journal_id' : self._getAnalyticJournal(cr, uid, context),
        }}
hr_analytic_timesheet()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

