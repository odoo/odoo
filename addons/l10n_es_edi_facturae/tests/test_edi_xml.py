import logging
import random
from base64 import b64encode
from datetime import datetime
from hashlib import sha1
from unittest.mock import patch

import lxml
from freezegun import freeze_time

from odoo import Command, fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools import file_open

_logger = logging.getLogger(__name__)


# Used to patch the computation of `is_valid` so that a certificate is
# always valid regardless of the start and end date set on it.
def _compute_is_valid(self):
    for cert in self:
        cert.is_valid = True


@tagged('post_install_l10n', 'post_install', '-at_install')
@patch('odoo.addons.certificate.models.certificate.CertificateCertificate._compute_is_valid', _compute_is_valid)
class TestEdiFacturaeXmls(AccountTestInvoicingCommon):
    @classmethod
    @AccountTestInvoicingCommon.setup_country('es')
    def setUpClass(cls):
        super().setUpClass()
        cls.frozen_today = datetime(year=2023, month=1, day=1, hour=0, minute=0, second=0)

        # ==== Companies ====
        cls.company_data['company'].write({  # -> PersonTypeCode 'J'
            'street': "C. de Embajadores, 68-116",
            'state_id': cls.env.ref('base.state_es_m').id,
            'city': "Madrid",
            'zip': "12345",
            'vat': 'ES59962470K',
        })

        cls.caixabank = cls.env['res.bank'].create({
            'name': 'CAIXABANK',
            'bic': 'CAIXESBBXXX',
        })

        cls.env['res.partner.bank'].create({
            'acc_number': 'ES9121000418450200051332',
            'partner_id': cls.company_data['company'].partner_id.id,
            'bank_id': cls.caixabank.id,
            'acc_type': 'iban',
        })

        # ==== Business ====
        cls.partner_a.write({  # -> PersonTypeCode 'F'
            'country_id': cls.env.ref('base.be').id,  # -> ResidenceTypeCode 'U'
            'vat': 'BE0477472701',
            'city': "Namur",
            'street': "Rue de Bruxelles, 15000",
            'zip': "5000",
            'invoice_edi_format': 'es_facturae',
        })

        cls.partner_b.write({
            'name': 'Ayuntamiento de San Sebastián de los Reyes',
            'is_company': True,
            'country_id': cls.env.ref('base.es').id,
            'vat': 'P2813400E',
            'city': 'San Sebastián de los Reyes',
            'street': 'Plaza de la Constitución, 1',
            'zip': '28701',
            'state_id': cls.env.ref('base.state_es_m').id,
        })
        partner_b_ac = cls.partner_b.copy()
        partner_b_ac.write({
            'type': 'facturae_ac',
            'parent_id': cls.partner_b.id,
            'name': 'Intervención Municipal',
            'l10n_es_edi_facturae_ac_center_code': 'L01281343',
            'l10n_es_edi_facturae_ac_role_type_ids': [
                Command.link(cls.env.ref('l10n_es_edi_facturae.ac_role_type_01').id),
                Command.link(cls.env.ref('l10n_es_edi_facturae.ac_role_type_02').id),
                Command.link(cls.env.ref('l10n_es_edi_facturae.ac_role_type_03').id),
            ],
        })

        cls.partner_us = cls.env['res.partner'].create({
            'name': 'Indigo Exterior',
            'city': 'Fremont',
            'zip': '94538',
            'country_id': cls.env.ref('base.us').id,
            'state_id': cls.env['res.country.state'].search([('name', '=', 'California')]).id,
            'email': 'indigo.exterior@example.com',
            'company_type': 'company',
            'is_company': True,
        })

        cls.password = "test"

        cls.certificate_module = "odoo.addons.certificate.models.certificate"
        cls.move_module = "odoo.addons.l10n_es_edi_facturae.models.account_move"
        with freeze_time(cls.frozen_today), patch(f"{cls.certificate_module}.fields.Datetime.now", lambda x=None: cls.frozen_today):
            cls.certificate = cls.env["certificate.certificate"].create({
                'name': 'Test ES certificate',
                'content': b64encode(file_open('l10n_es_edi_facturae/tests/data/certificate_test.pfx', 'rb').read()),
                'pkcs12_password': 'test',
                'company_id': cls.company_data['company'].id,
                'scope': 'facturae',
            })

        cls.tax, cls.tax_2 = cls.env['account.tax'].create([{
                'name': "IVA 21% (Bienes)",
                'company_id': cls.company_data['company'].id,
                'amount': 21.0,
                'price_include_override': 'tax_excluded',
                'l10n_es_edi_facturae_tax_type': '01'
            }, {
                'name': "IVA 21% (Bienes) Included",
                'company_id': cls.company_data['company'].id,
                'amount': 21.0,
                'price_include_override': 'tax_included',
                'l10n_es_edi_facturae_tax_type': '01'
        }
        ])

        cls.nsmap = {
            'ds': "http://www.w3.org/2000/09/xmldsig#", 'fac': "http://www.facturae.es/Facturae/2007/v3.1/Facturae",
            'xades': "http://uri.etsi.org/01903/v1.3.2#", 'xd': "http://www.w3.org/2000/09/xmldsig#",
        }

        cls.maxDiff = None

    @classmethod
    def create_invoice(cls, **kwargs):
        return cls.env['account.move'].with_context(edi_test_mode=True).create({
            'partner_id': cls.partner_a.id,
            'invoice_date': cls.frozen_today.isoformat(),
            'date': cls.frozen_today.isoformat(),
            **kwargs,
            'invoice_line_ids': [
                Command.create({'product_id': cls.product_a.id, 'price_unit': 1000.0, **line_vals, })
                for line_vals in kwargs.get('invoice_line_ids', [])
            ],
        })

    def create_send_and_print(self, invoices, **kwargs):
        wizard_model = 'account.move.send.wizard' if len(invoices) == 1 else 'account.move.send.batch.wizard'
        return self.env[wizard_model]\
            .with_context(active_model='account.move', active_ids=invoices.ids)\
            .create(kwargs)

    def _mock_sha1(self):
        return patch(f"{self.move_module}.sha1", lambda x: sha1())

    def test_generate_signed_xml(self, date=None):
        random.seed(42)
        date = date or self.frozen_today
        # We need to patch dates and uuid to ensure the signature's consistency
        with freeze_time(date), \
                patch(f"{self.certificate_module}.fields.Datetime.now", lambda x=None: date), \
                self._mock_sha1():
            invoice = self.create_invoice(
                partner_id=self.partner_a.id,
                move_type='out_invoice',
                invoice_line_ids=[
                    {'price_unit': 100.0, 'tax_ids': [self.tax.id]},
                    {'price_unit': 100.0, 'tax_ids': [self.tax.id]},
                    {'price_unit': 242.0, 'tax_ids': [self.tax_2.id]},
                    {'price_unit': 1000.0, "discount": 10, "tax_ids": [self.tax.id]},
                    {'price_unit': 1210.0, "discount": -10, "tax_ids": [self.tax_2.id]},
                ],
            )
            invoice.action_post()
            generated_file, errors = invoice._l10n_es_edi_facturae_render_facturae()
            self.assertFalse(errors)
            self.assertTrue(generated_file)

            with file_open("l10n_es_edi_facturae/tests/data/expected_signed_document.xml", "rt") as f:
                expected_xml = lxml.etree.fromstring(f.read().encode())
            self.assertXmlTreeEqual(lxml.etree.fromstring(generated_file), expected_xml)

    def test_cannot_generate_unsigned_xml(self):
        """ Test that no valid certificate prevents a xml generation"""
        def _compute_is_valid(self):
            for cert in self:
                cert.is_valid = False

        random.seed(42)
        with freeze_time(self.frozen_today), \
                patch(f"{self.certificate_module}.fields.Datetime.now", lambda x=None: self.frozen_today), \
                patch(f'{self.certificate_module}.CertificateCertificate._compute_is_valid', _compute_is_valid), \
                self._mock_sha1():
            invoice = self.create_invoice(partner_id=self.partner_a.id, move_type='out_invoice', invoice_line_ids=[{'price_unit': 100.0, 'tax_ids': [self.tax.id]}])
            invoice.action_post()
            wizard = self.create_send_and_print(invoice)
            with self.assertRaises(UserError):
                wizard.action_send_and_print()

    def test_no_certificate_facturae_not_selected(self):
        self.certificate.unlink()
        invoice = self.create_invoice(partner_id=self.partner_a.id, move_type='out_invoice', invoice_line_ids=[{'price_unit': 100.0, 'tax_ids': [self.tax.id]}])
        invoice.action_post()
        wizard = self.create_send_and_print(invoice)
        # Expect a UserError if no certificate is configured
        with self.assertRaises(UserError):
            wizard.action_send_and_print()

    def test_in_invoice(self):
        random.seed(42)
        # We need to patch dates and uuid to ensure the signature's consistency
        with freeze_time(self.frozen_today), \
                patch(f"{self.certificate_module}.fields.Datetime.now", lambda x=None: self.frozen_today), \
                self._mock_sha1():
            invoice = self.create_invoice(
                partner_id=self.partner_a.id,
                move_type='in_invoice',
                invoice_line_ids=[
                    {'price_unit': 100.0, 'tax_ids': [self.tax.id]},
                    {'price_unit': 100.0, 'tax_ids': [self.tax.id]},
                    {'price_unit': 242.0, 'tax_ids': [self.tax_2.id]},
                    {'price_unit': 1000.0, "discount": 10, "tax_ids": [self.tax.id]},
                    {'price_unit': 1000.0, "discount": -10, "tax_ids": [self.tax.id]},
                ],
            )
            invoice.action_post()
            generated_file, errors = invoice._l10n_es_edi_facturae_render_facturae()
            self.assertFalse(errors)
            self.assertTrue(generated_file)

            with file_open("l10n_es_edi_facturae/tests/data/expected_in_invoice_document.xml", "rt") as f:
                expected_xml = lxml.etree.fromstring(f.read().encode())
            self.assertXmlTreeEqual(lxml.etree.fromstring(generated_file), expected_xml)

    def test_out_invoice_decimals(self):
        decimal_precision = self.env['decimal.precision'].search([('name', '=', 'Product Price')])
        decimal_precision.digits = 4
        with freeze_time(self.frozen_today):
            invoice = self.create_invoice(
                partner_id=self.partner_a.id,
                move_type='out_invoice',
                invoice_line_ids=[
                    {'price_unit': 2.0592, 'quantity': 22.0, 'tax_ids': [self.tax.id]},
                ],
            )
            invoice.action_post()

            generated_file, errors = invoice._l10n_es_edi_facturae_render_facturae()
            self.assertFalse(errors)
            self.assertTrue(generated_file)

            with file_open("l10n_es_edi_facturae/tests/data/expected_out_invoice_4_decimals.xml", "rt") as f:
                expected_xml = lxml.etree.fromstring(f.read().encode())

            self.assertXmlTreeEqual(lxml.etree.fromstring(generated_file), expected_xml)

    def test_refund_invoice(self):
        random.seed(42)
        # We need to patch dates and uuid to ensure the signature's consistency
        with freeze_time(self.frozen_today), \
                patch(f"{self.certificate_module}.fields.Datetime.now", lambda x=None: self.frozen_today), \
                self._mock_sha1():
            invoice = self.create_invoice(
                partner_id=self.partner_a.id,
                move_type='out_invoice',
                invoice_line_ids=[
                    {'price_unit': 100.0, 'tax_ids': [self.tax.id]},
                    {'price_unit': 100.0, 'tax_ids': [self.tax.id]},
                ],
            )
            invoice.action_post()
            reversal_wizard = self.env['account.move.reversal'].create({
                'move_ids': invoice.ids,
                'journal_id': invoice.journal_id.id,
                'date': self.frozen_today,
                'company_id': self.company_data['company'].id,
                'l10n_es_edi_facturae_reason_code': '01'
            })
            reversal_wizard.modify_moves()
            refund = invoice.reversal_move_ids
            refund.ref = 'ABCD-2023-001'
            generated_file, errors = refund._l10n_es_edi_facturae_render_facturae()
            self.assertFalse(errors)
            self.assertTrue(generated_file)

            with file_open("l10n_es_edi_facturae/tests/data/expected_refund_document.xml", "rt") as f:
                expected_xml = lxml.etree.fromstring(f.read().encode())
            self.assertXmlTreeEqual(lxml.etree.fromstring(generated_file), expected_xml)

    def test_discount_100_percent(self):
        """ Create an invoice with a 100% discount """
        with freeze_time(self.frozen_today), \
                patch(f"{self.certificate_module}.fields.Datetime.now", lambda x=None: self.frozen_today), \
                self._mock_sha1():
            invoice = self.create_invoice(
                partner_id=self.partner_a.id,
                move_type='out_invoice',
                invoice_line_ids=[{'product_id': self.product_a.id, 'price_unit': 1000.0, 'discount': 100.0, 'quantity': 2}],
            )
            invoice.action_post()
            wizard = self.create_send_and_print(invoice)
            result = wizard.action_send_and_print()

            self.assertEqual(result['type'], 'ir.actions.act_window_close')
            self.assertEqual(invoice.invoice_line_ids[0].price_subtotal, 0.0)

    def test_import_multiple_invoices(self):
        with file_open("l10n_es_edi_facturae/tests/data/import_multiple_invoices.xml", "rt") as f:
            content = f.read().encode()

        attachment = self.env['ir.attachment'].create({'name': 'invoice.xml', 'raw': content})
        sale_journal = self.company_data['default_journal_sale'].with_context(default_move_type='out_invoice')
        moves = sale_journal._create_document_from_attachment(attachment.ids)

        currency = self.env['res.currency'].search([('name', '=', 'EUR')])

        self.assertRecordValues(moves, [
            {
                'partner_id': self.partner_us.id,
                'amount_total': 2186.20,
                'amount_untaxed': 2119.0,
                'amount_tax': 67.2,
                'move_type': 'out_invoice',
                'currency_id': currency.id,
                'invoice_date': fields.Date.from_string('2023-08-01'),
                'invoice_date_due': fields.Date.from_string('2023-08-31'),
                'ref': 'INV/2023/00005',
                'narration': '<p>Terms and conditions.</p>',
            },
            {
                'partner_id': self.partner_us.id,
                'amount_total': 1161.60,
                'amount_untaxed': 960.0,
                'amount_tax': 201.60,
                'move_type': 'out_invoice',
                'currency_id': currency.id,
                'invoice_date': fields.Date.from_string('2023-07-01'),
                'invoice_date_due': fields.Date.from_string('2023-07-31'),
                'ref': 'INV/2023/00006',
                'narration': '<p>Legal References.</p>',
            },
        ])

        # Check first invoice's lines.
        self.assertRecordValues(moves[0].invoice_line_ids, [
            {
                'name': '[E-COM07] Large Cabinet',
                'price_unit': 320.0,
                'quantity': 1.0,
                'price_total': 387.2,
                'discount': 0.0,
            },
            {
                'name': '[E-COM09] Large Desk',
                'price_unit': 1799.0,
                'quantity': 1.0,
                'price_total': 1799,
                'discount': 0.0,
            }
        ])

        # Check second invoice's lines.
        self.assertRecordValues(moves[1].invoice_line_ids, [
            {
                'name': '[E-COM07] Large Cabinet',
                'price_unit': 320.0,
                'quantity': 3.0,
                'price_total': 1161.60,
                'discount': 0.0,
            },
        ])

    def test_import_withheld_taxes(self):
        with file_open("l10n_es_edi_facturae/tests/data/import_withholding_invoice.xml", "rt") as f:
            content = f.read().encode()
        attachment = self.env['ir.attachment'].create({'name': 'invoice.xml', 'raw': content})

        sale_journal = self.company_data['default_journal_sale'].with_context(default_move_type='out_invoice')
        move = sale_journal._create_document_from_attachment(attachment.ids)

        self.assertRecordValues(move, [
            {
                'amount_total': 323.2,
                'amount_untaxed': 320.0,
                'amount_tax': 3.2,
            },
        ])

        tax_amounts = [tax.amount for tax in move.invoice_line_ids.tax_ids]

        # Check first invoice's lines.
        self.assertEqual(tax_amounts, [21.0, -20.0])

    @freeze_time('2023-01-01')
    def test_generate_with_administrative_centers(self):
        invoice = self.create_invoice(
            partner_id=self.partner_b.id,
            move_type='out_invoice',
            invoice_line_ids=[{'price_unit': 100.0, 'tax_ids': [self.tax.id]},]
        )
        invoice.action_post()
        generated_file, errors = invoice._l10n_es_edi_facturae_render_facturae()
        self.assertFalse(errors)
        self.assertTrue(generated_file)

        with file_open('l10n_es_edi_facturae/tests/data/expected_ac_document.xml', 'rt') as f:
            expected_xml = lxml.etree.fromstring(f.read().encode())
        self.assertXmlTreeEqual(lxml.etree.fromstring(generated_file), expected_xml)

    @freeze_time('2023-01-01')
    def test_generate_with_invoice_period(self):
        invoice = self.create_invoice(
            partner_id=self.partner_a.id,
            move_type='out_invoice',
            invoice_line_ids=[{'price_unit': 100.0, 'tax_ids': [self.tax.id]}],
            l10n_es_invoicing_period_start_date='2023-01-01',
            l10n_es_invoicing_period_end_date='2023-01-31',
        )
        invoice.action_post()
        generated_file, errors = invoice._l10n_es_edi_facturae_render_facturae()
        self.assertFalse(errors)
        self.assertTrue(generated_file)

        with file_open('l10n_es_edi_facturae/tests/data/expected_invoice_period_document.xml', 'rt') as f:
            expected_xml = lxml.etree.fromstring(f.read().encode())
        self.assertXmlTreeEqual(lxml.etree.fromstring(generated_file), expected_xml)

    @freeze_time('2023-01-01')
    def test_generate_with_payment_means(self):
        invoice = self.create_invoice(
            partner_id=self.partner_a.id,
            move_type='out_invoice',
            invoice_line_ids=[{'price_unit': 100.0, 'tax_ids': [self.tax.id]}],
            l10n_es_payment_means='14',
        )
        invoice.action_post()
        generated_file, errors = invoice._l10n_es_edi_facturae_render_facturae()
        self.assertFalse(errors)
        self.assertTrue(generated_file)

        with file_open('l10n_es_edi_facturae/tests/data/expected_invoice_payment_means.xml', 'rt') as f:
            expected_xml = lxml.etree.fromstring(f.read().encode())
        self.assertXmlTreeEqual(lxml.etree.fromstring(generated_file), expected_xml)

    def test_simplified_invoice(self):
        """
        Test that in the facturae xml uses the correct InvoiceDocumentType for simplified invoices
        """

        partner = self.env.ref('l10n_es.partner_simplified')
        partner.vat = 'ESA12345674'
        partner.country_id = self.env['res.country'].search([('code', '=', 'ES')])

        # We need to patch dates and uuid to ensure the signature's consistency
        with freeze_time(datetime(2023, 1, 1)):
            invoice = self.create_invoice(
                partner_id=partner.id,
                move_type='out_invoice',
                invoice_line_ids=[
                    {'price_unit': 100.0, 'tax_ids': [self.tax.id]},
                ],
            )
            invoice.action_post()
            generated_file, errors = invoice._l10n_es_edi_facturae_render_facturae()
            self.assertFalse(errors)
            self.assertTrue(generated_file)

            with file_open("l10n_es_edi_facturae/tests/data/expected_simplified_document.xml", "rt") as f:
                expected_xml = lxml.etree.fromstring(f.read().encode())
            self.assertXmlTreeEqual(lxml.etree.fromstring(generated_file), expected_xml)

    def test_download_facturae_xml_functionality(self):
        """ Test Factura-e XML download functionality for invoices. """
        with freeze_time(self.frozen_today), \
                patch(f"{self.certificate_module}.fields.Datetime.now", lambda x=None: self.frozen_today), \
                self._mock_sha1():

            invoice = self.create_invoice(
                partner_id=self.partner_a.id,
                move_type='out_invoice',
                invoice_line_ids=[
                    {'price_unit': 100.0, 'tax_ids': [self.tax.id]},
                    {'price_unit': 200.0, 'tax_ids': [self.tax.id]},
                ],
            )
            invoice.action_post()

            # Generate and store XML file
            xml_content, errors = invoice._l10n_es_edi_facturae_render_facturae()
            self.assertFalse(errors)
            self.assertTrue(xml_content)

            # Create attachment for testing
            attachment = self.env['ir.attachment'].create({
                'name': invoice._l10n_es_edi_facturae_get_filename(),
                'raw': xml_content,
                'res_model': 'account.move',
                'res_id': invoice.id,
            })

            invoice.l10n_es_edi_facturae_xml_id = attachment

            # Test get_extra_print_items includes Factura-e download option
            print_items = invoice.get_extra_print_items()
            facturae_items = [item for item in print_items if item.get('key') == 'download_xml_facturae']
            self.assertEqual(len(facturae_items), 1, "Should have exactly one Factura-e download option")

            facturae_item = facturae_items[0]
            expected_url = f'/account/download_invoice_documents/{invoice.id}/facturae'
            expected_item = {
                'key': 'download_xml_facturae',
                'description': 'Factura-e XML',
                'type': 'ir.actions.act_url',
                'url': expected_url,
                'target': 'download',
            }
            self.assertEqual(facturae_item, expected_item)

    def test_download_facturae_xml_legal_documents(self):
        """ Test _get_invoice_legal_documents method for facturae filetype. """
        with freeze_time(self.frozen_today), \
                patch(f"{self.certificate_module}.fields.Datetime.now", lambda x=None: self.frozen_today), \
                self._mock_sha1():

            invoice = self.create_invoice(
                partner_id=self.partner_a.id,
                move_type='out_invoice',
                invoice_line_ids=[{'price_unit': 150.0, 'tax_ids': [self.tax.id]}],
            )
            invoice.action_post()

            # Test with existing XML file
            xml_content, errors = invoice._l10n_es_edi_facturae_render_facturae()
            self.assertFalse(errors)

            # Create attachment for testing
            attachment = self.env['ir.attachment'].create({
                'name': invoice._l10n_es_edi_facturae_get_filename(),
                'raw': xml_content,
                'res_model': 'account.move',
                'res_id': invoice.id,
            })
            invoice.l10n_es_edi_facturae_xml_id = attachment

            self.assertEqual(invoice._get_invoice_legal_documents('facturae'), {
                'filename': attachment.name,
                'filetype': 'xml',
                'content': attachment.raw,
            })

            # Test with no XML file
            invoice.l10n_es_edi_facturae_xml_id = False
            self.assertIsNone(invoice._get_invoice_legal_documents('facturae'),
                             "Should return None when no XML file exists")

    def test_download_facturae_xml_batch_scenario(self):
        """ Test Factura-e XML download with multiple invoices. """
        with freeze_time(self.frozen_today), \
                patch(f"{self.certificate_module}.fields.Datetime.now", lambda x=None: self.frozen_today), \
                self._mock_sha1():

            # Create multiple invoices with different scenarios
            invoices = self.env['account.move']

            # Invoice 1: With Factura-e XML
            invoice1 = self.create_invoice(
                partner_id=self.partner_a.id,
                move_type='out_invoice',
                invoice_line_ids=[{'price_unit': 100.0, 'tax_ids': [self.tax.id]}],
            )
            invoice1.action_post()
            xml_content1, _ = invoice1._l10n_es_edi_facturae_render_facturae()
            attachment1 = self.env['ir.attachment'].create({
                'name': invoice1._l10n_es_edi_facturae_get_filename(),
                'raw': xml_content1,
                'res_model': 'account.move',
                'res_id': invoice1.id,
            })
            invoice1.l10n_es_edi_facturae_xml_id = attachment1
            invoices |= invoice1

            # Invoice 2: With Factura-e XML
            invoice2 = self.create_invoice(
                partner_id=self.partner_b.id,
                move_type='out_invoice',
                invoice_line_ids=[{'price_unit': 200.0, 'tax_ids': [self.tax.id]}],
            )
            invoice2.action_post()
            xml_content2, _ = invoice2._l10n_es_edi_facturae_render_facturae()
            attachment2 = self.env['ir.attachment'].create({
                'name': invoice2._l10n_es_edi_facturae_get_filename(),
                'raw': xml_content2,
                'res_model': 'account.move',
                'res_id': invoice2.id,
            })
            invoice2.l10n_es_edi_facturae_xml_id = attachment2
            invoices |= invoice2

            # Invoice 3: Without Factura-e XML (should be excluded)
            invoice3 = self.create_invoice(
                partner_id=self.partner_a.id,
                move_type='out_invoice',
                invoice_line_ids=[{'price_unit': 50.0, 'tax_ids': [self.tax.id]}],
            )
            invoice3.action_post()
            invoices |= invoice3

            # Test get_extra_print_items for batch
            print_items = invoices.get_extra_print_items()
            facturae_items = [item for item in print_items if item.get('key') == 'download_xml_facturae']
            self.assertEqual(len(facturae_items), 1, "Should have one Factura-e download option for batch")

            # Test action method for batch
            expected_action = {
                'type': 'ir.actions.act_url',
                'url': f'/account/download_invoice_documents/{invoice1.id},{invoice2.id}/facturae',
                'target': 'download',
            }
            self.assertEqual(invoices.action_invoice_download_facturae(), expected_action)

    def test_out_invoice_rounding(self):
        company = self.company_data['company']
        company.tax_calculation_rounding_method = 'round_globally'
        with freeze_time(self.frozen_today):
            invoice = self.create_invoice(
                partner_id=self.partner_a.id,
                move_type='out_invoice',
                invoice_line_ids=[
                    {'price_unit': 2.02, 'quantity': 25.0, 'tax_ids': [self.tax.id]},
                    {'price_unit': 7.29, 'quantity': 2.0, 'tax_ids': [self.tax.id]},
                    {'price_unit': 7.32, 'quantity': 5.0, 'tax_ids': [self.tax.id]},
                    {'price_unit': 9.50, 'quantity': 25.0, 'tax_ids': [self.tax.id]},
                ],
            )
            invoice.action_post()
            generated_file, errors = invoice._l10n_es_edi_facturae_render_facturae()
            self.assertFalse(errors)
            self.assertTrue(generated_file)

            with file_open("l10n_es_edi_facturae/tests/data/expected_out_invoice_round_glob.xml", "rt") as f:
                expected_xml = lxml.etree.fromstring(f.read().encode())
            self.assertXmlTreeEqual(lxml.etree.fromstring(generated_file), expected_xml)
