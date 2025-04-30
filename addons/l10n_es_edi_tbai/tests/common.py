# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from pytz import timezone
from datetime import date, datetime
import requests
from unittest.mock import Mock

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
            cert_name = 'bizkaia_111111.p12'
            cert_password = '111111'
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

<<<<<<< 98ef54a1bb7a2c3085b7802efdb88a55a83622b6
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
||||||| 51027e84e269f9c5d96b56d64488e1deb2f66c02
    L10N_ES_TBAI_SAMPLE_XML_POST = """<?xml version='1.0' encoding='UTF-8'?>
<T:TicketBai xmlns:etsi="http://uri.etsi.org/01903/v1.3.2#" xmlns:T="urn:ticketbai:emision" xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
  <Cabecera>
    <IDVersionTBAI>1.2</IDVersionTBAI>
  </Cabecera>
  <Sujetos>
    <Emisor>
      <NIF>___ignore___</NIF>
      <ApellidosNombreRazonSocial>EUS Company</ApellidosNombreRazonSocial>
    </Emisor>
    <Destinatarios>
      <IDDestinatario>
        <IDOtro>
          <IDType>02</IDType>
          <ID>BE0477472701</ID>
        </IDOtro>
        <ApellidosNombreRazonSocial>&amp;@&#224;&#193;$&#163;&#8364;&#232;&#234;&#200;&#202;&#246;&#212;&#199;&#231;&#161;&#8539;&#8482;&#179;</ApellidosNombreRazonSocial>
        <CodigoPostal>___ignore___</CodigoPostal>
        <Direccion>___ignore___</Direccion>
      </IDDestinatario>
    </Destinatarios>
    <VariosDestinatarios>N</VariosDestinatarios>
    <EmitidaPorTercerosODestinatario>N</EmitidaPorTercerosODestinatario>
  </Sujetos>
  <Factura>
    <CabeceraFactura>
      <SerieFactura>INVTEST</SerieFactura>
      <NumFactura>01</NumFactura>
      <FechaExpedicionFactura>01-01-2022</FechaExpedicionFactura>
      <HoraExpedicionFactura>___ignore___</HoraExpedicionFactura>
      <FacturaSimplificada>N</FacturaSimplificada>
    </CabeceraFactura>
    <DatosFactura>
      <DescripcionFactura>manual</DescripcionFactura>
      <DetallesFactura>
        <IDDetalleFactura>
          <DescripcionDetalle>producta</DescripcionDetalle>
          <Cantidad>5.00</Cantidad>
          <ImporteUnitario>1000.00</ImporteUnitario>
          <Descuento>1000.00</Descuento>
          <ImporteTotal>4840.00</ImporteTotal>
        </IDDetalleFactura>
      </DetallesFactura>
      <ImporteTotalFactura>4840.00</ImporteTotalFactura>
      <Claves>
        <IDClave>
          <ClaveRegimenIvaOpTrascendencia>01</ClaveRegimenIvaOpTrascendencia>
        </IDClave>
      </Claves>
    </DatosFactura>
    <TipoDesglose>
      <DesgloseTipoOperacion>
        <Entrega>
          <Sujeta>
            <NoExenta>
              <DetalleNoExenta>
                <TipoNoExenta>S1</TipoNoExenta>
                <DesgloseIVA>
                  <DetalleIVA>
                    <BaseImponible>4000.00</BaseImponible>
                    <TipoImpositivo>21.00</TipoImpositivo>
                    <CuotaImpuesto>840.00</CuotaImpuesto>
                    <OperacionEnRecargoDeEquivalenciaORegimenSimplificado>N</OperacionEnRecargoDeEquivalenciaORegimenSimplificado>
                  </DetalleIVA>
                </DesgloseIVA>
              </DetalleNoExenta>
            </NoExenta>
          </Sujeta>
        </Entrega>
      </DesgloseTipoOperacion>
    </TipoDesglose>
  </Factura>
  <HuellaTBAI>
    <Software>
      <LicenciaTBAI>___ignore___</LicenciaTBAI>
      <EntidadDesarrolladora>
        <NIF>___ignore___</NIF>
      </EntidadDesarrolladora>
      <Nombre>___ignore___</Nombre>
      <Version>___ignore___</Version>
    </Software>
    <NumSerieDispositivo>___ignore___</NumSerieDispositivo>
  </HuellaTBAI>
</T:TicketBai>
""".encode("utf-8")
=======
    L10N_ES_TBAI_SAMPLE_XML_POST = """<?xml version='1.0' encoding='UTF-8'?>
<T:TicketBai xmlns:etsi="http://uri.etsi.org/01903/v1.3.2#" xmlns:T="urn:ticketbai:emision" xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
  <Cabecera>
    <IDVersionTBAI>1.2</IDVersionTBAI>
  </Cabecera>
  <Sujetos>
    <Emisor>
      <NIF>___ignore___</NIF>
      <ApellidosNombreRazonSocial>EUS Company</ApellidosNombreRazonSocial>
    </Emisor>
    <Destinatarios>
      <IDDestinatario>
        <IDOtro>
          <IDType>02</IDType>
          <ID>BE0477472701</ID>
        </IDOtro>
        <ApellidosNombreRazonSocial>&amp;@&#224;&#193;$&#163;&#8364;&#232;&#234;&#200;&#202;&#246;&#212;&#199;&#231;&#161;&#8539;&#8482;&#179;</ApellidosNombreRazonSocial>
        <CodigoPostal>___ignore___</CodigoPostal>
        <Direccion>___ignore___</Direccion>
      </IDDestinatario>
    </Destinatarios>
    <VariosDestinatarios>N</VariosDestinatarios>
    <EmitidaPorTercerosODestinatario>N</EmitidaPorTercerosODestinatario>
  </Sujetos>
  <Factura>
    <CabeceraFactura>
      <SerieFactura>INVTEST</SerieFactura>
      <NumFactura>01</NumFactura>
      <FechaExpedicionFactura>01-01-2025</FechaExpedicionFactura>
      <HoraExpedicionFactura>___ignore___</HoraExpedicionFactura>
      <FacturaSimplificada>N</FacturaSimplificada>
    </CabeceraFactura>
    <DatosFactura>
      <DescripcionFactura>manual</DescripcionFactura>
      <DetallesFactura>
        <IDDetalleFactura>
          <DescripcionDetalle>producta</DescripcionDetalle>
          <Cantidad>5.00</Cantidad>
          <ImporteUnitario>1000.00</ImporteUnitario>
          <Descuento>1000.00</Descuento>
          <ImporteTotal>4840.00</ImporteTotal>
        </IDDetalleFactura>
      </DetallesFactura>
      <ImporteTotalFactura>4840.00</ImporteTotalFactura>
      <Claves>
        <IDClave>
          <ClaveRegimenIvaOpTrascendencia>01</ClaveRegimenIvaOpTrascendencia>
        </IDClave>
      </Claves>
    </DatosFactura>
    <TipoDesglose>
      <DesgloseTipoOperacion>
        <Entrega>
          <Sujeta>
            <NoExenta>
              <DetalleNoExenta>
                <TipoNoExenta>S1</TipoNoExenta>
                <DesgloseIVA>
                  <DetalleIVA>
                    <BaseImponible>4000.00</BaseImponible>
                    <TipoImpositivo>21.00</TipoImpositivo>
                    <CuotaImpuesto>840.00</CuotaImpuesto>
                    <OperacionEnRecargoDeEquivalenciaORegimenSimplificado>N</OperacionEnRecargoDeEquivalenciaORegimenSimplificado>
                  </DetalleIVA>
                </DesgloseIVA>
              </DetalleNoExenta>
            </NoExenta>
          </Sujeta>
        </Entrega>
      </DesgloseTipoOperacion>
    </TipoDesglose>
  </Factura>
  <HuellaTBAI>
    <Software>
      <LicenciaTBAI>___ignore___</LicenciaTBAI>
      <EntidadDesarrolladora>
        <NIF>___ignore___</NIF>
      </EntidadDesarrolladora>
      <Nombre>___ignore___</Nombre>
      <Version>___ignore___</Version>
    </Software>
    <NumSerieDispositivo>___ignore___</NumSerieDispositivo>
  </HuellaTBAI>
</T:TicketBai>
""".encode("utf-8")
>>>>>>> 01fe708471c96711f161cf220d98a71ee0802602

