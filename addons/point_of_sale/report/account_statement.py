# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ReportAccountStatement(models.AbstractModel):
    _name = 'report.point_of_sale.report_statement'

    @api.multi
    def render_html(self, data=None):
        Report = self.env['report']
        report = Report._get_report_from_name('point_of_sale.report_statement')
        docargs = {
            'doc_ids': self.ids,
            'doc_model': report.model,
            'docs': self.env['account.bank.statement'].browse(self.ids),
        }
        return Report.render('point_of_sale.report_statement', docargs)
