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

class account_account_report(osv.osv):
    _name = "account.account.report"
    _description = "Account Report"
    _auto = False
    _columns = {
        'name': fields.char('Name', size=128, readonly=True),
        'code': fields.char('Code', size=64, readonly=True),
        'type': fields.selection([
            ('receivable', 'Receivable'),
            ('payable', 'Payable'),
            ('view', 'View'),
            ('consolidation', 'Consolidation'),
            ('other', 'Others'),
            ('closed', 'Closed'),
        ], 'Internal Type', readonly=True),
      'company_id': fields.many2one('res.company', 'Company', required=True),
      'currency_mode': fields.selection([('current', 'At Date'), ('average', 'Average Rate')], 'Outgoing Currencies Rate',readonly=True),
      'user_type': fields.many2one('account.account.type', 'Account Type',readonly=True),
      'credit': fields.float('Credit', readonly=True),
      'debit': fields.float('Debit', readonly=True),
      'balance': fields.float('Balance', readonly=True)
    }
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'account_account_report')
        cr.execute("""
            create or replace view account_account_report as (
                select
                    min(a.id) as id,
                    a.name,
                    a.code,
                    a.type as type,
                    a.company_id as company_id,
                    a.currency_mode as currency_mode,
                    a.user_type as user_type,
                    sum(m.credit) as credit,
                    sum(m.debit) as debit,
                    (sum(m.credit)-sum(m.debit)) as balance
                from
                        account_account as a
                    left join
                        account_move_line as m
                    on m.account_id=a.id
                group by
                    a.name,
                    a.code,
                    a.type,
                    a.company_id,
                    a.currency_mode,
                    a.user_type,
                    m.account_id
            )
        """)
account_account_report()
