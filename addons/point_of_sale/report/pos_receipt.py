# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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
from mx.DateTime.ISO import ParseAny
import pooler


class order(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(order, self).__init__(cr, uid, name, context=context)

        user = pooler.get_pool(cr.dbname).get('res.users').browse(cr, uid, uid)
        partner = user.company_id.partner_id

        self.localcontext.update({
            'time': time,
            'dformat': '%Y/%m/%d %H:%M:%S',
            'disc': self.discount,
            'net': self.netamount,
            'formatdate': self.formatdate,
            'address': partner.address and partner.address[0] or False,
        })

    def formatdate(self, datestr):
        dateobj = ParseAny(datestr)
        return dateobj.strftime(self.localcontext['dformat'])

    def netamount(self, order_line_id):
        sql = 'select (qty*price_unit) as net_price from pos_order_line where id = %s'
        self.cr.execute(sql, (order_line_id,))
        res = self.cr.fetchone()
        return res[0]

    def discount(self, order_id):
        sql = 'select discount, price_unit, qty from pos_order_line where order_id = %s '
        self.cr.execute(sql, (order_id,))
        res = self.cr.fetchall()
        dsum = 0
        for line in res:
            if line[0] != 0:
                dsum = dsum +(line[2] * (line[0]*line[1]/100))
        return dsum

report_sxw.report_sxw('report.pos.receipt', 'pos.order', 'addons/point_of_sale/report/pos_receipt.rml', parser=order, header=False)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

