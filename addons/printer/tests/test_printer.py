# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import io
from unittest.mock import patch

from PIL import Image

from odoo.exceptions import ValidationError
from odoo.tests import HttpCase, tagged

from odoo.addons.base.tests.common import BaseCommon


def make_image(width, height, black_box=None, mode='RGB', color='white', image_format='PNG'):
    """ A white image, with an optional black box (left, top, right, bottom). """
    img = Image.new(mode, (width, height), color)
    if black_box:
        img.paste('black', black_box)
    stream = io.BytesIO()
    img.save(stream, format=image_format)
    return stream.getvalue()


def raster_rows(document):
    """ The dots of an ePOS raster, as rows of 0 (white) and 1 (black). """
    raster = base64.b64decode(document['raster'])
    row_size = document['width'] // 8
    return [
        [(byte >> (7 - bit)) & 1 for byte in raster[row * row_size:(row + 1) * row_size] for bit in range(8)]
        for row in range(document['height'])
    ]


class PrinterCommon(BaseCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['ir.ui.view'].create([{
            'name': 'printer.test_report_zpl',
            'key': 'printer.test_report_zpl',
            'type': 'qweb',
            'arch': '<t t-name="printer.test_report_zpl"><t t-foreach="docs" t-as="doc">^XA^FD<t t-out="doc.name"/>^FS^XZ</t></t>',
        }, {
            'name': 'printer.test_report_text',
            'key': 'printer.test_report_text',
            'type': 'qweb',
            'arch': '<t t-name="printer.test_report_text"><t t-foreach="docs" t-as="doc">^XA^FD<t t-out="doc.name"/>^FS^XZ</t></t>',
        }, {
            'name': 'printer.test_report_pdf',
            'key': 'printer.test_report_pdf',
            'type': 'qweb',
            'arch': '''
                <t t-name="printer.test_report_pdf">
                    <t t-call="web.html_container">
                        <t t-foreach="docs" t-as="doc">
                            <div class="article" t-att-data-oe-model="doc._name" t-att-data-oe-id="doc.id">
                                <img src="/report/barcode/Code128/ABC"/>
                                <span t-out="doc.name"/>
                            </div>
                        </t>
                    </t>
                </t>''',
        }])
        Report = cls.env['ir.actions.report']
        cls.report_zpl = Report.create({
            'name': "Test Label (ZPL)",
            'model': 'res.partner',
            'report_type': 'qweb-text',
            'report_name': 'printer.test_report_zpl',
        })
        cls.report_text = Report.create({
            'name': "Test Text",
            'model': 'res.partner',
            'report_type': 'qweb-text',
            'report_name': 'printer.test_report_text',
        })
        cls.report_pdf = Report.create({
            'name': "Test PDF",
            'model': 'res.partner',
            'report_type': 'qweb-pdf',
            'report_name': 'printer.test_report_pdf',
            'paperformat_id': cls.env['report.paperformat'].create({
                'name': "4x6 in",
                'format': 'custom',
                'page_width': 102,
                'page_height': 152,
                'orientation': 'Portrait',
            }).id,
        })
        cls.printer_zpl, cls.printer_epos = cls.env['printer.printer'].create([{
            'name': "Packing station",
            'address': '192.168.1.20',
            'kind': 'zpl',
            'report_ids': [cls.report_zpl.id, cls.report_pdf.id],
        }, {
            'name': "Shipping desk",
            'address': 'epson-1.local:8080',
            'kind': 'epos',
            'report_ids': [cls.report_zpl.id, cls.report_pdf.id],
        }])
        cls.partners = cls.env['res.partner'].create([{'name': "Azure"}, {'name': "Deco"}])

    def render_printer_documents(self, report, printers):
        return self.env['ir.actions.report']._render_printer_documents(report, printers, self.partners.ids)


class TestPrinter(PrinterCommon):

    def test_display_name(self):
        self.assertEqual(self.printer_zpl.display_name, "Packing station")
        self.assertEqual(
            self.printer_zpl.with_context(printer_show_kind=True).display_name, "ZPL - Packing station")
        self.assertEqual(
            self.printer_epos.with_context(printer_show_kind=True).display_name, "ePOS - Shipping desk")

    def test_default_kind(self):
        printer = self.env['printer.printer'].create({'name': "Zebra", 'address': '10.0.0.3'})
        self.assertEqual(printer.kind, 'zpl')

    def test_address(self):
        for address in ('192.168.1.20', 'zebra-1.local:8080', 'printer', '10.0.0.3/epos', '[fe80::1]:631'):
            self.printer_zpl.address = address
        for address in ('http://192.168.1.20', '192.168.1.20 ', 'zebra 1', '-zebra', ':8080'):
            with self.subTest(address=address), self.assertRaises(ValidationError):
                self.printer_zpl.address = address
                self.printer_zpl.flush_recordset()

    def test_link_printers_and_reports(self):
        self.assertEqual(self.report_pdf.printer_ids, self.printer_zpl | self.printer_epos)
        self.printer_zpl.report_ids = self.report_text
        self.assertEqual(self.report_pdf.printer_ids, self.printer_epos)
        self.assertEqual(self.report_text.printer_ids, self.printer_zpl)
        self.report_pdf.sudo().printer_ids = self.printer_zpl
        self.assertEqual(self.printer_zpl.report_ids, self.report_text | self.report_pdf)
        self.assertEqual(self.printer_epos.report_ids, self.report_zpl)

    def test_report_action_printers(self):
        action = self.report_pdf.report_action(self.partners, config=False)
        self.assertEqual(sorted(action['printer_ids']), sorted((self.printer_zpl | self.printer_epos).ids))
        self.assertEqual(self.report_text.report_action(self.partners, config=False)['printer_ids'], [])
        # actions loaded by id, from the print menu
        self.assertIn('printer_ids', self.report_pdf._get_action_dict())

    def test_render_zpl(self):
        self.assertEqual(
            self.render_printer_documents(self.report_zpl, self.printer_zpl),
            {'zpl': ["^XA^FDAzure^FS^XZ^XA^FDDeco^FS^XZ"]},
        )
        # Only the text reports with ZPL in their name hold ZPL code.
        self.assertEqual(self.render_printer_documents(self.report_text, self.printer_zpl), {'zpl': []})
        self.assertEqual(self.render_printer_documents(self.report_pdf, self.printer_zpl), {'zpl': []})

    def test_render_epos(self):
        def run_image_engine(model, engine_name, bodies, width, height, image_format='jpg'):
            rendered.append((bodies, width, height))
            return [make_image(width, height, black_box=(0, 0, width, 10)) for body in bodies]

        rendered = []
        with patch.object(self.registry['ir.actions.report'], '_run_image_engine', run_image_engine):
            documents = self.render_printer_documents(self.report_pdf, self.printer_epos)
        self.assertEqual(set(documents), {'epos'})
        # One image per page, the size of the page.
        [(bodies, width, height)] = rendered
        self.assertEqual(len(bodies), 2)
        self.assertEqual((width, height), (386, 574))
        base_url = self.report_pdf._get_report_url()
        for body, partner in zip(bodies, self.partners):
            # the relative links resolve
            self.assertIn(f'<base href="{base_url}"', body)
            self.assertIn('/report/barcode/Code128/ABC', body)
            self.assertIn(partner.name, body)
        for document in documents['epos']:
            self.assertEqual(document['width'], 576)
            self.assertEqual(document['height'], round(574 * 576 / 386))
            rows = raster_rows(document)
            self.assertTrue(all(rows[0]), "the black band at the top prints black")
            self.assertFalse(any(rows[-1]), "the white page prints white")
        # Text reports are not for ePOS printers.
        self.assertEqual(self.render_printer_documents(self.report_zpl, self.printer_epos), {'epos': []})

    def test_render_each_kind(self):
        with patch.object(self.registry['ir.actions.report'], '_run_image_engine', lambda *args, **kwargs: []):
            documents = self.render_printer_documents(self.report_zpl, self.printer_zpl | self.printer_epos)
        self.assertEqual(documents, {'zpl': ["^XA^FDAzure^FS^XZ^XA^FDDeco^FS^XZ"], 'epos': []})

    def test_convert_image_to_epos(self):
        convert = self.env['ir.actions.report']._convert_image_to_epos_document
        # Scaled to the width of the paper, a black left half.
        document = convert(make_image(288, 300, black_box=(0, 0, 144, 300)))
        self.assertEqual((document['width'], document['height']), (576, 600))
        self.assertEqual(len(base64.b64decode(document['raster'])), 576 // 8 * 600)
        for row in raster_rows(document):
            self.assertTrue(all(row[:280]))
            self.assertFalse(any(row[296:]))

        # A landscape image is turned to portrait.
        document = convert(make_image(400, 200, black_box=(0, 0, 400, 100)))
        self.assertEqual((document['width'], document['height']), (576, 1152))
        rows = raster_rows(document)
        # the black top half of the landscape image is the right half of the portrait one
        self.assertTrue(all(row[300:] == [1] * 276 for row in rows))
        self.assertTrue(all(not any(row[:276]) for row in rows))

        # Transparent areas print white, and grays are dithered.
        transparent = convert(make_image(576, 600, mode='RGBA', color=(0, 0, 0, 0)))
        self.assertFalse(any(any(row) for row in raster_rows(transparent)))
        gray = convert(make_image(576, 600, color=(128, 128, 128), image_format='JPEG'))
        dots = [dot for row in raster_rows(gray) for dot in row]
        self.assertAlmostEqual(sum(dots) / len(dots), 0.5, delta=0.05)


@tagged('post_install', '-at_install')
class TestPrinterController(HttpCase, PrinterCommon):

    def test_report_documents(self):
        self.authenticate('test_user', 'test_user')
        documents = self.make_jsonrpc_request('/printer/report_documents', {
            'report_name': self.report_zpl.report_name,
            'printer_ids': [self.printer_zpl.id, self.printer_epos.id],
            'res_ids': self.partners.ids,
        })
        self.assertEqual(documents, {'zpl': ["^XA^FDAzure^FS^XZ^XA^FDDeco^FS^XZ"], 'epos': []})
