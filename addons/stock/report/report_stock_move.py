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


class report_stock_move(osv.osv):
    _name = "report.stock.move"
    _description = "Stock Statistics"
    _auto = False
    _columns = {
        'date_planned': fields.date('Date', readonly=True),
        'year': fields.char('Year', size=4, readonly=True),
        'day': fields.char('Day', size=128, readonly=True),
        'month':fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'),
            ('05','May'), ('06','June'), ('07','July'), ('08','August'), ('09','September'),
            ('10','October'), ('11','November'), ('12','December')], 'Month',readonly=True),
        'partner_id':fields.many2one('res.partner.address', 'Partner', readonly=True),
        'product_id':fields.many2one('product.product', 'Product', readonly=True),
        'company_id':fields.many2one('res.company', 'Company', readonly=True),
        'picking_id':fields.many2one('stock.picking', 'Packing', readonly=True),
        'type': fields.selection([('out', 'Sending Goods'), ('in', 'Getting Goods'), ('internal', 'Internal'), ('delivery', 'Delivery')], 'Shipping Type', required=True, select=True, help="Shipping type specify, goods coming in or going out."),
        'location_id': fields.many2one('stock.location', 'Source Location', readonly=True, select=True, help="Sets a location if you produce at a fixed location. This can be a partner location if you subcontract the manufacturing operations."),
        'location_dest_id': fields.many2one('stock.location', 'Dest. Location', readonly=True, select=True, help="Location where the system will stock the finished products."),
        'state': fields.selection([('draft', 'Draft'), ('waiting', 'Waiting'), ('confirmed', 'Confirmed'), ('assigned', 'Available'), ('done', 'Done'), ('cancel', 'Cancelled')], 'State', readonly=True, select=True),
        'product_qty':fields.integer('Qty',readonly=True),
        'value' : fields.float('Total Value', required=True),
        'day_diff2':fields.float('Delay (Days)',readonly=True, digits=(16,2), group_operator="avg"),
        'day_diff1':fields.float('Planned (Days)',readonly=True, digits=(16,2), group_operator="avg"),
        'day_diff':fields.float('Real (Days)',readonly=True, digits=(16,2), group_operator="avg"),
    }
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_stock_move')
        cr.execute("""
            create or replace view report_stock_move as (
               select min(m.id) as id,
                    m.date_planned as date_planned,
                    to_char(date_trunc('day',m.date_planned), 'YYYY') as year,
                    to_char(date_trunc('day',m.date_planned), 'MM') as month,
                    to_char(date_trunc('day',m.date_planned), 'YYYY-MM-DD') as day,
                    avg(date(m.date_planned)-date(m.create_date)) as day_diff,
                    avg(date(m.date_expected)-date(m.create_date)) as day_diff1,
                    avg(date(m.date_planned)-date(m.date_expected)) as day_diff2,
                    m.address_id as partner_id,
                    m.picking_id as picking_id,
                    m.company_id as company_id,
                    p.type as type,
                    m.location_id as location_id,
                    m.location_dest_id as location_dest_id,
                    m.product_id as product_id,
                    m.state as state,
                    m.product_uom as product_uom,
                    sum(m.product_qty) as product_qty,
                    pt.standard_price * sum(m.product_qty) as value
               from
                    stock_move m
                    left join stock_picking p on (m.picking_id=p.id)
                    left join product_product pp on (m.product_id=pp.id)
                    left join product_template pt on (pp.product_tmpl_id=pt.id)
               group by 
                    m.id, m.product_id,m.address_id, m.location_id, m.location_dest_id,
                    m.date_planned, m.state, m.product_uom,pt.standard_price,
                    m.picking_id, p.type, m.company_id
               )
        """)
report_stock_move()


class report_stock_inventory(osv.osv):
    _name = "report.stock.inventory"
    _description = "Stock Statistics"
    _auto = False
    _columns = {
        'date_planned': fields.datetime('Date', readonly=True),
        'partner_id':fields.many2one('res.partner.address', 'Partner', readonly=True),
        'product_id':fields.many2one('product.product', 'Product', readonly=True),
        'location_id': fields.many2one('stock.location', 'Location', readonly=True),
        'prodlot_id': fields.many2one('stock.production.lot', 'Lot', readonly=True),
        'company_id': fields.many2one('res.company', 'Company', readonly=True),
        'product_qty':fields.float('Qty', digits=(16,2), readonly=True),
        'value' : fields.float('Total Value', digits=(16,2), required=True),
        'state': fields.selection([('draft', 'Draft'), ('waiting', 'Waiting'), ('confirmed', 'Confirmed'), ('assigned', 'Available'), ('done', 'Done'), ('cancel', 'Cancelled')], 'State', readonly=True, select=True,
              help='When the stock move is created it is in the \'Draft\' state.\n After that it is set to \'Confirmed\' state.\n If stock is available state is set to \'Avaiable\'.\n When the picking it done the state is \'Done\'.\
              \nThe state is \'Waiting\' if the move is waiting for another one.'),
        'location_type': fields.selection([('supplier', 'Supplier Location'), ('view', 'View'), ('internal', 'Internal Location'), ('customer', 'Customer Location'), ('inventory', 'Inventory'), ('procurement', 'Procurement'), ('production', 'Production'), ('transit', 'Transit Location for Inter-Companies Transfers')], 'Location Type', required=True),
    }
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_stock_inventory')
        cr.execute("""
create or replace view report_stock_inventory as (
    (select
        min(m.id) as id, m.date_planned as date_planned,
        m.address_id as partner_id, m.location_id as location_id,
        m.product_id as product_id, l.usage as location_type,
        m.company_id,
        m.state as state, m.prodlot_id as prodlot_id,
        sum(-m.product_qty*u.factor)::decimal(16,2) as product_qty,
        sum(-pt.standard_price * m.product_qty * u.factor)::decimal(16,2) as value
    from
        stock_move m
            left join stock_picking p on (m.picking_id=p.id)
                left join product_product pp on (m.product_id=pp.id)
                    left join product_template pt on (pp.product_tmpl_id=pt.id)
            left join product_uom u on (m.product_uom=u.id)
                left join stock_location l on (m.location_id=l.id)
    group by
        m.id, m.product_id, m.address_id, m.location_id, m.prodlot_id,
        m.date_planned, m.state, l.usage, m.company_id
) union all (
    select
        -m.id as id, m.date_planned as date_planned,
        m.address_id as partner_id, m.location_dest_id as location_id,
        m.product_id as product_id, l.usage as location_type,
        m.company_id,
        m.state as state, m.prodlot_id as prodlot_id,
        sum(m.product_qty*u.factor)::decimal(16,2) as product_qty,
        sum(pt.standard_price * m.product_qty * u.factor)::decimal(16,2) as value
    from
        stock_move m
            left join stock_picking p on (m.picking_id=p.id)
                left join product_product pp on (m.product_id=pp.id)
                    left join product_template pt on (pp.product_tmpl_id=pt.id)
            left join product_uom u on (m.product_uom=u.id)
                left join stock_location l on (m.location_dest_id=l.id)
    group by
        m.id, m.product_id, m.address_id, m.location_id, m.location_dest_id,
        m.prodlot_id, m.date_planned, m.state, l.usage, m.company_id
    )
);
        """)
report_stock_inventory()



