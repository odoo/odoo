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

from openerp import api, fields, models
from openerp import tools


class account_followup_stat(models.Model):
    _name = "account_followup.stat"
    _description = "Follow-up Statistics"
    _rec_name = 'partner_id'
    _auto = False

    partner_id = fields.Many2one('res.partner', 'Partner', readonly=True)
    date_move = fields.Date('First move', readonly=True)
    date_move_last = fields.Date('Last move', readonly=True)
    date_followup = fields.Date('Latest followup', readonly=True)
    followup_id = fields.Many2one('account_followup.followup.line', 'Follow Ups', readonly=True, ondelete="cascade")
    balance = fields.Float('Balance', readonly=True)
    debit = fields.Float('Debit', readonly=True)
    credit = fields.Float('Credit', readonly=True)
    company_id = fields.Many2one('res.company', 'Company', readonly=True)
    blocked = fields.Boolean('Blocked', readonly=True)
    date = fields.Date('Account Date', readonly=True)

    _order = 'date_move'

    # def search(self, args, offset=0, limit=None, order=None, count=False):
    #     for arg in args:
    #         if arg[0] == 'date' and arg[2] == 'current_year':
    #             current_year = self.pool.get('account.fiscalyear').find(cr, uid)
    #             # TODO account.period is now removed
    #             # ids = self.pool.get('account.fiscalyear').read(cr, uid, [current_year], ['period_ids'])[0]['period_ids']
    #             # args.append(['period_id','in',ids])
    #             args.remove(arg)
    #     return super(account_followup_stat, self).search(cr, uid, args=args, offset=offset, limit=limit, order=order,
    #         context=context, count=count)

    # def read_group(self, cr, uid, domain, *args, **kwargs):
    #     for arg in domain:
    #         if arg[0] == 'date' and arg[2] == 'current_year':
    #             current_year = self.pool.get('account.fiscalyear').find(cr, uid)
    #             # TODO account.period is now removed
    #             # ids = self.pool.get('account.fiscalyear').read(cr, uid, [current_year], ['period_ids'])[0]['period_ids']
    #             # domain.append(['period_id','in',ids])
    #             domain.remove(arg)
    #     return super(account_followup_stat, self).read_group(cr, uid, domain, *args, **kwargs)

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'account_followup_stat')
        cr.execute("""
            create or replace view account_followup_stat as (
                SELECT
                    l.id as id,
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
                    l.date AS date
                FROM
                    account_move_line l
                    LEFT JOIN account_account a ON (l.account_id = a.id)
                    LEFT JOIN account_account_type act ON (a.user_type = act.id)
                WHERE
                    a.deprecated='f' AND
                    act.type = 'receivable' AND
                    l.reconciled is FALSE AND
                    l.partner_id IS NOT NULL
                GROUP BY
                    l.id, l.partner_id, l.company_id, l.blocked, l.date
            )""")
