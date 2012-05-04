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
from osv import fields, osv
import tools

def _type_get(self, cr, uid, context=None):
    obj = self.pool.get('auction.lot.category')
    ids = obj.search(cr, uid, [])
    res = obj.read(cr, uid, ids, ['name'], context)
    res = [(r['name'], r['name']) for r in res]
    return res

class report_auction(osv.osv):

    """Auction Report"""
    _name = "report.auction"
    _description = "Auction's Summary"
    _auto = False
    _columns = {
        'year': fields.char('Year', size=4, readonly=True),
        'month':fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'),
            ('05','May'), ('06','June'), ('07','July'), ('08','August'), ('09','September'),
            ('10','October'), ('11','November'), ('12','December')], 'Month',readonly=True),
        'day': fields.char('Day', size=128, readonly=True),
        'buyer_login': fields.char('Buyer Login', size=64, readonly=True, select=1),
        'buyer':fields.many2one('res.partner', 'Buyer', readonly=True, select=2),
        'seller': fields.many2one('res.partner', 'Seller', readonly=True, select=1),
        'object':fields.integer('No of objects', readonly=True, select=1),
        'total_price':fields.float('Total Price', digits=(16, 2), readonly=True, select=2),
        'lot_type': fields.selection(_type_get, 'Object category', size=64),
        'avg_price':fields.float('Avg Price.', digits=(16, 2), readonly=True, select=2),
        'date': fields.date('Create Date', select=1),
        'auction': fields.many2one('auction.dates', 'Auction date', readonly=True, select=1),
        'gross_revenue':fields.float('Gross Revenue', readonly=True),
        'net_revenue':fields.float('Net Revenue', readonly=True),
        'net_margin':fields.float('Net Margin', readonly=True),
        'avg_estimation':fields.float('Avg estimation', readonly=True),
        'user_id':fields.many2one('res.users', 'User', select=1),
        'state': fields.selection((('draft', 'Draft'), ('unsold', 'Unsold'), ('sold', 'Sold')), 'Status', readonly=True, select=1),

    }

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_auction')
        cr.execute('''
        create or replace view report_auction  as (
            select
                min(al.id) as id,
                al.ach_login as "buyer_login",
                ad.auction1 as date,
                al.state,
                al.create_uid as user_id,
                to_char(ad.auction1, 'YYYY') as year,
                to_char(ad.auction1, 'MM') as month,
                to_char(ad.auction1, 'YYYY-MM-DD') as day,
                al.ach_uid as "buyer",
                al.lot_type as lot_type,
                ade.partner_id as seller,
                ad.id as auction,
                count(al.id) as "object",
                sum(al.obj_price) as "total_price",
                (sum(al.obj_price)/count(al.id)) as "avg_price",
                sum(al.gross_revenue) as gross_revenue,
                sum(al.net_revenue) as net_revenue,
                avg(al.net_margin) as net_margin,
                sum(al.lot_est1+al.lot_est2)/2 as avg_estimation
            from
                auction_lots al,
                auction_dates ad,
                auction_deposit ade
            where
                ad.id=al.auction_id and ade.id=al.bord_vnd_id
            group by
               ad.auction1,
                al.ach_uid,
                ad.id,
                al.ach_login,
                ade.partner_id,
                al.state,
                al.create_uid,
                al.lot_type
             )
         ''')
report_auction()


#==========================
#Dashboard Report
#==========================

class report_auction_object_date(osv.osv):
    _name = "report.auction.object.date"
    _description = "Objects per day"
    _auto = False
    _columns = {
        'obj_num': fields.integer('# of Objects'),
        'name': fields.date('Created date', select=2),
        'month': fields.date('Month', select=1),
        'user_id':fields.many2one('res.users', 'User',select=1),
    }

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_auction_object_date')
        cr.execute("""create or replace view report_auction_object_date as
            (select
               min(l.id) as id,
               to_char(l.create_date, 'YYYY-MM-DD') as name,
               to_char(l.create_date, 'YYYY-MM-01') as month,
               count(l.obj_num) as obj_num,
               l.create_uid as user_id
            from
                auction_lots l
            group by
                to_char(l.create_date, 'YYYY-MM-DD'),
                to_char(l.create_date, 'YYYY-MM-01'),
                l.create_uid
            )
        """)
report_auction_object_date()

class report_auction_adjudication(osv.osv):
    _name = "report.auction.adjudication"
    _description = "report_auction_adjudication"
    _auto = False
    _columns = {
            'name': fields.many2one('auction.dates','Auction date',readonly=True,select=1),
            'state': fields.selection((('draft','Draft'),('close','Closed')),'Status', select=1),
            'adj_total': fields.float('Total Adjudication'),
            'date': fields.date('Date', readonly=True,select=1),
            'user_id':fields.many2one('res.users', 'User',select=1)

    }

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_auction_adjudication')
        cr.execute("""
            create or replace view report_auction_adjudication as (
                select
                    l.id as id,
                    l.id as name,
                    sum(m.obj_price) as adj_total,
                    to_char(l.create_date, 'YYYY-MM-01') as date,
                    l.create_uid as user_id,
                    l.state
                from
                    auction_dates l ,auction_lots m
                    where
                        m.auction_id=l.id
                    group by
                        l.id,l.state,l.name,l.create_uid,to_char(l.create_date, 'YYYY-MM-01')

            )
        """)
report_auction_adjudication()

class report_object_encoded(osv.osv):
    _name = "report.object.encoded"
    _description = "Object encoded"
    _auto = False
    _columns = {
        'user_id':fields.many2one('res.users', 'User', select=True),
        'estimation': fields.float('Estimation',select=True),
        'date': fields.date('Create Date',  required=True),
        'gross_revenue':fields.float('Gross revenue',readonly=True, select=True),
        'net_revenue':fields.float('Net revenue',readonly=True, select=True),
        'obj_margin':fields.float('Net margin', readonly=True, select=True),
        'obj_ret':fields.integer('# obj ret', readonly=True, select=True),
        'adj':fields.integer('Adj.', readonly=True, select=True),
        'obj_num':fields.integer('# of Encoded obj.', readonly=True, select=True),
        'state': fields.selection((('draft','Draft'),('unsold','Unsold'),('paid','Paid'),('invoiced','Invoiced')),'Status', required=True,select=1),
    }
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_object_encoded')
        cr.execute('''create or replace view report_object_encoded  as
            (select
                min(al.id) as id,
                to_char(al.create_date, 'YYYY-MM-DD') as date,
                al.state as state,
                al.create_uid as user_id,
                sum((100*lot_est1)/obj_price) as estimation,
                (SELECT count(1) FROM auction_lots WHERE obj_ret>0) as obj_ret,
                SUM(al.gross_revenue) as "gross_revenue",
                SUM(al.net_revenue) as "net_revenue",
                SUM(al.net_revenue)/count(al.id) as "obj_margin",
                COUNT(al.product_id) as obj_num,
                SUM(al.obj_price) as "adj"
            from auction_lots al
            where al.obj_price>0
            group by to_char(al.create_date, 'YYYY-MM-DD'), al.state, al.create_uid)
             ''')

report_object_encoded()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
