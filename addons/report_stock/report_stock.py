# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2008 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id$
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

from osv import osv, fields

class report_stock_prodlots(osv.osv):
    _name = "report.stock.prodlots"
    _description = "Stock report by production lots"
    _auto = False
    _columns = {
            'name': fields.float('Quantity', readonly=True),
            'location_id': fields.many2one('stock.location', 'Location', readonly=True, select=True),
            'product_id': fields.many2one('product.product', 'Product', readonly=True, select=True),
            'prodlot_id': fields.many2one('stock.production.lot', 'Production lot', readonly=True, select=True),
    }
    def init(self, cr):
        cr.execute("""
            create or replace view report_stock_prodlots as (
                select max(id) as id,
                    location_id,
                    product_id,
                    prodlot_id,
                    sum(qty) as name
                from (
                    select -max(sm.id) as id,
                        sm.location_id,
                        sm.product_id,
                        sm.prodlot_id,
                        -sum(sm.product_qty) as qty
                    from stock_move as sm
                    left join stock_location sl
                        on (sl.id = sm.location_id)
                    where state = 'done'
                        and sl.usage = 'internal'
                    group by sm.location_id, sm.product_id, sm.product_uom, sm.prodlot_id
                    union all
                    select max(sm.id) as id,
                        sm.location_dest_id as location_id,
                        sm.product_id,
                        sm.prodlot_id,
                        sum(sm.product_qty) as qty
                    from stock_move as sm
                    left join stock_location sl
                        on (sl.id = sm.location_dest_id)
                    where sm.state = 'done'
                        and sl.usage = 'internal'
                    group by sm.location_dest_id, sm.product_id, sm.product_uom, sm.prodlot_id
                ) as report
                group by location_id, product_id, prodlot_id
            )""")
report_stock_prodlots()


class report_inventory_latest(osv.osv):
    _name = "report.inventory.latest"
    _description = "Latest inventories by product."
    _auto = False
    _columns = {
            'name':  fields.datetime('Latest Date',readonly=True),
            'product': fields.many2one('product.product', 'Product', readonly=True, select=True),
            'inventory': fields.many2one('stock.inventory', 'Inventory Name', readonly=True, select=True),
            'qty': fields.float('Quantity', readonly=True, select=True),
            'uom' : fields.many2one('product.uom', 'UoM', readonly=True),
#            'date' : fields.datetime('Latest Date',readonly=True),
    }
    _order = 'name desc'
    def init(self, cr):
        cr.execute("""
            create or replace view report_inventory_latest as (
            select  max(l.id) as id,
            l.product_id as product, 
            l.product_qty as qty, 
            l.product_uom as uom ,
            min(l.inventory_id) as inventory, 
            i.date as name 
            from stock_inventory_line l 
                join stock_inventory i on (l.inventory_id=i.id)
            group by l.product_uom,l.product_qty,l.product_id,i.date
            
            )""")
report_inventory_latest()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

