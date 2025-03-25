# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import requests

from pytz import timezone
from datetime import date, datetime
from unittest.mock import Mock
from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.tools import file_open
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.account.tests.test_account_move_send import TestAccountMoveSendCommon


class TestEsEdiTbaiCommon(TestAccountMoveSendCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('es')
    def setUpClass(cls):
        super().setUpClass()

        cls.frozen_today = datetime(year=2025, month=1, day=1, hour=0, minute=0, second=0, tzinfo=timezone('utc'))

        # Allow to see the full result of AssertionError.
        cls.maxDiff = None

        # ==== Config ====

        cls.company_data['company'].write({
            'name': 'EUS Company',
            'state_id': cls.env.ref('base.state_es_ss').id,
            'vat': 'ESA12345674',
            'l10n_es_tbai_test_env': True,
        })
        cls._set_tax_agency('gipuzkoa')

        # ==== Business ====

        cls.partner_a.write({
            'name': "&@àÁ$£€èêÈÊöÔÇç¡⅛™³",  # special characters should be escaped appropriately
            'vat': 'BE0477472701',
            'country_id': cls.env.ref('base.be').id,
            'street': 'Rue Sans Souci 1',
            'zip': 93071,
            'invoice_edi_format': False,
        })

        cls.partner_b.write({
            'vat': 'ESF35999705',
        })

    @classmethod
    def _set_tax_agency(cls, agency):
        if agency == "araba":
            cert_name = 'araba_1234.p12'
            cert_password = '1234'
        elif agency == 'bizkaia':
            cert_name = 'Bizkaia-IZDesa2025.p12'
            cert_password = 'IZDesa2025'
        elif agency == 'gipuzkoa':
            cert_name = 'gipuzkoa_Iz3np32024.p12'
            cert_password = 'Iz3np32024'
        else:
            raise ValueError("Unknown tax agency: " + agency)

        cls.certificate = cls.env['certificate.certificate'].create({
            'name': 'Test ES TBAI certificate',
            'content': base64.b64encode(
                file_open("l10n_es_edi_tbai/demo/certificates/" + cert_name, 'rb').read()),
            'pkcs12_password': cert_password,
            'scope': 'tbai',
            'company_id': cls.company_data['company'].id,
        })

        # Prevent certificate expiration in tests
        cls.certificate.date_end = fields.Datetime.now() + relativedelta(days=2)
        cls.company_data['company'].write({
            'l10n_es_tbai_tax_agency': agency,
            'l10n_es_tbai_certificate_id': cls.certificate.id,
        })

    @classmethod
    def _get_tax_by_xml_id(cls, trailing_xml_id):
        """ Helper to retrieve a tax easily.

        :param trailing_xml_id: The trailing tax's xml id.
        :return:                An account.tax record
        """
        return cls.env.ref(f'account.{cls.env.company.id}_account_tax_template_{trailing_xml_id}')

    @classmethod
    def create_invoice(cls, **kwargs):
        return cls.env['account.move'].with_context(edi_test_mode=True).create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner_a.id,
            'invoice_date': '2025-01-01',
            'date': '2025-01-01',
            **kwargs,
            'invoice_line_ids': [(0, 0, {
                'product_id': cls.product_a.id,
                'price_unit': 1000.0,
                **line_vals,
            }) for line_vals in kwargs.get('invoice_line_ids', [])],
        })

    @classmethod
    def _create_posted_invoice(cls):
        out_invoice = cls.env['account.move'].create({
                'move_type': 'out_invoice',
                'invoice_date': date(2025, 1, 1),
                'partner_id': cls.partner_a.id,
                'invoice_line_ids': [(0, 0, {
                    'product_id': cls.product_a.id,
                    'price_unit': 1000.0,
                    'quantity': 5,
                    'discount': 20.0,
                    'tax_ids': [(6, 0, cls._get_tax_by_xml_id('s_iva21b').ids)],
            })],
        })
        out_invoice.action_post()
        return out_invoice

    @classmethod
    def _get_invoice_send_wizard(cls, invoice):
        out_invoice_send_wizard = cls.env['account.move.send.wizard']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({'sending_methods': []})
        return out_invoice_send_wizard

    @classmethod
    def _create_posted_bill(cls):
        bill = cls.env['account.move'].create({
            'move_type': 'in_invoice',
            'invoice_date': date.today(),
            'partner_id': cls.partner_a.id,
            'ref': "INV123",
            'invoice_line_ids': [(0, 0, {
                'product_id': cls.product_a.id,
                'price_unit': 1000.0,
                'quantity': 5,
                'discount': 20.0,
                'tax_ids': [(6, 0, cls._get_tax_by_xml_id('p_iva21_bc').ids)],
            })],
        })
        bill.action_post()
        return bill

    @classmethod
    def _get_sample_xml(cls, filename):
        with file_open(f'l10n_es_edi_tbai/tests/document_xmls/{filename}', 'rb') as file:
            content = file.read()
        return content

    @classmethod
    def _get_response_xml(cls, filename):
        with file_open(f'l10n_es_edi_tbai/tests/response_xmls/{filename}', 'rb') as file:
            content = file.read()
        return content


