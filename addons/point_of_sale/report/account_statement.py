# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
from openerp.osv import osv
from openerp.report import report_sxw


class account_statement(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(account_statement, self).__init__(cr, uid, name, context=context)
        self.total = 0.0
        self.localcontext.update({
            'time': time,
            'get_total': self._get_total,
            'get_data': self._get_data,
        })

    def _get_data(self, statement):
        lines = []
        for line in statement.line_ids:
            lines.append(line)

        return lines

    def _get_total(self, statement_line_ids):
        total = 0.0
        for line in statement_line_ids:
            total += line.amount
        return total


class report_account_statement(osv.AbstractModel):
    _name = 'report.point_of_sale.report_statement'
    _inherit = 'report.abstract_report'
    _template = 'point_of_sale.report_statement'
    _wrapped_report_class = account_statement
