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
import decimal_precision as dp

from osv import fields
from osv import osv
from tools.translate import _
import tools
from tools import config

class account_analytic_line(osv.osv):
    _inherit = 'account.analytic.line'
    _description = 'Analytic Line'
    _columns = {
        'product_uom_id' : fields.many2one('product.uom', 'UoM'),
        'product_id' : fields.many2one('product.product', 'Product'),
        'general_account_id' : fields.many2one('account.account', 'General Account', required=True, ondelete='cascade'),
        'move_id' : fields.many2one('account.move.line', 'Move Line', ondelete='cascade', select=True),
        'journal_id' : fields.many2one('account.analytic.journal', 'Analytic Journal', required=True, ondelete='cascade', select=True),
        'code' : fields.char('Code', size=8),
        'ref': fields.char('Ref.', size=64),
    }
    _defaults = {
        'date': lambda *a: time.strftime('%Y-%m-%d'),
        'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'account.analytic.line', c),
    }
    _order = 'date'
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if context is None:
            context = {}

        if context.get('from_date',False):
            args.append(['date', '>=',context['from_date']])
            
        if context.get('to_date',False):
            args.append(['date','<=',context['to_date']])
            
        return super(account_analytic_line, self).search(cr, uid, args, offset, limit,
                order, context=context, count=count)
        
    def _check_company(self, cr, uid, ids):
        lines = self.browse(cr, uid, ids)
        for l in lines:
            if l.move_id and not l.account_id.company_id.id == l.move_id.account_id.company_id.id:
                return False
        return True
    _constraints = [
#        (_check_company, 'You can not create analytic line that is not in the same company than the account line', ['account_id'])
    ]
    
    # Compute the cost based on the price type define into company
    # property_valuation_price_type property
    def on_change_unit_amount(self, cr, uid, id, prod_id, unit_amount,company_id,
            unit=False, context=None):
        if context==None:
            context={}
        uom_obj = self.pool.get('product.uom')
        product_obj = self.pool.get('product.product')
        company_obj=self.pool.get('res.company')
        if  prod_id:
            prod = product_obj.browse(cr, uid, prod_id)
            a = prod.product_tmpl_id.property_account_expense.id
            if not a:
                a = prod.categ_id.property_account_expense_categ.id
            if not a:
                raise osv.except_osv(_('Error !'),
                        _('There is no expense account defined ' \
                                'for this product: "%s" (id:%d)') % \
                                (prod.name, prod.id,))
            if not company_id:
                company_id=company_obj._company_default_get(cr, uid, 'account.analytic.line', context)
      
            # Compute based on pricetype
            pricetype=self.pool.get('product.price.type').browse(cr,uid,company_obj.browse(cr,uid,company_id).property_valuation_price_type.id)
            # Take the company currency as the reference one
            context['currency_id']=company_obj.browse(cr,uid,company_id).currency_id.id
            amount_unit=prod.price_get(pricetype.field, context)[prod.id]
            amount=amount_unit*unit_amount or 1.0
            return {'value': {
                'amount': - round(amount, 2),
                'general_account_id': a,
                }}
        return {}

    def view_header_get(self, cr, user, view_id, view_type, context):
        if context.get('account_id', False):
            # account_id in context may also be pointing to an account.account.id
            cr.execute('select name from account_analytic_account where id=%s', (context['account_id'],))
            res = cr.fetchone()
            if res:
                res = _('Entries: ')+ (res[0] or '')
            return res
        return False

account_analytic_line()


class timesheet_invoice(osv.osv):
    _name = "report.hr.timesheet.invoice.journal"
    _description = "Analytic Account Costs and Revenues"
    _auto = False
    _columns = {
        'name': fields.char('Year',size=64,required=False, readonly=True),
        'account_id':fields.many2one('account.analytic.account', 'Analytic Account', readonly=True, select=True),
        'journal_id': fields.many2one('account.analytic.journal', 'Journal', readonly=True),
        'quantity': fields.float('Quantities', readonly=True),
        'cost': fields.float('Credit', readonly=True),
        'revenue': fields.float('Debit', readonly=True),
        'month':fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'), ('05','May'), ('06','June'),
                                  ('07','July'), ('08','August'), ('09','September'), ('10','October'), ('11','November'), ('12','December')],'Month',readonly=True),
    }
    _order = 'name desc, account_id'
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_hr_timesheet_invoice_journal')
        cr.execute("""
        create or replace view report_hr_timesheet_invoice_journal as (
            select
                min(l.id) as id,
                to_char(l.date, 'YYYY') as name,
                to_char(l.date,'MM') as month,
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
                to_char(l.date, 'YYYY'),
                to_char(l.date,'MM'),
                journal_id,
                account_id
        )""")
timesheet_invoice()


class res_partner(osv.osv):
    """ Inherits partner and adds contract information in the partner form """
    _inherit = 'res.partner'
    
    _columns = {
                'contract_ids': fields.one2many('account.analytic.account', \
                                                    'partner_id', 'Contracts'), 
                }

res_partner()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

