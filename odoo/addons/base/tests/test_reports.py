# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import io
import logging
import unittest

import odoo
import odoo.tests

try:
    from pdfminer.converter import PDFPageAggregator
    from pdfminer.layout import LAParams, LTFigure, LTTextBox
    from pdfminer.pdfdocument import PDFDocument
    from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
    from pdfminer.pdfpage import PDFPage
    from pdfminer.pdfparser import PDFParser
    pdfminer = True
except ImportError:
    pdfminer = False

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


# Some paper format examples
PAPER_SIZES = {
    (842, 1190): 'A3',
    (595, 842): 'A4',
    (420, 595): 'A5',
    (297, 420): 'A6',
    (612, 792): 'Letter',
    (612, 1008): 'Legal',
    (792, 1224): 'Ledger',
}


class TestReportsRenderingCommon(odoo.tests.HttpCase):

    def setUp(self):
        super().setUp()
        self.report = self.env['ir.actions.report'].create({
            'name': 'Test Report Partner',
            'model': 'res.partner',
            'report_name': 'test_report.test_report_partner',
            'paperformat_id': self.env.ref('base.paperformat_euro').id,
        })

        self.partners = self.env['res.partner'].create([{
            'name': f'Report record {i}',
        } for i in range(2)])

        self.report_view = self.env['ir.ui.view'].create({
            'type': 'qweb',
            'name': 'test_report_partner',
            'key': 'test_report.test_report_partner',
            'arch': "<t></t>",
        })

    def get_paper_format(self, mediabox):
        """
            :param: mediabox: a page mediabox. (Example: (0, 0, 595, 842))
            :return: a (format, orientation). Example ('A4', 'portait')
        """
        x, y, width, height = mediabox
        self.assertEqual((x, y), (0, 0), "Expecting top corner to be 0, 0 ")
        orientation = 'portait'
        paper_size = (width, height)
        if width > height:
            orientation = 'landscape'
            paper_size = (height, width)
        return PAPER_SIZES.get(paper_size, f'custom{paper_size}'), orientation

    def create_pdf(self, partners=None, header_content=None, page_content=None, footer_content=None, save_pdf=False):
        if header_content is None:
            header_content = '''
                <img t-if="company.logo" t-att-src="image_data_uri(company.logo)" style="max-height: 45px;" alt="Logo"/>
                <span>Some header Text</span>
            '''

        if footer_content is None:
            footer_content = '''
                <div style="text-align:center">Footer for <t t-esc="o.name"/> Page: <span class="page"/> / <span class="topage"/></div>
            '''

        if page_content is None:
            page_content = '''
                <div class="page">
                    <div style="background-color:red">
                        Name: <t t-esc="o.name"/>
                    </div>
                </div>
            '''

        self.report_view.arch = f'''
                <t t-name="test_report.test_report_partner">
                    <t t-set="company" t-value="res_company"/>
                    <t t-call="web.html_container">
                        <t t-foreach="docs" t-as="o">
                            <div class="header" style="font-family:Sans">
                                {header_content}
                            </div>
                            <div class="article" style="font-family:Sans">
                                {page_content}
                            </div>
                            <div class="footer" style="font-family:Sans">
                                {footer_content}
                            </div>
                        </t>
                    </t>
                </t>
            '''
        # this templates doesn't use the "web.external_layout" in order to simplify the final result and make the edition of footer and header easier
        # this test does not aims to test company base.document.layout, but the rendering only.
        if partners is None:
            partners = self.partners
        pdf_content = self.report.with_context(force_report_rendering=True)._render_qweb_pdf(partners.ids)[0]
        if save_pdf:
            from pathlib import Path
            with open(str(Path.home())+'/test.pdf', 'wb') as f:
                f.write(pdf_content)
        return pdf_content

    def _get_pdf_pages(self, pdf_content):
        ioBytes = io.BytesIO(pdf_content)
        parser = PDFParser(ioBytes)
        doc = PDFDocument(parser)
        return list(PDFPage.create_pages(doc))

    def _parse_pdf(self, pdf_content, expected_format=('A4', 'portait')):
        """
            :param: pdf_content: the bdf binary content
            :param: expected_format: a get_paper_format like format.
            :return: list[list[(box, Element)]] a list of element per page
            Note: box is a 4 float tuple based on the top left corner to ease ordering of elements.
            The result is also rounded to one digit
        """
        pages = self._get_pdf_pages(pdf_content)
        ressource_manager = PDFResourceManager()
        device = PDFPageAggregator(ressource_manager, laparams=LAParams())
        interpreter = PDFPageInterpreter(ressource_manager, device)

        parsed_pages = []
        for page in pages:
            self.assertEqual(
                self.get_paper_format(page.mediabox),
                expected_format,
                f"Expecting pdf to be in A4 portait format"
            ) # this is the default expected format and other layout assertions are based on this one.
            page_height = page.mediabox[3] # only
            interpreter.process_page(page)
            layout = device.get_result()
            elements = []
            parsed_pages.append(elements)
            for obj in layout:
                box = (
                    round(page_height-obj.y1, 1),
                    round(obj.x0, 1),
                    round(page_height-obj.y0, 1),
                    round(obj.x1, 1),
                )
                if isinstance(obj, LTTextBox):
                    #inverse x to start from top left corner
                    elements.append((box, obj.get_text().strip()))
                elif isinstance(obj, LTFigure):
                    elements.append((box, 'LTFigure'))
            elements.sort()

        return parsed_pages

    def assertPageFormat(self, format, orientation):
        pdf_content = self.create_pdf()
        pages = self._get_pdf_pages(pdf_content)
        self.assertEqual(len(pages), 2)
        for page in pages:
            self.assertEqual(
                self.get_paper_format(page.mediabox),
                (format, orientation),
                f"Expecting pdf to be in {format} {orientation} format"
            )


