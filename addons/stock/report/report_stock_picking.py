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

class report_stock_picking(osv.osv):
    _name = "report.stock.picking"
    _description = "Stock Picking Report"
    _auto = False
    _columns = {
        'year': fields.char('Year',size=64,required=False, readonly=True),
        'month':fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'), ('05','May'), ('06','June'),
                                  ('07','July'), ('08','August'), ('09','September'), ('10','October'), ('11','November'), ('12','December')],'Month',readonly=True),
        'day': fields.char('Day', size=128, readonly=True),
        'nbr': fields.integer('# of Lines', readonly=True),
        'nbp': fields.integer('# of Picking', readonly=True),
        'partner_id':fields.many2one('res.partner', 'Partner', readonly=True),
        'product_qty': fields.float('# of Products', readonly=True),
        'product_uos_qty': fields.float('# of Products', readonly=True),
        'product_id': fields.many2one('product.product', 'Product', readonly=True),
        'date': fields.date('Date', readonly=True),
        'avg_days_to_deliver': fields.float('Avg Days to Deliver', digits=(16,2), readonly=True, group_operator="avg",
                                       help="Number of  Avg Days to deliver"),
        'state': fields.selection([('draft', 'Draft'),('auto', 'Waiting'),('confirmed', 'Confirmed'),('assigned', 'Available'),('done', 'Done'),('cancel', 'Cancelled')], 'State'),
        'type': fields.selection([('out', 'Sending Goods'), ('in', 'Getting Goods'), ('internal', 'Internal'), ('delivery', 'Delivery')], 'Shipping Type', required=True),
        'company_id': fields.many2one('res.company', 'Company', readonly=True),
        'invoice_state': fields.selection([
            ("invoiced", "Invoiced"),
            ("2binvoiced", "To Be Invoiced"),
            ("none", "Not from Picking")], "Invoice Status",readonly=True),
        'min_date': fields.date('Expected Date',help="Expected date for Picking. Default it takes current date"),
        'order_date': fields.date('Order Date', help="Date of Order"),
        'date_done': fields.date('Date Done', help="Date of completion"),
        'location_id': fields.many2one('stock.location', 'Source Location', help="Sets a location if you produce at a fixed location. This can be a partner location if you subcontract the manufacturing operations."),
        'location_dest_id': fields.many2one('stock.location', 'Dest. Location', help="Location where the system will stock the finished products."),
        'max_date': fields.date('Max.Expected Date'),
        'product_uos': fields.many2one('product.uom', 'Product UOS'),
        'product_uom': fields.many2one('product.uom', 'Product UOM'),
    }
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_stock_picking')
        cr.execute("""
            create or replace view report_stock_picking as (
                select
                    min(sm.id) as id,
                    date_trunc('day',sp.min_date) as min_date,
                    date_trunc('day',sp.date) as order_date,
                    date_trunc('day',sp.date_done) as date_done,
                    date_trunc('day',sp.max_date) as max_date,
                    to_char(sp.create_date, 'YYYY') as year,
                    to_char(sp.create_date, 'MM') as month,
                    to_char(sp.create_date, 'YYYY-MM-DD') as day,
                    sp.address_id as partner_id,
                    to_date(to_char(sp.create_date, 'MM-dd-YYYY'),'MM-dd-YYYY') as date,
                    count(sm.id) as nbr,
                    count(distinct sp.id) as nbp,
                    sum(sm.product_qty) as product_qty,
                    sum(sm.product_uos_qty) as product_uos_qty,
                    sm.product_id as product_id,
                    sm.location_dest_id as location_dest_id,
                    sm.location_id as location_id,
                    sp.type,
                    sm.product_uos,
                    sm.product_uom,
                    sp.invoice_state,
                    sp.company_id as company_id,
                    avg(extract('epoch' from (sp.date_done-sp.create_date)))/(3600*24) as  avg_days_to_deliver,
                    sp.state
                from stock_move as sm
                left join stock_picking as sp ON (sm.picking_id=sp.id)
                group by sp.type,
                         sp.create_date,
                         sp.address_id,
                         sm.product_id,
                         to_char(sp.create_date, 'YYYY'),
                         sm.location_dest_id,
                         sm.location_id,
                         to_char(sp.create_date, 'MM'),
                         to_char(sp.create_date, 'YYYY-MM-DD'),
                         sm.product_uos,
                         sm.product_uom,
                         date_trunc('day',sp.min_date),
                         date_trunc('day',sp.date),
                         date_trunc('day',sp.date_done),
                         date_trunc('day',sp.max_date),
                         sp.invoice_state,
                         sp.company_id,
                         sp.state

            )""")
report_stock_picking()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
