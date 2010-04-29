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
    _description = "Entries"
    _auto = False
    _rec_name = 'date'
    _columns = {
        'date': fields.date('Date', readonly=True),
        'nbr':fields.integer('# of Entries', readonly=True),
        'nbl':fields.integer('# of Lines', readonly=True),
        'amount': fields.float('Amount',readonly=True),
        'year': fields.char('Year', size=4, readonly=True),
        'day': fields.char('Day', size=128, readonly=True),
        'month':fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'),
            ('05','May'), ('06','June'), ('07','July'), ('08','August'), ('09','September'),
            ('10','October'), ('11','November'), ('12','December')], 'Month',readonly=True),
        'ref': fields.char('Reference', size=64,readonly=True),
        'period_id': fields.many2one('account.period', 'Period', readonly=True),
        'journal_id': fields.many2one('account.journal', 'Journal', readonly=True),
        'state': fields.selection([('draft','Draft'), ('posted','Posted')], 'State',readonly=True,
                                  help='When new account move is created the state will be \'Draft\'. When all the payments are done it will be in \'Posted\' state.'),
        'partner_id': fields.many2one('res.partner','Partner', readonly=True),
        'type': fields.selection([
            ('pay_voucher','Cash Payment'),
            ('bank_pay_voucher','Bank Payment'),
            ('rec_voucher','Cash Receipt'),
            ('bank_rec_voucher','Bank Receipt'),
            ('cont_voucher','Contra'),
            ('journal_sale_vou','Journal Sale'),
            ('journal_pur_voucher','Journal Purchase'),
            ('journal_voucher','Journal Voucher'),
        ],'Type',readonly=True),
        'company_id': fields.many2one('res.company', 'Company', readonly=True),
    }
    _order = 'date desc'

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'account_entries_report')
        cr.execute("""
            create or replace view account_entries_report as (
              select
                   min(l.id) as id,
                   am.ref as ref,
                   am.state as state,
                   am.date as date,
                   count(l.id) as nbr,
                   count(distinct am.id) as nbl,
                   l.debit as amount,
                   to_char(am.date, 'YYYY') as year,
                   to_char(am.date, 'MM') as month,
                   to_char(am.date, 'YYYY-MM-DD') as day,
                   am.company_id as company_id,
                   am.journal_id as journal_id,
                   am.period_id as period_id,
                   l.partner_id as partner_id,
                   am.type as type
             from
             account_move_line l
                 left join
             account_move am on (am.id=l.move_id)
                group by am.ref,
                am.state,
                am.date,
                am.company_id,
                am.journal_id,
                am.period_id,
                am.type,
                l.partner_id,
                l.debit
            )
        """)

account_entries_report()
