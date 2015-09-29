# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
from openerp.osv import osv
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
                              " LEFT JOIN product_product as pp ON pol.product_id = pp.id"
                              " LEFT JOIN product_taxes_rel as ptr ON pp.product_tmpl_id = ptr.prod_id " \
                              " LEFT JOIN account_tax as acct ON acct.id = ptr.tax_id " \
                              " WHERE pol.id = %s", (obj.id,))
        res=self.cr.fetchone()[0]
        return res


class report_pos_lines(osv.AbstractModel):
    _name = 'report.point_of_sale.report_saleslines'
    _inherit = 'report.abstract_report'
    _template = 'point_of_sale.report_saleslines'
    _wrapped_report_class = pos_lines