<<<<<<< 98ef54a1bb7a2c3085b7802efdb88a55a83622b6
    @classmethod
    def _get_invoice_send_wizard(cls, invoice):
        out_invoice_send_wizard = cls.env['account.move.send.wizard']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({'sending_methods': []})
        return out_invoice_send_wizard
||||||| 51027e84e269f9c5d96b56d64488e1deb2f66c02
    L10N_ES_TBAI_SAMPLE_XML_CANCEL = """<T:AnulaTicketBai xmlns:T="urn:ticketbai:anulacion">
  <Cabecera>
    <IDVersionTBAI>1.2</IDVersionTBAI>
  </Cabecera>
  <IDFactura>
    <Emisor>
      <NIF>09760433S</NIF>
      <ApellidosNombreRazonSocial>EUS Company</ApellidosNombreRazonSocial>
    </Emisor>
    <CabeceraFactura>
      <SerieFactura>INVTEST</SerieFactura>
      <NumFactura>01</NumFactura>
      <FechaExpedicionFactura>01-01-2022</FechaExpedicionFactura>
    </CabeceraFactura>
  </IDFactura>
  <HuellaTBAI>
    <Software>
      <LicenciaTBAI>___ignore___</LicenciaTBAI>
      <EntidadDesarrolladora>
        <NIF>___ignore___</NIF>
      </EntidadDesarrolladora>
      <Nombre>___ignore___</Nombre>
      <Version>___ignore___</Version>
    </Software>
    <NumSerieDispositivo>___ignore___</NumSerieDispositivo>
  </HuellaTBAI>
</T:AnulaTicketBai>""".encode("utf-8")
=======
    L10N_ES_TBAI_SAMPLE_XML_CANCEL = """<T:AnulaTicketBai xmlns:T="urn:ticketbai:anulacion">
  <Cabecera>
    <IDVersionTBAI>1.2</IDVersionTBAI>
  </Cabecera>
  <IDFactura>
    <Emisor>
      <NIF>09760433S</NIF>
      <ApellidosNombreRazonSocial>EUS Company</ApellidosNombreRazonSocial>
    </Emisor>
    <CabeceraFactura>
      <SerieFactura>INVTEST</SerieFactura>
      <NumFactura>01</NumFactura>
      <FechaExpedicionFactura>01-01-2025</FechaExpedicionFactura>
    </CabeceraFactura>
  </IDFactura>
  <HuellaTBAI>
    <Software>
      <LicenciaTBAI>___ignore___</LicenciaTBAI>
      <EntidadDesarrolladora>
        <NIF>___ignore___</NIF>
      </EntidadDesarrolladora>
      <Nombre>___ignore___</Nombre>
      <Version>___ignore___</Version>
    </Software>
    <NumSerieDispositivo>___ignore___</NumSerieDispositivo>
  </HuellaTBAI>
</T:AnulaTicketBai>""".encode("utf-8")
>>>>>>> 01fe708471c96711f161cf220d98a71ee0802602

