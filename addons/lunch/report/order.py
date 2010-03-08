# -*- encoding: utf-8 -*-
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
from osv import osv


class order(report_sxw.rml_parse):

    def sum_price(self, orders):
        res = 0.0
        for o in orders:
            res += o.price
        return res

    def __init__(self, cr, uid, name, context):
        super(order, self).__init__(cr, uid, name, context)

        self.localcontext.update({
        'time': time,
        'sum_price': self.sum_price,
        })

report_sxw.report_sxw('report.lunch.order', 'lunch.order',
        'addons/lunch/report/order.rml',parser=order, header=False)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

