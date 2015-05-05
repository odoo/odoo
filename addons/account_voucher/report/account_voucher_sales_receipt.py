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

from openerp import tools
from openerp import models, fields

class sale_receipt_report(models.Model):
    _name = "sale.receipt.report"
    _description = "Sales Receipt Statistics"
    _auto = False
    _rec_name = 'date'
    date = fields.Date(readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)
    journal_id = fields.Many2one('account.journal', string='Journal', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Partner', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    user_id = fields.Many2one('res.users', string='Salesperson', readonly=True)
    price_total = fields.Float(string='Total Without Tax', readonly=True)
    price_total_tax = fields.Float(string='Total With Tax', readonly=True)
    nbr = fields.Integer(string='# of Voucher Lines', readonly=True)
    type = fields.Selection([
        ('sale', 'Sale'),
        ('purchase', 'Purchase'),
    ], readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('proforma', 'Pro-forma'),
        ('posted', 'Posted'),
        ('cancel', 'Cancelled')
    ], string='Voucher Status', readonly=True)
    pay_now = fields.Selection([
        ('pay_now', 'Pay Directly'),
        ('pay_later', 'Pay Later or Group Funds'),
    ], string='Payment', readonly=True)
    date_due = fields.Date(string='Due Date', readonly=True)
    account_id = fields.Many2one('account.account', string='Account', readonly=True, domain=[('deprecated', '=', False)])
    delay_to_pay = fields.Float(string='Avg. Delay To Pay', readonly=True, group_operator="avg")
    due_delay = fields.Float(string='Avg. Due Delay', readonly=True, group_operator="avg")

    _order = 'date desc'

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'sale_receipt_report')
        cr.execute("""
            create or replace view sale_receipt_report as (
                select min(avl.id) as id,
                    av.date as date,
                    av.partner_id as partner_id,
                    aj.currency_id as currency_id,
                    av.journal_id as journal_id,
                    rp.user_id as user_id,
                    av.company_id as company_id,
                    count(avl.*) as nbr,
                    av.voucher_type as type,
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
                    sum((select extract(epoch from avg(date_trunc('day',aml.date)-date_trunc('day',l.create_date)))/(24*60*60)::decimal(16,2)
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
                where av.voucher_type='sale' and aj.type='sale'
                group by
                    av.date,
                    av.id,
                    av.partner_id,
                    aj.currency_id,
                    av.journal_id,
                    rp.user_id,
                    av.company_id,
                    av.voucher_type,
                    av.state,
                    av.date_due,
                    av.account_id,
                    av.tax_amount,
                    av.amount,
                    av.tax_amount,
                    av.pay_now
            )
        """)
