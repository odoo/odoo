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
    _description = "partner info related account move line"
    _auto = False
    _order = 'last_reconciliation_date'

    def search(self, cr, uid, args, offset=0, limit=None, order=None,
            context=None, count=False):
        if context is None:
            context = {}
        account_type = context.get('account_type', False)
        if account_type == "receivable":
            args += [('customer','=', True)]
        if account_type == "payable":
            args += [('supplier','=', True)]
        return super(account_move_reconciliation, self).search(cr, uid, args, offset, limit,
                order, context=context, count=count)

    def _rec_progress(self, cr, uid, ids, prop, unknow_none, context=None):
        res = {}
        to_reconcile_ids = self.search(cr, uid, [], context=context)
        to_reconcile = to_reconcile_ids and len(to_reconcile_ids) or 0
        today_reconcile_ids = self.search(cr, uid, [('last_reconciliation_date','=',time.strftime('%Y-%m-%d'))], context=context)
        today_reconcile = today_reconcile_ids and len(today_reconcile_ids) or 0
        if to_reconcile < 0:
            reconciliation_progress = 100
        else:
            reconciliation_progress = (100 / (float( to_reconcile + today_reconcile) or 1.0)) * today_reconcile
        for id in ids:
            res[id] = reconciliation_progress
        return res
  
        
    def skip_partner(self, cr, uid, ids, context):
        self.pool.get('res.partner').write(cr, uid, ids ,{'last_reconciliation_date':time.strftime("%Y-%m-%d")}, context)
            
    _columns = {
        'partner_id':fields.many2one('res.partner', 'Partner'),
        'last_reconciliation_date':fields.related('partner_id', 'last_reconciliation_date' ,type='datetime', relation='res.partner', string='Last Reconciliation'),
        'latest_date' :fields.date('Latest Entry'),
        'supplier': fields.related('partner_id', 'supplier' ,type='boolean', string='Supplier'),
        'customer': fields.related('partner_id', 'customer' ,type='boolean', string='Customer'),
        'reconciliation_progress': fields.function(_rec_progress, string='Progress (%)',  type='float'),
    }
    
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'account_move_reconciliation')
        cr.execute("""
            CREATE or REPLACE VIEW account_move_reconciliation as (
                SELECT move_line.partner_id AS id, move_line.partner_id AS partner_id, SUM(move_line.debit) AS debit, SUM(move_line.credit) AS credit, 
                        MAX(move_line.date) AS latest_date,
                        MIN(partner.last_reconciliation_date) AS last_reconciliation_date
                FROM account_move_line move_line
                LEFT JOIN account_account a ON (a.id = move_line.account_id)
                RIGHT JOIN res_partner partner ON (move_line.partner_id = partner.id)
                WHERE a.reconcile IS TRUE
                    AND move_line.reconcile_id IS NULL
                    AND (partner.last_reconciliation_date IS NULL OR move_line.date > partner.last_reconciliation_date)
                    AND move_line.state <> 'draft'
                GROUP BY move_line.partner_id
             )
        """)
account_move_reconciliation()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
