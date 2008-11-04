# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import fields,osv

def _code_get(self, cr, uid, context={}):
    acc_type_obj = self.pool.get('account.account.type')
    ids = acc_type_obj.search(cr, uid, [])
    res = acc_type_obj.read(cr, uid, ids, ['code', 'name'], context)
    return [(r['code'], r['name']) for r in res]


class report_account_receivable(osv.osv):
    _name = "report.account.receivable"
    _description = "Receivable accounts"
    _auto = False
    _columns = {
        'name': fields.char('Week of Year', size=7, readonly=True),
        'type': fields.selection(_code_get, 'Account Type', required=True),
        'balance':fields.float('Balance', readonly=True),
        'debit':fields.float('Debit', readonly=True),
        'credit':fields.float('Credit', readonly=True),
    }
    _order = 'name desc'
    def init(self, cr):
        cr.execute("""
            create or replace view report_account_receivable as (
                select
                    min(l.id) as id,
                    to_char(date,'YYYY:IW') as name,
                    sum(l.debit-l.credit) as balance,
                    sum(l.debit) as debit,
                    sum(l.credit) as credit,
                    a.type
                from
                    account_move_line l
                left join
                    account_account a on (l.account_id=a.id)
                where
                    l.state <> 'draft'
                group by
                    to_char(date,'YYYY:IW'), a.type
            )""")
report_account_receivable()

                    #a.type in ('receivable','payable')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

