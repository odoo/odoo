##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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
import tools

class sale_receipt_report(osv.osv):
    _name = "sale.receipt.report"
    _description = "Sales Receipt Statistics"
    _auto = False
    _rec_name = 'date'
    _columns = {
        'date': fields.date('Date', readonly=True),
        'year': fields.char('Year', size=4, readonly=True),
        'day': fields.char('Day', size=128, readonly=True),
        'month': fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'),
            ('05','May'), ('06','June'), ('07','July'), ('08','August'), ('09','September'),
            ('10','October'), ('11','November'), ('12','December')], 'Month', readonly=True),
        'currency_id': fields.many2one('res.currency', 'Currency', readonly=True),
        'journal_id': fields.many2one('account.journal', 'Journal', readonly=True),
        'partner_id': fields.many2one('res.partner', 'Partner', readonly=True),
        'company_id': fields.many2one('res.company', 'Company', readonly=True),
        'user_id': fields.many2one('res.users', 'Salesman', readonly=True),
        'price_total': fields.float('Total Without Tax', readonly=True),
        'price_total_tax': fields.float('Total With Tax', readonly=True),
        'nbr':fields.integer('# of Voucher Lines', readonly=True),
        'type': fields.selection([
            ('sale','Sale'),
            ('purchase','Purchase'),
            ('payment','Payment'),
            ('receipt','Receipt'),
            ],'Type', readonly=True),
        'state': fields.selection([
            ('draft','Draft'),
             ('proforma','Pro-forma'),
             ('posted','Posted'),
             ('cancel','Cancelled')
            ], 'Voucher State', readonly=True),
        'pay_now':fields.selection([
            ('pay_now','Pay Directly'),
            ('pay_later','Pay Later or Group Funds'),
        ],'Payment', readonly=True),
        'date_due': fields.date('Due Date', readonly=True),
        'account_id': fields.many2one('account.account', 'Account',readonly=True),
        'delay_to_pay': fields.float('Avg. Delay To Pay', readonly=True, group_operator="avg"),
        'due_delay': fields.float('Avg. Due Delay', readonly=True, group_operator="avg")
    }
    _order = 'date desc'
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'sale_receipt_report')
        cr.execute("""
            create or replace view sale_receipt_report as (
                select min(avl.id) as id,
                    av.date as date,
                    to_char(av.date, 'YYYY') as year,
                    to_char(av.date, 'MM') as month,
                    to_char(av.date, 'YYYY-MM-DD') as day,
                    av.partner_id as partner_id,
                    aj.currency as currency_id,
                    av.journal_id as journal_id,
                    rp.user_id as user_id,
                    av.company_id as company_id,
                    count(avl.*) as nbr,
                    av.type as type,
                    av.state,
                    av.pay_now,
                    av.date_due as date_due,
                    av.account_id as account_id,
                    sum(av.amount-av.tax_amount)/(select count(l.id) from account_voucher_line as l
                            left join account_voucher as a ON (a.id=l.voucher_id)
                            where a.id=av.id) as price_total,
                    sum(av.amount)/(select count(l.id) from account_voucher_line as l
                            left join account_voucher as a ON (a.id=l.voucher_id)
                            where a.id=av.id) as price_total_tax,
                    sum((select extract(epoch from avg(date_trunc('day',aml.date_created)-date_trunc('day',l.create_date)))/(24*60*60)::decimal(16,2)
                        from account_move_line as aml
                        left join account_voucher as a ON (a.move_id=aml.move_id)
                        left join account_voucher_line as l ON (a.id=l.voucher_id)
                        where a.id=av.id)) as delay_to_pay,
                    sum((select extract(epoch from avg(date_trunc('day',a.date_due)-date_trunc('day',a.date)))/(24*60*60)::decimal(16,2)
                        from account_move_line as aml
                        left join account_voucher as a ON (a.move_id=aml.move_id)
                        left join account_voucher_line as l ON (a.id=l.voucher_id)
                        where a.id=av.id)) as due_delay
                from account_voucher_line as avl
                left join account_voucher as av on (av.id=avl.voucher_id)
                left join res_partner as rp ON (rp.id=av.partner_id)
                left join account_journal as aj ON (aj.id=av.journal_id)
                where av.type='sale' and aj.type in ('sale','sale_refund')
                group by
                    av.date,
                    av.id,
                    to_char(av.date, 'YYYY'),
                    to_char(av.date, 'MM'),
                    to_char(av.date, 'YYYY-MM-DD'),
                    av.partner_id,
                    aj.currency,
                    av.journal_id,
                    rp.user_id,
                    av.company_id,
                    av.type,
                    av.state,
                    av.date_due,
                    av.account_id,
                    av.tax_amount,
                    av.amount,
                    av.tax_amount,
                    av.pay_now
            )
        """)

sale_receipt_report()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