def create_mock_response(content, headers=None):
    mock_response = Mock(spec=requests.Response)
    mock_response.content = content
    mock_response.headers = headers or {}
    return mock_response


class TestEsEdiTbaiCommonGipuzkoa(TestEsEdiTbaiCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.mock_response_post_invoice_success = create_mock_response(cls._get_response_xml('post_invoice_success_gi.xml'))
        cls.mock_response_cancel_invoice_success = create_mock_response(cls._get_response_xml('cancel_invoice_success_gi.xml'))
        cls.mock_response_failure = create_mock_response(cls._get_response_xml('post_or_cancel_invoice_failure_gi.xml'))
        cls.mock_request_error = requests.exceptions.RequestException("A request exception")


class TestEsEdiTbaiCommonBizkaia(TestEsEdiTbaiCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.mock_response_post_invoice_success = create_mock_response(
            cls._get_response_xml('post_invoice_success_bi.xml'),
            cls.RESPONSE_HEADERS_SUCCESS
        )
        cls.mock_response_cancel_invoice_success = create_mock_response(
            cls._get_response_xml('cancel_invoice_success_bi.xml'),
            cls.RESPONSE_HEADERS_SUCCESS
        )
        cls.mock_response_post_invoice_failure = create_mock_response(
            cls._get_response_xml('post_invoice_failure_bi.xml'),
            cls.RESPONSE_HEADERS_FAILURE
        )
        cls.mock_response_cancel_invoice_failure = create_mock_response(
            cls._get_response_xml('cancel_invoice_failure_bi.xml'),
            cls.RESPONSE_HEADERS_FAILURE
        )
        cls.mock_response_post_bill_success = create_mock_response(
            cls._get_response_xml('post_bill_success_bi.xml'),
            cls.RESPONSE_HEADERS_SUCCESS
        )
        cls.mock_response_cancel_bill_success = create_mock_response(
            cls._get_response_xml('cancel_bill_success_bi.xml'),
            cls.RESPONSE_HEADERS_SUCCESS
        )
        cls.mock_response_post_bill_failure = create_mock_response(
            None,
            cls.RESPONSE_HEADERS_FAILURE
        )
        cls.mock_response_cancel_bill_failure = create_mock_response(
            cls._get_response_xml('cancel_bill_failure_bi.xml'),
            cls.RESPONSE_HEADERS_FAILURE
        )
        cls.mock_request_error = requests.exceptions.RequestException("A request exception")

        cls.company.l10n_es_tbai_tax_agency = 'bizkaia'

    RESPONSE_HEADERS_SUCCESS = {
        'eus-bizkaia-n3-tipo-respuesta': 'Correcto',
        'eus-bizkaia-n3-codigo-respuesta': '',
    }

    RESPONSE_HEADERS_FAILURE = {
        'eus-bizkaia-n3-tipo-respuesta': 'Incorrecto',
        'eus-bizkaia-n3-codigo-respuesta': 'B4_1000002',
        'eus-bizkaia-n3-mensaje-respuesta': 'An error msg.',
    }
