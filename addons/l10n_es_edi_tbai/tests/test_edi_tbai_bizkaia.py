from unittest.mock import Mock, patch
import requests

from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import TestEsEdiTbaiCommon


RESPONSE_HEADERS_SUCCESS = {
    'eus-bizkaia-n3-tipo-respuesta': 'Correcto',
    'eus-bizkaia-n3-codigo-respuesta': '',
}

RESPONSE_HEADERS_FAILURE = {
    'eus-bizkaia-n3-tipo-respuesta': 'Incorrecto',
    'eus-bizkaia-n3-codigo-respuesta': 'B4_1000002',
    'eus-bizkaia-n3-mensaje-respuesta': 'An error msg.',
}

RESPONSE_CONTENT_POST_INVOICE_SUCCESS = """
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ns2:LROEPJ240FacturasEmitidasConSGAltaRespuesta xmlns:ns2="xxx">
    <Cabecera>
        <Modelo>XXX</Modelo>
        <Capitulo>XXX</Capitulo>
        <Subcapitulo>XXX</Subcapitulo>
        <Operacion>XXX</Operacion>
        <Version>XXX</Version>
        <Ejercicio>XXX</Ejercicio>
        <ObligadoTributario>
            <NIF>XXX</NIF>
            <ApellidosNombreRazonSocial>XXX</ApellidosNombreRazonSocial>
        </ObligadoTributario>
    </Cabecera>
    <DatosPresentacion>
        <FechaPresentacion>XXX</FechaPresentacion>
        <NIFPresentador>XXX</NIFPresentador>
    </DatosPresentacion>
    <Registros>
        <Registro>
            <Identificador>
                <IDFactura>
                    <SerieFactura>XXX</SerieFactura>
                    <NumFactura>XXX</NumFactura>
                    <FechaExpedicionFactura>XXX</FechaExpedicionFactura>
                </IDFactura>
            </Identificador>
            <SituacionRegistro>
                <EstadoRegistro>Correcto</EstadoRegistro>
            </SituacionRegistro>
        </Registro>
    </Registros>
</ns2:LROEPJ240FacturasEmitidasConSGAltaRespuesta>
""".strip().encode('utf-8')

RESPONSE_CONTENT_CANCEL_INVOICE_SUCCESS = """
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ns2:LROEPJ240FacturasEmitidasConSGAnulacionRespuesta xmlns:ns2="xxx">
    <Cabecera>
        <Modelo>XXX</Modelo>
        <Capitulo>XXX</Capitulo>
        <Subcapitulo>XXX</Subcapitulo>
        <Operacion>XXX</Operacion>
        <Version>XXX</Version>
        <Ejercicio>XXX</Ejercicio>
        <ObligadoTributario>
            <NIF>XXX</NIF>
            <ApellidosNombreRazonSocial>XXX</ApellidosNombreRazonSocial>
        </ObligadoTributario>
    </Cabecera>
    <DatosPresentacion>
        <FechaPresentacion>XXX</FechaPresentacion>
        <NIFPresentador>XXX</NIFPresentador>
    </DatosPresentacion>
    <Registros>
        <Registro>
            <Identificador>
                <IDFactura>
                    <SerieFactura>XXX</SerieFactura>
                    <NumFactura>XXX</NumFactura>
                    <FechaExpedicionFactura>XXX</FechaExpedicionFactura>
                </IDFactura>
            </Identificador>
            <SituacionRegistro>
                <EstadoRegistro>Correcto</EstadoRegistro>
            </SituacionRegistro>
        </Registro>
    </Registros>
</ns2:LROEPJ240FacturasEmitidasConSGAnulacionRespuesta>
""".strip().encode('utf-8')

