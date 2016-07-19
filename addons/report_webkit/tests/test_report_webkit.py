# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import os
import odoo.tests
from odoo import tools
from odoo.report import render_report

class TestReportsWebkit(odoo.tests.TransactionCase):

    def test_report_webkit(self):
        report_ids = self.env['ir.actions.report.xml'].search([]).ids
        data, format = render_report(self.env.cr, self.env.uid, report_ids, 'webkit.ir.actions.report.xml', {}, context=self.env.context)
        if tools.config['test_report_directory']:
            file(os.path.join(tools.config['test_report_directory'], 'report_webkit_demo_report.' + format), 'wb+').write(data)
