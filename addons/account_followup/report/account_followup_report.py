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

from osv import fields, osv
import tools

def _code_get(self, cr, uid, context={}):
    acc_type_obj = self.pool.get('account.account.type')
    ids = acc_type_obj.search(cr, uid, [])
    res = acc_type_obj.read(cr, uid, ids, ['code', 'name'], context)
    return [(r['code'], r['name']) for r in res]


class account_followup_stat(osv.osv):
    _name = "account_followup.stat"
    _description = "Followup Statistics"
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
        'company_id': fields.many2one('res.company', 'Company', readonly=True),
        'blocked': fields.boolean('Blocked', readonly=True),
        'period_id': fields.many2one('account.period', 'Period', readonly=True),

    }
    _order = 'date_move'

    def search(self, cr, uid, args, offset=0, limit=None, order=None,
                context=None, count=False):
            for arg in args:
                if arg[0] == 'period_id' and arg[2] == 'current_year':
                    current_year = self.pool.get('account.fiscalyear').find(cr, uid)
                    ids = self.pool.get('account.fiscalyear').read(cr, uid, [current_year], ['period_ids'])[0]['period_ids']
                    args.append(['period_id','in',ids])
            for a in [['period_id','in','current_year']]:
                temp_args = tuple(a)
                if temp_args in args:
                    args.remove(temp_args)
            return super(account_followup_stat, self).search(cr, uid, args=args, offset=offset, limit=limit, order=order,
                context=context, count=count)

    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None):
            todel=[]
            for arg in domain:
                if arg[0] == 'period_id' and arg[2] == 'current_year':
                    current_year = self.pool.get('account.fiscalyear').find(cr, uid)
                    ids = self.pool.get('account.fiscalyear').read(cr, uid, [current_year], ['period_ids'])[0]['period_ids']
                    domain.append(['period_id','in',ids])
                    todel.append(arg)
            for a in [['period_id','in','current_year']]:
                temp_args = tuple(a)
                if temp_args in domain:
                    domain.remove(temp_args)
            return super(account_followup_stat, self).read_group(cr, uid, domain, fields, groupby, offset, limit, context)

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'account_followup_stat')
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
                    a.type as account_type,
                    l.company_id as company_id,
                    l.blocked,
                    am.period_id as period_id
                from
                    account_move_line l
                    LEFT JOIN account_account a ON (l.account_id=a.id)
                    LEFT JOIN res_company c ON (l.company_id=c.id)
                    LEFT JOIN account_move am ON (am.id=l.move_id)
                    LEFT JOIN account_period p ON (am.period_id=p.id)
                where
                    l.reconcile_id is NULL and
                    a.type = 'receivable'
                    and a.active and
                    l.partner_id is not NULL and
                    l.company_id is not NULL and
                    l.blocked is not NULL
                    group by
                    l.partner_id, a.type, l.company_id,l.blocked,am.period_id
            )""")
account_followup_stat()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: