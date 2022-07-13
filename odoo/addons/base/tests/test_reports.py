# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

import odoo
import odoo.tests


_logger = logging.getLogger(__name__)


@odoo.tests.tagged('post_install', '-at_install')
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
                report._render_qweb_html(report_records.ids)
            else:
                continue

    def test_barcode_check_digit(self):
        ean8 = "87111125"
        self.assertEqual(self.env['ir.actions.report'].get_barcode_check_digit("0" * 10 + ean8), int(ean8[-1]))
        ean13 = "1234567891231"
        self.assertEqual(self.env['ir.actions.report'].get_barcode_check_digit("0" * 5 + ean13), int(ean13[-1]))

    def test_barcode_encoding(self):
        self.assertTrue(self.env['ir.actions.report'].check_barcode_encoding('20220006', 'ean8'))
        self.assertTrue(self.env['ir.actions.report'].check_barcode_encoding('93855341', 'ean8'))
        self.assertTrue(self.env['ir.actions.report'].check_barcode_encoding('2022071416014', 'ean13'))
        self.assertTrue(self.env['ir.actions.report'].check_barcode_encoding('9745213796142', 'ean13'))

        self.assertFalse(self.env['ir.actions.report'].check_barcode_encoding('2022a006', 'ean8'), 'should contains digits only')
        self.assertFalse(self.env['ir.actions.report'].check_barcode_encoding('20220000', 'ean8'), 'incorrect check digit')
        self.assertFalse(self.env['ir.actions.report'].check_barcode_encoding('93855341', 'ean13'), 'ean13 is a 13-digits barcode')
        self.assertFalse(self.env['ir.actions.report'].check_barcode_encoding('9745213796142', 'ean8'), 'ean8 is a 8-digits barcode')
        self.assertFalse(self.env['ir.actions.report'].check_barcode_encoding('9745213796148', 'ean13'), 'incorrect check digit')
        self.assertFalse(self.env['ir.actions.report'].check_barcode_encoding('2022!71416014', 'ean13'), 'should contains digits only')
        self.assertFalse(self.env['ir.actions.report'].check_barcode_encoding('0022071416014', 'ean13'), 'when starting with one zero, it indicates that a 12-digit UPC-A code follows')
