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
from decimal_precision import decimal_precision as dp


class report_stock_move(osv.osv):
    _name = "report.stock.move"
    _description = "Moves Statistics"
    _auto = False
    _columns = {
        'date': fields.date('Date', readonly=True),
        'year': fields.char('Year', size=4, readonly=True),
        'day': fields.char('Day', size=128, readonly=True),
        'month':fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'),
            ('05','May'), ('06','June'), ('07','July'), ('08','August'), ('09','September'),
            ('10','October'), ('11','November'), ('12','December')], 'Month',readonly=True),
        'partner_id':fields.many2one('res.partner.address', 'Partner', readonly=True),
        'product_id':fields.many2one('product.product', 'Product', readonly=True),
        'company_id':fields.many2one('res.company', 'Company', readonly=True),
        'picking_id':fields.many2one('stock.picking', 'Packing', readonly=True),
        'type': fields.selection([('out', 'Sending Goods'), ('in', 'Getting Goods'), ('internal', 'Internal'), ('other', 'Others')], 'Shipping Type', required=True, select=True, help="Shipping type specify, goods coming in or going out."),
        'location_id': fields.many2one('stock.location', 'Source Location', readonly=True, select=True, help="Sets a location if you produce at a fixed location. This can be a partner location if you subcontract the manufacturing operations."),
        'location_dest_id': fields.many2one('stock.location', 'Dest. Location', readonly=True, select=True, help="Location where the system will stock the finished products."),
        'state': fields.selection([('draft', 'Draft'), ('waiting', 'Waiting'), ('confirmed', 'Confirmed'), ('assigned', 'Available'), ('done', 'Done'), ('cancel', 'Cancelled')], 'State', readonly=True, select=True),
        'product_qty':fields.integer('Quantity',readonly=True),
        'categ_id': fields.many2one('product.category', 'Product Category', ),
        'product_qty_in':fields.integer('In Qty',readonly=True),
        'product_qty_out':fields.integer('Out Qty',readonly=True),
        'value' : fields.float('Total Value', required=True),
        'day_diff2':fields.float('Lag (Days)',readonly=True,  digits_compute=dp.get_precision('Shipping Delay'), group_operator="avg"),
        'day_diff1':fields.float('Planned Lead Time (Days)',readonly=True, digits_compute=dp.get_precision('Shipping Delay'), group_operator="avg"),
        'day_diff':fields.float('Execution Lead Time (Days)',readonly=True,  digits_compute=dp.get_precision('Shipping Delay'), group_operator="avg"),
        'stock_journal': fields.many2one('stock.journal','Stock Journal', select=True),


    }

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_stock_move')
        cr.execute("""
            CREATE OR REPLACE view report_stock_move AS (
                SELECT
                        min(sm_id) as id,
                        date_trunc('day',al.dp) as date,
                        al.curr_year as year,
                        al.curr_month as month,
                        al.curr_day as day,
                        al.curr_day_diff as day_diff,
                        al.curr_day_diff1 as day_diff1,
                        al.curr_day_diff2 as day_diff2,
                        al.location_id as location_id,
                        al.picking_id as picking_id,
                        al.company_id as company_id,
                        al.location_dest_id as location_dest_id,
                        al.product_qty,
                        al.out_qty as product_qty_out,
                        al.in_qty as product_qty_in,
                        al.address_id as partner_id,
                        al.product_id as product_id,
                        al.state as state ,
                        al.product_uom as product_uom,
                        al.categ_id as categ_id,
                        coalesce(al.type, 'other') as type,
                        al.stock_journal as stock_journal,
                        sum(al.in_value - al.out_value) as value
                    FROM (SELECT
                        CASE WHEN sp.type in ('out') THEN
                            sum(sm.product_qty * pu.factor / pu2.factor)
                            ELSE 0.0
                            END AS out_qty,
                        CASE WHEN sp.type in ('in') THEN
                            sum(sm.product_qty * pu.factor / pu2.factor)
                            ELSE 0.0
                            END AS in_qty,
                        CASE WHEN sp.type in ('out') THEN
                            sum(sm.product_qty * pu.factor / pu2.factor) * pt.standard_price
                            ELSE 0.0
                            END AS out_value,
                        CASE WHEN sp.type in ('in') THEN
                            sum(sm.product_qty * pu.factor / pu2.factor) * pt.standard_price
                            ELSE 0.0
                            END AS in_value,
                        min(sm.id) as sm_id,
                        sm.date as dp,
                        to_char(date_trunc('day',sm.date), 'YYYY') as curr_year,
                        to_char(date_trunc('day',sm.date), 'MM') as curr_month,
                        to_char(date_trunc('day',sm.date), 'YYYY-MM-DD') as curr_day,
                        avg(date(sm.date)-date(sm.create_date)) as curr_day_diff,
                        avg(date(sm.date_expected)-date(sm.create_date)) as curr_day_diff1,
                        avg(date(sm.date)-date(sm.date_expected)) as curr_day_diff2,
                        sm.location_id as location_id,
                        sm.location_dest_id as location_dest_id,
                        sum(sm.product_qty) as product_qty,
                        pt.categ_id as categ_id ,
                        sm.address_id as address_id,
                        sm.product_id as product_id,
                        sm.picking_id as picking_id,
                            sm.company_id as company_id,
                            sm.state as state,
                            sm.product_uom as product_uom,
                            sp.type as type,
                            sp.stock_journal_id AS stock_journal
                    FROM
                        stock_move sm
                        LEFT JOIN stock_picking sp ON (sm.picking_id=sp.id)
                        LEFT JOIN product_product pp ON (sm.product_id=pp.id)
                        LEFT JOIN product_uom pu ON (sm.product_uom=pu.id)
                          LEFT JOIN product_uom pu2 ON (sm.product_uom=pu2.id)
                        LEFT JOIN product_template pt ON (pp.product_tmpl_id=pt.id)
                        LEFT JOIN stock_location sl ON (sm.location_id = sl.id)

                    GROUP BY
                        sm.id,sp.type, sm.date,sm.address_id,
                        sm.product_id,sm.state,sm.product_uom,sm.date_expected,
                        sm.product_id,pt.standard_price, sm.picking_id, sm.product_qty,
                        sm.company_id,sm.product_qty, sm.location_id,sm.location_dest_id,pu.factor,pt.categ_id, sp.stock_journal_id)
                    AS al

                    GROUP BY
                        al.out_qty,al.in_qty,al.curr_year,al.curr_month,
                        al.curr_day,al.curr_day_diff,al.curr_day_diff1,al.curr_day_diff2,al.dp,al.location_id,al.location_dest_id,
                        al.address_id,al.product_id,al.state,al.product_uom,
                        al.picking_id,al.company_id,al.type,al.product_qty, al.categ_id, al.stock_journal
               )
        """)

