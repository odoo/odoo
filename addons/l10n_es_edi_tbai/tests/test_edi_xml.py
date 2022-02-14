# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time
from lxml import etree
from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import TestEsEdiTbaiCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestEdiXmls(TestEsEdiTbaiCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['ir.attachment']._l10n_es_tbai_load_xsd_attachments()  # Gov. XSD download

        cls.out_invoice = cls.env['account.move'].create({
            'name': 'INV/01',
            'move_type': 'out_invoice',
            'partner_id': cls.partner_a.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': cls.product_a.id,
                'price_unit': 1000.0,
                'quantity': 5,
                'discount': 20.0,
                'tax_ids': [(6, 0, cls._get_tax_by_xml_id('s_iva21b').ids)],
            })],
        })

        cls.edi_format = cls.env['account.edi.format'].search([
            ('code', '=', 'es_tbai')
        ])

    def test_format_post(self):
        xml_doc = self.edi_format._l10n_es_tbai_get_invoice_xml(self.out_invoice, cancel=False)

        # TODO validate for all tax agencies
        self._validate_format_xsd(
            xml_doc,
            f'l10n_es_edi_tbai.{self.env.company.l10n_es_tbai_tax_agency}_ticketBaiV1-2.xsd'
        )

    def test_format_cancel(self):
        self.out_invoice.l10n_es_tbai_registration_date = self.frozen_today  # currently values comes from attachment_edi (None here)

        xml_doc = self.edi_format._l10n_es_tbai_get_invoice_xml(self.out_invoice, cancel=True)

        # TODO validate for all tax agencies
        self._validate_format_xsd(
            xml_doc,
            f'l10n_es_edi_tbai.{self.env.company.l10n_es_tbai_tax_agency}_Anula_ticketBaiV1-2.xsd'
        )

    def _validate_format_xsd(self, xml_doc, xsd_name):
        xml_bytes = etree.tostring(xml_doc, encoding="UTF-8")
        try:
            self.env['l10n_es.edi.tbai.util']._validate_format_xsd(xml_bytes, xsd_name)
        except UserError as e:
            self.fail(str(e))

    def test_xml_tree_post(self):
        with freeze_time(self.frozen_today):
            xml_doc = self.edi_format._l10n_es_tbai_get_invoice_xml(self.out_invoice, cancel=False)
            xml_expected = etree.fromstring("""<?xml version='1.0' encoding='UTF-8'?>
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
    <EmitidaPorTercerosODestinatario>D</EmitidaPorTercerosODestinatario>
  </Sujetos>
  <Factura>
    <CabeceraFactura>
      <SerieFactura>INVTEST</SerieFactura>
      <NumFactura>01</NumFactura>
      <FechaExpedicionFactura>01-01-2022</FechaExpedicionFactura>
      <HoraExpedicionFactura>___ignore___</HoraExpedicionFactura>
    </CabeceraFactura>
    <DatosFactura>
      <DescripcionFactura>manual</DescripcionFactura>
      <DetallesFactura>
        <IDDetalleFactura>
          <DescripcionDetalle>producta</DescripcionDetalle>
          <Cantidad>5.00</Cantidad>
          <ImporteUnitario>1000.00</ImporteUnitario>
          <Descuento>20.00</Descuento>
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
  <ds:Signature Id="___ignore___">
    <ds:SignedInfo>
      <ds:CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>
      <ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>
      <ds:Reference URI="">
        <ds:Transforms>
          <ds:Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/>
        </ds:Transforms>
        <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
        <ds:DigestValue>___ignore___</ds:DigestValue>
      </ds:Reference>
      <ds:Reference URI="___ignore___">
        <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
        <ds:DigestValue>___ignore___</ds:DigestValue>
      </ds:Reference>
      <ds:Reference URI="___ignore___">
        <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
        <ds:DigestValue>___ignore___</ds:DigestValue>
      </ds:Reference>
    </ds:SignedInfo>
    <ds:SignatureValue>___ignore___</ds:SignatureValue>
    <ds:KeyInfo Id="___ignore___">
      <ds:X509Data>
        <ds:X509Certificate>___ignore___</ds:X509Certificate>
      </ds:X509Data>
      <ds:KeyValue>
        <ds:RSAKeyValue>
          <ds:Modulus>___ignore___</ds:Modulus>
          <ds:Exponent>AQAB</ds:Exponent>
        </ds:RSAKeyValue>
      </ds:KeyValue>
    </ds:KeyInfo>
    <ds:Object>
      <etsi:QualifyingProperties Target="___ignore___">
        <etsi:SignedProperties Id="___ignore___">
          <etsi:SignedSignatureProperties>
            <etsi:SigningTime>___ignore___</etsi:SigningTime>
            <etsi:SigningCertificateV2>
              <etsi:Cert>
                <etsi:CertDigest>
                  <ds:DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha256"/>
                  <ds:DigestValue>___ignore___</ds:DigestValue>
                </etsi:CertDigest>
              </etsi:Cert>
            </etsi:SigningCertificateV2>
            <etsi:SignaturePolicyIdentifier>
              <etsi:SignaturePolicyId>
                <etsi:SigPolicyId>
                  <etsi:Identifier>https://www.gipuzkoa.eus/TicketBAI/signature</etsi:Identifier>
                  <etsi:Description>Pol&#237;tica de Firma TicketBAI 1.0</etsi:Description>
                </etsi:SigPolicyId>
                <etsi:SigPolicyHash>
                  <ds:DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha256"/>
                  <ds:DigestValue>___ignore___</ds:DigestValue>
                </etsi:SigPolicyHash>
              </etsi:SignaturePolicyId>
            </etsi:SignaturePolicyIdentifier>
          </etsi:SignedSignatureProperties>
        </etsi:SignedProperties>
      </etsi:QualifyingProperties>
    </ds:Object>
  </ds:Signature>
</T:TicketBai>
""".encode("utf-8"))
            self.assertXmlTreeEqual(xml_doc, xml_expected)
