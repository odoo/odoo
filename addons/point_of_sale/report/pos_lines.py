# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from openerp import api, models


class ReportPosLines(models.AbstractModel):
    _name = 'report.point_of_sale.report_saleslines'
    _inherit = 'report.abstract_report'
    _template = 'point_of_sale.report_saleslines'

    def __total_quantity__(self, record):
        tot = 0
        for line in record.lines:
            tot += line.qty
        return tot

    def __taxes__(self, record):
        self.env.cr.execute ( " Select acct.name from pos_order as po " \
                              " LEFT JOIN pos_order_line as pol ON po.id = pol.order_id " \
                              " LEFT JOIN product_product as pp ON pol.product_id = pp.id"
                              " LEFT JOIN product_taxes_rel as ptr ON pp.product_tmpl_id = ptr.prod_id " \
                              " LEFT JOIN account_tax as acct ON acct.id = ptr.tax_id " \
                              " WHERE pol.id = %s", (record.id,))
        return self.env.cr.fetchone()[0]

    @api.multi
    def render_html(self, data=None):
        Report = self.env['report']
        report = Report._get_report_from_name('point_of_sale.report_saleslines')
        docargs = {
            'doc_ids': self._ids,
            'doc_model': report.model,
            'docs': self.env['pos.order'].browse(self.ids),
            'data': data,
            'time': time,
            'total_quantity': self.__total_quantity__,
            'taxes': self.__taxes__,
        }
        return Report.render('point_of_sale.report_saleslines', docargs)
