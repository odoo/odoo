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

class pos_details_summary(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(pos_details_summary, self).__init__(cr, uid, name, context=context)
        self.total = 0.0
        self.localcontext.update({
            'time': time,
            'strip_name': self._strip_name,
            'getpayments': self._get_payments,
            'getqtytotal': self._get_qty_total,
            'getsumdisc': self._get_sum_discount,
            'getpaidtotal': self._paid_total,
            'gettotalofthaday': self._total_of_the_day,
            'getsuminvoice': self._sum_invoice,
            'gettaxamount': self._get_tax_amount,
            'getsalestotal': self._get_sales_total,
            'getstartperiod': self._get_start_period,
            'getendperiod': self._get_end_period,
            'getcompany':self.get_company
        })

    def get_company(self, objects):
        comp=[obj.company_id.name for obj in objects]
        return '%s' % (comp[0])

    def _get_qty_total(self, objects):
        #code for the sum of qty_total
        return reduce(lambda acc, object:
                                        acc + reduce(
                                                lambda sum_qty, line:
                                                        sum_qty + line.qty,
                                                object.lines,
                                                0 ),
                                    objects,
                                    0)

    def _get_sum_discount(self, objects):
        #code for the sum of discount value
        return reduce(lambda acc, object:
                                        acc + reduce(
                                                lambda sum_dis, line:
                                                        sum_dis + ((line.price_unit * line.qty ) * (line.discount / 100)),
                                                object.lines,
                                                0.0),
                                    objects,
                                    0.0 )

    def _get_payments(self, objects):
        result = {}
        for obj in objects:
            for statement in obj.statement_ids:
                if statement.journal_id:
                    result[statement.journal_id] = result.get(statement.journal_id, 0.0) + statement.amount
        return result

    def _paid_total(self, objects):
        return sum(self._get_payments(objects).values(), 0.0)

    def _total_of_the_day(self, objects):
        total_paid = self._paid_total(objects)
        total_invoiced = self._sum_invoice(objects)
        return total_paid - total_invoiced

    def _sum_invoice(self, objects):
        return reduce(lambda acc, obj:
                                                acc + obj.invoice_id.amount_total,
                                    [o for o in objects if o.invoice_id and o.invoice_id.number],
                                    0.0)

    def _ellipsis(self, string, maxlen=100, ellipsis = '...'):
        ellipsis = ellipsis or ''
        return string[:maxlen - len(ellipsis) ] + (ellipsis, '')[len(string) < maxlen]

    def _strip_name(self, name, maxlen=50):
        return self._ellipsis(name, maxlen, ' ...')

    def _get_tax_amount(self, objects):
        res = {}
        list_ids = []
        for order in objects:
            for line in order.lines:
                if len(line.product_id.taxes_id):
                    tax = line.product_id.taxes_id[0]
                    res[tax.name] = (line.price_unit * line.qty * (1-(line.discount or 0.0) / 100.0)) + (tax.id in list_ids and res[tax.name] or 0)
                    list_ids.append(tax.id)
        return res

    def _get_sales_total(self, objects):
        return reduce(lambda x, o: x + len(o.lines), objects, 0)

    def _get_start_period(self, objects):
        date_orders = sorted([obj.date_order for obj in objects])
        min_date = date_orders[0]
        return '%s' % min_date


    def _get_end_period(self, objects):
        date_orders = sorted([obj.date_order for obj in objects])
        max_date = date_orders[-1]
        return '%s' % max_date


report_sxw.report_sxw('report.pos.details_summary',
                                            'pos.order',
                                            'addons/point_of_sale/report/pos_details_summary.rml',
                                            parser=pos_details_summary,
                                            header='internal')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
