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

#4  remove get_unreconcile_entry method mange it with domain

class account_move_line(osv.osv):
    _inherit = "account.move.line"
    
    def get_unreconcile_entry(self, cr, uid, ids, context=None):
        records = self.read(cr, uid, ids, ['reconcile_id'])
        res = []
        for record in records:
            if not record.get('reconcile_id'):
                res.append(record['id'])
        return res

account_move_line();


class account_move_reconciliation(osv.osv):
    _name = "account.move.reconciliation"
    _description = "All partner info related account move line"
    _auto = False
    
    def _rec_progress(self, cr, uid, ids, prop, unknow_none, context=None):
        active_ids = context.get('active_ids', [])
        res = 0
        if active_ids:
            total_records = self.search(cr, uid, [('id','in',active_ids)])
            total_unreconcile = 0
            for record in self.read(cr, uid, total_records, ['unreconcile_count'], context=context):
                if record['unreconcile_count'] > 0:
                    total_unreconcile += 1
            res =  float(len(total_records) - total_unreconcile)/len(total_records) * 100
        res_all = {}
        for id in ids:
            res_all[id] = res
        return res_all
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        obj_move_line = self.pool.get('account.move.line')
        ids = super(account_move_reconciliation, self).search(cr, uid, args, offset, limit, order, context, count)
        res_ids = []
        for id in ids:
            last_reconciliation_date = self.browse(cr, uid, id, context=context).last_reconciliation_date
            if not last_reconciliation_date:
                res_ids.append(id)
            else:
                move_ids = obj_move_line.search(cr, uid, [('partner_id','=', id),('create_date','>', last_reconciliation_date)])
                if move_ids:
                    res_ids.append(id)
        return res_ids
    
    def skip_partner(self, cr, uid, ids, context):
        res_partner = self.pool.get('res.partner')
        for partner in self.browse(cr, uid, ids, context=context):
            res_partner.write(cr, uid, [partner.id] ,{'last_reconciliation_date':time.strftime("%Y-%m-%d %H:%M:%S")})
            
            
    _columns = {
        'partner_id':fields.many2one('res.partner', 'Partner'),
        'last_reconciliation_date':fields.related('partner_id', 'last_reconciliation_date' ,type='datetime', relation='res.partner', string='Last Reconciliation'),
        'latest_date' :fields.date('Latest Entry'),
        'reconciliation_progress': fields.function(_rec_progress, string='Progress (%)',  type='float'),
        'unreconcile_count':fields.integer('Unreconcile Count'),
    }
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'account_move_reconciliation')
        cr.execute("""
            CREATE or REPLACE VIEW account_move_reconciliation as (
                SELECT  move_line.partner_id as id, move_line.partner_id, 
                MAX(move_line.date) as latest_date,
                (select count(unreconcile.id) from account_move_line as unreconcile where unreconcile.reconcile_id is null and unreconcile.partner_id = move_line.partner_id) as unreconcile_count
                FROM account_move_line as move_line where move_line.state <> 'draft'
                GROUP by move_line.partner_id
                )
        """)
account_move_reconciliation()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: