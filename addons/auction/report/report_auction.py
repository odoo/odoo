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
        'total_price':fields.float('Total Adj.', digits=(16, 2), readonly=True, select=2), 
        'avg_price':fields.float('Avg Adj.', digits=(16, 2), readonly=True, select=2), 
        'date': fields.date('Create Date', select=1),
        'auction': fields.many2one('auction.dates', 'Auction date', readonly=True, select=1),
        'gross_revenue':fields.float('Gross Revenue', readonly=True), 
        'net_revenue':fields.float('Net Revenue', readonly=True), 
        'net_margin':fields.float('Net Margin', readonly=True),
        'avg_estimation':fields.float('Avg estimation', readonly=True),
        'user_id':fields.many2one('res.users', 'User', select=1),
        'state': fields.selection((('draft', 'Draft'), ('unsold', 'Unsold'), ('sold', 'Sold')), 'State', readonly=True, select=1),
        
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
                al.create_uid
             )
         ''')
report_auction()
