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

import tools
from osv import fields,osv

class account_invoice_report(osv.osv):
    _name = "account.invoice.report"
    _description = "Invoices Statistics"
    _auto = False
    _rec_name = 'date'
    _columns = {
        'date': fields.date('Date', readonly=True),
        'year': fields.char('Year', size=4, readonly=True),
        'day': fields.char('Day', size=128, readonly=True),
        'month':fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'),
            ('05','May'), ('06','June'), ('07','July'), ('08','August'), ('09','September'),
            ('10','October'), ('11','November'), ('12','December')], 'Month',readonly=True),
        'product_id':fields.many2one('product.product', 'Product', readonly=True),
        'product_qty':fields.float('Qty', readonly=True),
        'payment_term': fields.many2one('account.payment.term', 'Payment Term',readonly=True),
        'period_id': fields.many2one('account.period', 'Force Period', domain=[('state','<>','done')],readonly=True),
        'fiscal_position': fields.many2one('account.fiscal.position', 'Fiscal Position',readonly=True),
        'currency_id': fields.many2one('res.currency', 'Currency', readonly=True),
        'journal_id': fields.many2one('account.journal', 'Journal',readonly=True),
        'partner_id':fields.many2one('res.partner', 'Partner', readonly=True),
        'company_id':fields.many2one('res.company', 'Company', readonly=True),
        'user_id':fields.many2one('res.users', 'Salesman', readonly=True),
        'price_total':fields.float('Total Price', readonly=True),
        'price_average':fields.float('Average Price', readonly=True),
        'nbr':fields.integer('# of Lines', readonly=True),
        'type': fields.selection([
            ('out_invoice','Customer Invoice'),
            ('in_invoice','Supplier Invoice'),
            ('out_refund','Customer Refund'),
            ('in_refund','Supplier Refund'),
            ],'Type', readonly=True),
        'state': fields.selection([
            ('draft','Draft'),
            ('proforma','Pro-forma'),
            ('proforma2','Pro-forma'),
            ('open','Open'),
            ('paid','Done'),
            ('cancel','Cancelled')
            ], 'Order State', readonly=True),
        'date_due': fields.date('Due Date', readonly=True),
        'address_contact_id': fields.many2one('res.partner.address', 'Contact Address Name', readonly=True),
        'address_invoice_id': fields.many2one('res.partner.address', 'Invoice Address Name', readonly=True),
        'account_id': fields.many2one('account.account', 'Account',readonly=True),
        'partner_bank': fields.many2one('res.partner.bank', 'Bank Account',readonly=True),
        'residual':fields.float('Total Residual', readonly=True),
        'delay_to_pay':fields.float('Avg. Delay To Pay', readonly=True, group_operator="avg"),
    }
    _order = 'date desc'
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'account_invoice_report')
        cr.execute("""
            create or replace view account_invoice_report as (
                 select
                     min(l.id) as id,
                     s.date_invoice as date,
                     to_char(s.date_invoice, 'YYYY') as year,
                     to_char(s.date_invoice, 'MM') as month,
                     to_char(s.date_invoice, 'YYYY-MM-DD') as day,
                     l.product_id as product_id,
                     sum(l.quantity * u.factor) as product_qty,
                     s.partner_id as partner_id,
                     s.payment_term as payment_term,
                     s.period_id as period_id,
                     s.currency_id as currency_id,
                     s.journal_id as journal_id,
                     s.fiscal_position as fiscal_position,
                     s.user_id as user_id,
                     s.company_id as company_id,
                     sum(l.quantity*l.price_unit) as price_total,
                     (sum(l.quantity*l.price_unit)/sum(l.quantity * u.factor))::decimal(16,2) as price_average,
                     count(*) as nbr,
                     s.type as type,
                     s.state,
                     s.date_due as date_due,
                     s.address_contact_id as address_contact_id,
                     s.address_invoice_id as address_invoice_id,
                     s.account_id as account_id,
                     s.partner_bank as partner_bank,
                     s.residual as residual,
                     case when s.state != 'paid' then null else
                            extract(epoch from avg(am.date_created-l.create_date))/(24*60*60)::decimal(16,2)
                     end as delay_to_pay
                 from
                 account_invoice_line l
                 left join
                     account_invoice s on (s.id=l.invoice_id)
                     left join product_uom u on (u.id=l.uos_id),
                 account_move_line am left join account_invoice i on (i.move_id=am.move_id)
                 where
                        am.account_id=i.account_id
                 group by
                     s.type,
                     s.date_invoice,
                     s.partner_id,
                     l.product_id,
                     l.uos_id,
                     s.user_id,
                     s.state,
                     s.residual,
                     s.company_id,
                     s.payment_term,
                     s.period_id,
                     s.fiscal_position,
                     s.currency_id,
                     s.journal_id,
                     s.date_due,
                     s.address_contact_id,
                     s.address_invoice_id,
                     s.account_id,
                     s.partner_bank
            )
        """)
account_invoice_report()