report_stock_move()


class report_stock_inventory(osv.osv):
    _name = "report.stock.inventory"
    _description = "Stock Statistics"
    _auto = False
    _columns = {
        'date': fields.datetime('Date', readonly=True),
        'partner_id':fields.many2one('res.partner.address', 'Partner', readonly=True),
        'product_id':fields.many2one('product.product', 'Product', readonly=True),
        'product_categ_id':fields.many2one('product.category', 'Product Category', readonly=True),
        'location_id': fields.many2one('stock.location', 'Location', readonly=True),
        'prodlot_id': fields.many2one('stock.production.lot', 'Lot', readonly=True),
        'company_id': fields.many2one('res.company', 'Company', readonly=True),
        'product_qty':fields.float('Quantity',  digits_compute=dp.get_precision('Product UoM'), readonly=True),
        'value' : fields.float('Total Value',  digits_compute=dp.get_precision('Account'), required=True),
        'state': fields.selection([('draft', 'Draft'), ('waiting', 'Waiting'), ('confirmed', 'Confirmed'), ('assigned', 'Available'), ('done', 'Done'), ('cancel', 'Cancelled')], 'State', readonly=True, select=True,
              help='When the stock move is created it is in the \'Draft\' state.\n After that it is set to \'Confirmed\' state.\n If stock is available state is set to \'Avaiable\'.\n When the picking it done the state is \'Done\'.\
              \nThe state is \'Waiting\' if the move is waiting for another one.'),
        'location_type': fields.selection([('supplier', 'Supplier Location'), ('view', 'View'), ('internal', 'Internal Location'), ('customer', 'Customer Location'), ('inventory', 'Inventory'), ('procurement', 'Procurement'), ('production', 'Production'), ('transit', 'Transit Location for Inter-Companies Transfers')], 'Location Type', required=True),
    }
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_stock_inventory')
        cr.execute("""
CREATE OR REPLACE view report_stock_inventory AS (
    (SELECT
        min(m.id) as id, m.date as date,
        m.address_id as partner_id, m.location_id as location_id,
        m.product_id as product_id, pt.categ_id as product_categ_id, l.usage as location_type,
        m.company_id,
        m.state as state, m.prodlot_id as prodlot_id,

        coalesce(sum(-pt.standard_price * m.product_qty * pu.factor / pu2.factor)::decimal, 0.0) as value,
        coalesce(sum(-m.product_qty * pu.factor / pu2.factor)::decimal, 0.0) as product_qty
    FROM
        stock_move m
            LEFT JOIN stock_picking p ON (m.picking_id=p.id)
            LEFT JOIN product_product pp ON (m.product_id=pp.id)
                LEFT JOIN product_template pt ON (pp.product_tmpl_id=pt.id)
                LEFT JOIN product_uom pu ON (pt.uom_id=pu.id)
                LEFT JOIN product_uom pu2 ON (m.product_uom=pu2.id)
            LEFT JOIN product_uom u ON (m.product_uom=u.id)
            LEFT JOIN stock_location l ON (m.location_id=l.id)
    GROUP BY
        m.id, m.product_id, m.product_uom, pt.categ_id, m.address_id, m.location_id,  m.location_dest_id,
        m.prodlot_id, m.date, m.state, l.usage, m.company_id, pt.uom_id
) UNION ALL (
    SELECT
        -m.id as id, m.date as date,
        m.address_id as partner_id, m.location_dest_id as location_id,
        m.product_id as product_id, pt.categ_id as product_categ_id, l.usage as location_type,
        m.company_id,
        m.state as state, m.prodlot_id as prodlot_id,
        coalesce(sum(pt.standard_price * m.product_qty * pu.factor / pu2.factor)::decimal, 0.0) as value,
        coalesce(sum(m.product_qty * pu.factor / pu2.factor)::decimal, 0.0) as product_qty
    FROM
        stock_move m
            LEFT JOIN stock_picking p ON (m.picking_id=p.id)
            LEFT JOIN product_product pp ON (m.product_id=pp.id)
                LEFT JOIN product_template pt ON (pp.product_tmpl_id=pt.id)
                LEFT JOIN product_uom pu ON (pt.uom_id=pu.id)
                LEFT JOIN product_uom pu2 ON (m.product_uom=pu2.id)
            LEFT JOIN product_uom u ON (m.product_uom=u.id)
            LEFT JOIN stock_location l ON (m.location_dest_id=l.id)
    GROUP BY
        m.id, m.product_id, m.product_uom, pt.categ_id, m.address_id, m.location_id, m.location_dest_id,
        m.prodlot_id, m.date, m.state, l.usage, m.company_id, pt.uom_id
    )
);
        """)
report_stock_inventory()


