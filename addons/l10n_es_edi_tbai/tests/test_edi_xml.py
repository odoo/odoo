# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from base64 import b64encode
from datetime import datetime, date

from freezegun import freeze_time
from lxml import etree

from odoo.addons.l10n_es_edi_tbai.models.xml_utils import NS_MAP
from odoo.tests import tagged

from .common import TestEsEdiTbaiCommon


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestEdiTbaiXmls(TestEsEdiTbaiCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.out_invoice = cls.env['account.move'].create({
            'name': 'INV/01',
            'move_type': 'out_invoice',
            'invoice_date': date(2022, 1, 1),
            'partner_id': cls.partner_a.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': cls.product_a.id,
                'price_unit': 1000.0,
                'quantity': 5,
                'discount': 20.0,
                'tax_ids': [(6, 0, cls._get_tax_by_xml_id('s_iva21b').ids)],
            })],
        })
        cls.edi_format = cls.env.ref('l10n_es_edi_tbai.edi_es_tbai')

    def test_xml_tree_post(self):
        """Test of Customer Invoice XML"""
        with freeze_time(self.frozen_today):
            xml_doc = self.edi_format._get_l10n_es_tbai_invoice_xml(self.out_invoice, cancel=False)[self.out_invoice]['xml_file']
            xml_doc.remove(xml_doc.find("Signature", namespaces=NS_MAP))
            xml_expected = etree.fromstring(super().L10N_ES_TBAI_SAMPLE_XML_POST)
            self.assertXmlTreeEqual(xml_doc, xml_expected)

    def test_xml_tree_post_multicurrency(self):
        """Test of Customer Invoice XML. The invoice is not in company currency and has a line with a 100% discount"""

        currency_usd = self.env.ref('base.USD')
        currency_usd.active = True
        date = str(self.out_invoice.invoice_date)
        self.env['res.currency.rate'].create({
            'name': date,
            'company_id': self.company_data['company'].id,
            'currency_id': currency_usd.id,
            'rate': 0.5})
        invoice = self.env['account.move'].create({
            'name': 'INV/01',
            'move_type': 'out_invoice',
            'invoice_date': date,
            'partner_id': self.partner_a.id,
            'currency_id': currency_usd.id,
            'invoice_line_ids': [
                (0, 0, {
                    'product_id': self.product_a.id,
                    'price_unit': 123.00,
                    'quantity': 5,
                    'discount': 20.0,
                    'tax_ids': [(6, 0, self._get_tax_by_xml_id('s_iva21b').ids)],
                }),
                (0, 0, {
                    'product_id': self.product_a.id,
                    'price_unit': 123.00,
                    'quantity': 5,
                    'discount': 100.0,
                    'tax_ids': [(6, 0, self._get_tax_by_xml_id('s_iva21b').ids)],
                }),
            ],
        })

        with freeze_time(self.frozen_today):
            xml_doc = self.edi_format._get_l10n_es_tbai_invoice_xml(invoice, cancel=False)[invoice]['xml_file']
            xml_doc.remove(xml_doc.find("Signature", namespaces=NS_MAP))
            xml_expected_base = etree.fromstring(super().L10N_ES_TBAI_SAMPLE_XML_POST)
            xpath = """
                <xpath expr="//DetallesFactura" position="replace">
                    <DetallesFactura>
                      <IDDetalleFactura>
                          <DescripcionDetalle>producta</DescripcionDetalle>
                          <Cantidad>5.00000000</Cantidad>
                          <ImporteUnitario>246.00000000</ImporteUnitario>
                          <Descuento>246.00000000</Descuento>
                          <ImporteTotal>1190.64000000</ImporteTotal>
                      </IDDetalleFactura>
                      <IDDetalleFactura>
                          <DescripcionDetalle>producta</DescripcionDetalle>
                          <Cantidad>5.00000000</Cantidad>
                          <ImporteUnitario>246.00000000</ImporteUnitario>
                          <Descuento>1230.00000000</Descuento>
                          <ImporteTotal>0.00000000</ImporteTotal>
                      </IDDetalleFactura>
                    </DetallesFactura>
                </xpath>
                <xpath expr="//ImporteTotalFactura" position="replace">
                    <ImporteTotalFactura>1190.64</ImporteTotalFactura>
                </xpath>
                <xpath expr="//DesgloseIVA" position="replace">
                    <DesgloseIVA>
                      <DetalleIVA>
                        <BaseImponible>984.00</BaseImponible>
                        <TipoImpositivo>21.00</TipoImpositivo>
                        <CuotaImpuesto>206.64</CuotaImpuesto>
                        <OperacionEnRecargoDeEquivalenciaORegimenSimplificado>N</OperacionEnRecargoDeEquivalenciaORegimenSimplificado>
                      </DetalleIVA>
                    </DesgloseIVA>
                </xpath>
            """
            xml_expected = self.with_applied_xpath(xml_expected_base, xpath)
            self.assertXmlTreeEqual(xml_doc, xml_expected)

    def test_xml_tree_in_post(self):
        """Test XML of vendor bill for LROE Batuz"""
        with freeze_time(self.frozen_today):
            self.in_invoice = self.env['account.move'].create({
                'name': 'INV/01',
                'move_type': 'in_invoice',
                'invoice_date': datetime.now(),
                'partner_id': self.partner_a.id,
                'invoice_line_ids': [(0, 0, {
                    'product_id': self.product_a.id,
                    'price_unit': 1000.0,
                    'quantity': 5,
                    'discount': 20.0,
                    'tax_ids': [(6, 0, self._get_tax_by_xml_id('p_iva21_bc').ids)],
                })],
            })
            xml_doc = etree.fromstring(self.edi_format._l10n_es_tbai_get_invoice_content_edi(self.in_invoice))
            xml_expected = etree.fromstring(super().L10N_ES_TBAI_SAMPLE_XML_POST_IN)
            self.assertXmlTreeEqual(xml_doc, xml_expected)

    def test_xml_tree_in_ic_post(self):
        """Test XML of vendor bill for LROE Batuz intra-community"""
        with freeze_time(self.frozen_today):
            self.in_invoice = self.env['account.move'].create({
                'name': 'INV/01',
                'move_type': 'in_invoice',
                'invoice_date': datetime.now(),
                'partner_id': self.partner_b.id,
                'invoice_line_ids': [(0, 0, {
                    'product_id': self.product_a.id,
                    'price_unit': 1000.0,
                    'quantity': 5,
                    'discount': 20.0,
                    'tax_ids': [(6, 0, self._get_tax_by_xml_id('p_iva21_ic_bc').ids)],
                }), (0, 0, {
                    'product_id': self.product_b.id,
                    'price_unit': 2000.0,
                    'quantity': 5,
                    'discount': 20.0,
                    'tax_ids': [(6, 0, self._get_tax_by_xml_id('p_iva21_sp_in').ids)],
                })],
            })
            xml_doc = etree.fromstring(self.edi_format._l10n_es_tbai_get_invoice_content_edi(self.in_invoice))
            xml_expected = etree.fromstring(super().L10N_ES_TBAI_SAMPLE_XML_POST_IN_IC)
            self.assertXmlTreeEqual(xml_doc, xml_expected)

    def test_xml_tree_cancel(self):
        self.out_invoice.l10n_es_tbai_post_xml = b64encode(b"""<TicketBAI>
<CabeceraFactura><FechaExpedicionFactura>01-01-2022</FechaExpedicionFactura></CabeceraFactura>
<ds:SignatureValue xmlns:ds="http://www.w3.org/2000/09/xmldsig#">TEXT</ds:SignatureValue>
</TicketBAI>""")  # hack to set out_invoice's registration date
        xml_doc = self.edi_format._get_l10n_es_tbai_invoice_xml(self.out_invoice, cancel=True)[self.out_invoice]['xml_file']
        xml_doc.remove(xml_doc.find("Signature", namespaces=NS_MAP))
        xml_expected = etree.fromstring(super().L10N_ES_TBAI_SAMPLE_XML_CANCEL)
        self.assertXmlTreeEqual(xml_doc, xml_expected)
