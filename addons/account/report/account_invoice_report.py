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
import decimal_precision as dp
from osv import fields,osv

class account_invoice_report(osv.osv):
    _name = "account.invoice.report"
    _description = "Invoices Statistics"
    _auto = False
    _rec_name = 'date'

    def _compute_amounts_in_user_currency(self, cr, uid, ids, field_names, args, context=None):
        """Compute the amounts in the currency of the user
        """
        if context is None:
            context={}
        currency_obj = self.pool.get('res.currency')
        currency_rate_obj = self.pool.get('res.currency.rate')
        user_currency_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.currency_id.id
        currency_rate_id = currency_rate_obj.search(cr, uid, [('rate', '=', 1)], limit=1, context=context)[0]
        base_currency_id = currency_rate_obj.browse(cr, uid, currency_rate_id, context=context).currency_id.id
        res = {}
        ctx = context.copy()
        for item in self.browse(cr, uid, ids, context=context):
            ctx['date'] = item.date
            price_total = currency_obj.compute(cr, uid, base_currency_id, user_currency_id, item.price_total, context=ctx)
            price_average = currency_obj.compute(cr, uid, base_currency_id, user_currency_id, item.price_average, context=ctx)
            residual = currency_obj.compute(cr, uid, base_currency_id, user_currency_id, item.residual, context=ctx)
            res[item.id] = {
                'user_currency_price_total': price_total,
                'user_currency_price_average': price_average,
                'user_currency_residual': residual,
            }
        return res

    _columns = {
        'date': fields.date('Date', readonly=True),
        'year': fields.char('Year', size=4, readonly=True),
        'day': fields.char('Day', size=128, readonly=True),
        'month': fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'),
            ('05','May'), ('06','June'), ('07','July'), ('08','August'), ('09','September'),
            ('10','October'), ('11','November'), ('12','December')], 'Month', readonly=True),
        'product_id': fields.many2one('product.product', 'Product', readonly=True),
        'product_qty':fields.float('Qty', readonly=True),
        'uom_name': fields.char('Reference Unit of Measure', size=128, readonly=True),
        'payment_term': fields.many2one('account.payment.term', 'Payment Term', readonly=True),
        'period_id': fields.many2one('account.period', 'Force Period', domain=[('state','<>','done')], readonly=True),
        'fiscal_position': fields.many2one('account.fiscal.position', 'Fiscal Position', readonly=True),
        'currency_id': fields.many2one('res.currency', 'Currency', readonly=True),
        'categ_id': fields.many2one('product.category','Category of Product', readonly=True),
        'journal_id': fields.many2one('account.journal', 'Journal', readonly=True),
        'partner_id': fields.many2one('res.partner', 'Partner', readonly=True),
        'company_id': fields.many2one('res.company', 'Company', readonly=True),
        'user_id': fields.many2one('res.users', 'Salesperson', readonly=True),
        'price_total': fields.float('Total Without Tax', readonly=True),
        'user_currency_price_total': fields.function(_compute_amounts_in_user_currency, string="Total Without Tax", type='float', digits_compute=dp.get_precision('Account'), multi="_compute_amounts"),
        'price_average': fields.float('Average Price', readonly=True, group_operator="avg"),
        'user_currency_price_average': fields.function(_compute_amounts_in_user_currency, string="Average Price", type='float', digits_compute=dp.get_precision('Account'), multi="_compute_amounts"),
        'currency_rate': fields.float('Currency Rate', readonly=True),
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
            ], 'Invoice Status', readonly=True),
        'date_due': fields.date('Due Date', readonly=True),
        'account_id': fields.many2one('account.account', 'Account',readonly=True),
        'account_line_id': fields.many2one('account.account', 'Account Line',readonly=True),
        'partner_bank_id': fields.many2one('res.partner.bank', 'Bank Account',readonly=True),
        'residual': fields.float('Total Residual', readonly=True),
        'user_currency_residual': fields.function(_compute_amounts_in_user_currency, string="Total Residual", type='float', digits_compute=dp.get_precision('Account'), multi="_compute_amounts"),
        'delay_to_pay': fields.float('Avg. Delay To Pay', readonly=True, group_operator="avg"),
        'due_delay': fields.float('Avg. Due Delay', readonly=True, group_operator="avg"),
    }
    _order = 'date desc'


    def _select(self):
        select_str = """
            SELECT min(ail.id) as id,
                    ai.date_invoice as date,
                    to_char(ai.date_invoice, 'YYYY') as year,
                    to_char(ai.date_invoice, 'MM') as month,
                    to_char(ai.date_invoice, 'YYYY-MM-DD') as day,
                    ail.product_id,
                    ai.partner_id as partner_id,
                    ai.payment_term as payment_term,
                    ai.period_id as period_id,
                    (case when u.uom_type not in ('reference') then
                        (select name from product_uom where uom_type='reference' and active and category_id=u.category_id LIMIT 1)
                    else
                        u.name
                    end) as uom_name,
                    ai.currency_id as currency_id,
                    ai.journal_id as journal_id,
                    ai.fiscal_position as fiscal_position,
                    ai.user_id as user_id,
                    ai.company_id as company_id,
                    count(ail.*) as nbr,
                    ai.type as type,
                    ai.state,
                    pt.categ_id,
                    ai.date_due as date_due,
                    ai.account_id as account_id,
                    ail.account_id as account_line_id,
                    ai.partner_bank_id as partner_bank_id,
                    sum(case when ai.type in ('out_refund','in_invoice') then
                         -ail.quantity / u.factor
                        else
                         ail.quantity / u.factor
                        end) as product_qty,

                    sum(case when ai.type in ('out_refund','in_invoice') then
                         -ail.price_subtotal
                        else
                          ail.price_subtotal
                        end) / cr.rate as price_total,

                    (case when ai.type in ('out_refund','in_invoice') then
                      sum(-ail.price_subtotal)
                    else
                      sum(ail.price_subtotal)
                    end) / (CASE WHEN sum(ail.quantity/u.factor) <> 0
                       THEN
                         (case when ai.type in ('out_refund','in_invoice')
                          then sum(-ail.quantity/u.factor)
                          else sum(ail.quantity/u.factor) end)
                       ELSE 1
                       END)
                     / cr.rate as price_average,

                    cr.rate as currency_rate,
                    sum((select extract(epoch from avg(date_trunc('day',aml.date_created)-date_trunc('day',l.create_date)))/(24*60*60)::decimal(16,2)
                        from account_move_line as aml
                        left join account_invoice as a ON (a.move_id=aml.move_id)
                        left join account_invoice_line as l ON (a.id=l.invoice_id)
                        where a.id=ai.id)) as delay_to_pay,
                    sum((select extract(epoch from avg(date_trunc('day',a.date_due)-date_trunc('day',a.date_invoice)))/(24*60*60)::decimal(16,2)
                        from account_move_line as aml
                        left join account_invoice as a ON (a.move_id=aml.move_id)
                        left join account_invoice_line as l ON (a.id=l.invoice_id)
                        where a.id=ai.id)) as due_delay,
                    (case when ai.type in ('out_refund','in_invoice') then
                      -ai.residual
                    else
                      ai.residual
                    end)/ (CASE WHEN
                        (select count(l.id) from account_invoice_line as l
                         left join account_invoice as a ON (a.id=l.invoice_id)
                         where a.id=ai.id) <> 0
                       THEN
                        (select count(l.id) from account_invoice_line as l
                         left join account_invoice as a ON (a.id=l.invoice_id)
                         where a.id=ai.id)
                       ELSE 1
                       END) / cr.rate as residual
        """
        return select_str

    def _where(self):
        where_str = """
            WHERE cr.id in (select id from res_currency_rate cr2  where (cr2.currency_id = ai.currency_id)
                and ((ai.date_invoice is not null and cr.name <= ai.date_invoice) or (ai.date_invoice is null and cr.name <= NOW())) order by name desc limit 1)
        """
        return where_str

    def _from(self):
        from_str = """
            FROM account_invoice_line as ail
                left join account_invoice as ai ON (ai.id=ail.invoice_id)
                left join product_product pr on (pr.id=ail.product_id)
                left join product_template pt on (pt.id=pr.product_tmpl_id)
                left join product_uom u on (u.id=ail.uos_id),
                res_currency_rate cr
        """
        return from_str

    def _group_by(self):
        group_by_str = """
            GROUP BY ail.product_id,
                    ai.date_invoice,
                    ai.id,
                    cr.rate,
                    to_char(ai.date_invoice, 'YYYY'),
                    to_char(ai.date_invoice, 'MM'),
                    to_char(ai.date_invoice, 'YYYY-MM-DD'),
                    ai.partner_id,
                    ai.payment_term,
                    ai.period_id,
                    u.name,
                    ai.currency_id,
                    ai.journal_id,
                    ai.fiscal_position,
                    ai.user_id,
                    ai.company_id,
                    ai.type,
                    ai.state,
                    pt.categ_id,
                    ai.date_due,
                    ai.account_id,
                    ail.account_id,
                    ai.partner_bank_id,
                    ai.residual,
                    ai.amount_total,
                    u.uom_type,
                    u.category_id
        """
        return group_by_str

    def init(self, cr):
        # self._table = account_invoice_report
        tools.drop_view_if_exists(cr, self._table)
        cr.execute("CREATE or REPLACE VIEW %s as (%s %s %s %s)" % (
                    self._table, 
                    self._select(), self._from(), self._where(), self._group_by()))

account_invoice_report()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
