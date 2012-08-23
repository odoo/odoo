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

class analytic_entries_report(osv.osv):
    _name = "analytic.entries.report"
    _description = "Analytic Entries Statistics"
    _auto = False
    _columns = {
        'date': fields.date('Date', readonly=True),
        'year': fields.char('Year', size=4, readonly=True),
        'day': fields.char('Day', size=128, readonly=True),
        'month':fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'),
            ('05','May'), ('06','June'), ('07','July'), ('08','August'), ('09','September'),
            ('10','October'), ('11','November'), ('12','December')], 'Month',readonly=True),
        'user_id': fields.many2one('res.users', 'User',readonly=True),
        'name': fields.char('Description', size=64, readonly=True),
        'partner_id': fields.many2one('res.partner', 'Partner'),
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'currency_id': fields.many2one('res.currency', 'Currency', required=True),
        'account_id': fields.many2one('account.analytic.account', 'Account', required=False),
        'general_account_id': fields.many2one('account.account', 'General Account', required=True),
        'journal_id': fields.many2one('account.analytic.journal', 'Journal', required=True),
        'move_id': fields.many2one('account.move.line', 'Move', required=True),
        'product_id': fields.many2one('product.product', 'Product', required=True),
        'product_uom_id': fields.many2one('product.uom', 'Product Unit of Measure', required=True),
        'amount': fields.float('Amount', readonly=True),
        'unit_amount': fields.float('Quantity', readonly=True),
        'nbr': fields.integer('#Entries', readonly=True),
    }
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'analytic_entries_report')
        cr.execute("""
            create or replace view analytic_entries_report as (
                 select
                     min(a.id) as id,
                     count(distinct a.id) as nbr,
                     a.date as date,
                     to_char(a.date, 'YYYY') as year,
                     to_char(a.date, 'MM') as month,
                     to_char(a.date, 'YYYY-MM-DD') as day,
                     a.user_id as user_id,
                     a.name as name,
                     analytic.partner_id as partner_id,
                     a.company_id as company_id,
                     a.currency_id as currency_id,
                     a.account_id as account_id,
                     a.general_account_id as general_account_id,
                     a.journal_id as journal_id,
                     a.move_id as move_id,
                     a.product_id as product_id,
                     a.product_uom_id as product_uom_id,
                     sum(a.amount) as amount,
                     sum(a.unit_amount) as unit_amount
                 from
                     account_analytic_line a, account_analytic_account analytic
                 where analytic.id = a.account_id
                 group by
                     a.date, a.user_id,a.name,analytic.partner_id,a.company_id,a.currency_id,
                     a.account_id,a.general_account_id,a.journal_id,
                     a.move_id,a.product_id,a.product_uom_id
            )
        """)
analytic_entries_report()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
