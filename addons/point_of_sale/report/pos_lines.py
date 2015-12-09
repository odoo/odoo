# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
from odoo import api, models


class ReportPosLines(models.AbstractModel):
    _name = "report.point_of_sale.report_saleslines"

    @api.multi
    def render_html(self, data=None):
        Report = self.env['report']
        report = Report._get_report_from_name('point_of_sale.report_saleslines')
        orders = self.env['pos.order'].browse(self.ids)

        docargs = {
            'doc_ids': self.ids,
            'doc_model': report.model,
            'docs': orders,
            'time': time,
        }
        return Report.render('point_of_sale.report_saleslines', docargs)
