# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import io
import logging
import os
import tempfile

import PyPDF2

import odoo
from odoo.tests import TransactionCase, HttpCase, get_db_name, tagged
from odoo.tools import config, file_open


_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install', 'post_install_l10n', 'reports')
class TestReports(TransactionCase):
    def test_reports(self):
        invoice_domain = [('move_type', 'in', ('out_invoice', 'out_refund', 'out_receipt', 'in_invoice', 'in_refund', 'in_receipt'))]
        specific_model_domains = {
            'account.report_original_vendor_bill': [('move_type', 'in', ('in_invoice', 'in_receipt'))],
            'account.report_invoice_with_payments': invoice_domain,
            'account.report_invoice': invoice_domain,
        }
        Report = self.env['ir.actions.report']
        for report in Report.search([('report_type', 'like', 'qweb')]):
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
                        Report._render_qweb_html(report.id, record.ids)
                else:
                    Report._render_qweb_html(report.id, report_records.ids)
            else:
                continue

class PDFMixin:
    def assertPdfEqual(self, test_content, truth_path):
        with file_open(truth_path, 'rb') as truth_file:
            truth_content = truth_file.read()

        # neuter dates
        before, _, after = test_content.partition(b'CreationDate')
        test_content = before + after.partition(b'\n')[2]
        before, _, after = truth_content.partition(b'CreationDate')
        truth_content = before + after.partition(b'\n')[2]

        # assert equal
        if test_content == truth_content:
            return

        pdf_dir = os.path.join(config['screenshots'], get_db_name(), 'pdfs')
        os.makedirs(pdf_dir, exist_ok=True)

        # failure
        filename = os.path.basename(truth_path)
        test_path = os.path.join(pdf_dir, filename)
        with open(test_path, 'wb') as test_file:
            test_file.write(test_content)

        raise AssertionError(' '.join(f"""
            The PDF generated during the test isn't equivalent to the
            PDF stored at {truth_path} which is our 'truth' file. The
            generated PDF is saved at {test_path} so you can look up the
            differences.
            """.strip().split())
        )


@tagged('post_install', '-at_install', 'post_install_l10n', 'reports')
class TestReportsPDF(HttpCase, PDFMixin):
    def test_report_pdf(self):
        self.env['ir.asset'].create({
            'bundle': 'base.test_assets_greetings',
            'name': '/base/tests/static/greetings.css',
            'path': '/base/tests/static/greetings.css',
        })
        self.env['ir.asset'].create({
            'bundle': 'base.test_assets_greetings',
            'name': '/base/tests/static/greetings.js',
            'path': '/base/tests/static/greetings.js',
        })
        with file_open('base/tests/static/greetings.xml', 'r') as greetings_xml:
            view = self.env['ir.ui.view'].create({
                'name': 'test_greetings',
                'type': 'qweb',
                'arch': greetings_xml.read()
            })
            self.env['ir.model.data'].create({
                'name': 'test_greetings',
                'model': 'ir.ui.view',
                'module': 'base',
                'res_id': view.id,
            })
        action = self.env['ir.actions.report'].create({
            'name': 'test_reports',
            'model': 'res.company',
            'binding_model_id': self.env.user.company_id.id,
            'binding_type': 'report',
            'report_type': 'qweb-pdf',
            'report_name': 'base.test_greetings',
            'report_file': 'test_greetings',
        })

        iar = self.env['ir.actions.report'].with_context(force_report_rendering=True)
        content_pdf, report_type = iar._render(action, self.env.company.ids)
        self.assertEqual(report_type, 'pdf')
        self.assertPdfEqual(content_pdf, 'base/tests/static/greetings.pdf')
