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

class res_partner(osv.osv):
    _inherit = 'res.partner'
    _columns = {
        'partner_move_count': fields.integer('Partner move line count')
    }
res_partner()

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


class account_move_partner_info(osv.osv):
    _name = "account.move.partner.info"
    _description = "All partner info related account move line"
    _auto = False
    
    def _rec_progress(self, cr, uid, ids, prop, unknow_none, context=None):
        res = 0
        cr.execute("""SELECT partner_id, reconcile_id 
                   FROM account_move_line WHERE state <> 'draft' 
                   GROUP BY partner_id, reconcile_id""")
        result = cr.fetchall()
        partner_total = len(result)
        partner_reconcile = len([ (x,y) for x, y in result if y == None  ])
        if partner_total:
            res = float(partner_total- partner_reconcile)/partner_total * 100
        
        res_all = {}
        for id in ids:
            res_all[id] = res
        return res_all
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        ids = super(account_move_partner_info, self).search(cr, uid, args, offset, limit, order, context, count)
        res = []
        for l in self.browse(cr, uid, ids, context=context):
            if (not  l.partner_move_count) or (l.move_lines_count >l.partner_move_count):
                res.append(l.id)
        return res
    
    _columns = {
        'partner_id':fields.many2one('res.partner', 'Partner'),
        'last_reconciliation_date':fields.datetime('Last Reconciliation'),
        'latest_date' :fields.date('Latest Entry'),
        'reconciliation_progress': fields.function(_rec_progress, string='Progress (%)',  type='float'),
        'move_lines_count':fields.integer('Move Count'),
        'partner_move_count':fields.integer('Partner move line count'),
    }
    def skip_partner(self, cr, uid, ids, context):
        res_partner = self.pool.get('res.partner')
        for line in self.browse(cr, uid, ids, context=context):
            res_partner.write(cr, uid, [line.id] ,{'partner_move_count':line.move_lines_count})
            
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'account_move_partner_info')
        cr.execute("""
            create or replace view account_move_partner_info as (
                SELECT  p.id, p.id as partner_id, 
                max(p.last_reconciliation_date) as last_reconciliation_date,
                max(l.date) as latest_date, 
                count(l.id)  as move_lines_count,
                max(p.partner_move_count) as partner_move_count    
                FROM account_move_line as l INNER JOIN res_partner AS p ON (l.partner_id = p.id)
                group by p.id
                )
        """)
account_move_partner_info()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: