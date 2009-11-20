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


class pos_details_summary(report_sxw.rml_parse):

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

    def _get_payments(self, objects, ignore_gift=False):
        gift_journal_id = None
        if ignore_gift:
            config_journal_ids = self.pool.get("pos.config.journal").search(self.cr, self.uid, [('code', '=', 'GIFT')])
            if len(config_journal_ids):
                config_journal = self.pool.get("pos.config.journal").browse(self.cr, self.uid, config_journal_ids, {})[0]
                gift_journal_id = config_journal.journal_id.id

        result = {}
        for obj in objects:
            for payment in obj.payments:
                if gift_journal_id and gift_journal_id == payment.journal_id.id:
                    continue
                result[payment.journal_id.name] = result.get(payment.journal_id.name, 0.0) + payment.amount
        return result

    def _paid_total(self, objects):
        return sum(self._get_payments(objects, True).values(), 0.0)

    def _total_of_the_day(self, objects):
        total_paid = sum(self._get_payments(objects, True).values(), 0.0)
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

    def _get_period(self, objects):
        date_orders = [obj.date_order for obj in objects]
        min_date = min(date_orders)
        max_date = max(date_orders)
        if min_date == max_date:
            return '%s' % min_date
        else:
            return '%s - %s' % (min_date, max_date)

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
            'getperiod': self._get_period,
        })

report_sxw.report_sxw('report.pos.details_summary',
                                            'pos.order',
                                            'addons/point_of_sale/report/pos_details_summary.rml',
                                            parser=pos_details_summary,
                                            header=None)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

