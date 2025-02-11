# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

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

    def test_xml_tree_post(self):
        """Test of Customer Invoice XML"""
        with freeze_time(self.frozen_today):
            edi_document = self.out_invoice._l10n_es_tbai_create_edi_document(cancel=False)
            edi_document._generate_xml(self.out_invoice._l10n_es_tbai_get_values(cancel=False))
            xml_doc = edi_document._get_xml()
            xml_doc.remove(xml_doc.find("Signature", namespaces=NS_MAP))
            xml_expected = etree.fromstring(super()._get_sample_xml('xml_post.xml'))
            self.assertXmlTreeEqual(xml_doc, xml_expected)

    def test_xml_tree_post_generic_sequence(self):
        """Test TBAI on moves whose sequence does not contain a '/'"""
        with freeze_time(self.frozen_today):
            invoice = self.out_invoice.copy({
                'name': 'INV01',
                'invoice_date': date(2022, 1, 1),
            })
            edi_document = invoice._l10n_es_tbai_create_edi_document(cancel=False)
            edi_document._generate_xml(invoice._l10n_es_tbai_get_values(cancel=False))
            xml_doc = edi_document._get_xml()
            xml_doc.remove(xml_doc.find("Signature", namespaces=NS_MAP))
            xml_expected = etree.fromstring(super()._get_sample_xml('xml_post.xml'))
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
            edi_document = invoice._l10n_es_tbai_create_edi_document(cancel=False)
            edi_document._generate_xml(invoice._l10n_es_tbai_get_values(cancel=False))
            xml_doc = edi_document._get_xml()
            xml_doc.remove(xml_doc.find("Signature", namespaces=NS_MAP))
            xml_expected_base = etree.fromstring(super()._get_sample_xml('xml_post.xml'))
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

    def test_xml_tree_post_retention(self):
        self.out_invoice.invoice_line_ids.tax_ids = [(4, self._get_tax_by_xml_id('s_irpf15').id)]
        with freeze_time(self.frozen_today):
            edi_document = self.out_invoice._l10n_es_tbai_create_edi_document(cancel=False)
            edi_document._generate_xml(self.out_invoice._l10n_es_tbai_get_values(cancel=False))
            xml_doc = edi_document._get_xml()
            xml_doc.remove(xml_doc.find("Signature", namespaces=NS_MAP))
            xml_expected_base = etree.fromstring(super()._get_sample_xml('xml_post.xml'))
            xpath = """
                <xpath expr="//ImporteTotalFactura" position="after">
                    <RetencionSoportada>600.00</RetencionSoportada>
                </xpath>
            """
            xml_expected = self.with_applied_xpath(xml_expected_base, xpath)
            self.assertXmlTreeEqual(xml_doc, xml_expected)

    def test_xml_tree_post_multitax(self):
        self.out_invoice.invoice_line_ids.tax_ids = [self._get_tax_by_xml_id('s_req52').id, self._get_tax_by_xml_id('s_iva21b').id]
        with freeze_time(self.frozen_today):
            edi_document = self.out_invoice._l10n_es_tbai_create_edi_document(cancel=False)
            edi_document._generate_xml(self.out_invoice._l10n_es_tbai_get_values(cancel=False))
            xml_doc = edi_document._get_xml()
            xml_doc.remove(xml_doc.find("Signature", namespaces=NS_MAP))
            xml_expected_base = etree.fromstring(super()._get_sample_xml('xml_post.xml'))
            xpath = """
                <xpath expr="//ImporteTotal" position="replace">
                    <ImporteTotal>5048.00000000</ImporteTotal>
                </xpath>
                <xpath expr="//ImporteTotalFactura" position="replace">
                    <ImporteTotalFactura>5048.00</ImporteTotalFactura>
                </xpath>
            """
            xml_expected = self.with_applied_xpath(xml_expected_base, xpath)
            self.assertXmlTreeEqual(xml_doc, xml_expected)

    def test_xml_tree_in_post(self):
        """Test XML of vendor bill for LROE Batuz"""
        self.company_data['company'].l10n_es_tbai_tax_agency = 'bizkaia'

        with freeze_time(self.frozen_today):
            self.in_invoice = self.env['account.move'].create({
                'name': 'INV/01',
                'move_type': 'in_invoice',
                'ref': 'INV/5234',
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
            edi_document = self.in_invoice._l10n_es_tbai_create_edi_document(cancel=False)
            edi_document._generate_xml(self.in_invoice._l10n_es_tbai_get_values(cancel=False))
            xml_doc = edi_document._get_xml()
            xml_expected = etree.fromstring(super()._get_sample_xml('xml_post_in.xml'))
            self.assertXmlTreeEqual(xml_doc, xml_expected)

    def test_xml_tree_in_140_post(self):
        """Test XML of vendor bill for LROE Batuz autonomos (modelo 140)"""
        self.company_data['company'].l10n_es_tbai_tax_agency = 'bizkaia'
        self.company_data['company'].vat = '09760433S'
        self.env['ir.config_parameter'].sudo().set_param('l10n_es_edi_tbai.epigrafe', '102100')

        with freeze_time(self.frozen_today):
            self.in_invoice = self.env['account.move'].create({
                'name': 'INV/01',
                'ref': 'INV/5234',
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
            edi_document = self.in_invoice._l10n_es_tbai_create_edi_document(cancel=False)
            edi_document._generate_xml(self.in_invoice._l10n_es_tbai_get_values(cancel=False))
            xml_doc = edi_document._get_xml()
            xml_expected = etree.fromstring(super()._get_sample_xml('xml_post_in_140.xml'))
            self.assertXmlTreeEqual(xml_doc, xml_expected)

    def test_xml_tree_in_ic_post(self):
        """Test XML of vendor bill for LROE Batuz intra-community"""
        self.company_data['company'].l10n_es_tbai_tax_agency = 'bizkaia'

        with freeze_time(self.frozen_today):
            self.in_invoice = self.env['account.move'].create({
                'name': 'INV/01',
                'move_type': 'in_invoice',
                'ref': 'INV/5234',
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
            edi_document = self.in_invoice._l10n_es_tbai_create_edi_document(cancel=False)
            edi_document._generate_xml(self.in_invoice._l10n_es_tbai_get_values(cancel=False))
            xml_doc = edi_document._get_xml()
            xml_expected = etree.fromstring(super()._get_sample_xml('xml_post_in_ic.xml'))
            self.assertXmlTreeEqual(xml_doc, xml_expected)

    def test_xml_tree_cancel(self):
        post_xml = b"""<TicketBAI>
<CabeceraFactura><FechaExpedicionFactura>01-01-2022</FechaExpedicionFactura></CabeceraFactura>
<ds:SignatureValue xmlns:ds="http://www.w3.org/2000/09/xmldsig#">TEXT</ds:SignatureValue>
</TicketBAI>"""  # hack to set out_invoice's registration date
        post_edi_document = self.out_invoice._l10n_es_tbai_create_edi_document()
        post_xml_attachment = self.env['ir.attachment'].create({
            'name': self.out_invoice._l10n_es_tbai_get_attachment_name(cancel=True),
            'raw': post_xml,
            'type': 'binary',
            'res_model': 'account.move',
            'res_id': self.out_invoice.id,
            'res_field': 'xml_attachment_id',
        })
        post_edi_document.xml_attachment_id = post_xml_attachment
        self.out_invoice.l10n_es_tbai_post_document_id = post_edi_document
        cancel_edi_document = self.out_invoice._l10n_es_tbai_create_edi_document(cancel=True)
        cancel_edi_document._generate_xml(self.out_invoice._l10n_es_tbai_get_values(cancel=True))
        xml_doc = cancel_edi_document._get_xml()
        xml_doc.remove(xml_doc.find("Signature", namespaces=NS_MAP))
        xml_expected = etree.fromstring(super()._get_sample_xml('xml_cancel.xml'))
        self.assertXmlTreeEqual(xml_doc, xml_expected)