<<<<<<< 98ef54a1bb7a2c3085b7802efdb88a55a83622b6
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
||||||| 51027e84e269f9c5d96b56d64488e1deb2f66c02
    L10N_ES_TBAI_SAMPLE_XML_POST_IN = """
<lrpjframp:LROEPJ240FacturasRecibidasAltaModifPeticion xmlns:lrpjframp="https://www.batuz.eus/fitxategiak/batuz/LROE/esquemas/LROE_PJ_240_2_FacturasRecibidas_AltaModifPeticion_V1_0_1.xsd">
    <Cabecera>
        <Modelo>240</Modelo>
        <Capitulo>2</Capitulo>
        <Operacion>A00</Operacion>
        <Version>1.0</Version>
        <Ejercicio>2022</Ejercicio>
        <ObligadoTributario>
            <NIF>09760433S</NIF>
            <ApellidosNombreRazonSocial>EUS Company</ApellidosNombreRazonSocial>
        </ObligadoTributario>
    </Cabecera>
    <FacturasRecibidas>
        <FacturaRecibida>
                <EmisorFacturaRecibida>
                    <IDOtro>
                        <IDType>02</IDType>
                        <ID>BE0477472701</ID>
                    </IDOtro>
                    <ApellidosNombreRazonSocial>&amp;@àÁ$£€èêÈÊöÔÇç¡⅛™³</ApellidosNombreRazonSocial>
                </EmisorFacturaRecibida>
                <CabeceraFactura>
                    <SerieFactura>TEST</SerieFactura>
                    <NumFactura>INV/5234</NumFactura>
                    <FechaExpedicionFactura>01-01-2022</FechaExpedicionFactura>
                    <FechaRecepcion>01-01-2022</FechaRecepcion>
                    <TipoFactura>F1</TipoFactura>
                </CabeceraFactura>
                <DatosFactura>
                    <DescripcionOperacion>INV/5234</DescripcionOperacion>
                    <Claves>
                        <IDClave>
                            <ClaveRegimenIvaOpTrascendencia>01</ClaveRegimenIvaOpTrascendencia>
                        </IDClave>
                    </Claves>
                    <ImporteTotalFactura>4840.00</ImporteTotalFactura>
                </DatosFactura>
                <IVA>
                    <DetalleIVA>
                        <CompraBienesCorrientesGastosBienesInversion>C</CompraBienesCorrientesGastosBienesInversion>
                        <InversionSujetoPasivo>N</InversionSujetoPasivo>
                        <BaseImponible>4000.00</BaseImponible>
                        <TipoImpositivo>21.0</TipoImpositivo>
                        <CuotaIVASoportada>840.00</CuotaIVASoportada>
                        <CuotaIVADeducible>840.00</CuotaIVADeducible>
                    </DetalleIVA>
                </IVA>
        </FacturaRecibida>
    </FacturasRecibidas>
</lrpjframp:LROEPJ240FacturasRecibidasAltaModifPeticion>"""
=======
    L10N_ES_TBAI_SAMPLE_XML_POST_IN = """
<lrpjframp:LROEPJ240FacturasRecibidasAltaModifPeticion xmlns:lrpjframp="https://www.batuz.eus/fitxategiak/batuz/LROE/esquemas/LROE_PJ_240_2_FacturasRecibidas_AltaModifPeticion_V1_0_1.xsd">
    <Cabecera>
        <Modelo>240</Modelo>
        <Capitulo>2</Capitulo>
        <Operacion>A00</Operacion>
        <Version>1.0</Version>
        <Ejercicio>2025</Ejercicio>
        <ObligadoTributario>
            <NIF>09760433S</NIF>
            <ApellidosNombreRazonSocial>EUS Company</ApellidosNombreRazonSocial>
        </ObligadoTributario>
    </Cabecera>
    <FacturasRecibidas>
        <FacturaRecibida>
                <EmisorFacturaRecibida>
                    <IDOtro>
                        <IDType>02</IDType>
                        <ID>BE0477472701</ID>
                    </IDOtro>
                    <ApellidosNombreRazonSocial>&amp;@àÁ$£€èêÈÊöÔÇç¡⅛™³</ApellidosNombreRazonSocial>
                </EmisorFacturaRecibida>
                <CabeceraFactura>
                    <SerieFactura>TEST</SerieFactura>
                    <NumFactura>INV/5234</NumFactura>
                    <FechaExpedicionFactura>01-01-2025</FechaExpedicionFactura>
                    <FechaRecepcion>01-01-2025</FechaRecepcion>
                    <TipoFactura>F1</TipoFactura>
                </CabeceraFactura>
                <DatosFactura>
                    <DescripcionOperacion>INV/5234</DescripcionOperacion>
                    <Claves>
                        <IDClave>
                            <ClaveRegimenIvaOpTrascendencia>01</ClaveRegimenIvaOpTrascendencia>
                        </IDClave>
                    </Claves>
                    <ImporteTotalFactura>4840.00</ImporteTotalFactura>
                </DatosFactura>
                <IVA>
                    <DetalleIVA>
                        <CompraBienesCorrientesGastosBienesInversion>C</CompraBienesCorrientesGastosBienesInversion>
                        <InversionSujetoPasivo>N</InversionSujetoPasivo>
                        <BaseImponible>4000.00</BaseImponible>
                        <TipoImpositivo>21.0</TipoImpositivo>
                        <CuotaIVASoportada>840.00</CuotaIVASoportada>
                        <CuotaIVADeducible>840.00</CuotaIVADeducible>
                    </DetalleIVA>
                </IVA>
        </FacturaRecibida>
    </FacturasRecibidas>
</lrpjframp:LROEPJ240FacturasRecibidasAltaModifPeticion>"""
>>>>>>> 01fe708471c96711f161cf220d98a71ee0802602

