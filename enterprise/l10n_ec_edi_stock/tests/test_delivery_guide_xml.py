from base64 import b64decode
from datetime import datetime
from freezegun import freeze_time
from lxml import etree
import pytz

from odoo.tests import tagged
from .common import TestECDeliveryGuideCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestECDeliveryGuide(TestECDeliveryGuideCommon):

    @freeze_time('2025-02-24')
    def test_send_delivery_guide_flow(self):
        ''' Test the delivery guide submission + cancellation flow. '''
        with self.mock_zeep_client((
            (
                # First call: send the delivery guide
                'validarComprobante',
                {
                    'xml': b'<guiaRemision id="comprobante" version="1.1.0">\n  <infoTributaria>\n    <ambiente>2</ambiente>\n    <tipoEmision>1</tipoEmision>\n    <razonSocial>EC Test Company (official)</razonSocial>\n    <nombreComercial>EC Test Company</nombreComercial>\n    <ruc>1792366836001</ruc>\n    <claveAcceso>2402202506179236683600120010010000000013121521416</claveAcceso>\n    <codDoc>06</codDoc>\n    <estab>001</estab>\n    <ptoEmi>001</ptoEmi>\n    <secuencial>000000001</secuencial>\n    <dirMatriz>Avenida Machala 42</dirMatriz>\n  </infoTributaria>\n  <infoGuiaRemision>\n    <dirEstablecimiento>Avenida Machala 42</dirEstablecimiento>\n    <dirPartida>Avenida Machala 42</dirPartida>\n    <razonSocialTransportista>Delivery guide Carrier EC</razonSocialTransportista>\n    <tipoIdentificacionTransportista>05</tipoIdentificacionTransportista>\n    <rucTransportista>0750032310</rucTransportista>\n    <obligadoContabilidad>SI</obligadoContabilidad>\n    <fechaIniTransporte>24/02/2025</fechaIniTransporte>\n    <fechaFinTransporte>11/03/2025</fechaFinTransporte>\n    <placa>OBA1413</placa>\n  </infoGuiaRemision>\n  <destinatarios>\n    <destinatario>\n      <identificacionDestinatario>0453661050152</identificacionDestinatario>\n      <razonSocialDestinatario>EC Test Partner A\xc3\xa0\xc3\x81\xc2\xb3$\xc2\xa3\xe2\x82\xac\xc3\xa8\xc3\xaa\xc3\x88\xc3\x8a\xc3\xb6\xc3\x94\xc3\x87\xc3\xa7\xc2\xa1\xe2\x85\x9b&amp;@\xe2\x84\xa2</razonSocialDestinatario>\n      <dirDestinatario>Av. Libertador Sim\xc3\xb3n Bol\xc3\xadvar 1155 -  - Quito - Ecuador</dirDestinatario>\n      <motivoTraslado>Goods Dispatch</motivoTraslado>\n      <detalles>\n        <detalle>\n          <codigoInterno>N/A</codigoInterno>\n          <descripcion>Computadora</descripcion>\n          <cantidad>1.0</cantidad>\n        </detalle>\n      </detalles>\n    </destinatario>\n  </destinatarios>\n</guiaRemision>\n',
                },
                {
                    'estado': 'RECIBIDA',
                    'comprobantes': None
                },
            ),
            (
                # Second call: retrieve the status
                'autorizacionComprobante',
                {
                    'claveAccesoComprobante': '2402202506179236683600120010010000000013121521416',
                },
                {
                    'numeroComprobantes': '1',
                    'autorizaciones': {
                        'autorizacion': [{
                            'estado': 'AUTORIZADO',
                            'numeroAutorizacion': '1912202406010364761600110010010001912253121521419',
                            'fechaAutorizacion': datetime(2024, 12, 19, 12, 5, 29, tzinfo=pytz.FixedOffset(-5 * 60)),
                            'ambiente': 'PRUEBAS',
                            'comprobante': 'dummy',
                            'mensajes': None,
                        }],
                    },
                },
            ),
            (
                # Third call: retrieve the status
                'autorizacionComprobante',
                {
                    'claveAccesoComprobante': '2402202506179236683600120010010000000013121521416',
                },
                {
                    'numeroComprobantes': '1',
                    'autorizaciones': {
                        'autorizacion': [{
                            'estado': 'CANCELADO',
                            'mensajes': None,
                        }],
                    },
                },
            )
        )):
            # Send the delivery guide
            stock_picking = self.get_stock_picking()
            self.prepare_delivery_guide(stock_picking)

            self.assertRecordValues(stock_picking, [{
                'l10n_ec_edi_status': 'sent',
                'l10n_ec_delivery_guide_error': False,
                'l10n_ec_authorization_date': datetime(2024, 12, 19, 12, 5, 29),
            }])

            # Cancel the delivery guide
            stock_picking.button_action_cancel_delivery_guide()
            stock_picking.l10n_ec_send_delivery_guide_to_cancel()
            self.assertRecordValues(stock_picking, [{
                'l10n_ec_edi_status': 'cancelled',
                'l10n_ec_delivery_guide_error': False,
                'l10n_ec_authorization_date': False,
            }])

    def test_xml_tree_delivery_guide_basic(self):
        '''
        Validates the XML content of a delivery guide
        '''
        with freeze_time(self.frozen_today):
            stock_picking = self.get_stock_picking()
            self.prepare_delivery_guide(stock_picking)
            attachment_id = self.env['ir.attachment'].search([
                ('res_model', '=', 'stock.picking'),
                ('res_id', '=', stock_picking.id),
            ])
            decoded_content = b64decode(attachment_id.datas).decode('utf-8')
            self.assertXmlTreeEqual(
                etree.fromstring(decoded_content),
                etree.fromstring(L10N_EC_EDI_XML_DELIVERY_GUIDE),
            )


