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

import time
from report import report_sxw

class pos_sales_user_today_current_user(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(pos_sales_user_today_current_user, self).__init__(cr, uid, name, context=context)
        self.total = 0.0
        self.qty = 0.0
        self.localcontext.update({
            'time': time,
            'get_user':self._get_user,
            'get_data_current_user':self._get_data_current_user,
            'get_data_current_user_tot':self._get_data_current_user_tot,
            'get_data_current_user_qty':self._get_data_current_user_qty,
        })

    def _get_user(self, user):
        pos_user={}
        self.cr.execute("select name from res_users where id = %s",str(self.uid))
        pos_user=self.cr.dictfetchone()
        return pos_user['name']

    def _get_data_current_user(self, user):
        data={}
        self.cr.execute("select po.name,po. state,sum(pol.qty)as Qty,sum((pol.price_unit * pol.qty * (1 - (pol.discount) / 100.0))) as Total " \
                        "from pos_order as po,pos_order_line as pol,product_product as pp,product_template as pt, res_users as ru,res_company as rc  " \
                        "where pt.id=pp.product_tmpl_id and pp.id=pol.product_id and po.id = pol.order_id  " \
                        "and to_char(date_trunc('day',po.date_order),'YYYY-MM-DD')::date = current_date  and po.user_id = ru.id and rc.id = %s and ru.id = %s " \
                        "group by po.name, po.state " \
                ,(str(user.company_id.id),str(self.uid)))

        data = self.cr.dictfetchall()
        for d in data:
            self.total += d['total']
            self.qty += d['qty']
        return data

    def _get_data_current_user_tot(self, user):
        return self.total

    def _get_data_current_user_qty(self, user):
        return self.qty

report_sxw.report_sxw('report.pos.sales.user.today.current.user', 'pos.order', 'addons/point_of_sale/report/pos_sales_user_today_current_user.rml', parser=pos_sales_user_today_current_user,header='internal')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: