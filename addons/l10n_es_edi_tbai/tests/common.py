# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from datetime import datetime

from odoo.addons.account_edi.tests.common import AccountEdiTestCommon
from odoo.tools import misc
from pytz import timezone


class TestEsEdiTbaiCommon(AccountEdiTestCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='es_full', edi_format_ref='l10n_es_edi_tbai.edi_es_tbai'):
        super().setUpClass(chart_template_ref=chart_template_ref, edi_format_ref=edi_format_ref)

        cls.frozen_today = datetime(year=2022, month=1, day=1, hour=0, minute=0, second=0, tzinfo=timezone('utc'))

        # Allow to see the full result of AssertionError.
        cls.maxDiff = None

        # ==== Config ====

        cls.company_data['company'].write({
            'name': 'EUS Company',
            'country_id': cls.env.ref('base.es').id,
            'state_id': cls.env.ref('base.state_es_ss').id,
            'vat': 'ES09760433S',
            'l10n_es_edi_test_env': True,
        })

        cls.certificate = None
        cls._set_tax_agency('gipuzkoa')

        # ==== Business ====

        cls.partner_a.write({
            'name': "&@àÁ$£€èêÈÊöÔÇç¡⅛™³",  # special characters should be escaped appropriately
            'vat': 'BE0477472701',
            'country_id': cls.env.ref('base.be').id,
            'street': 'Rue Sans Souci 1',
            'zip': 93071,
        })

        cls.partner_b.write({
            'vat': 'ESF35999705',
        })

        cls.product_t = cls.env["product.product"].create(
            {"name": "Test product"})
        cls.partner_t = cls.env["res.partner"].create({"name": "Test partner", "vat": "ESF35999705"})

    @classmethod
    def _set_tax_agency(cls, agency):
        if agency == "araba":
            cert_name = 'araba_1234.p12'
            cert_password = '1234'
        elif agency == 'bizkaia':
            cert_name = 'bizkaia_111111.p12'
            cert_password = '111111'
        elif agency == 'gipuzkoa':
            cert_name = 'gipuzkoa_IZDesa2021.p12'
            cert_password = 'IZDesa2021'
        else:
            raise ValueError("Unknown tax agency: " + agency)

        cls.certificate = cls.env['l10n_es_edi.certificate'].create({
            'content': base64.encodebytes(
                misc.file_open("l10n_es_edi_tbai/demo/certificates/" + cert_name, 'rb').read()),
            'password': cert_password,
        })
        cls.company_data['company'].write({
            'l10n_es_tbai_tax_agency': agency,
            'l10n_es_edi_certificate_id': cls.certificate.id,
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
            'invoice_date': '2022-01-01',
            'date': '2022-01-01',
            **kwargs,
            'invoice_line_ids': [(0, 0, {
                'product_id': cls.product_a.id,
                'price_unit': 1000.0,
                **line_vals,
            }) for line_vals in kwargs.get('invoice_line_ids', [])],
        })

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
                    <SerieFactura>INVTEST</SerieFactura>
                    <NumFactura>01</NumFactura>
                    <FechaExpedicionFactura>01-01-2022</FechaExpedicionFactura>
                    <FechaRecepcion>01-01-2022</FechaRecepcion>
                    <TipoFactura>F1</TipoFactura>
                </CabeceraFactura>
                <DatosFactura>
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
                        <BaseImponible>4000.0</BaseImponible>
                        <TipoImpositivo>21.0</TipoImpositivo>
                        <CuotaIVASoportada>840.0</CuotaIVASoportada>
                        <CuotaIVADeducible>840.0</CuotaIVADeducible>
                    </DetalleIVA>
                </IVA>
        </FacturaRecibida>
    </FacturasRecibidas>
</lrpjframp:LROEPJ240FacturasRecibidasAltaModifPeticion>"""


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
                    <SerieFactura>INVTEST</SerieFactura>
                    <NumFactura>01</NumFactura>
                    <FechaExpedicionFactura>01-01-2022</FechaExpedicionFactura>
                    <FechaRecepcion>01-01-2022</FechaRecepcion>
                    <TipoFactura>F1</TipoFactura>
                </CabeceraFactura>
                <DatosFactura>
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
                        <BaseImponible>4000.0</BaseImponible>
                        <TipoImpositivo>21.0</TipoImpositivo>
                        <CuotaIVASoportada>840.0</CuotaIVASoportada>
                        <CuotaIVADeducible>840.0</CuotaIVADeducible>
                    </DetalleIVA><DetalleIVA>
                        <CompraBienesCorrientesGastosBienesInversion>G</CompraBienesCorrientesGastosBienesInversion>
                        <InversionSujetoPasivo>N</InversionSujetoPasivo>
                        <BaseImponible>8000.0</BaseImponible>
                        <TipoImpositivo>21.0</TipoImpositivo>
                        <CuotaIVASoportada>1680.0</CuotaIVASoportada>
                        <CuotaIVADeducible>1680.0</CuotaIVADeducible>
                    </DetalleIVA>
                </IVA>
            </FacturaRecibida>
        </FacturasRecibidas>
    </lrpjframp:LROEPJ240FacturasRecibidasAltaModifPeticion>
    """