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
from mx import DateTime
from osv import fields, osv, orm
from tools import config
from tools.translate import _
import ir
import netsvc
import os
import time
import tools


def _type_get(self, cr, uid, context=None):
    if not context:
        context = {}
    cr.execute('select name, name from auction_lot_category order by name')
    return cr.fetchall()

class report_attendance(osv.osv):
    _name="report.attendance"
    _description = "Report Sign In/Out"
    _auto = False
    #_rec_name='date'
    _columns = {
        'name': fields.date('Date', readonly=True, select=1), 
        'employee_id' : fields.many2one('hr.employee', "Employee's Name", select=1, readonly=True), 
        'total_attendance': fields.float('Total', readonly=True), 
}
    def init(self, cr):
        cr.execute("""CREATE OR REPLACE VIEW report_attendance AS
            SELECT
                id,
                name,
                employee_id,
                CASE WHEN SUM(total_attendance) < 0
                    THEN (SUM(total_attendance) +
                        CASE WHEN current_date <> name
                            THEN 1440
                            ELSE (EXTRACT(hour FROM current_time) * 60) + EXTRACT(minute FROM current_time)
                        END
                        )
                    ELSE SUM(total_attendance)
                END /60  as total_attendance
            FROM (
                SELECT
                    max(a.id) as id,
                    a.name::date as name,
                    a.employee_id,
                    SUM(((EXTRACT(hour FROM a.name) * 60) + EXTRACT(minute FROM a.name)) * (CASE WHEN a.action = 'sign_in' THEN -1 ELSE 1 END)) as total_attendance
                FROM hr_attendance a
                where name > current_date + interval '-1 day'
                GROUP BY a.name::date, a.employee_id
            ) AS fs
            GROUP BY name,fs.id,employee_id
            """)

report_attendance()

class report_auction_object_date(osv.osv):
    _name = "report.auction.object.date"
    _description = "Objects per day"
    _auto = False
    _columns = {
        'obj_num': fields.integer('# of Objects'), 
        'name': fields.date('Created date', select=2), 
        'month': fields.date('Month', select=1), 
        'user_id':fields.many2one('res.users', 'User', select=1), 
    }
 #l.create_uid as user,

    def init(self, cr):
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

class report_auction_estimation_adj_category(osv.osv):
    _name = "report.auction.estimation.adj.category"
    _description = "comparaison estimate/adjudication "
    _auto = False
    _rec_name='date'
    _columns = {
            'lot_est1': fields.float('Minimum Estimation', select=2), 
            'lot_est2': fields.float('Maximum Estimation', select=2), 
#            'obj_price': fields.float('Adjudication price'),
            'date': fields.date('Date', readonly=True, select=1), 
            'lot_type': fields.selection(_type_get, 'Object Type', size=64), 
            'adj_total': fields.float('Total Adjudication', select=2), 
            'user_id':fields.many2one('res.users', 'User', select=1)
    }

    def init(self, cr):
        cr.execute("""
            create or replace view report_auction_estimation_adj_category as (
                select
                   min(l.id) as id,
                   to_char(l.create_date, 'YYYY-MM-01') as date,
                   l.lot_type as lot_type,
                   sum(l.lot_est1) as lot_est1,
                   sum(l.lot_est2) as lot_est2,
                   sum(l.obj_price) as adj_total,
                   l.create_uid as user_id
                from
                    auction_lots l,auction_dates m
                where
                    l.auction_id=m.id and l.obj_price >0
                group by
                     to_char(l.create_date, 'YYYY-MM-01'),lot_type,l.create_uid
            )
        """)
report_auction_estimation_adj_category()

class report_auction_adjudication(osv.osv):
    _name = "report.auction.adjudication"
    _description = "report_auction_adjudication"
    _auto = False
    _columns = {
            'name': fields.many2one('auction.dates', 'Auction date', readonly=True, select=1), 
            'state': fields.selection((('draft', 'Draft'), ('close', 'Closed')), 'State', select=1), 
            'adj_total': fields.float('Total Adjudication'), 
            'date': fields.date('Date', readonly=True, select=1), 
            'user_id':fields.many2one('res.users', 'User', select=1)

    }


    def init(self, cr):
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

class report_deposit_border(osv.osv):
    _name="report.deposit.border"
    _description = "Report deposit border"
    _auto = False
    _rec_name='bord'
    _columns = {
        'bord': fields.char('Depositer Inventory', size=64, required=True), 
        'seller': fields.many2one('res.partner', 'Seller', select=1), 
        'moy_est' : fields.float('Avg. Est', select=1, readonly=True), 
        'total_marge': fields.float('Total margin', readonly=True), 
        'nb_obj':fields.float('# of objects', readonly=True), 
}
    def init(self, cr):
        cr.execute("""CREATE OR REPLACE VIEW report_deposit_border AS
            SELECT
                min(al.id) as id,
                ab.partner_id as seller,
                ab.name as bord,
                COUNT(al.id) as nb_obj,
                SUM((al.lot_est1 + al.lot_est2)/2) as moy_est,
                SUM(al.net_revenue)/(count(ad.id)) as total_marge

            FROM
                auction_lots al,auction_deposit ab,auction_dates ad
            WHERE
                ad.id=al.auction_id
                and al.bord_vnd_id=ab.id
            GROUP BY
                ab.name,ab.partner_id""")
