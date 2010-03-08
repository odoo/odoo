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
import time
from report import report_sxw

class pos_payment_report_user(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(pos_payment_report_user, self).__init__(cr, uid, name, context)
        self.total = 0.0
        self.localcontext.update({
                'time': time,
                'pos_payment_user': self.__pos_payment_user__,
                'pos_payment_user_total':self.__pos_payment_user__total__,
                })

    def __pos_payment_user__(self,form):
        data={}
        ids = form['user_id'][0][-1]
        idss = map(str, ids)
        sql = "select pt.name,pol.qty,pol.discount,pol.price_unit, " \
                         "(pol.price_unit * pol.qty * (1 - (pol.discount) / 100.0)) as total  " \
                         "from pos_order as po,pos_order_line as pol,product_product as pp,product_template as pt " \
                         "where pt.id=pp.product_tmpl_id and pp.id=pol.product_id and po.id = pol.order_id  " \
                         "and po.state in ('paid','invoiced') and to_char(date_trunc('day',po.date_order),'YYYY-MM-DD')::date = current_date " \
                         "and po.user_id in (%s)" % (",".join(idss), )
        self.cr.execute (sql)
        data=self.cr.dictfetchall()
        return data
    def __pos_payment_user__total__(self,form):
        res=[]
        ids = form['user_id'][0][-1]
        idss = map(str, ids)
        self.cr.execute ("select sum(pol.price_unit * pol.qty * (1 - (pol.discount) / 100.0)) " \
                         "from pos_order as po,pos_order_line as pol,product_product as pp,product_template as pt " \
                         "where pt.id=pp.product_tmpl_id and pp.id=pol.product_id and po.id = pol.order_id " \
                         "and po.state='paid' and to_char(date_trunc('day',po.date_order),'YYYY-MM-DD')::date = current_date " \
                         "and po.user_id in (%s)" % (",".join(idss), ))
        res=self.cr.fetchone()
        res = res and res[0] or None

        return res


report_sxw.report_sxw('report.pos.payment.report.user', 'pos.order', 'addons/point_of_sale/report/pos_payment_report_user.rml', parser=pos_payment_report_user)
