RESPONSE_CONTENT_POST_INVOICE_FAILURE = """
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ns2:LROEPJ240FacturasEmitidasConSGAltaRespuesta xmlns:ns2="xxx">
    <Cabecera>
        <Modelo>XXX</Modelo>
        <Capitulo>XXX</Capitulo>
        <Subcapitulo>XXX</Subcapitulo>
        <Operacion>XXX</Operacion>
        <Version>XXX</Version>
        <Ejercicio>XXX</Ejercicio>
        <ObligadoTributario>
            <NIF>XXX</NIF>
            <ApellidosNombreRazonSocial>XXX</ApellidosNombreRazonSocial>
        </ObligadoTributario>
    </Cabecera>
    <Registros>
        <Registro>
            <Identificador>
                <TicketBai>XXX</TicketBai>
            </Identificador>
            <SituacionRegistro>
                <EstadoRegistro>Incorrecto</EstadoRegistro>
                <CodigoErrorRegistro>B4_2000001</CodigoErrorRegistro>
                <DescripcionErrorRegistroES>Error description in Spanish.</DescripcionErrorRegistroES>
                <DescripcionErrorRegistroEU>Error description in Basque.</DescripcionErrorRegistroEU>
            </SituacionRegistro>
        </Registro>
    </Registros>
</ns2:LROEPJ240FacturasEmitidasConSGAltaRespuesta>
""".strip().encode('utf-8')

RESPONSE_CONTENT_CANCEL_INVOICE_FAILURE = """
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ns2:LROEPJ240FacturasEmitidasConSGAnulacionRespuesta xmlns:ns2="xxx">
    <Cabecera>
        <Modelo>XXX</Modelo>
        <Capitulo>XXX</Capitulo>
        <Subcapitulo>XXX</Subcapitulo>
        <Operacion>XXX</Operacion>
        <Version>XXX</Version>
        <Ejercicio>XXX</Ejercicio>
        <ObligadoTributario>
            <NIF>XXX</NIF>
            <ApellidosNombreRazonSocial>XXX</ApellidosNombreRazonSocial>
        </ObligadoTributario>
    </Cabecera>
    <Registros>
        <Registro>
            <Identificador>
                <AnulacionTicketBai>XXXX</AnulacionTicketBai>
            </Identificador>
            <SituacionRegistro>
                <EstadoRegistro>Incorrecto</EstadoRegistro>
                <CodigoErrorRegistro>B4_2000001</CodigoErrorRegistro>
                <DescripcionErrorRegistroES>Error description in Spanish.</DescripcionErrorRegistroES>
                <DescripcionErrorRegistroEU>Error description in Basque.</DescripcionErrorRegistroEU>
            </SituacionRegistro>
        </Registro>
    </Registros>
</ns2:LROEPJ240FacturasEmitidasConSGAnulacionRespuesta>
""".strip().encode('utf-8')


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestSendAndPrintEdiBizkaia(TestEsEdiTbaiCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        def create_mock_response(content, headers):
            mock_response = Mock(spec=requests.Response)
            mock_response.content = content
            mock_response.headers = headers
            return mock_response

        cls.mock_response_post_invoice_success = create_mock_response(
            RESPONSE_CONTENT_POST_INVOICE_SUCCESS,
            RESPONSE_HEADERS_SUCCESS
        )
        cls.mock_response_cancel_invoice_success = create_mock_response(
            RESPONSE_CONTENT_CANCEL_INVOICE_SUCCESS,
            RESPONSE_HEADERS_SUCCESS
        )
        cls.mock_response_post_invoice_failure = create_mock_response(
            RESPONSE_CONTENT_POST_INVOICE_FAILURE,
            RESPONSE_HEADERS_FAILURE
        )
        cls.mock_response_cancel_invoice_failure = create_mock_response(
            RESPONSE_CONTENT_CANCEL_INVOICE_FAILURE,
            RESPONSE_HEADERS_FAILURE
        )
        cls.mock_request_error = requests.exceptions.RequestException("A request exception")

        cls.company.l10n_es_tbai_tax_agency = 'bizkaia'

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
                return_value=self.mock_response_post_invoice_failure,
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
                return_value=self.mock_response_cancel_invoice_failure,
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
