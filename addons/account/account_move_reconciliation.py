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
import time

import tools
from osv import fields,osv

class account_move_line(osv.osv):
    _inherit = "account.move.line"
    
    def get_unreconcile_entry(self, cr, uid, ids, context=None):
        return self.search(cr, uid, [('id', 'in', ids), ('reconcile_id', '=', False)], context=context)

account_move_line();


class account_move_reconciliation(osv.osv):
    _name = "account.move.reconciliation"
    _description = "All partner info related account move line"
    _auto = False

    def _get_to_reconcile(self, cr, uid, context=None):
        query= ''
        if context and context.get('account_type', False) == 'payable':
            query = 'AND p.supplier = True'

        cr.execute("""
                  SELECT p_id FROM (SELECT l.partner_id as p_id, SUM(l.debit) AS debit, SUM(l.credit) AS credit
                                    FROM account_move_line AS l LEFT JOIN account_account a ON (l.account_id = a.id)
                                                                LEFT JOIN res_partner p ON (p.id = l.partner_id)
                                    WHERE a.reconcile = 't'
                                    AND l.reconcile_id IS NULL
                                    AND  (%s >  to_char(p.last_reconciliation_date, 'YYYY-MM-DD') OR  p.last_reconciliation_date IS NULL )
                                    AND  l.state <> 'draft' """ +query + """
                                    GROUP BY l.partner_id) AS tmp
                              WHERE debit >= 0
                              AND credit >= 0
                """,(time.strftime('%Y-%m-%d'),)
        )
        return len(map(lambda x: x[0], cr.fetchall())) - 1

    def _get_today_reconciled(self, cr, uid, context=None):
        query= ''
        if context and context.get('account_type', False) == 'payable':
            query = 'AND p.supplier = True'

        cr.execute(
                """SELECT l.partner_id 
                FROM account_move_line AS l LEFT JOIN res_partner p ON (p.id = l.partner_id)
                WHERE l.reconcile_id IS NULL
                AND %s =  to_char(p.last_reconciliation_date, 'YYYY-MM-DD')
                AND l.state <> 'draft' """ +query + """
                GROUP BY l.partner_id """,(time.strftime('%Y-%m-%d'),)
        )
        return len(map(lambda x: x[0], cr.fetchall())) + 1
    
    def _rec_progress(self, cr, uid, ids, prop, unknow_none, context=None):
        res = {}
        to_reconcile = self._get_to_reconcile(cr, uid, context)
        today_reconcile = self._get_today_reconciled(cr, uid, context)
        if to_reconcile < 0:
            reconciliation_progress = 100
        else:
            reconciliation_progress = (100 / (float( to_reconcile + today_reconcile) or 1.0)) * today_reconcile
        for id in ids:
            res[id] = reconciliation_progress
        return res
#    
    def get_partners(self, cr, uid, context=None):
        query= ''
        if context and context.get('account_type', False) == 'payable':
            query = 'AND p.supplier = True'
        cr.execute(
             """
             SELECT p.id
             FROM res_partner p
             RIGHT JOIN (
                SELECT l.partner_id AS partner_id, SUM(l.debit) AS debit, SUM(l.credit) AS credit
                FROM account_move_line l
                LEFT JOIN account_account a ON (a.id = l.account_id)
                    LEFT JOIN res_partner p ON (l.partner_id = p.id)
                    WHERE a.reconcile IS TRUE
                    AND l.reconcile_id IS NULL
                    AND (p.last_reconciliation_date IS NULL OR l.date > p.last_reconciliation_date)
                    AND l.state <> 'draft' """ +query + """
                    GROUP BY l.partner_id
                ) AS s ON (p.id = s.partner_id)
                ORDER BY p.last_reconciliation_date""")
        return cr.fetchall()
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        ids = super(account_move_reconciliation, self).search(cr, uid, args, offset, limit, order, context, count)
        res = self.get_partners(cr, uid, context=context)
        return map(lambda x: x[0], res)
    
    def skip_partner(self, cr, uid, ids, context):
        self.pool.get('res.partner').write(cr, uid, ids ,{'last_reconciliation_date':time.strftime("%Y-%m-%d")}, context)
            
    _columns = {
        'partner_id':fields.many2one('res.partner', 'Partner'),
        'last_reconciliation_date':fields.related('partner_id', 'last_reconciliation_date' ,type='datetime', relation='res.partner', string='Last Reconciliation'),
        'latest_date' :fields.date('Latest Entry'),
        'reconciliation_progress': fields.function(_rec_progress, string='Progress (%)',  type='float'),
    }
    
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'account_move_reconciliation')
        cr.execute("""
            CREATE or REPLACE VIEW account_move_reconciliation as (
                SELECT  move_line.partner_id as id, move_line.partner_id, 
                MAX(move_line.date) as latest_date
                FROM account_move_line as move_line where move_line.state <> 'draft'
                GROUP by move_line.partner_id
                )
        """)
account_move_reconciliation()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: