# -*- coding: utf-8 -*-
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

def _code_get(self, cr, uid, context={}):
    acc_type_obj = self.pool.get('account.account.type')
    ids = acc_type_obj.search(cr, uid, [])
    res = acc_type_obj.read(cr, uid, ids, ['code', 'name'], context)
    return [(r['code'], r['name']) for r in res]


class account_followup_stat(osv.osv):
    _name = "account_followup.stat"
    _description = "Followup statistics"
    _auto = False
    _columns = {
        'name': fields.many2one('res.partner', 'Partner', readonly=True),
        'account_type': fields.selection(_code_get, 'Account Type', readonly=True),
        'date_move':fields.date('First move', readonly=True),
        'date_move_last':fields.date('Last move', readonly=True),
        'date_followup':fields.date('Latest followup', readonly=True),
        'followup_id': fields.many2one('account_followup.followup.line',
            'Follow Ups', readonly=True, ondelete="cascade"),
        'balance':fields.float('Balance', readonly=True),
        'debit':fields.float('Debit', readonly=True),
        'credit':fields.float('Credit', readonly=True),
    }
    _order = 'date_move'
    def init(self, cr):
        cr.execute("""
            create or replace view account_followup_stat as (
                select
                    l.partner_id as id,
                    l.partner_id as name,
                    min(l.date) as date_move,
                    max(l.date) as date_move_last,
                    max(l.followup_date) as date_followup,
                    max(l.followup_line_id) as followup_id,
                    sum(l.debit) as debit,
                    sum(l.credit) as credit,
                    sum(l.debit - l.credit) as balance,
                    a.type as account_type
                from
                    account_move_line l
                left join
                    account_account a on (l.account_id=a.id)
                where
                    l.reconcile_id is NULL and
                    a.type = 'receivable'
                    and a.active and
                    l.partner_id is not null
                group by
                    l.partner_id, a.type
            )""")
account_followup_stat()




# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

