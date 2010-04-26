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

class analytic_report(osv.osv):
    _name = "analytic.report"
    _description = "Analytic Accounts Statistics"
    _auto = False
    _columns = {
        'date_start': fields.date('Date Start', readonly=True),
        'date_end': fields.date('Date End',readonly=True),
        'name' : fields.char('Analytic Account', size=128, readonly=True),
        'partner_id' : fields.many2one('res.partner', 'Associated Partner',readonly=True),
        'journal_id' : fields.many2one('account.analytic.journal', 'Analytic Journal', readonly=True),
        'parent_id': fields.many2one('account.analytic.account', 'Parent Analytic Account', readonly=True),
        'user_id' : fields.many2one('res.users', 'Account Manager',readonly=True),
        'product_id' : fields.many2one('product.product', 'Product',readonly=True),
        'quantity': fields.float('Quantity',readonly=True),
        'debit' : fields.float('Debit',readonly=True),
        'credit' : fields.float('Credit',readonly=True),
        'balance' : fields.float('Balance',readonly=True),
        'year': fields.char('Year', size=4, readonly=True),
        'month':fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'),
            ('05','May'), ('06','June'), ('07','July'), ('08','August'), ('09','September'),
            ('10','October'), ('11','November'), ('12','December')], 'Month',readonly=True),
        'state': fields.selection([('draft','Draft'),
                                   ('open','Open'),
                                   ('pending','Pending'),
                                   ('cancelled', 'Cancelled'),
                                   ('close','Close'),
                                   ('template', 'Template')],
                'State', readonly=True),
    }
    _order = 'date_start desc'
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'analytic_report')
        cr.execute("""
            create or replace view analytic_report as (
                 select
                      min(s.id) as id,
                      to_char(s.create_date, 'YYYY') as year,
                      to_char(s.create_date, 'MM') as month,
                      l.journal_id,
                      l.product_id,
                      s.parent_id,
                      s.date_start,
                      s.date as date_end,
                      s.user_id,
                      s.name,
                      s.partner_id,
                      s.quantity,
                      s.debit,
                      s.credit,
                      s.balance,
                      count(*) as nbr,
                      s.state
                from account_analytic_account s
                left join account_analytic_line l on (s.id=l.account_id)
                GROUP BY s.create_date,s.state,l.journal_id,s.name,
                      s.partner_id,s.date_start,s.date,s.user_id,s.quantity,
                      s.debit,s.credit,s.balance,s.parent_id,l.product_id
            )
        """)
analytic_report()
