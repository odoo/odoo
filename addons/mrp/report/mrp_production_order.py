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
from osv import fields,osv
import tools


class mrp_production_order(osv.osv):
    _name = "mrp.production.order"
    _description = "Production Order Report"
    _auto = False
    _columns = {
        'name': fields.char('Year',size=64,required=False, readonly=True),
        'month':fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'), ('05','May'), ('06','June'),
                                  ('07','July'), ('08','August'), ('09','September'), ('10','October'), ('11','November'), ('12','December')],'Month',readonly=True),
        'reference': fields.char('Reference', size=64, required=True),
        'origin': fields.char('Source Document', size=64),
        'nbr': fields.integer('# of Orders', readonly=True),
        'product_id': fields.many2one('product.product', 'Product', required=True, domain=[('type','<>','service')]),
        'state': fields.selection([('draft','Draft'),('picking_except', 'Picking Exception'),('confirmed','Waiting Goods'),('ready','Ready to Produce'),('in_production','In Production'),('cancel','Cancelled'),('done','Done')],'State', readonly=True),
        'scheduled_date':fields.date('Scheduled Date'),
        'location_src_id': fields.many2one('stock.location', 'Raw Materials Location', required=True),
        'location_dest_id': fields.many2one('stock.location', 'Finished Products Location', required=True),


    }
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'mrp_production_order')
        cr.execute("""
            create or replace view mrp_production_order as (
                select
                    min(c.id) as id,
                    to_char(c.create_date, 'YYYY') as name,
                    to_char(c.create_date, 'MM') as month,
                    c.state,
                    c.product_id,
                    count(*) as nbr,
                    to_date(to_char(c.date_planned, 'dd-MM-YYYY'),'dd-MM-YYYY') as scheduled_date,
                    c.name as reference,
                    c.origin,
                    c.location_src_id,
                    c.location_dest_id
                from
                    mrp_production c
                group by to_char(c.create_date, 'YYYY'), to_char(c.create_date, 'MM'), c.state,c.product_id,to_date(to_char(c.date_planned, 'dd-MM-YYYY'),'dd-MM-YYYY'),c.name,c.location_src_id,c.location_dest_id,c.origin
            )""")
mrp_production_order()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