<<<<<<< 98ef54a1bb7a2c3085b7802efdb88a55a83622b6
    @classmethod
    def _get_sample_xml(cls, filename):
        with file_open(f'l10n_es_edi_tbai/tests/document_xmls/{filename}', 'rb') as file:
            content = file.read()
        return content
||||||| 51027e84e269f9c5d96b56d64488e1deb2f66c02
    L10N_ES_TBAI_SAMPLE_XML_POST_IN_ND = """
<lrpjframp:LROEPJ240FacturasRecibidasAltaModifPeticion xmlns:lrpjframp="https://www.batuz.eus/fitxategiak/batuz/LROE/esquemas/LROE_PJ_240_2_FacturasRecibidas_AltaModifPeticion_V1_0_1.xsd">
    <Cabecera>
        <Modelo>240</Modelo>
        <Capitulo>2</Capitulo>
        <Operacion>A00</Operacion>
        <Version>1.0</Version>
        <Ejercicio>2022</Ejercicio>
        <ObligadoTributario>
            <NIF>09760433S</NIF>
            <ApellidosNombreRazonSocial>EUS Company</ApellidosNombreRazonSocial>
        </ObligadoTributario>
    </Cabecera>
    <FacturasRecibidas>
        <FacturaRecibida>
                <EmisorFacturaRecibida>
                    <IDOtro>
                        <IDType>02</IDType>
                        <ID>BE0477472701</ID>
                    </IDOtro>
                    <ApellidosNombreRazonSocial>&amp;@àÁ$£€èêÈÊöÔÇç¡⅛™³</ApellidosNombreRazonSocial>
                </EmisorFacturaRecibida>
                <CabeceraFactura>
                    <SerieFactura>TEST</SerieFactura>
                    <NumFactura>INV/5234</NumFactura>
                    <FechaExpedicionFactura>01-01-2022</FechaExpedicionFactura>
                    <FechaRecepcion>01-01-2022</FechaRecepcion>
                    <TipoFactura>F1</TipoFactura>
                </CabeceraFactura>
                <DatosFactura>
                    <DescripcionOperacion>INV/5234</DescripcionOperacion>
                    <Claves>
                        <IDClave>
                            <ClaveRegimenIvaOpTrascendencia>01</ClaveRegimenIvaOpTrascendencia>
                        </IDClave>
                    </Claves>
                    <ImporteTotalFactura>1100.00</ImporteTotalFactura>
                </DatosFactura>
                <IVA>
                    <DetalleIVA>
                        <CompraBienesCorrientesGastosBienesInversion>C</CompraBienesCorrientesGastosBienesInversion>
                        <InversionSujetoPasivo>N</InversionSujetoPasivo>
                        <BaseImponible>1000.00</BaseImponible>
                        <TipoImpositivo>10.0</TipoImpositivo>
                        <CuotaIVASoportada>100.00</CuotaIVASoportada>
                        <CuotaIVADeducible>0.00</CuotaIVADeducible>
                    </DetalleIVA>
                </IVA>
        </FacturaRecibida>
    </FacturasRecibidas>
</lrpjframp:LROEPJ240FacturasRecibidasAltaModifPeticion>"""
=======
    L10N_ES_TBAI_SAMPLE_XML_POST_IN_ND = """
<lrpjframp:LROEPJ240FacturasRecibidasAltaModifPeticion xmlns:lrpjframp="https://www.batuz.eus/fitxategiak/batuz/LROE/esquemas/LROE_PJ_240_2_FacturasRecibidas_AltaModifPeticion_V1_0_1.xsd">
    <Cabecera>
        <Modelo>240</Modelo>
        <Capitulo>2</Capitulo>
        <Operacion>A00</Operacion>
        <Version>1.0</Version>
        <Ejercicio>2025</Ejercicio>
        <ObligadoTributario>
            <NIF>09760433S</NIF>
            <ApellidosNombreRazonSocial>EUS Company</ApellidosNombreRazonSocial>
        </ObligadoTributario>
    </Cabecera>
    <FacturasRecibidas>
        <FacturaRecibida>
                <EmisorFacturaRecibida>
                    <IDOtro>
                        <IDType>02</IDType>
                        <ID>BE0477472701</ID>
                    </IDOtro>
                    <ApellidosNombreRazonSocial>&amp;@àÁ$£€èêÈÊöÔÇç¡⅛™³</ApellidosNombreRazonSocial>
                </EmisorFacturaRecibida>
                <CabeceraFactura>
                    <SerieFactura>TEST</SerieFactura>
                    <NumFactura>INV/5234</NumFactura>
                    <FechaExpedicionFactura>01-01-2025</FechaExpedicionFactura>
                    <FechaRecepcion>01-01-2025</FechaRecepcion>
                    <TipoFactura>F1</TipoFactura>
                </CabeceraFactura>
                <DatosFactura>
                    <DescripcionOperacion>INV/5234</DescripcionOperacion>
                    <Claves>
                        <IDClave>
                            <ClaveRegimenIvaOpTrascendencia>01</ClaveRegimenIvaOpTrascendencia>
                        </IDClave>
                    </Claves>
                    <ImporteTotalFactura>1100.00</ImporteTotalFactura>
                </DatosFactura>
                <IVA>
                    <DetalleIVA>
                        <CompraBienesCorrientesGastosBienesInversion>C</CompraBienesCorrientesGastosBienesInversion>
                        <InversionSujetoPasivo>N</InversionSujetoPasivo>
                        <BaseImponible>1000.00</BaseImponible>
                        <TipoImpositivo>10.0</TipoImpositivo>
                        <CuotaIVASoportada>100.00</CuotaIVASoportada>
                        <CuotaIVADeducible>0.00</CuotaIVADeducible>
                    </DetalleIVA>
                </IVA>
        </FacturaRecibida>
    </FacturasRecibidas>
</lrpjframp:LROEPJ240FacturasRecibidasAltaModifPeticion>"""
>>>>>>> 01fe708471c96711f161cf220d98a71ee0802602

