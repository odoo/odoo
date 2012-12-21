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

class pos_lines(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(pos_lines, self).__init__(cr, uid, name, context=context)
        self.total = 0.0
        self.localcontext.update({
            'time': time,
            'total_quantity': self.__total_quantity__,
            'taxes':self.__taxes__,

        })

    def __total_quantity__(self, obj):
        tot = 0
        for line in obj.lines:
            tot += line.qty
        self.total = tot
        return self.total

    def __taxes__(self, obj):
        self.cr.execute ( " Select acct.name from pos_order as po " \
                              " LEFT JOIN pos_order_line as pol ON po.id = pol.order_id " \
                              " LEFT JOIN product_taxes_rel as ptr ON pol.product_id = ptr.prod_id " \
                              " LEFT JOIN account_tax as acct ON acct.id = ptr.tax_id " \
                              " WHERE pol.id = %s", (obj.id,))
        res=self.cr.fetchone()[0]
        return res

report_sxw.report_sxw('report.pos.lines', 'pos.order', 'addons/point_of_sale/report/pos_lines.rml', parser=pos_lines,header='internal')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
