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


class auction_total_rml(report_sxw.rml_parse):
    total_obj=[]
    def __init__(self, cr, uid, name, context):
        super(auction_total_rml, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'sum_taxes':self.sum_taxes,
            'sold_item':self.sold_item,
            'sum_buyer':self.sum_buyer,
            'sum_seller':self.sum_seller,
            'sum_buyer_paid':self.sum_buyer_paid,
            'sum_adj':self.sum_adj,
            'count_comm':self.count_comm,
            'sum_minadj':self.sum_minadj,
            'sum_maxadj':self.sum_maxadj,
            'sum_credit':self.sum_credit,
            'sum_debit': self.sum_debit,
            'chek_paid': self.chek_paid,
            'check_paid_seller': self.check_paid_seller,
            'count_take': self.count_take,
            'sum_credit_seller':self.sum_credit_seller,
            'sum_debit_buyer': self.sum_debit_buyer,
            'get_auc_detail': self.get_auc_detail
        })
    def get_auc_detail(self,objects):
        auc_lot_ids = []
        for lot_id  in objects:
            auc_lot_ids.append(lot_id.id)
        self.total_obj=auc_lot_ids
        self.cr.execute('SELECT auction_id FROM auction_lots '
                        'WHERE id IN %s '
                        'GROUP BY auction_id',
                        (tuple(auc_lot_ids),))
        auc_date_ids = self.cr.fetchall()
        auct_dat=[]
        for ad_id in auc_date_ids:
            auc_dates_fields = self.pool.get('auction.dates').read(self.cr,self.uid,ad_id[0],['name','auction1','id'])
            auct_dat.append(auc_dates_fields)
        return auct_dat


    def sum_taxes(self,auction_id):
            self.cr.execute("select count(1) from auction_lots where id in ("+",".join(map(str,self.total_obj))+") and auction_id=%s group by auction_id ", (auction_id,))
            res = self.cr.fetchone()
            return res[0]
    def sold_item(self, object_id):
        self.cr.execute("select count(1) from auction_lots where id in ("+",".join(map(str,self.total_obj))+") and auction_id=%s and state in ('unsold') ", (object_id,))
        res = self.cr.fetchone()
        return str(res[0])


    def sum_buyer(self, auction_id):
        self.cr.execute("select count(*) from auction_lots where id in ("+",".join(map(str,self.total_obj))+") and auction_id=%s and (ach_uid is not null or ach_login is not null) ", (auction_id,))
        res = self.cr.fetchone()
        return str(res[0])


    def sum_seller(self, auction_id):
        self.cr.execute("select count(distinct bord_vnd_id)  from auction_lots where id in ("+",".join(map(str,self.total_obj))+") and auction_id=%s AND bord_vnd_id is not null ", (auction_id,))
        res = self.cr.fetchone()
        return res[0]

    def sum_adj(self, auction_id):
        self.cr.execute("select sum(obj_price) from auction_lots where id in ("+",".join(map(str,self.total_obj))+") and auction_id=%s ", (auction_id,))
        res = self.cr.fetchone()
        return str(res[0])

    def count_take(self, auction_id):
        self.cr.execute("select count(*) from auction_lots where id in ("+",".join(map(str,self.total_obj))+") and auction_id=%s and ach_emp='True' ", (auction_id,))
        res = self.cr.fetchone()
        return str(res[0])

    def chek_paid(self, auction_id):
        self.cr.execute("select count(1) from auction_lots where id in ("+",".join(map(str,self.total_obj))+") and auction_id=%s and ((paid_ach='T') or (is_ok='T')) ", (auction_id,))
        res = self.cr.fetchone()
        return str(res[0])
    def check_paid_seller(self,auction_id):
        self.cr.execute("select sum(seller_price) from auction_lots where id in ("+",".join(map(str,self.total_obj))+") and auction_id=%s and paid_vnd != 'T' ", (auction_id,))
        res = self.cr.fetchone()
        return str(res[0]) or 0.0

    def sum_credit(self,auction_id):
        self.cr.execute("select sum(buyer_price) from auction_lots where id in ("+",".join(map(str,self.total_obj))+") and auction_id=%s", (auction_id,))
        res = self.cr.fetchone()
        return str(res[0])

    def sum_debit_buyer(self,auction_id):
        self.cr.execute("select sum(buyer_price) from auction_lots where id in ("+",".join(map(str,self.total_obj))+") and auction_id=%s", (auction_id,))
        res = self.cr.fetchone()
        return str(res[0] or 0)

    def sum_debit(self,object_id):
        self.cr.execute("select sum(seller_price) from auction_lots where auction_id=%s", (object_id,))
        res = self.cr.fetchone()
        return str(res[0] or 0)

    def sum_credit_seller(self, object_id):


        self.cr.execute("select sum(seller_price) from auction_lots where id in ("+",".join(map(str,self.total_obj))+") and auction_id=%s", (object_id,))
        res = self.cr.fetchone()
        return str(res[0] or 0)

    def sum_minadj(self, auction_id):
        self.cr.execute('select sum(lot_est1) from auction_lots where id in ('+','.join(map(str,self.total_obj))+') and auction_id=%s', (auction_id,))
        res = self.cr.fetchone()
        return str(res[0]) or 0

    def sum_maxadj(self, auction_id):
        self.cr.execute('select sum(lot_est2) from auction_lots where id in ('+','.join(map(str,self.total_obj))+') and auction_id=%s', (auction_id,))
        res = self.cr.fetchone()
        return str(res[0]) or 0

    def sum_buyer_paid(self, auction_id):
        self.cr.execute("select count(*) from auction_lots where id in ("+",".join(map(str,self.total_obj))+") and auction_id=%s and state = 'paid' ", (auction_id,))
        res = self.cr.fetchone()
        return str(res[0])

    def count_comm(self, auction_id):
        self.cr.execute("select count(*) from auction_lots where id in ("+",".join(map(str,self.total_obj))+") and auction_id=%s and obj_comm is not null ", (auction_id,))
        res = self.cr.fetchone()
        return str(res[0])


report_sxw.report_sxw('report.auction.total.rml', 'auction.lots', 'addons/auction/report/auction_total.rml',parser=auction_total_rml)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

