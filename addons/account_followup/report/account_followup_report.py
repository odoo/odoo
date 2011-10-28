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

class account_followup_stat(osv.osv):
    _name = "account_followup.stat"
    _description = "Followup Statistics"
    _rec_name = 'partner_id'
    _auto = False
    _columns = {
        'partner_id': fields.many2one('res.partner', 'Partner', readonly=True),
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
                args.remove(arg)
        return super(account_followup_stat, self).search(cr, uid, args=args, offset=offset, limit=limit, order=order,
            context=context, count=count)

    def read_group(self, cr, uid, domain, *args, **kwargs):
        for arg in domain:
            if arg[0] == 'period_id' and arg[2] == 'current_year':
                current_year = self.pool.get('account.fiscalyear').find(cr, uid)
                ids = self.pool.get('account.fiscalyear').read(cr, uid, [current_year], ['period_ids'])[0]['period_ids']
                domain.append(['period_id','in',ids])
                domain.remove(arg)
        return super(account_followup_stat, self).read_group(cr, uid, domain, *args, **kwargs)

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'account_followup_stat')
        cr.execute("""
            create or replace view account_followup_stat as (
                SELECT
                    l.partner_id as id,
                    l.partner_id AS partner_id,
                    min(l.date) AS date_move,
                    max(l.date) AS date_move_last,
                    max(l.followup_date) AS date_followup,
                    max(l.followup_line_id) AS followup_id,
                    sum(l.debit) AS debit,
                    sum(l.credit) AS credit,
                    sum(l.debit - l.credit) AS balance,
                    l.company_id AS company_id,
                    l.blocked as blocked,
                    l.period_id AS period_id
                FROM
                    account_move_line l
                    LEFT JOIN account_account a ON (l.account_id = a.id)
                WHERE
                    a.active AND
                    a.type = 'receivable' AND
                    l.reconcile_id is NULL AND
                    l.partner_id IS NOT NULL
                GROUP BY
                    l.id, l.partner_id, l.company_id, l.blocked, l.period_id
            )""")
account_followup_stat()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
