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

class account_entries_report(osv.osv):
    _name = "account.entries.report"
    _description = "Journal Items Analysis"
    _auto = False
    _rec_name = 'date'
    _columns = {
        'date': fields.date('Effective Date', readonly=True),
        'date_created': fields.date('Date Created', readonly=True),
        'date_maturity': fields.date('Date Maturity', readonly=True),
        'ref': fields.char('Reference', size=64, readonly=True),
        'nbr':fields.integer('# of Items', readonly=True),
        'debit':fields.float('Debit', readonly=True),
        'credit':fields.float('Credit', readonly=True),
        'balance': fields.float('Balance', readonly=True),
        'day': fields.char('Day', size=128, readonly=True),
        'year': fields.char('Year', size=4, readonly=True),
        'date': fields.date('Date', size=128, readonly=True),
        'month':fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'),
            ('05','May'), ('06','June'), ('07','July'), ('08','August'), ('09','September'),
            ('10','October'), ('11','November'), ('12','December')], 'Month', readonly=True),
        'period_id': fields.many2one('account.period', 'Period', readonly=True),
        'account_id': fields.many2one('account.account', 'Account', readonly=True),
        'journal_id': fields.many2one('account.journal', 'Journal', readonly=True),
        'fiscalyear_id': fields.many2one('account.fiscalyear', 'Fiscal Year', readonly=True),
        'product_id': fields.many2one('product.product', 'Product', readonly=True),
        'state': fields.selection([('draft','Draft'), ('posted','Posted')], 'State', readonly=True,
                                  help='When new account move is created the state will be \'Draft\'. When all the payments are done it will be in \'Posted\' state.'),
        'state_2': fields.selection([('draft','Draft'), ('valid','Valid')], 'State of Move Line', readonly=True,
                                  help='When new move line is created the state will be \'Draft\'.\n* When all the payments are done it will be in \'Valid\' state.'),
        'reconcile_id': fields.many2one('account.move.reconcile', readonly=True),
        'partner_id': fields.many2one('res.partner','Partner', readonly=True),
        'analytic_account_id' : fields.many2one('account.analytic.account', 'Analytic Account', readonly=True),
        'quantity': fields.float('Products Quantity', digits=(16,2), readonly=True),
        'user_type': fields.many2one('account.account.type', 'Account Type', readonly=True),
        'type': fields.selection([
            ('receivable', 'Receivable'),
            ('payable', 'Payable'),
            ('view', 'View'),
            ('consolidation', 'Consolidation'),
            ('other', 'Others'),
            ('closed', 'Closed'),
        ], 'Internal Type', readonly=True, help="This type is used to differentiate types with "\
            "special effects in OpenERP: view can not have entries, consolidation are accounts that "\
            "can have children accounts for multi-company consolidations, payable/receivable are for "\
            "partners accounts (for debit/credit computations), closed for depreciated accounts."),
        'company_id': fields.many2one('res.company', 'Company', readonly=True),
    }
    _order = 'date desc'
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'account_entries_report')
        cr.execute("""
            create or replace view account_entries_report as (
            select
                l.id as id,
                am.date as date,
                l.date_maturity as date_maturity,
                l.date_created as date_created,
                am.ref as ref,
                am.state as state,
                l.state as state_2,
                l.reconcile_id as reconcile_id,
                to_char(am.date, 'YYYY') as year,
                to_char(am.date, 'MM') as month,
                to_char(am.date, 'YYYY-MM-DD') as day,
                l.partner_id as partner_id,
                l.product_id as product_id,
                am.company_id as company_id,
                am.journal_id as journal_id,
                p.fiscalyear_id as fiscalyear_id,
                am.period_id as period_id,
                l.account_id as account_id,
                l.analytic_account_id as analytic_account_id,
                a.type as type,
                a.user_type as user_type,
                1 as nbr,
                l.quantity as quantity,
                l.debit as debit,
                l.credit as credit,
                l.debit-l.credit as balance
            from
                account_move_line l
                left join account_account a on (l.account_id = a.id)
                left join account_move am on (am.id=l.move_id)
                left join account_period p on (am.period_id=p.id)
                where l.state != 'draft'
            )
        """)
account_entries_report()
