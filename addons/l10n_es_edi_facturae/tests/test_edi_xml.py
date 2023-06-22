import logging
import random
from base64 import b64encode
from datetime import datetime
from hashlib import sha1
from unittest.mock import patch

import lxml
from freezegun import freeze_time

from odoo import Command
from odoo.addons.account_edi.tests.common import AccountEdiTestCommon
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools import file_open

_logger = logging.getLogger(__name__)

@tagged('post_install_l10n', 'post_install', '-at_install')
class TestEdiFacturaeXmls(AccountEdiTestCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref='es_full', edi_format_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref, edi_format_ref=edi_format_ref)
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

        # ==== Business ====
        cls.partner_a.write({  # -> PersonTypeCode 'F'
            'country_id': cls.env.ref('base.be').id,  # -> ResidenceTypeCode 'U'
            'vat': 'BE0477472701',
            'city': "Namur",
            'street': "Rue de Bruxelles, 15000",
            'zip': "5000",
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
            generated_file, errors = refund._l10n_es_edi_facturae_render_facturae()
            self.assertFalse(errors)
            self.assertTrue(generated_file)

            with file_open("l10n_es_edi_facturae/tests/data/expected_refund_document.xml", "rt") as f:
                expected_xml = lxml.etree.fromstring(f.read().encode())
            self.assertXmlTreeEqual(lxml.etree.fromstring(generated_file), expected_xml)
