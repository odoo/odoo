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
from tools.translate import _

class account_analytic_line(osv.osv):
    _name = 'account.analytic.line'
    _description = 'Analytic lines'
    _columns = {
        'name' : fields.char('Description', size=256, required=True),
        'date' : fields.date('Date', required=True),
        'amount' : fields.float('Amount', required=True),
        'unit_amount' : fields.float('Quantity'),
        'product_uom_id' : fields.many2one('product.uom', 'UoM'),
        'product_id' : fields.many2one('product.product', 'Product'),
        'account_id' : fields.many2one('account.analytic.account', 'Analytic Account', required=True, ondelete='cascade', select=True),
        'general_account_id' : fields.many2one('account.account', 'General Account', required=True, ondelete='cascade'),
        'move_id' : fields.many2one('account.move.line', 'Move Line', ondelete='cascade', select=True),
        'journal_id' : fields.many2one('account.analytic.journal', 'Analytic Journal', required=True, ondelete='cascade', select=True),
        'code' : fields.char('Code', size=8),
        'user_id' : fields.many2one('res.users', 'User',),
        'ref': fields.char('Ref.', size=32),
    }
    _defaults = {
        'date': lambda *a: time.strftime('%Y-%m-%d'),
    }
    _order = 'date'
    
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None):
        if context is None:
            context = {}

        if context.get('from_date',False):
            args.append(['date', '>=',context['from_date']])
            
        if context.get('to_date',False):
            args.append(['date','<=',context['to_date']])
            
        return super(account_analytic_line, self).search(cr, uid, args, offset, limit,
                order, context=context)
        
    def _check_company(self, cr, uid, ids):
        lines = self.browse(cr, uid, ids)
        for l in lines:
            if l.move_id and not l.account_id.company_id.id == l.move_id.account_id.company_id.id:
                return False
        return True
    _constraints = [
#        (_check_company, 'You can not create analytic line that is not in the same company than the account line', ['account_id'])
    ]
    
    def on_change_unit_amount(self, cr, uid, id, prod_id, unit_amount,
            unit=False, context=None):
        uom_obj = self.pool.get('product.uom')
        product_obj = self.pool.get('product.product')
        if unit_amount and prod_id:
            prod = product_obj.browse(cr, uid, prod_id)
            a = prod.product_tmpl_id.property_account_expense.id
            if not a:
                a = prod.categ_id.property_account_expense_categ.id
            if not a:
                raise osv.except_osv(_('Error !'),
                        _('There is no expense account define ' \
                                'for this product: "%s" (id:%d)') % \
                                (prod.name, prod.id,))
            amount = unit_amount * uom_obj._compute_price(cr, uid,
                    prod.uom_id.id, prod.standard_price, unit)
            return {'value': {
                'amount': - round(amount, 2),
                'general_account_id': a,
                }}
        return {}

    def view_header_get(self, cr, user, view_id, view_type, context):
        if context.get('account_id', False):
            cr.execute('select name from account_analytic_account where id=%s', (context['account_id'],))
            res = cr.fetchone()
            res = _('Entries: ')+ (res[0] or '')
            return res
        return False

account_analytic_line()


class timesheet_invoice(osv.osv):
    _name = "report.hr.timesheet.invoice.journal"
    _description = "Analytic account costs and revenues"
    _auto = False
    _columns = {
        'name': fields.date('Month', readonly=True),
        'account_id':fields.many2one('account.analytic.account', 'Analytic Account', readonly=True, select=True),
        'journal_id': fields.many2one('account.analytic.journal', 'Journal', readonly=True),
        'quantity': fields.float('Quantities', readonly=True),
        'cost': fields.float('Credit', readonly=True),
        'revenue': fields.float('Debit', readonly=True)
    }
    _order = 'name desc, account_id'
    def init(self, cr):
        cr.execute("""
        create or replace view report_hr_timesheet_invoice_journal as (
            select
                min(l.id) as id,
                date_trunc('month', l.date)::date as name,
                sum(
                    CASE WHEN l.amount>0 THEN 0 ELSE l.amount
                    END
                ) as cost,
                sum(
                    CASE WHEN l.amount>0 THEN l.amount ELSE 0
                    END
                ) as revenue,
                sum(l.unit_amount* COALESCE(u.factor, 1)) as quantity,
                journal_id,
                account_id
            from account_analytic_line l
                LEFT OUTER join product_uom u on (u.id=l.product_uom_id)
            group by
                date_trunc('month', l.date),
                journal_id,
                account_id
        )""")
timesheet_invoice()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