<<<<<<< 98ef54a1bb7a2c3085b7802efdb88a55a83622b6
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
||||||| 51027e84e269f9c5d96b56d64488e1deb2f66c02
    L10N_ES_TBAI_SAMPLE_XML_POST_IN_IC = """
<lrpjframp:LROEPJ240FacturasRecibidasAltaModifPeticion xmlns:lrpjframp="https://www.batuz.eus/fitxategiak/batuz/LROE/esquemas/LROE_PJ_240_2_FacturasRecibidas_AltaModifPeticion_V1_0_1.xsd">
    <Cabecera>
        <Modelo>240</Modelo>
        <Capitulo>2</Capitulo>
        <Operacion>A00</Operacion>
        <Version>1.0</Version>
        <Ejercicio>2022</Ejercicio>
        <ObligadoTributario>
            <NIF>09760433S</NIF>
            <ApellidosNombreRazonSocial>EUS Company</ApellidosNombreRazonSocial>
        </ObligadoTributario>
    </Cabecera>
    <FacturasRecibidas>
        <FacturaRecibida>
                <EmisorFacturaRecibida>
                    <NIF>F35999705</NIF>
                    <ApellidosNombreRazonSocial>partner_b</ApellidosNombreRazonSocial>
                </EmisorFacturaRecibida>
                <CabeceraFactura>
                    <SerieFactura>TEST</SerieFactura>
                    <NumFactura>INV/5234</NumFactura>
                    <FechaExpedicionFactura>01-01-2022</FechaExpedicionFactura>
                    <FechaRecepcion>01-01-2022</FechaRecepcion>
                    <TipoFactura>F1</TipoFactura>
                </CabeceraFactura>
                <DatosFactura>
                    <DescripcionOperacion>INV/5234</DescripcionOperacion>
                    <Claves>
                        <IDClave>
                            <ClaveRegimenIvaOpTrascendencia>09</ClaveRegimenIvaOpTrascendencia>
                        </IDClave>
                    </Claves>
                    <ImporteTotalFactura>12000.00</ImporteTotalFactura>
                </DatosFactura>
                <IVA>
                    <DetalleIVA>
                        <CompraBienesCorrientesGastosBienesInversion>C</CompraBienesCorrientesGastosBienesInversion>
                        <InversionSujetoPasivo>N</InversionSujetoPasivo>
                        <BaseImponible>4000.00</BaseImponible>
                        <TipoImpositivo>21.0</TipoImpositivo>
                        <CuotaIVASoportada>840.00</CuotaIVASoportada>
                        <CuotaIVADeducible>840.00</CuotaIVADeducible>
                    </DetalleIVA><DetalleIVA>
                        <CompraBienesCorrientesGastosBienesInversion>G</CompraBienesCorrientesGastosBienesInversion>
                        <InversionSujetoPasivo>N</InversionSujetoPasivo>
                        <BaseImponible>8000.00</BaseImponible>
                        <TipoImpositivo>21.0</TipoImpositivo>
                        <CuotaIVASoportada>1680.00</CuotaIVASoportada>
                        <CuotaIVADeducible>1680.00</CuotaIVADeducible>
                    </DetalleIVA>
                </IVA>
            </FacturaRecibida>
        </FacturasRecibidas>
    </lrpjframp:LROEPJ240FacturasRecibidasAltaModifPeticion>
    """
