# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from openerp import models, api


class ReportPosPayment(models.AbstractModel):
    _name = 'report.point_of_sale.report_payment'
    _inherit = 'report.abstract_report'
    _template = 'point_of_sale.report_payment'

    def _pos_payment(self, record):
        self.total = 0
        data = {}
        if self.env['pos.order'].search([('id', '=', record.id)]):
            self.env.cr.execute ("select pt.name,pp.default_code as code,pol.qty,pu.name as uom,pol.discount,pol.price_unit, " \
                                 "(pol.price_unit * pol.qty * (1 - (pol.discount) / 100.0)) as total  " \
                                 "from pos_order as po,pos_order_line as pol,product_product as pp,product_template as pt, product_uom as pu " \
                                 "where pt.id=pp.product_tmpl_id and pp.id=pol.product_id and po.id = pol.order_id  and pu.id=pt.uom_id " \
                                 "and po.state IN ('paid','invoiced') and to_char(date_trunc('day',po.date_order),'YYYY-MM-DD')::date = current_date and po.id=%d"%(record.id))
            data=self.env.cr.dictfetchall()
        else:
            self.env.cr.execute ("select pt.name,pp.default_code as code,pol.qty,pu.name as uom,pol.discount,pol.price_unit, " \
                                 "(pol.price_unit * pol.qty * (1 - (pol.discount) / 100.0)) as total  " \
                                 "from pos_order as po,pos_order_line as pol,product_product as pp,product_template as pt, product_uom as pu  " \
                                 "where pt.id=pp.product_tmpl_id and pp.id=pol.product_id and po.id = pol.order_id and pu.id=pt.uom_id  " \
                                 "and po.state IN ('paid','invoiced') and to_char(date_trunc('day',po.date_order),'YYYY-MM-DD')::date = current_date")
            data=self.env.cr.dictfetchall()
        for d in data:
            self.total += d['price_unit'] * d['qty']
        return data

    def _pos_payment_total(self):
        return self.total

    @api.multi
    def render_html(self, data=None):
        Report = self.env['report']
        report = Report._get_report_from_name('point_of_sale.report_payment')
        docargs = {
            'doc_ids': self._ids,
            'doc_model': report.model,
            'docs': self.env['pos.order'].browse(self.ids),
            'data': data,
            'time': time,
            'pos_payment': self._pos_payment,
            'pos_payment_total': self._pos_payment_total,
        }
        return Report.render('point_of_sale.report_payment', docargs)
