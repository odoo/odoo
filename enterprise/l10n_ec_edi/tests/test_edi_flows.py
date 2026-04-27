from datetime import datetime
import pytz

from odoo.tests import tagged
from .common import TestEcEdiCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestEcEdiFlow(TestEcEdiCommon):
    def test_send_invoice(self):
        ''' Test the delivery guide submission + cancellation flow. '''

        expected_operations = (
            (
                # First call: send the invoice
                'validarComprobante',
                {
                    'xml': b'<factura version="2.1.0" id="comprobante">\n  <infoTributaria>\n    <ambiente>2</ambiente>\n    <tipoEmision>1</tipoEmision>\n    <razonSocial>EC Test Company (official)</razonSocial>\n    <nombreComercial>EC Test Company</nombreComercial>\n    <ruc>1792366836001</ruc>\n    <claveAcceso>2501202201179236683600110010010000000013121521410</claveAcceso>\n    <codDoc>01</codDoc>\n    <estab>001</estab>\n    <ptoEmi>001</ptoEmi>\n    <secuencial>000000001</secuencial>\n    <dirMatriz>Avenida Machala 42</dirMatriz>\n  </infoTributaria>\n  <infoFactura>\n    <fechaEmision>25/01/2022</fechaEmision>\n    <dirEstablecimiento>Avenida Machala 42</dirEstablecimiento>\n    <obligadoContabilidad>SI</obligadoContabilidad>\n    <tipoIdentificacionComprador>04</tipoIdentificacionComprador>\n    <razonSocialComprador>EC Test Partner A\xc3\xa0\xc3\x81\xc2\xb3$\xc2\xa3\xe2\x82\xac\xc3\xa8\xc3\xaa\xc3\x88\xc3\x8a\xc3\xb6\xc3\x94\xc3\x87\xc3\xa7\xc2\xa1\xe2\x85\x9b&amp;@\xe2\x84\xa2</razonSocialComprador>\n    <identificacionComprador>0453661050152</identificacionComprador>\n    <direccionComprador>Av. Libertador Sim\xc3\xb3n Bol\xc3\xadvar 1155</direccionComprador>\n    <totalSinImpuestos>400.000000</totalSinImpuestos>\n    <totalDescuento>100.00</totalDescuento>\n    <totalConImpuestos>\n      <totalImpuesto>\n        <codigo>2</codigo>\n        <codigoPorcentaje>5</codigoPorcentaje>\n        <baseImponible>400.000000</baseImponible>\n        <tarifa>5.000000</tarifa>\n        <valor>20.00</valor>\n      </totalImpuesto>\n    </totalConImpuestos>\n    <importeTotal>420.00</importeTotal>\n    <moneda>DOLAR</moneda>\n    <pagos>\n      <pago>\n        <formaPago>16</formaPago>\n        <total>420.00</total>\n        <plazo>0</plazo>\n        <unidadTiempo>dias</unidadTiempo>\n      </pago>\n    </pagos>\n  </infoFactura>\n  <detalles>\n    <detalle>\n      <codigoPrincipal>N/A</codigoPrincipal>\n      <descripcion>product_a</descripcion>\n      <cantidad>5.000000</cantidad>\n      <precioUnitario>100.000000</precioUnitario>\n      <descuento>100.00</descuento>\n      <precioTotalSinImpuesto>400.00</precioTotalSinImpuesto>\n      <impuestos>\n        <impuesto>\n          <codigo>2</codigo>\n          <codigoPorcentaje>5</codigoPorcentaje>\n          <tarifa>5.000000</tarifa>\n          <baseImponible>400.000000</baseImponible>\n          <valor>20.00</valor>\n        </impuesto>\n      </impuestos>\n    </detalle>\n  </detalles>\n  <infoAdicional>\n    <campoAdicional nombre="Referencia">Fact 001-001-000000001</campoAdicional>\n    <campoAdicional nombre="Vendedor">Because I am accountman!</campoAdicional>\n    <campoAdicional nombre="E-mail">accountman@test.com</campoAdicional>\n  </infoAdicional>\n</factura>\n'
                },
                {
                    'estado': 'RECIBIDA',
                    'comprobantes': None,
                },
            ),
            (
                # Second call: retrieve the status
                'autorizacionComprobante',
                {'claveAccesoComprobante': '2501202201179236683600110010010000000013121521410'},
                {
                    'numeroComprobantes': '1',
                    'autorizaciones': {
                        'autorizacion': [{
                            'estado': 'AUTORIZADO',
                            'numeroAutorizacion': '2501202201179236683600110010010000000013121521410',
                            'fechaAutorizacion': datetime(2024, 12, 19, 12, 5, 29, tzinfo=pytz.FixedOffset(-5 * 60)),
                            'ambiente': 'PRUEBAS',
                            'comprobante': 'dummy',
                            'mensajes': None,
                        }],
                    },
                },
            ),
        )

        line_vals = self.get_invoice_line_vals(vat_tax_xmlid='tax_vat_05_510_sup_01')
        out_invoice = self.get_invoice(
            {
                'move_type': 'out_invoice',
                'partner_id': self.partner_a.id,
            },
            invoice_line_args=line_vals,
        )

        out_invoice.action_post()

        with self.mock_zeep_client(expected_operations):
            # Send the invoice
            out_invoice.button_process_edi_web_services()
