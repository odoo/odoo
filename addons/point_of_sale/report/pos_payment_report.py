# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
from odoo import api, models


class ReportPosPayment(models.AbstractModel):
    _name = 'report.point_of_sale.report_payment'

    def _get_pos_payment(self, orders=False):
        data = dict(map(lambda x: (x, {'lines': [], 'total': 0.0}), orders.ids))
        for order in orders:
            for line in order.lines:
                product = line.product_id
                data[order.id]['lines'].append({
                    'name': product.product_tmpl_id.name,
                    'code': product.code,
                    'uom': product.uom_id.name,
                    'discount': line.discount,
                    'price_unit': line.price_unit,
                    'qty': line.qty,
                    'total': (line.price_unit * line.qty * (1 - (line.discount) / 100.0))
                })
                data[order.id]['total'] += line.price_unit * line.qty
        return data

    @api.multi
    def render_html(self, data=None):
        Report = self.env['report']
        report = Report._get_report_from_name('point_of_sale.report_payment')
        orders = self.env['pos.order'].browse(self.ids)

        docargs = {
            'doc_ids': self.ids,
            'doc_model': report.model,
            'docs': orders.ids,
            'time': time,
            'pos_payments': self._get_pos_payment(orders),
        }
        return Report.render('point_of_sale.report_payment', docargs)
