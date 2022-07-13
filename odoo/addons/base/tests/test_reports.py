# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

import odoo
import odoo.tests


_logger = logging.getLogger(__name__)


@odoo.tests.tagged('post_install', '-at_install', 'post_install_l10n')
class TestReports(odoo.tests.TransactionCase):
    def test_reports(self):
        invoice_domain = [('move_type', 'in', ('out_invoice', 'out_refund', 'out_receipt', 'in_invoice', 'in_refund', 'in_receipt'))]
        specific_model_domains = {
            'account.report_original_vendor_bill': [('move_type', 'in', ('in_invoice', 'in_receipt'))],
            'account.report_invoice_with_payments': invoice_domain,
            'account.report_invoice': invoice_domain,
        }
        for report in self.env['ir.actions.report'].search([('report_type', 'like', 'qweb')]):
            report_model = 'report.%s' % report.report_name
            try:
                self.env[report_model]
            except KeyError:
                # Only test the generic reports here
                _logger.info("testing report %s", report.report_name)
                report_model_domain = specific_model_domains.get(report.report_name, [])
                report_records = self.env[report.model].search(report_model_domain, limit=10)
                if not report_records:
                    _logger.info("no record found skipping report %s", report.report_name)

                # Test report generation
                if not report.multi:
                    for record in report_records:
                        report._render_qweb_html(record.ids)
                else:
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
