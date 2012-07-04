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
    
    _columns = {
        'partner_id':fields.many2one('res.partner', 'Partner'),
        'last_reconciliation_date':fields.datetime('Last Reconciliation'),
        'latest_date' :fields.date('Latest Entry'),
#        'followup_date': fields.date('Latest Follow-up'),   
        'reconciliation_progress': fields.function(_rec_progress, string='Progress (%)',  type='float')

    }
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'account_move_partner_info')
        cr.execute("""
            create or replace view account_move_partner_info as (
                SELECT  p.id, p.id as partner_id, 
                max(p.last_reconciliation_date) as last_reconciliation_date,
                max(l.date) as latest_date
                FROM account_move_line as l INNER JOIN res_partner AS p ON (l.partner_id = p.id)
                group by p.id
                )
        """)
account_move_partner_info()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:



#SELECT  p.id as partner_id, 
#        max(p.last_reconciliation_date) as last_reconciliation_date,
#        max(l.date) as latest_date,
#        max(l.followup_date) as followup_date
#From account_move_line as l INNER JOIN res_partner AS p ON (l.partner_id = p.id)
#group by p.id