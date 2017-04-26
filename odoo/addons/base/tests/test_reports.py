# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

import odoo
import odoo.tests


_logger = logging.getLogger(__name__)


@odoo.tests.common.at_install(False)
@odoo.tests.common.post_install(True)
class TestReports(odoo.tests.TransactionCase):
    def test_reports(self):
        domain = [('report_type', 'like', 'qweb')]
        for report in self.env['ir.actions.report'].search(domain):
            report_model = 'report.%s' % report.report_name
            try:
                self.env[report_model]
            except KeyError:
                # Only test the generic reports here
                _logger.info("testing report %s", report.report_name)
                report_model = self.env[report.model]
                report_records = report_model.search([], limit=10)
                if not report_records:
                    _logger.info("no record found skipping report %s", report.report_name)
                if not report.multi:
                    report_records = report_records[:1]

                # Test report generation
                report.render_qweb_html(report_records.ids)
            else:
                continue
