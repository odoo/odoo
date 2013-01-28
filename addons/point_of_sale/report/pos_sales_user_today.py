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
from openerp.report import report_sxw

class pos_sales_user_today(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(pos_sales_user_today, self).__init__(cr, uid, name, context=context)
        self.total = 0.0
        self.localcontext.update({
            'time': time,
            'get_data':self._get_data,

        })

    def _get_data(self, form):
        data={}
        ids = form['user_id']

        self.cr.execute("select po.name as pos,po.date_order,ru.name as user,po.state,rc.name " \
                        "from pos_order as po,res_users as ru,res_company as rc " \
                        "where to_char(date_trunc('day',po.date_order),'YYYY-MM-DD')::date = current_date " \
                        "and po.company_id=rc.id and po.user_id=ru.id and po.user_id IN %s", (tuple(ids), ))

        data = self.cr.dictfetchall()
        return data

report_sxw.report_sxw('report.pos.sales.user.today', 'pos.order', 'addons/point_of_sale/report/pos_sales_user_today.rml', parser=pos_sales_user_today,header='internal')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
