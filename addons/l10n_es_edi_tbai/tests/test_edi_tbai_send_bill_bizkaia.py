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

RESPONSE_CONTENT_POST_BILL_SUCCESS = """
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ns2:LROEPJ240FacturasRecibidasAltaModifRespuesta xmlns:ns2="xxx">
    <Cabecera>
        <Modelo>XXX</Modelo>
        <Capitulo>XXX</Capitulo>
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
            <IDRecibida>
                <SerieFactura>XXX</SerieFactura>
                <NumFactura>XXX</NumFactura>
                <FechaExpedicionFactura>XXX</FechaExpedicionFactura>
                <EmisorFacturaRecibida>
                    <NIF>XXX</NIF>
                </EmisorFacturaRecibida>
            </IDRecibida>
            <SituacionRegistro>
                <EstadoRegistro>Correcto</EstadoRegistro>
            </SituacionRegistro>
        </Registro>
    </Registros>
</ns2:LROEPJ240FacturasRecibidasAltaModifRespuesta>
""".strip().encode('utf-8')

RESPONSE_CONTENT_CANCEL_BILL_SUCCESS = """
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ns2:LROEPJ240FacturasRecibidasAnulacionRespuesta xmlns:ns2="xxx">
    <Cabecera>
        <Modelo>XXX</Modelo>
        <Capitulo>XXX</Capitulo>
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
            <IDRecibida>
                <SerieFactura>XXX</SerieFactura>
                <NumFactura>XXX</NumFactura>
                <FechaExpedicionFactura>XXX</FechaExpedicionFactura>
                <EmisorFacturaRecibida>
                    <NIF>XXX</NIF>
                </EmisorFacturaRecibida>
            </IDRecibida>
            <SituacionRegistro>
                <EstadoRegistro>Correcto</EstadoRegistro>
            </SituacionRegistro>
        </Registro>
    </Registros>
</ns2:LROEPJ240FacturasRecibidasAnulacionRespuesta>
""".strip().encode('utf-8')


RESPONSE_CONTENT_POST_BILL_FAILURE = None

RESPONSE_CONTENT_CANCEL_BILL_FAILURE = """
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ns2:LROEPJ240FacturasRecibidasAnulacionRespuesta xmlns:ns2="xxx">
    <Cabecera>
        <Modelo>XXX</Modelo>
        <Capitulo>XXX</Capitulo>
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
            <IDRecibida>
                <NumFactura>XXX</NumFactura>
                <FechaExpedicionFactura>XXX</FechaExpedicionFactura>
                <EmisorFacturaRecibida>
                    <NIF>XXX</NIF>
                </EmisorFacturaRecibida>
            </IDRecibida>
            <SituacionRegistro>
                <EstadoRegistro>Incorrecto</EstadoRegistro>
                <CodigoErrorRegistro>B4_2000004</CodigoErrorRegistro>
                <DescripcionErrorRegistroES>Error description in Spanish.</DescripcionErrorRegistroES>
                <DescripcionErrorRegistroEU>Error description in Basque.</DescripcionErrorRegistroEU>
            </SituacionRegistro>
        </Registro>
    </Registros>
</ns2:LROEPJ240FacturasRecibidasAnulacionRespuesta>
""".strip().encode('utf-8')


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestSendBillEdiBizkaia(TestEsEdiTbaiCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        def create_mock_response(content, headers):
            mock_response = Mock(spec=requests.Response)
            mock_response.content = content
            mock_response.headers = headers
            return mock_response

        cls.mock_response_post_bill_success = create_mock_response(
            RESPONSE_CONTENT_POST_BILL_SUCCESS,
            RESPONSE_HEADERS_SUCCESS
        )
        cls.mock_response_cancel_bill_success = create_mock_response(
            RESPONSE_CONTENT_CANCEL_BILL_SUCCESS,
            RESPONSE_HEADERS_SUCCESS
        )
        cls.mock_response_post_bill_failure = create_mock_response(
            RESPONSE_CONTENT_POST_BILL_FAILURE,
            RESPONSE_HEADERS_FAILURE
        )
        cls.mock_response_cancel_bill_failure = create_mock_response(
            RESPONSE_CONTENT_CANCEL_BILL_FAILURE,
            RESPONSE_HEADERS_FAILURE
        )
        cls.mock_request_error = requests.exceptions.RequestException("A request exception")

        cls.company.l10n_es_tbai_tax_agency = 'bizkaia'

    def test_post_and_cancel_bill_tbai_success(self):
        bill = self._create_posted_bill()

        self.assertEqual(bill.l10n_es_tbai_state, 'to_send')
        self.assertFalse(bill.l10n_es_tbai_chain_index)
        self.assertFalse(bill.l10n_es_tbai_post_file)

        with patch(
            'odoo.addons.l10n_es_edi_tbai.models.account_move.requests.Session.request',
            return_value=self.mock_response_post_bill_success,
            ):
            bill.l10n_es_tbai_send_bill()

        self.assertEqual(bill.l10n_es_tbai_state, 'sent')
        # No chain index for vendor bills
        self.assertFalse(bill.l10n_es_tbai_chain_index)
        self.assertTrue(bill.l10n_es_tbai_post_file)

        self.assertEqual(bill.state, 'posted')
        self.assertFalse(bill.l10n_es_tbai_cancel_file)

        with patch(
            'odoo.addons.l10n_es_edi_tbai.models.account_move.requests.Session.request',
            return_value=self.mock_response_cancel_bill_success,
            ):
            bill.l10n_es_tbai_cancel()

        self.assertEqual(bill.l10n_es_tbai_state, 'cancelled')
        self.assertEqual(bill.state, 'cancel')
        self.assertTrue(bill.l10n_es_tbai_cancel_file)

    def test_post_bill_tbai_failure(self):
        bill = self._create_posted_bill()

        with self.assertRaises(UserError):
            with patch(
                'odoo.addons.l10n_es_edi_tbai.models.account_move.requests.Session.request',
                return_value=self.mock_response_post_bill_failure,
                ):
                bill.l10n_es_tbai_send_bill()

    def test_cancel_bill_tbai_failure(self):
        bill = self._create_posted_bill()

        with patch(
            'odoo.addons.l10n_es_edi_tbai.models.account_move.requests.Session.request',
            return_value=self.mock_response_post_bill_success,
            ):
            bill.l10n_es_tbai_send_bill()

        with self.assertRaises(UserError):
            with patch(
                'odoo.addons.l10n_es_edi_tbai.models.account_move.requests.Session.request',
                return_value=self.mock_response_cancel_bill_failure,
                ):
                bill.l10n_es_tbai_cancel()

    def test_post_bill_tbai_request_error(self):
        bill = self._create_posted_bill()

        with self.assertRaises(UserError):
            with patch(
                'odoo.addons.l10n_es_edi_tbai.models.account_move.requests.Session.request',
                side_effect=self.mock_request_error,
                ):
                bill.l10n_es_tbai_send_bill()
