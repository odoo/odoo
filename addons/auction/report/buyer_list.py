# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


import pooler
import time
from report import report_sxw
from osv import osv
from tools.translate import _

class buyer_list(report_sxw.rml_parse):
    auc_lot_ids=[]
    sum_adj_price_val=0.0
    sum_buyer_obj_price_val=0.0
    sum_buyer_price_val=0.0
    sum_lot_val=0.0
    def __init__(self, cr, uid, name, context):
        super(buyer_list, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'lines_lots_from_auction' : self.lines_lots_from_auction,
            'lines_lots_auct_lot' : self.lines_lots_auct_lot,
            'sum_adj_price':self.sum_adj_price,
            'sum_buyer_obj_price':self.sum_buyer_obj_price,
            'sum_buyer_price':self.sum_buyer_price,
            'sum_lots':self.sum_lots
    })

    def lines_lots_from_auction(self,objects):

        auc_lot_ids = []
        for lot_id  in objects:
            auc_lot_ids.append(lot_id.id)
        self.auc_lot_ids=auc_lot_ids
        self.cr.execute('SELECT auction_id FROM auction_lots WHERE id IN %s GROUP BY auction_id',
                        (tuple(auc_lot_ids),))
        auc_date_ids = self.cr.fetchall()
        auct_dat=[]
        for ad_id in auc_date_ids:
            auc_dates_fields = self.pool.get('auction.dates').read(self.cr,self.uid,ad_id[0],['name'])
            self.cr.execute('select * from auction_buyer_taxes_rel abr,auction_dates ad where ad.id=abr.auction_id and ad.id=%s', (ad_id[0],))
            res=self.cr.fetchall()
            total=0
            for r in res:
                buyer_rel_field = self.pool.get('account.tax').read(self.cr,self.uid,r[1],['amount'])
                total = total + buyer_rel_field['amount']
            auc_dates_fields['amount']=total
            auct_dat.append(auc_dates_fields)
        return auct_dat

    def lines_lots_auct_lot(self,obj):
        auc_lot_ids = []

        auc_date_ids = self.pool.get('auction.dates').search(self.cr,self.uid,([('name','like',obj['name'])]))

        self.cr.execute('SELECT ach_login AS ach_uid, COUNT(1) AS no_lot, '\
                        'SUM(obj_price) AS adj_price, '\
                        'SUM(buyer_price)-SUM(obj_price) AS buyer_cost, '\
                        'SUM(buyer_price) AS to_pay '\
                        'FROM auction_lots WHERE id IN %s '\
                        'AND auction_id=%s AND ach_login IS NOT NULL '\
                        'GROUP BY ach_login ORDER BY ach_login',
                        (tuple(self.auc_lot_ids), auc_date_ids[0],))
        res = self.cr.dictfetchall()
        for r in res:
                self.sum_adj_price_val = self.sum_adj_price_val + r['adj_price']
                self.sum_buyer_obj_price_val = self.sum_buyer_obj_price_val + r['buyer_cost']
                self.sum_buyer_price_val = self.sum_buyer_price_val + r['to_pay']
                self.sum_lot_val = self.sum_lot_val + r['no_lot']#
        return res
    def sum_lots(self):
        return self.sum_lot_val
    def sum_adj_price(self):
        return self.sum_adj_price_val

    def sum_buyer_obj_price(self):
        return self.sum_buyer_obj_price_val

    def sum_buyer_price(self):
        return self.sum_buyer_price_val
report_sxw.report_sxw('report.buyer.list', 'auction.lots', 'addons/auction/report/buyer_list.rml', parser=buyer_list)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