=======
    L10N_ES_TBAI_SAMPLE_XML_POST_IN_IC = """
<lrpjframp:LROEPJ240FacturasRecibidasAltaModifPeticion xmlns:lrpjframp="https://www.batuz.eus/fitxategiak/batuz/LROE/esquemas/LROE_PJ_240_2_FacturasRecibidas_AltaModifPeticion_V1_0_1.xsd">
    <Cabecera>
        <Modelo>240</Modelo>
        <Capitulo>2</Capitulo>
        <Operacion>A00</Operacion>
        <Version>1.0</Version>
        <Ejercicio>2025</Ejercicio>
        <ObligadoTributario>
            <NIF>09760433S</NIF>
            <ApellidosNombreRazonSocial>EUS Company</ApellidosNombreRazonSocial>
        </ObligadoTributario>
    </Cabecera>
    <FacturasRecibidas>
        <FacturaRecibida>
                <EmisorFacturaRecibida>
                    <NIF>F35999705</NIF>
                    <ApellidosNombreRazonSocial>partner_b</ApellidosNombreRazonSocial>
                </EmisorFacturaRecibida>
                <CabeceraFactura>
                    <SerieFactura>TEST</SerieFactura>
                    <NumFactura>INV/5234</NumFactura>
                    <FechaExpedicionFactura>01-01-2025</FechaExpedicionFactura>
                    <FechaRecepcion>01-01-2025</FechaRecepcion>
                    <TipoFactura>F1</TipoFactura>
                </CabeceraFactura>
                <DatosFactura>
                    <DescripcionOperacion>INV/5234</DescripcionOperacion>
                    <Claves>
                        <IDClave>
                            <ClaveRegimenIvaOpTrascendencia>09</ClaveRegimenIvaOpTrascendencia>
                        </IDClave>
                    </Claves>
                    <ImporteTotalFactura>12000.00</ImporteTotalFactura>
                </DatosFactura>
                <IVA>
                    <DetalleIVA>
                        <CompraBienesCorrientesGastosBienesInversion>C</CompraBienesCorrientesGastosBienesInversion>
                        <InversionSujetoPasivo>N</InversionSujetoPasivo>
                        <BaseImponible>4000.00</BaseImponible>
                        <TipoImpositivo>21.0</TipoImpositivo>
                        <CuotaIVASoportada>840.00</CuotaIVASoportada>
                        <CuotaIVADeducible>840.00</CuotaIVADeducible>
                    </DetalleIVA><DetalleIVA>
                        <CompraBienesCorrientesGastosBienesInversion>G</CompraBienesCorrientesGastosBienesInversion>
                        <InversionSujetoPasivo>N</InversionSujetoPasivo>
                        <BaseImponible>8000.00</BaseImponible>
                        <TipoImpositivo>21.0</TipoImpositivo>
                        <CuotaIVASoportada>1680.00</CuotaIVASoportada>
                        <CuotaIVADeducible>1680.00</CuotaIVADeducible>
                    </DetalleIVA>
                </IVA>
            </FacturaRecibida>
        </FacturasRecibidas>
    </lrpjframp:LROEPJ240FacturasRecibidasAltaModifPeticion>
    """
>>>>>>> 01fe708471c96711f161cf220d98a71ee0802602