L10N_EC_EDI_XML_DELIVERY_GUIDE = """<autorizacion>
    <estado>AUTORIZADO</estado>
    <numeroAutorizacion>2501202206179236683600110010010000000013121521412</numeroAutorizacion>
    <fechaAutorizacion>2022-01-24 00:00:00</fechaAutorizacion>
    <ambiente>PRUEBAS</ambiente>
    <comprobante>
        <guiaRemision id="comprobante" version="1.1.0">
            <infoTributaria>
                <ambiente>1</ambiente>
                <tipoEmision>1</tipoEmision>
                <razonSocial>EC Test Company (official)</razonSocial>
                <nombreComercial>EC Test Company</nombreComercial>
                <ruc>1792366836001</ruc>
                <claveAcceso>2501202206179236683600110010010000000013121521412</claveAcceso>
                <codDoc>06</codDoc>
                <estab>001</estab>
                <ptoEmi>001</ptoEmi>
                <secuencial>000000001</secuencial>
                <dirMatriz>Avenida Machala 42</dirMatriz>
            </infoTributaria>
            <infoGuiaRemision>
                <dirEstablecimiento>Avenida Machala 42</dirEstablecimiento>
                <dirPartida>Avenida Machala 42</dirPartida>
                <razonSocialTransportista>Delivery guide Carrier EC</razonSocialTransportista>
                <tipoIdentificacionTransportista>05</tipoIdentificacionTransportista>
                <rucTransportista>0750032310</rucTransportista>
                <obligadoContabilidad>SI</obligadoContabilidad>
                <fechaIniTransporte>25/01/2022</fechaIniTransporte>
                <fechaFinTransporte>09/02/2022</fechaFinTransporte>
                <placa>OBA1413</placa>
            </infoGuiaRemision>
            <destinatarios>
                <destinatario>
                    <identificacionDestinatario>0453661050152</identificacionDestinatario>
                    <razonSocialDestinatario>EC Test Partner AàÁ³$£€èêÈÊöÔÇç¡⅛&amp;@™</razonSocialDestinatario>
                    <dirDestinatario>Av. Libertador Simón Bolívar 1155 -  - Quito - Ecuador</dirDestinatario>
                    <motivoTraslado>Goods Dispatch</motivoTraslado>
                    <detalles>
                        <detalle>
                            <codigoInterno>N/A</codigoInterno>
                            <descripcion>Computadora</descripcion>
                            <cantidad>1.0</cantidad>
                        </detalle>
                    </detalles>
                </destinatario>
            </destinatarios>
        </guiaRemision>
    </comprobante>
</autorizacion>
""".encode()
