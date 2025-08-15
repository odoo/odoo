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

@tagged('post_install_l10n', 'post_install', '-at_install')
class TestEdiFacturaeXmls(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref='es_full'):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.frozen_today = datetime(year=2023, month=1, day=1, hour=0, minute=0, second=0)

        # ==== Companies ====
        cls.company_data['company'].write({  # -> PersonTypeCode 'J'
            'country_id': cls.env.ref('base.es').id,  # -> ResidenceTypeCode 'R'
            'street': "C. de Embajadores, 68-116",
            'state_id': cls.env.ref('base.state_es_m').id,
            'city': "Madrid",
            'zip': "12345",
            'vat': 'ES59962470K',
        })
        cls.company_data_2['company'].write({  # -> PersonTypeCode 'J'
            'country_id': cls.env.ref('base.us').id,  # -> ResidenceTypeCode 'R'
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
        })

        cls.partner_us = cls.env['res.partner'].create({
            'name': 'Indigo Exterior',
            'city': 'Fremont',
            'zip': '94538',
            'country_id': cls.env.ref('base.us').id,
            'state_id': cls.env['res.country.state'].search([('name', '=', 'California')]).id,
            'email': 'indigo-exterior@example.com',
            'company_type': 'company',
            'is_company': True,
        })

        cls.password = "test"

        cls.certificate_module = "odoo.addons.l10n_es_edi_facturae.models.l10n_es_edi_facturae_certificate"
        with freeze_time(cls.frozen_today), patch(f"{cls.certificate_module}.fields.datetime.now", lambda x=None: cls.frozen_today):
            cls.certificate = cls.env["l10n_es_edi_facturae.certificate"].sudo().create({
                "content": b64encode(file_open('l10n_es_edi_facturae/tests/data/certificate_test.pfx', 'rb').read()),
                "password": "test",
                'company_id': cls.company_data['company'].id,
            })

        cls.tax, cls.tax_2 = cls.env['account.tax'].create([{
                'name': "IVA 21% (Bienes)",
                'company_id': cls.company_data['company'].id,
                'amount': 21.0,
                'price_include': False,
                'l10n_es_edi_facturae_tax_type': '01'
            }, {
                'name': "IVA 21% (Bienes) Included",
                'company_id': cls.company_data['company'].id,
                'amount': 21.0,
                'price_include': True,
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
        template = self.env.ref(invoices._get_mail_template())
        return self.env['account.move.send'].with_context(
            active_model='account.move',
            active_ids=invoices.ids,
        ).create({
            'mail_template_id': template.id,
            **kwargs,
        })

    def test_generate_signed_xml(self, date=None):
        random.seed(42)
        date = date or self.frozen_today
        # We need to patch dates and uuid to ensure the signature's consistency
        with freeze_time(date), \
                patch(f"{self.certificate_module}.fields.datetime.now", lambda x=None: date), \
                patch(f"{self.certificate_module}.sha1", lambda x: sha1()):
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
        self.certificate.unlink()
        random.seed(42)
        with freeze_time(self.frozen_today), \
                patch(f"{self.certificate_module}.fields.datetime.now", lambda x=None: self.frozen_today), \
                patch(f"{self.certificate_module}.sha1", lambda x: sha1()):
            invoice = self.create_invoice(partner_id=self.partner_a.id, move_type='out_invoice', invoice_line_ids=[{'price_unit': 100.0, 'tax_ids': [self.tax.id]},],)
            invoice.action_post()
            wizard = self.create_send_and_print(invoice)
            with self.assertRaises(UserError):
                wizard.action_send_and_print()

    def test_tax_withheld(self):
        with freeze_time(self.frozen_today), \
                patch(f"{self.certificate_module}.fields.datetime.now", lambda x=None: self.frozen_today), \
                patch(f"{self.certificate_module}.sha1", lambda x: sha1()):
            witholding_taxes = self.env["account.tax"].create([{
                'name': "IVA 21%",
                'company_id': self.company_data['company'].id,
                'amount': 21.0,
                'price_include': False,
                'l10n_es_edi_facturae_tax_type': '01'
            }, {
                'name': "IVA 21% withholding",
                'company_id': self.company_data['company'].id,
                'amount': -21.0,
                'price_include': False,
                'l10n_es_edi_facturae_tax_type': '01'
            }])

            invoice = self.create_invoice(
                partner_id=self.partner_a.id,
                move_type='out_invoice',
                invoice_line_ids=[
                    {'price_unit': 100.0, 'tax_ids': witholding_taxes.ids},
                    {'price_unit': 100.0, 'tax_ids': witholding_taxes.ids},
                    {'price_unit': 200.0, 'tax_ids': witholding_taxes.ids},
                ],
            )
            invoice.action_post()
            generated_file, errors = invoice._l10n_es_edi_facturae_render_facturae()
            self.assertFalse(errors)
            self.assertTrue(generated_file)
            with file_open("l10n_es_edi_facturae/tests/data/expected_tax_withholding.xml", "rt") as f:
                expected_xml = lxml.etree.fromstring(f.read().encode())
            self.assertXmlTreeEqual(lxml.etree.fromstring(generated_file), expected_xml)

    def test_in_invoice(self):
        random.seed(42)
        # We need to patch dates and uuid to ensure the signature's consistency
        with freeze_time(self.frozen_today), \
                patch(f"{self.certificate_module}.fields.datetime.now", lambda x=None: self.frozen_today), \
                patch(f"{self.certificate_module}.sha1", lambda x: sha1()):
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

    def test_out_invoice(self):
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
                patch(f"{self.certificate_module}.fields.datetime.now", lambda x=None: self.frozen_today), \
                patch(f"{self.certificate_module}.fields.datetime.now", lambda x=None: self.frozen_today), \
                patch(f"{self.certificate_module}.sha1", lambda x: sha1()):
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
            refund = invoice.reversal_move_id
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
                patch(f"{self.certificate_module}.fields.datetime.now", lambda x=None: self.frozen_today), \
                patch(f"{self.certificate_module}.sha1", lambda x: sha1()):
            invoice = self.create_invoice(
                partner_id=self.partner_a.id,
                move_type='out_invoice',
                invoice_line_ids=[{'product_id': self.product_a.id, 'price_unit': 1000.0, 'discount': 100.0, 'quantity': 2}],
            )
            invoice.action_post()
            wizard = self.create_send_and_print(invoice)
            result = wizard.action_send_and_print()

            self.assertEqual(result['type'], 'ir.actions.act_url')
            self.assertEqual(invoice.invoice_line_ids[0].price_subtotal, 0.0)

    def test_import_multiple_invoices(self):
        with file_open("l10n_es_edi_facturae/tests/data/import_multiple_invoices.xml", "rt") as f:
            imported_xml = lxml.etree.fromstring(f.read().encode())

        moves = self.env['account.move'].create({'move_type': 'out_invoice'})
        moves._import_invoice_facturae(moves, {'xml_tree': imported_xml})

        moves += self.env['account.move'].search([('ref', '=', 'INV/2023/00006'), ('company_id', '=', self.company_data['company'].id)], limit=1)

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
            imported_xml = lxml.etree.fromstring(f.read().encode())

        move = self.env['account.move'].create({'move_type': 'out_invoice'})
        move._import_invoice_facturae(move, {'xml_tree': imported_xml})

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
