# -*- encoding: utf-8 -*-
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

class asset_asset_report(osv.osv):
    _name = "asset.asset.report"
    _description = "Assets Analysis"
    _auto = False
    _columns = {
        'name': fields.char('Year', size=16, required=False, readonly=True),
        'month':fields.selection([('01', 'January'), ('02', 'February'), \
                                  ('03', 'March'), ('04', 'April'),\
                                  ('05', 'May'), ('06', 'June'), \
                                  ('07', 'July'), ('08', 'August'),\
                                  ('09', 'September'), ('10', 'October'),\
                                  ('11', 'November'), ('12', 'December')], 'Month', readonly=True),
        'day': fields.char('Day', size=16, readonly=True),
        'purchase_date': fields.date('Asset Date', required=True),
        'asset_id': fields.many2one('account.asset.asset', string='Asset', readonly=True),
        'asset_category_id': fields.many2one('account.asset.category',string='Asset category'),
        'partner_id': fields.many2one('res.partner', 'Partner', readonly=True),
        'state': fields.selection([('draft','Draft'),('open','Running'),('close','Close')], 'state', required=True, readonly=True),
        'remaining_value': fields.float('Amount to Depreciate', required=True, readonly=True),
        'depreciated_value': fields.float('Amount Already Depreciated', required=True, readonly=True),
        'move_check': fields.boolean('Posted', readonly=True),
        'nbr': fields.integer('# of Depreciation Lines', readonly=True),
        'company_id': fields.many2one('res.company', 'Company', readonly=True),
    }
    
    def init(self, cr):
    	tools.drop_view_if_exists(cr, 'asset_asset_report')
     	cr.execute("""
    	    create or replace view asset_asset_report as (
                select 
                    min(dl.id) as id,
                    to_char(a.purchase_date, 'YYYY') as name,
                    to_char(a.purchase_date, 'MM') as month,
                    to_char(a.purchase_date, 'YYYY-MM-DD') as day,
                    a.purchase_date as purchase_date,
                    dl.amount as remaining_value,
                    dl.move_check as move_check,
                    dl.asset_id as asset_id,
                    a.category_id as asset_category_id,
                    a.partner_id as partner_id,
                    a.state as state,
                    count(dl.*) as nbr,
                    a.company_id as company_id
                from
                    account_asset_depreciation_line dl
                    left join account_asset_asset a on (dl.asset_id=a.id)
                group by 
                    dl.asset_id, dl.move_check, a.state, 
                    a.category_id, a.partner_id, a.purchase_date, dl.amount,
                    a.company_id, a.purchase_value, a.salvage_value
        )""")
	
asset_asset_report()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
