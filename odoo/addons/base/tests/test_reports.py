# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

import odoo
import odoo.tests


_logger = logging.getLogger(__name__)

SPECIFIC_MODEL_DOMAINS = {}


@odoo.tests.tagged('post_install', '-at_install', 'post_install_l10n')
class TestReports(odoo.tests.TransactionCase):
    def test_reports(self):
        Report = self.env['ir.actions.report']
        for report in Report.search([('report_type', 'like', 'qweb')]):
            report_model = 'report.%s' % report.report_name
            try:
                self.env[report_model]
            except KeyError:
                # Only test the generic reports here
                _logger.info("testing report %s", report.report_name)
                report_model_domain = SPECIFIC_MODEL_DOMAINS.get(report.report_name, [])
                report_records = self.env[report.model].search(report_model_domain, limit=10)
                if not report_records:
                    _logger.info("no record found skipping report %s", report.report_name)

                # Test report generation
                if not report.multi:
                    for record in report_records:
                        Report._render_qweb_html(report.id, record.ids)
                else:
                    Report._render_qweb_html(report.id, report_records.ids)
            else:
                continue
