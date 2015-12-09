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
        })

    def __total_quantity__(self, obj):
        tot = 0
        for line in obj.lines:
            tot += line.qty
        self.total = tot
        return self.total


class report_pos_lines(osv.AbstractModel):
    _name = 'report.point_of_sale.report_saleslines'
    _inherit = 'report.abstract_report'
    _template = 'point_of_sale.report_saleslines'
    _wrapped_report_class = pos_lines
