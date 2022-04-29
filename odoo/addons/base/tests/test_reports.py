# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import io
import logging

import odoo
import odoo.tests

try:
    from pdfminer.converter import TextConverter
    from pdfminer.layout import LAParams
    from pdfminer.pdfdocument import PDFDocument
    from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
    from pdfminer.pdfpage import PDFPage
    from pdfminer.pdfparser import PDFParser
    pdfminer = True
except ImportError:
    pdfminer = False
    from PyPDF2 import PdfFileReader

_logger = logging.getLogger(__name__)


@odoo.tests.tagged('post_install', '-at_install')
class TestReports(odoo.tests.TransactionCase):
    def test_reports(self):
        domain = [('report_type', 'like', 'qweb')]
        for report in self.env['ir.actions.report'].search(domain):
            report_model = 'report.%s' % report.report_name
            if report_model not in self.env:
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


@odoo.tests.tagged('post_install', '-at_install')
class TestReportsPdf(odoo.tests.HttpCase):
    def test_report_pdf_rendering(self):
        """
        This test aims to test as much as possible the current pdf rendering,
        especially multipage headers and footer
        which currently justify using wkhtmltopdf with patched qt
        """

        self.env['ir.ui.view'].create({
            'type': 'qweb',
            'name': 'test_report_partner',
            'key': 'base.test_report_partner',
            'arch': '''
                <t t-name="base.test_report_partner">                    
                    <t t-set="company" t-value="res_company"/>
                    <t t-call="web.html_container">
                        <t t-foreach="docs" t-as="o">
                            <div class="header">
                                <img t-if="company.logo" t-att-src="image_data_uri(company.logo)" style="max-height: 45px;" alt="Logo"/>
                                <span id="header_text">Some header Text</span>
                            </div>
                            <div class="article">
                                <t t-set="partner" t-value="o"/>
                                <div class="page">
                                    Name: <t t-esc="partner.name"/>
                                    <div style="page-break-before:always;">
                                        Second page for <t t-esc="partner.name"/>
                                    </div>
                                </div>
                            </div>
                            <div class="footer">
                                Footer for <t t-esc="partner.name"/> Page: <span class="page"/> / <span class="topage"/>
                            </div>
                        </t>
                    </t>
                </t>
            ''',
        })

        report = self.env['ir.actions.report'].create({
            'name': 'Test Report Partner',
            'model': 'res.partner',
            'report_name': 'base.test_report_partner',
            'paperformat_id': self.env.ref('base.paperformat_euro').id,
        })
        partners = self.env['res.partner'].create([{
            'name': 'Report record 1',
        }, {
            'name': 'Report record 2',
        }])

        pdf_content = report.with_context(force_report_rendering=True)._render_qweb_pdf(partners.ids)[0]
        ioBytes = io.BytesIO(pdf_content)

        expected_page_number = len(partners)*2

        if pdfminer:
            parser = PDFParser(ioBytes)
            doc = PDFDocument(parser)
            pages = list(PDFPage.create_pages(doc))
            ressource_manager = PDFResourceManager()

            self.assertEqual(len(pages), expected_page_number)
            pages_lines = []

            for page in pages:
                output_string = io.StringIO()
                text_converter = TextConverter(ressource_manager, output_string, laparams=LAParams())
                interpreter = PDFPageInterpreter(ressource_manager, text_converter)
                interpreter.process_page(page)
                self.assertEqual(page.mediabox, [0, 0, 595, 842]) # expected ppi for a4, USLetter would be [0, 0, 612, 792] cf: https://developers.hp.com/hp-linux-imaging-and-printing/tech_docs/page_sizes
                pages_lines.append([line.strip() for line in output_string.getvalue().split('\n') if line.strip()])

            expected_pages_lines = []
            for partner in partners:
                expected_pages_lines.append([
                    'Some header Text',
                    f'Name: {partner.name}',
                    f'Footer for {partner.name} Page: 1 / 2',
                ])
                expected_pages_lines.append([
                    'Some header Text',
                    f'Second page for {partner.name}',
                    f'Footer for {partner.name} Page: 2 / 2',
                ])
            self.assertEqual(pages_lines, expected_pages_lines)
        else:
            _logger.warning('pdfminer.six is missing, skipping pdf content check')
            reader = PdfFileReader(ioBytes, strict=False, overwriteWarnings=False)
            self.assertEqual(reader.getNumPages(), expected_page_number)