@odoo.tests.tagged('post_install', '-at_install', 'pdf_rendering')
class TestReportsRendering(TestReportsRenderingCommon):
    """
        This test aims to test as much as possible the current pdf rendering,
        especially multipage headers and footers
        (the main reason why we are currently using wkhtmltopdf with patched qt)
        A custom template without web.external_layout is used on purpose in order to
        easily test headers and footer regarding rendering only,
        without using any comany document.layout logic
    """

    def test_format_A4(self):
        self.report.paperformat_id = self.env.ref('base.paperformat_euro')
        self.assertPageFormat('A4', 'portait')

    def test_format_letter(self):
        self.report.paperformat_id = self.env.ref('base.paperformat_us')
        self.assertPageFormat('Letter', 'portait')

    def test_format_landscape(self):
        format = self.env.ref('base.paperformat_euro')
        format.orientation='Landscape'
        self.report.paperformat_id = format
        self.assertPageFormat('A4', 'landscape')

    def test_layout(self):
        pdf_content = self.create_pdf()
        pages = self._parse_pdf(pdf_content)
        self.assertEqual(len(pages), 2)
        expected_pages = []
        for partner in self.partners:
            expected_pages.append([
                ((14.3, 29.6, 43.1, 137.2), 'LTFigure'),
                ((16.0, 137.2, 33.4, 234.6), 'Some header Text'),
                ((109.5, 29.6, 126.9, 147.0), f'Name: {partner.name}'),
                ((747.9, 201.9, 765.3, 393.4), f'Footer for {partner.name} Page: 1 / 1'),
            ])
        self.assertEqual(
            pages,
            expected_pages
        )

    def test_report_pdf_page_break(self):

        partners = self.partners[:2]
        page_content = '''
                <div class="page">
                    <div style="background-color:red">
                        Name: <t t-esc="o.name"/>
                    </div>
                    <div style="page-break-before:always;background-color:blue">
                        Last page for <t t-esc="o.name"/>
                    </div>
                </div>
            '''

        pdf_content = self.create_pdf(partners=partners, page_content=page_content)

        pages = self._parse_pdf(pdf_content)

        self.assertEqual(len(pages), 4, "Expecting 2 pages * 2 partners")

        expected_pages_lines = []
        for partner in self.partners:
            expected_pages_lines.append([
                'LTFigure', #logo
                'Some header Text',
                f'Name: {partner.name}',
                f'Footer for {partner.name} Page: 1 / 2',
            ])
            expected_pages_lines.append([
                'LTFigure', #logo
                'Some header Text',
                f'Last page for {partner.name}',
                f'Footer for {partner.name} Page: 2 / 2',
            ])
        pages_contents = [[elem[1] for elem in page] for page in pages]
        self.assertEqual(pages_contents, expected_pages_lines)

    def test_pdf_render_page_overflow(self):
        page_content = '''
            <div class="page">
                <div style="background-color:red">
                    Name: <t t-esc="o.name"/>
                    <div t-foreach="range(50)" t-as="pos" t-esc="pos"/>
                </div>
            </div>
        '''
        pdf_content = self.create_pdf(page_content=page_content)
        pages = self._parse_pdf(pdf_content)

        page_break_at = 40 # this may change if font size/family or margins are different: not an assertion

        expected_pages_lines = []
        for partner in self.partners:
            expected_pages_lines.append([
                'LTFigure', #logo
                'Some header Text',
                f'Name: {partner.name}\n' + '\n'.join([str(i) for i in range(page_break_at)]),
                f'Footer for {partner.name} Page: 1 / 2',
            ])
            expected_pages_lines.append([
                'LTFigure', #logo
                'Some header Text',
                f'\n'.join([str(i) for i in range(page_break_at, 50)]),
                f'Footer for {partner.name} Page: 2 / 2',
            ])
        pages_contents = [[elem[1] for elem in page] for page in pages]
        self.assertEqual(pages_contents, expected_pages_lines)

    def test_thead_tbody_repeat(self):
        """
            Check that thead and t-foot are repeated after page break inside a tbody
        """
        page_content = '''
            <div class="page">
                <table class="table">
                    <thead><tr><th> T1 </th><th> T2 </th><th> T3 </th></tr></thead>
                    <tbody>
                    <t t-foreach="range(30)" t-as="pos">
                        <tr><td><t t-esc="pos"/></td><td><t t-esc="pos"/></td><td><t t-esc="pos"/></td></tr>
                    </t>
                    </tbody>
                    <tfoot><tr><th> T1 </th><th> T2 </th><th> T3 </th></tr></tfoot>
                </table>
            </div>
        '''

        pdf_content = self.create_pdf(page_content=page_content)
        pages = self._parse_pdf(pdf_content)

        page_break_at = 18 # this may change if font size/family or margins are different: not an assertion

        def expected_table(start, end):
            table = ['T1', 'T2', 'T3'] # thead
            for i in range(start, end):
                table += [str(i), str(i), str(i)]
            table += ['T1', 'T2', 'T3'] # tfoot
            return table

        expected_pages_lines = []
        for partner in self.partners:
            expected_pages_lines.append([
                'LTFigure', #logo
                'Some header Text'
            ] + expected_table(0, page_break_at) + [
                f'Footer for {partner.name} Page: 1 / 2',
            ])
            expected_pages_lines.append([
                'LTFigure', #logo
                'Some header Text'
            ] + expected_table(page_break_at, 30) + [
                f'Footer for {partner.name} Page: 2 / 2',
            ])
        pages_contents = [[elem[1] for elem in page] for page in pages]
        self.assertEqual(pages_contents, expected_pages_lines)


@odoo.tests.tagged('post_install', '-at_install', '-standard', 'pdf_rendering')
class TestReportsRenderingLimitations(TestReportsRenderingCommon):
    def test_no_clip(self):
        """
            Current version will add a fixed margin on top of document
            This test demonstrates this limitation
        """
        header_content = '''
            <div style="background-color:blue">
                <div t-foreach="range(10)" t-as="pos" t-esc="'Header %s' % pos"/>
            </div>
        '''
        page_content = '''
            <div class="page">
                <div style="background-color:red; margin-left:100px">
                    <div t-foreach="range(10)" t-as="pos" t-esc="'Content %s' % pos"/>
                </div>
            </div>
        '''
        # adding a margin on page to avoid bot block to me considered as the same
        pdf_content = self.create_pdf(page_content=page_content, header_content=header_content)
        pages = self._parse_pdf(pdf_content)
        self.assertEqual(len(pages), 2, "2 partners")
        page = pages[0]
        self.assertEqual(len(page), 3, "Expecting 3 box per page, Header, body, footer")
        header_box = page[0][0]
        body_box = page[1][0]
        header_box_bottom = header_box[2]
        body_box_top = body_box[0]
        self.assertGreaterEqual(body_box_top, header_box_bottom)
