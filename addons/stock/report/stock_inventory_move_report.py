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

class stock_inventory_move(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(stock_inventory_move, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
             'time': time,
             'qty_total':self._qty_total
        })

    def _qty_total(self, objects):
        total = 0.0
        uom = objects[0].product_uom.name
        for obj in objects:
            total += obj.product_qty
        return {'quantity':total,'uom':uom}

report_sxw.report_sxw(
    'report.stock.inventory.move',
    'stock.inventory',
    'addons/stock/report/stock_inventory_move.rml',
    parser=stock_inventory_move,
    header='internal'
)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
