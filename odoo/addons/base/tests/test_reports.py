# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import io
import logging
from base64 import b64decode

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


@odoo.tests.tagged('post_install', '-at_install', 'post_install_l10n')
class TestReports(odoo.tests.TransactionCase):
    def test_reports(self):
        invoice_domain = [('move_type', 'in', ('out_invoice', 'out_refund', 'out_receipt', 'in_invoice', 'in_refund', 'in_receipt'))]
        specific_model_domains = {
            'account.report_original_vendor_bill': [('move_type', 'in', ('in_invoice', 'in_receipt'))],
            'account.report_invoice_with_payments': invoice_domain,
            'account.report_invoice': invoice_domain,
            'l10n_th.report_commercial_invoice': invoice_domain,
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

    def test_report_reload_from_attachment(self):
        def get_attachments(res_id):
            return self.env["ir.attachment"].search([('res_model', "=", "res.partner"), ("res_id", "=", res_id)])

        Report = self.env['ir.actions.report'].with_context(force_report_rendering=True)

        report = Report.create({
            'name': 'test report',
            'report_name': 'base.test_report',
            'model': 'res.partner',
        })

        self.env['ir.ui.view'].create({
            'type': 'qweb',
            'name': 'base.test_report',
            'key': 'base.test_report',
            'arch': '''
                <main>
                    <div class="article" data-oe-model="res.partner" t-att-data-oe-id="docs.id">
                        <span t-field="docs.display_name" />
                    </div>
                </main>
            '''
        })

        pdf_text = "0"
        def _run_wkhtmltopdf(*args, **kwargs):
            return bytes(pdf_text, "utf-8")

        self.patch(type(Report), "_run_wkhtmltopdf", _run_wkhtmltopdf)

        # sanity check: the report is not set to save attachment
        # assert that there are no pre-existing attachment
        partner_id = self.env.user.partner_id.id
        self.assertFalse(get_attachments(partner_id))
        pdf = report._render_qweb_pdf(report.id, [partner_id])
        self.assertFalse(get_attachments(partner_id))
        self.assertEqual(pdf[0], b"0")

        # set the report to reload from attachment and make one
        pdf_text = "1"
        report.attachment = "'test_attach'"
        report.attachment_use = True
        report._render_qweb_pdf(report.id, [partner_id])
        attach_1 = get_attachments(partner_id)
        self.assertTrue(attach_1.exists())

        # use the context key to not reload from attachment
        # and not create another one
        pdf_text = "2"
        report = report.with_context(report_pdf_no_attachment=True)
        pdf = report._render_qweb_pdf(report.id, [partner_id])
        attach_2 = get_attachments(partner_id)
        self.assertEqual(attach_2.id, attach_1.id)

        self.assertEqual(b64decode(attach_1.datas), b"1")
        self.assertEqual(pdf[0], b"2")


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

class Box:
    """
    Utility class to help assertions
    """
    def __init__(self, obj, page_height, page_width):
        self.x1 = round(obj.x0, 1)
        self.y1 = round(page_height-obj.y1, 1)
        self.x2 = round(obj.x1, 1)
        self.y2 = round(page_height-obj.y0, 1)
        self.page_height = page_height
        self.page_width = page_width

    @property
    def height(self):
        return self.y2 - self.y1

    @property
    def width(self):
        return self.x2 - self.x1

    @property
    def top(self):
        return self.y1

    @property
    def left(self):
        return self.x1

    @property
    def end_top(self):
        return self.y2

    @property
    def end_left(self):
        return self.x2

    @property
    def right(self):
        return self.page_width - self.x2

    @property
    def bottom(self):
        return self.page_height - self.y2

    def __lt__(self, other):
        return (self.y1, self.x1, self.y2, self.x2) < (other.y1, other.x1, other.y2, other.x2)


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
        self.last_pdf_content = None
        self.last_pdf_content_saved = False

    def _addError(self, result, test, exc_info):
        if self.last_pdf_content and not self.last_pdf_content_saved:
            self.last_pdf_content_saved = True
            self.save_pdf()
        super()._addError(result, test, exc_info)

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

    def create_pdf(self, partners=None, header_content=None, page_content=None, footer_content=None):
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
        self.last_pdf_content = self.env['ir.actions.report'].with_context(force_report_rendering=True)._render_qweb_pdf(self.report, partners.ids)[0]
        return self.last_pdf_content

    def save_pdf(self):
        assert self.last_pdf_content
        odoo.tests.save_test_file(self._testMethodName, self.last_pdf_content, 'pdf_', 'pdf', document_type='Report PDF', logger=_logger)

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
                "Expecting pdf to be in A4 portait format",
            ) # this is the default expected format and other layout assertions are based on this one.
            interpreter.process_page(page)
            layout = device.get_result()
            elements = []
            parsed_pages.append(elements)
            for obj in layout:
                box = Box(
                    obj,
                    page_height=pages[0].mediabox[3],
                    page_width=pages[0].mediabox[2],
                )
                if isinstance(obj, LTTextBox):
                    #inverse x to start from top left corner
                    elements.append((box, obj.get_text().strip()))
                elif isinstance(obj, LTFigure):
                    elements.append((box, 'LTFigure'))
            elements.sort()

        return parsed_pages

    def assertPageFormat(self, paper_format, orientation):
        pdf_content = self.create_pdf()
        pages = self._get_pdf_pages(pdf_content)
        self.assertEqual(len(pages), 2)
        for page in pages:
            self.assertEqual(
                self.get_paper_format(page.mediabox),
                (paper_format, orientation),
                f"Expecting pdf to be in {paper_format} {orientation} format",
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
        paper_format = self.env.ref('base.paperformat_euro')
        paper_format.orientation = 'Landscape'
        self.report.paperformat_id = paper_format
        self.assertPageFormat('A4', 'landscape')

    def test_layout(self):
        pdf_content = self.create_pdf()
        pages = self._parse_pdf(pdf_content)
        self.assertEqual(len(pages), 2)

        page_contents = [[elem[1] for elem in page] for page in pages]

        expected_pages_content = [[
            'LTFigure',
            'Some header Text',
            f'Name: {partner.name}',
            f'Footer for {partner.name} Page: 1 / 1',
        ] for partner in self.partners]

        self.assertEqual(
            page_contents,
            expected_pages_content,
        )

        page_positions = [[elem[0] for elem in page] for page in pages]
        logo, header, content, footer = page_positions[0]

        # leaving this as reference but this is to fragile to make a strict assertion
        # 14.3, 29.6, 43.1, 137.2     # logo
        # 19.1, 137.2, 32.5, 214.2   # header
        # 111.3, 29.6, 124.8, 123.7   # content
        # 751.6, 220.1, 765.1, 375.0  # footer

        #
        #   \ \ / // _ \ | | | || _ \  | |
        #    \ V /| (_) || |_| ||   /  | |__ / _ \/ _` |/ _ \     Some header Text
        #     |_|  \___/  \___/ |_|_\  |____|\___/\__, |\___/
        #
        #
        #   Name: Report record 0
        #
        #
        #
        #
        #
        #
        #             Footer for Report record 0 Page: 1 / 1
        #
        #

        self.assertEqual(logo.left, content.left, 'Logo and content should have the same left margin')
        self.assertEqual(header.left, logo.end_left, 'Header starts after logo')
        self.assertGreaterEqual(header.top, logo.top, 'header is vertically centered on logo')
        self.assertGreaterEqual(logo.end_top, header.end_top, 'header is vertically centered on logo')
        self.assertGreaterEqual(content.top, logo.end_top, 'Content is bellow logo')
        self.assertGreaterEqual(footer.top, content.end_top, 'Footer is bellow content')
        self.assertGreaterEqual(100, footer.bottom, 'Footer is on the bottom of the page')
        self.assertAlmostEqual(footer.left, footer.right, -1, 'Footer is centered on the page')

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

        expected_pages_contents = []
        for partner in self.partners:
            expected_pages_contents.append([
                'LTFigure', #logo
                'Some header Text',
                f'Name: {partner.name}',
                f'Footer for {partner.name} Page: 1 / 2',
            ])
            expected_pages_contents.append([
                'LTFigure', #logo
                'Some header Text',
                f'Last page for {partner.name}',
                f'Footer for {partner.name} Page: 2 / 2',
            ])
        pages_contents = [[elem[1] for elem in page] for page in pages]
        self.assertEqual(pages_contents, expected_pages_contents)

    def test_pdf_render_page_overflow(self):
        nb_lines = 80

        page_content = f'''
            <div class="page">
                <div style="background-color:red">
                    Name: <t t-esc="o.name"/>
                    <div t-foreach="range({nb_lines})" t-as="pos" t-esc="pos"/>
                </div>
            </div>
        '''
        pdf_content = self.create_pdf(page_content=page_content)
        pages = self._parse_pdf(pdf_content)

        self.assertEqual(len(pages), 4, '4 pages are expected, 2 per record (you may ensure `nb_lines` has a correct value to generate an oveflow)')
        page_break_at = int(pages[1][2][1].split('\n')[0])  # This element should be the first line, 61 when this test was written

        expected_pages_contents = []
        for partner in self.partners:
            expected_pages_contents.append([
                'LTFigure', #logo
                'Some header Text',
                f'Name: {partner.name}\n' + '\n'.join([str(i) for i in range(page_break_at)]),
                f'Footer for {partner.name} Page: 1 / 2',
            ])
            expected_pages_contents.append([
                'LTFigure', #logo
                'Some header Text',
                '\n'.join([str(i) for i in range(page_break_at, nb_lines)]),
                f'Footer for {partner.name} Page: 2 / 2',
            ])
        pages_contents = [[elem[1] for elem in page] for page in pages]
        self.assertEqual(pages_contents, expected_pages_contents)

    def test_thead_tbody_repeat(self):
        """
            Check that thead and t-foot are repeated after page break inside a tbody
        """
        nb_lines = 50
        page_content = f'''
            <div class="page">
                <table class="table">
                    <thead><tr><th> T1 </th><th> T2 </th><th> T3 </th></tr></thead>
                    <tbody>
                    <t t-foreach="range({nb_lines})" t-as="pos">
                        <tr><td><t t-esc="pos"/></td><td><t t-esc="pos"/></td><td><t t-esc="pos"/></td></tr>
                    </t>
                    </tbody>
                    <tfoot><tr><th> T1 </th><th> T2 </th><th> T3 </th></tr></tfoot>
                </table>
            </div>
        '''

        pdf_content = self.create_pdf(page_content=page_content)
        pages = self._parse_pdf(pdf_content)

        self.assertEqual(len(pages), 4, '4 pages are expected, 2 per record (you may ensure `nb_lines` has a correct value to generate an oveflow)')
        page_break_at = int(pages[1][5][1])  # This element should be the first line of the table, 28 when this test was written

        def expected_table(start, end):
            table = ['T1', 'T2', 'T3'] # thead
            for i in range(start, end):
                table += [str(i), str(i), str(i)]
            table += ['T1', 'T2', 'T3'] # tfoot
            return table

        expected_pages_contents = []
        for partner in self.partners:
            expected_pages_contents.append([
                'LTFigure', #logo
                'Some header Text',
                * expected_table(0, page_break_at),
                f'Footer for {partner.name} Page: 1 / 2',
            ])
            expected_pages_contents.append([
                'LTFigure', #logo
                'Some header Text',
                * expected_table(page_break_at, nb_lines),
                f'Footer for {partner.name} Page: 2 / 2',
            ])

        pages_contents = [[elem[1] for elem in page] for page in pages]
        self.assertEqual(pages_contents, expected_pages_contents)


@odoo.tests.tagged('post_install', '-at_install', '-standard', 'pdf_rendering')
class TestReportsRenderingLimitations(TestReportsRenderingCommon):
    def test_no_clip(self):
        """
            Current version will add a fixed margin on top of document
            This test demonstrates this limitation
        """
        header_content = '''
            <div style="background-color:blue">
                <div t-foreach="range(15)" t-as="pos" t-esc="'Header %s' % pos"/>
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
        header = page[0][0]
        content = page[1][0]
        self.assertGreaterEqual(content.top, header.end_top, "EXISTING LIMITATION: large header shouldn't overflow on body, but they do")
