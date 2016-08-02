# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import os
from odoo import tools
from odoo.tests import common


class TestReportWebkit(common.TransactionCase):
    """Print the report_webkit demo report."""

    def setUp(self):
        super(TestReportWebkit, self).setUp()
        self.IrActionsReportXml = self.env['ir.actions.report.xml']

    def test_00_print_report_webkit(self):
        action_reports = self.IrActionsReportXml.search([])
        data, format = self.IrActionsReportXml.render_report(action_reports.ids, 'webkit.ir.actions.report.xml', {})
        if tools.config['test_report_directory']:
            file(os.path.join(tools.config['test_report_directory'], 'report_webkit_demo_report.'+format), 'wb+').write(data)
