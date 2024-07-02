from unittest.mock import Mock, patch
import requests

from odoo.exceptions import UserError
from odoo.tests import tagged


from .common import TestEsEdiTbaiCommon

RESPONSE_CONTENT_POST_INVOICE_SUCCESS = """
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ns2:TicketBaiResponse xmlns:ns2="urn:ticketbai:emision">
    <Salida>
        <IdentificadorTBAI>XXX</IdentificadorTBAI>
        <FechaRecepcion>XXX</FechaRecepcion>
        <Estado>00</Estado>
        <Descripcion>XXX</Descripcion>
        <Azalpena>XXX</Azalpena>
        <ResultadosValidacion>
            <Codigo>1234</Codigo>
            <Descripcion>Explanation in Spanish</Descripcion>
            <Azalpena>Explanation in Basque</Azalpena>
        </ResultadosValidacion>
        <CSV>XXX</CSV>
    </Salida>
</ns2:TicketBaiResponse>
""".strip().encode('utf-8')

RESPONSE_CONTENT_CANCEL_INVOICE_SUCCESS = """
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ns2:TicketBaiResponse xmlns:ns2="urn:ticketbai:emision">
    <Salida>
        <IdentificadorTBAI>XXX</IdentificadorTBAI>
        <FechaRecepcion>XXX</FechaRecepcion>
        <Estado>00</Estado>
        <Descripcion>XXX</Descripcion>
        <Azalpena>XXX</Azalpena>
        <CSV>XXX</CSV>
    </Salida>
</ns2:TicketBaiResponse>
""".strip().encode('utf-8')

RESPONSE_CONTENT_FAILURE = """
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ns2:TicketBaiResponse xmlns:ns2="urn:ticketbai:emision">
    <Salida>
        <FechaRecepcion>XXX</FechaRecepcion>
        <Estado>01</Estado>
        <Descripcion>XXX</Descripcion>
        <Azalpena>XXX</Azalpena>
        <ResultadosValidacion>
            <Codigo>002</Codigo>
            <Descripcion>Error in Spanish.</Descripcion>
            <Azalpena>Error in Basque.</Azalpena>
        </ResultadosValidacion>
    </Salida>
</ns2:TicketBaiResponse>
""".strip().encode('utf-8')


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestSendAndPrintEdiGipuzkoa(TestEsEdiTbaiCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        def create_mock_response(content):
            mock_response = Mock(spec=requests.Response)
            mock_response.content = content
            return mock_response

        cls.mock_response_post_invoice_success = create_mock_response(RESPONSE_CONTENT_POST_INVOICE_SUCCESS)
        cls.mock_response_cancel_invoice_success = create_mock_response(RESPONSE_CONTENT_CANCEL_INVOICE_SUCCESS)
        cls.mock_response_failure = create_mock_response(RESPONSE_CONTENT_FAILURE)
        cls.mock_request_error = requests.exceptions.RequestException("A request exception")

    def test_post_and_cancel_invoice_tbai_success(self):
        invoice = self._create_posted_invoice()
        invoice_send_wizard = self._get_invoice_send_wizard(invoice)

        self.assertEqual(invoice.l10n_es_tbai_state, 'to_send')
        self.assertFalse(invoice.l10n_es_tbai_chain_index)
        self.assertFalse(invoice.l10n_es_tbai_post_file)

        with patch(
            'odoo.addons.l10n_es_edi_tbai.models.account_move.requests.Session.request',
            return_value=self.mock_response_post_invoice_success,
            ):
            invoice_send_wizard.action_send_and_print()

        self.assertEqual(invoice.l10n_es_tbai_state, 'sent')
        self.assertTrue(invoice.l10n_es_tbai_chain_index)
        self.assertTrue(invoice.l10n_es_tbai_post_file)

        self.assertEqual(invoice.state, 'posted')
        self.assertFalse(invoice.l10n_es_tbai_cancel_file)

        with patch(
            'odoo.addons.l10n_es_edi_tbai.models.account_move.requests.Session.request',
            return_value=self.mock_response_cancel_invoice_success,
            ):
            invoice.l10n_es_tbai_cancel()

        self.assertEqual(invoice.l10n_es_tbai_state, 'cancelled')
        self.assertEqual(invoice.state, 'cancel')
        self.assertTrue(invoice.l10n_es_tbai_cancel_file)

    def test_post_invoice_tbai_failure(self):
        invoice = self._create_posted_invoice()
        invoice_send_wizard = self._get_invoice_send_wizard(invoice)

        with self.assertRaises(UserError):
            with patch(
                'odoo.addons.l10n_es_edi_tbai.models.account_move.requests.Session.request',
                return_value=self.mock_response_failure,
                ):
                invoice_send_wizard.action_send_and_print()

    def test_cancel_invoice_tbai_failure(self):
        invoice = self._create_posted_invoice()
        invoice_send_wizard = self._get_invoice_send_wizard(invoice)

        with patch(
            'odoo.addons.l10n_es_edi_tbai.models.account_move.requests.Session.request',
            return_value=self.mock_response_post_invoice_success,
            ):
            invoice_send_wizard.action_send_and_print()

        with self.assertRaises(UserError):
            with patch(
                'odoo.addons.l10n_es_edi_tbai.models.account_move.requests.Session.request',
                return_value=self.mock_response_failure,
                ):
                invoice.l10n_es_tbai_cancel()

    def test_post_invoice_tbai_request_error(self):
        invoice = self._create_posted_invoice()
        invoice_send_wizard = self._get_invoice_send_wizard(invoice)

        with self.assertRaises(UserError):
            with patch(
                'odoo.addons.l10n_es_edi_tbai.models.account_move.requests.Session.request',
                side_effect=self.mock_request_error,
                ):
                invoice_send_wizard.action_send_and_print()
