from io import BytesIO
from odoo import Command
from odoo.tests import tagged, HttpCase
from odoo.tools import BinaryBytes, file_open
from os.path import basename
from lxml import etree
from base64 import b64decode


def read_file(file_path):
    contents = None
    with file_open(file_path, 'rb') as file:
        contents = file.read()
    if not contents:
        raise FileNotFoundError(f'The file {file_path} could not be found.')
    return contents


def extract_pdf_from_xml(xml_file):
    """
    :param xml_file raw bytes of an XML file with a PDF file embedded in it
    :return raw bytes of the PDF file embedded in the XML file
    """
    xml_root = etree.parse(BytesIO(xml_file)).getroot()
    embedded_documents = [
            {
                'data': b64decode(doc.text),
                **dict(zip(doc.keys(), doc.values()))
            } for doc in xml_root.xpath("//*[contains(local-name(), 'EmbeddedDocumentBinaryObject')]")
        ]
    pdf_documents = filter(lambda doc: '.pdf' in doc.get('filename') or doc.get('mimeCode') == 'application/pdf', embedded_documents)
    return [doc.get('data') or b'\0' for doc in pdf_documents]


@tagged("-at_install", "post_install")
class TestAccountMoveAttachment(HttpCase):
    def _send_account_move(self, account_move):
        partner = self.env['res.partner'].create({
            'name': 'partner_a',
            'invoice_sending_method': 'manual',
            'invoice_edi_format': False,
            'company_id': False,
        })

        tax_price_include = self.env['account.tax'].create({
            'name': '10% incl',
            'type_tax_use': 'sale',
            'amount_type': 'percent',
            'amount': 10,
            'price_include_override': 'tax_included',
            'include_base_amount': True,
        })

        product = self.env['product.product'].create({
            'name': 'product',
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'lst_price': 110.0,
            'taxes_id': [(6, 0, tax_price_include.ids)],
        })

        account_move.write({
            'move_type': 'out_invoice',
            'partner_id': partner,
            'invoice_date': '2019-01-21',
            'date': '2019-01-21',
            'invoice_line_ids': [
                Command.create({
                    'name': 'test line',
                    'product_id': product.id,
                }),
            ],
        })
        account_move.action_post()
        account_move.action_send_and_print()

    def test_preserving_manually_added_attachments(self):
        """ Preserve attachments manually added (not coming from emails) to an invoice """
        self.authenticate("admin", "admin")

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
        })
        self.assertFalse(invoice.attachment_ids)
        response = self.url_open("/mail/attachment/upload",
            {
                "csrf_token": self.csrf_token(),
                "thread_id": invoice.id,
                "thread_model": "account.move",
            },
            files={'ufile': ('salut.txt', b"Salut !\n", 'text/plain')},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(invoice.attachment_ids)

    def test_create_records_from_empty_pdf_attachment(self):
        """Ensure importing an empty PDF attachment does not crash and still returns created records."""
        attachment = self.env['ir.attachment'].create({
            'name': 'invoice.pdf',
            'mimetype': 'application/pdf',
        })
        records = self.env['account.move']._create_records_from_attachments(attachment)
        self.assertTrue(records)

    def test_check_create_from_pdf_match(self):
        """
            check that creating records from a PDF uses that PDF for sending/printing.
        """
        pdf_file_path = './account/tests/test_files/test_pdf.pdf'
        pdf_file = read_file(pdf_file_path)

        attachment = self.env['ir.attachment'].create({
            'name': basename(pdf_file_path),
            'mimetype': 'application/pdf',
            'raw': BinaryBytes(pdf_file)
        })

        account_move = self.env['account.move']._create_records_from_attachments(attachment)

        self._send_account_move(account_move)

        self.assertEqual(pdf_file, account_move.invoice_pdf_report_id.raw.content)

    def test_check_create_from_xml_match(self):
        """
            check that creating records from an XML file extracts the PDF file from it
            and uses that PDF file for sending/printing.
        """
        xml_file_path = './account/tests/test_files/xml_with_embedded_pdf.xml'
        xml_file = read_file(xml_file_path)

        attachment = self.env['ir.attachment'].create({
            'name': basename(xml_file_path),
            'mimetype': 'application/xml',
            'raw': BinaryBytes(xml_file)
        })

        account_move = self.env['account.move']._create_records_from_attachments(attachment)

        self._send_account_move(account_move)

        extracted_pdf_file_data = extract_pdf_from_xml(xml_file)[0]

        self.assertEqual(extracted_pdf_file_data, account_move.invoice_pdf_report_id.raw.content)
