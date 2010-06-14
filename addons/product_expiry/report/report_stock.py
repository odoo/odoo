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

from osv import osv, fields
from tools.translate import _
import tools
from tools.sql import drop_view_if_exists

class stock_report_prodlots(osv.osv):
    _name = "stock.report.prodlots1"
    _description = "Stock report by production lots"
    _auto = False
    _columns = {
            'name': fields.float('Quantity', readonly=True),
            'location_id': fields.many2one('stock.location', 'Location', readonly=True, select=True),
            'product_id': fields.many2one('product.product', 'Product', readonly=True, select=True),
            'prodlot_id': fields.many2one('stock.production.lot', 'Production lot', readonly=True, select=True),
            'life_date': fields.date('End of Life Date',
            help='The date the lot may become dangerous and should not be consumed.'),
            'use_date': fields.date('Best before Date',
                help='The date the lot starts deteriorating without becoming dangerous.'),
            'removal_date': fields.date('Removal Date',
                help='The date the lot should be removed.'),
            'alert_date': fields.date('Alert Date'),

    }
    
    def init(self, cr):
        drop_view_if_exists(cr, 'stock_report_prodlots1')
        cr.execute("""
            create or replace view stock_report_prodlots1 as (
                    select max(id) as id,
                    location_id,
                    product_id,
                    prodlot_id,
                    life_date,
                    use_date, 
                    removal_date,
                    alert_date,
                    sum(qty) as name
                from (
                    select -max(sm.id) as id,
                        sm.location_id,
                        sm.product_id,
                        sm.prodlot_id,
                        spl.life_date,
                        spl.use_date, 
                        spl.removal_date,
                        spl.alert_date,
                        -sum(sm.product_qty /uo.factor) as qty
                    from stock_move as sm
                    left join stock_location sl
                        on (sl.id = sm.location_id)
                    left join stock_production_lot spl
                        on (sm.prodlot_id=spl.id)
                    left join product_uom uo
                        on (uo.id=sm.product_uom)
                    where state = 'done'
                    group by sm.location_id, sm.product_id, sm.product_uom, sm.prodlot_id,
                    spl.life_date,
                    spl.use_date, 
                    spl.removal_date,
                    spl.alert_date

                    union all
                    select max(sm.id) as id,
                        sm.location_dest_id as location_id,
                        sm.product_id,
                        sm.prodlot_id,
                        spl.life_date,
                        spl.use_date, 
                        spl.removal_date,
                        spl.alert_date,
                        sum(sm.product_qty /uo.factor) as qty
                    from stock_move as sm
                    left join stock_location sl
                        on (sl.id = sm.location_dest_id)
                    left join stock_production_lot spl
                        on (sm.prodlot_id=spl.id)
                    left join product_uom uo
                        on (uo.id=sm.product_uom)
                    where sm.state = 'done'
                    group by sm.location_dest_id, sm.product_id, sm.product_uom, sm.prodlot_id,
                    spl.life_date,
                    spl.use_date, 
                    spl.removal_date,
                    spl.alert_date

                ) as report
                group by location_id, product_id, prodlot_id, 
                    life_date,
                    use_date, 
                    removal_date,
                    alert_date
            )""")
        
    def unlink(self, cr, uid, ids, context={}):
        raise osv.except_osv(_('Error !'), _('You cannot delete any record!'))

        
stock_report_prodlots()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
