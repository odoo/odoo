# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime

from openerp import models, api


class ReportAccountStatement(models.AbstractModel):
    _name = 'report.point_of_sale.report_statement'
    _inherit = 'report.abstract_report'
    _template = 'point_of_sale.report_statement'

    def _get_total(self, statement_line_ids):
        total = 0.0
        for line in statement_line_ids:
            total += line.amount
        return total

    @api.multi
    def render_html(self, data=None):
        Report = self.env['report']
        report = Report._get_report_from_name('point_of_sale.report_statement')
        records = self.env['account.bank.statement'].browse(self.ids)
        docargs = {
            'doc_ids': self._ids,
            'doc_model': report.model,
            'docs': records,
            'data': data,
            'datetime': datetime,
            'get_total': self._get_total,
        }
        return Report.render('point_of_sale.report_statement', docargs)