report_deposit_border()

class report_object_encoded(osv.osv):
    _name = "report.object.encoded"
    _description = "Object encoded"
    _auto = False
    _columns = {
        'state': fields.selection((('draft', 'Draft'), ('unsold', 'Unsold'), ('paid', 'Paid'), ('invoiced', 'Invoiced')), 'State', required=True, select=1), 
        'user_id':fields.many2one('res.users', 'User', select=1), 
        'estimation': fields.float('Estimation', select=2), 
        'date': fields.date('Create Date', required=True), 
#        'gross_revenue':fields.float('Gross revenue',readonly=True, select=2),
#        'net_revenue':fields.float('Net revenue',readonly=True, select=2),
#        'obj_margin':fields.float('Net margin', readonly=True, select=2),
        'obj_ret':fields.integer('# obj ret', readonly=True, select=2), 
#        'adj':fields.integer('Adj.', readonly=True, select=2),
        'obj_num':fields.integer('# of Encoded obj.', readonly=True, select=2), 
    }
    def init(self, cr):
        cr.execute('''create or replace view report_object_encoded  as
            (select min(al.id) as id,
                to_char(al.create_date, 'YYYY-MM-DD') as date,
                al.state as state,
                al.create_uid as user_id,
                (SELECT count(1) FROM auction_lots WHERE obj_ret>0) as obj_ret,
                sum((100* al.lot_est1)/al.obj_price) as estimation,
                COUNT(al.product_id) as obj_num
            from auction_lots al
            where al.obj_price>0 and state='draft'
            group by to_char(al.create_date, 'YYYY-MM-DD'), al.state, al.create_uid)
             ''')
report_object_encoded()


class report_object_encoded_manager(osv.osv):
    _name = "report.object.encoded.manager"
    _description = "Object encoded"
    _auto = False
    _columns = {
        'user_id':fields.many2one('res.users', 'User', select=True), 
        'estimation': fields.float('Estimation', select=True), 
        'date': fields.date('Create Date', required=True), 
        'gross_revenue':fields.float('Gross revenue', readonly=True, select=True), 
        'net_revenue':fields.float('Net revenue', readonly=True, select=True), 
        'obj_margin':fields.float('Net margin', readonly=True, select=True), 
        'obj_ret':fields.integer('# obj ret', readonly=True, select=True), 
        'adj':fields.integer('Adj.', readonly=True, select=True), 
        'obj_num':fields.integer('# of Encoded obj.', readonly=True, select=True), 
    }
    def init(self, cr):
        cr.execute('''create or replace view report_object_encoded_manager  as
            (select
                min(al.id) as id,
                to_char(al.create_date, 'YYYY-MM-DD') as date,
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
            group by to_char(al.create_date, 'YYYY-MM-DD'), al.create_uid)
             ''')
report_object_encoded_manager()

class report_unclassified_objects(osv.osv):
    _name = "report.unclassified.objects"
    _description = "Unclassified objects "
    _auto = False
    _columns = {
        'name': fields.char('Short Description', size=64, required=True), 
        'obj_num': fields.integer('Catalog Number'), 
        'obj_price': fields.float('Adjudication price'), 
        'lot_num': fields.integer('List Number', required=True, select=1), 
        'state': fields.selection((('draft', 'Draft'), ('unsold', 'Unsold'), ('paid', 'Paid'), ('sold', 'Sold')), 'State', required=True, readonly=True), 
        'obj_comm': fields.boolean('Commission'), 
        'bord_vnd_id': fields.many2one('auction.deposit', 'Depositer Inventory', required=True), 
        'ach_login': fields.char('Buyer Username', size=64), 
        'lot_est1': fields.float('Minimum Estimation'), 
        'lot_est2': fields.float('Maximum Estimation'), 
        'lot_type': fields.selection(_type_get, 'Object category', size=64), 
        'auction': fields.many2one('auction.dates', 'Auction date', readonly=True, select=1), 
    }
    def init(self, cr):
        cr.execute("""create or replace view report_unclassified_objects as
            (select
                min(al.id) as id,
                al.name as name,
                al.obj_price as obj_price,
                al.obj_num as obj_num,
                al.lot_num as lot_num,
                al.state as state,
                al.obj_comm as obj_comm,
                al.bord_vnd_id as bord_vnd_id,
                al.ach_login as ach_login,
                al.lot_est1 as lot_est1,
                al.lot_est2 as lot_est2,
                al.lot_type as lot_type,
                al.auction_id as auction
            from auction_lots al,auction_lot_category ac
            where (al.lot_type=ac.name) AND (ac.aie_categ='41') AND (al.auction_id is null)
group by al.obj_price,al.obj_num, al.lot_num, al.state, al.obj_comm,al.bord_vnd_id,al.ach_login,al.lot_est1,al.lot_est2,al.lot_type,al.auction_id,al.name)
             """)
report_unclassified_objects()

