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

rml_parents = {
    'tr': 1,
    'li': 1,
    'story': 0,
    'section': 0
}

class sale_order_1(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(sale_order_1, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'time': time,
            'sale_order_lines': self.sale_order_lines,
          #  'repeat_In':self.repeat_In,
        })
        self.context = context

    def sale_order_lines(self, sale_order):
        result = []
        sub_total = {}
        order_lines = []
        res = {}
        obj_order_line = self.pool.get('sale.order.line')
        ids = obj_order_line.search(self.cr, self.uid, [('order_id', '=', sale_order.id)])
        for id in range(0, len(ids)):
            order = obj_order_line.browse(self.cr, self.uid, ids[id], self.context.copy())
            order_lines.append(order)

        i = 1
        j = 0
        sum_flag = {}
        sum_flag[j] = -1
        for entry in order_lines:
            res = {}

            if entry.layout_type == 'article':
                res['tax_id'] = ', '.join(map(lambda x: x.name, entry.tax_id)) or ''
                res['name'] = entry.name
                res['product_uom_qty'] = entry.product_uos and entry.product_uos_qty or entry.product_uom_qty or 0.00
                res['product_uom'] = entry.product_uos and entry.product_uos.name or entry.product_uom.name
                res['price_unit'] = entry.price_unit or 0.00
                res['discount'] = entry.discount and entry.discount or 0.00
                res['price_subtotal'] = entry.price_subtotal and entry.price_subtotal or 0.00
                sub_total[i] = entry.price_subtotal and entry.price_subtotal
                i = i + 1
                res['note'] = entry.notes or ''
                res['currency'] = sale_order.pricelist_id.currency_id.name
                res['layout_type'] = entry.layout_type
            else:
                res['product_uom_qty'] = ''
                res['price_unit'] = ''
                res['discount'] = ''
                res['tax_id'] = ''
                res['layout_type'] = entry.layout_type
                res['note'] = entry.notes or ''
                res['product_uom'] = ''

                if entry.layout_type == 'subtotal':
                    res['name'] = entry.name
                    sum = 0
                    sum_id = 0
                    if sum_flag[j] == -1:
                        temp = 1
                    else:
                        temp = sum_flag[j]

                    for sum_id in range(temp, len(sub_total)+1):
                        sum += sub_total[sum_id]
                    sum_flag[j+1] = sum_id +1

                    j = j + 1
                    res['price_subtotal'] = sum
                    res['currency'] = sale_order.pricelist_id.currency_id.name
                    res['quantity'] = ''
                    res['price_unit'] = ''
                    res['discount'] = ''
                    res['tax_id'] = ''
                    res['product_uom'] = ''
                elif entry.layout_type == 'title':
                    res['name'] = entry.name
                    res['price_subtotal'] = ''
                    res['currency'] = ''
                elif entry.layout_type == 'text':
                    res['name'] = entry.name
                    res['price_subtotal'] = ''
                    res['currency'] = ''
                elif entry.layout_type == 'line':
                    res['product_uom_qty'] = ''
                    res['price_unit'] = ' '
                    res['discount'] = ''
                    res['tax_id'] = ''
                    res['product_uom'] = ''
                    res['name'] = '__________________________________________________________________________________________________________________'
                    res['price_subtotal'] = ''
                    res['currency'] = ''
                elif entry.layout_type == 'break':
                    res['layout_type'] = entry.layout_type
                    res['name'] = entry.name
                    res['price_subtotal'] = ''
                    res['currency'] = ''
                else:
                    res['name'] = entry.name
                    res['price_subtotal'] = ''
                    res['currency'] = sale_order.pricelist_id.currency_id.name

            result.append(res)
        return result

report_sxw.report_sxw('report.sale.order.layout', 'sale.order', 'addons/sale_layout/report/report_sale_layout.rml', parser=sale_order_1)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:


