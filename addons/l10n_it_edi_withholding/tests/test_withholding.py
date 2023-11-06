# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from lxml import etree
from collections import namedtuple

from odoo import tools
from odoo.tests import tagged
from odoo.exceptions import ValidationError
from odoo.addons.l10n_it_edi.tests.common import TestItEdi


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestWithholdingAndPensionFundTaxes(TestItEdi):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.purchase_journal = cls.company_data_2['default_journal_purchase']

        def find_tax_by_ref(ref_name):
            return cls.env.ref(f'l10n_it_edi_withholding.{cls.company.id}_{ref_name}')

        cls.withholding_sale_tax = find_tax_by_ref('20vwc')
        cls.withholding_sale_tax_23 = find_tax_by_ref('23vwo')
        cls.pension_fund_sale_tax = find_tax_by_ref('4vcp')
        cls.enasarco_sale_tax = find_tax_by_ref('enasarcov')
        cls.withholding_purchase_tax_23 = find_tax_by_ref('23awo')
        cls.enasarco_purchase_tax = find_tax_by_ref('enasarcoa')

        cls.withholding_sale_line = {
            'name': 'withholding_line',
            'quantity': 1,
            'tax_ids': [(6, 0, [
                cls.withholding_sale_tax.id,
                cls.company.account_sale_tax_id.id,
            ])]
        }

        cls.pension_fund_sale_line = {
            'name': 'pension_fund_line',
            'quantity': 1,
            'tax_ids': [(6, 0, [
                cls.withholding_sale_tax.id,
                cls.pension_fund_sale_tax.id,
                cls.company.account_sale_tax_id.id,
            ])]
        }

        cls.enasarco_sale_line = {
            'name': 'enasarco_line',
            'quantity': 1,
            'tax_ids': [(6, 0, [
                cls.enasarco_sale_tax.id,
                cls.withholding_sale_tax_23.id,
                cls.company.account_sale_tax_id.id,
            ])]
        }

        invoice_data = cls.get_real_client_invoice_data()
        cls.withholding_tax_invoice = cls.env['account.move'].with_company(cls.company).create({
            'move_type': 'out_invoice',
            'company_id': cls.company.id,
            'partner_id': cls.italian_partner_a.id,
            'invoice_date': datetime.date(2022, 3, 24),
            'invoice_date_due': datetime.date(2022, 3, 24),
            'invoice_line_ids': [
                (0, 0, {
                    **cls.withholding_sale_line,
                    'name': name,
                    'price_unit': price,
                }) for (name, price) in invoice_data.lines
            ],
        })

        cls.pension_fund_tax_invoice = cls.env['account.move'].with_company(cls.company).create({
            'move_type': 'out_invoice',
            'company_id': cls.company.id,
            'partner_id': cls.italian_partner_a.id,
            'invoice_date': datetime.date(2022, 3, 24),
            'invoice_date_due': datetime.date(2022, 3, 24),
            'invoice_line_ids': [
                (0, 0, {
                    **cls.pension_fund_sale_line,
                    'name': name,
                    'price_unit': price,
                }) for (name, price) in invoice_data.lines
            ]
        })

        cls.enasarco_tax_invoice = cls.env['account.move'].with_company(cls.company).create({
            'move_type': 'out_invoice',
            'company_id': cls.company.id,
            'partner_id': cls.italian_partner_a.id,
            'invoice_date': datetime.date(2022, 3, 24),
            'invoice_date_due': datetime.date(2022, 3, 24),
            'invoice_line_ids': [
                (0, 0, {
                    **cls.enasarco_sale_line,
                    'name': name,
                    'price_unit': price,
                }) for (name, price) in invoice_data.lines
            ]
        })

        cls.withholding_tax_invoice._post()
        cls.pension_fund_tax_invoice._post()
        cls.enasarco_tax_invoice._post()

        cls.edi_withholding_tax_xml = cls._get_withholding_test_file_content('IT00470550013_withh.xml')
        cls.edi_pension_fund_tax_xml = cls._get_withholding_test_file_content('IT00470550013_pfund.xml')
        cls.edi_enasarco_tax_xml = cls._get_withholding_test_file_content('IT00470550013_enasa.xml')

    @classmethod
    def _get_withholding_test_file_content(cls, filename):
        """ Get the content of a test file inside this module """
        path = 'l10n_it_edi_withholding/tests/expected_xmls/' + filename
        with tools.file_open(path, mode='rb') as test_file:
            return test_file.read()

    @classmethod
    def get_real_client_invoice_data(cls):
        data = {
            'lines': [
                ('Ordinary accounting service for the year', 350.0),
                ('Balance deposit for the past year', 300.0),
                ('Ordinary accounting service for the trimester', 50.0),
                ('Electronic invoices management', 50.0),
            ],
            'base': 750.0,
            'tax_amount': 165.0,
            'with_tax': 915.0,
            'withholding_amount': 150.0,
            'with_withholding': 765.0,
            'pension_fund_amount': 30.0,
            'with_pension_fund': 951.6,
            'tax_amount_with_pension_fund': 171.6,
            'payment_amount': 801.6,
        }
        return namedtuple('ClientInvoice', data.keys())(**data)

    def test_withholding_tax_constraints(self):
        with self.assertRaises(ValidationError):
            self.withholding_sale_tax.amount = 10
        with self.assertRaises(ValidationError):
            self.withholding_sale_tax.l10n_it_withholding_type = False
        with self.assertRaises(ValidationError):
            self.withholding_sale_tax.l10n_it_withholding_reason = False
        with self.assertRaises(ValidationError):
            self.company.account_sale_tax_id.l10n_it_withholding_type = "RT02"

    def test_withholding_taxes_export(self):
        """
            Invoice
            -------------------------------------------------------------
            Ordinary accounting service for the year               350.00
            Balance deposit for the past year                      300.00
            Ordinary accounting service for the trimester           50.00
            Electronic invoices management                          50.00
            -------------------------------------------------------------
            Total untaxed:                                         750.00
            Withholding:     20% of Untaxed Amount                -150.00
            VAT:             22% of Untaxed Amount                 165.00
            Document total:  Untaxed Amount + VAT                  915.00
            Payment amount:  Document total - Withholding          765.00
        """
        invoice_etree = etree.fromstring(self.edi_format._l10n_it_edi_export_invoice_as_xml(self.withholding_tax_invoice))
        invoice_data = self.get_real_client_invoice_data()
        expected_etree = self.with_applied_xpath(
            etree.fromstring(self.edi_basis_xml),
            '''
            <xpath expr="//FatturaElettronicaBody//DatiBeniServizi" position="replace">
                <DatiBeniServizi>
            ''' + ''.join(f'''
                  <DettaglioLinee>
                    <NumeroLinea>{n}</NumeroLinea>
                    <Descrizione>{name}</Descrizione>
                    <Quantita>1.00</Quantita>
                    <PrezzoUnitario>{price:.6f}</PrezzoUnitario>
                    <PrezzoTotale>{price:.2f}</PrezzoTotale>
                    <AliquotaIVA>22.00</AliquotaIVA>
                    <Ritenuta>SI</Ritenuta>
                  </DettaglioLinee>
             ''' for n, (name, price) in enumerate(invoice_data.lines, 1)) + f'''
                  <DatiRiepilogo>
                    <AliquotaIVA>22.00</AliquotaIVA>
                    <ImponibileImporto>{invoice_data.base:.2f}</ImponibileImporto>
                    <Imposta>{invoice_data.tax_amount:.2f}</Imposta>
                    <EsigibilitaIVA>I</EsigibilitaIVA>
                  </DatiRiepilogo>
                </DatiBeniServizi>
            </xpath>
            <xpath expr="//DettaglioPagamento//ImportoPagamento" position="inside">
                {invoice_data.with_withholding:.2f}
            </xpath>
            <xpath expr="//DatiGeneraliDocumento//ImportoTotaleDocumento" position="before">
                <DatiRitenuta>
                    <TipoRitenuta>RT02</TipoRitenuta>
                    <ImportoRitenuta>{invoice_data.withholding_amount:.2f}</ImportoRitenuta>
                    <AliquotaRitenuta>20.00</AliquotaRitenuta>
                    <CausalePagamento>A</CausalePagamento>
                </DatiRitenuta>
            </xpath>
            <xpath expr="//DatiGeneraliDocumento//ImportoTotaleDocumento" position="inside">
                {invoice_data.with_tax:.2f}
            </xpath>
            '''
        )
        invoice_etree = self.with_applied_xpath(invoice_etree, "<xpath expr='.//Allegati' position='replace'/>")
        self.assertXmlTreeEqual(invoice_etree, expected_etree)

    def test_withholding_taxes_import(self):
        imported_etree = etree.fromstring(self.edi_withholding_tax_xml)
        invoice = self.edi_format._create_invoice_from_xml_tree("IT00470550013_withh.xml", imported_etree, self.purchase_journal)
        invoice_data = self.get_real_client_invoice_data()
        for line in invoice.line_ids.filtered(lambda x: x.name in [data[0] for data in invoice_data.lines]):
            withholding_taxes = line.tax_ids.filtered(lambda x: x.l10n_it_withholding_type)
            pension_fund_taxes = line.tax_ids.filtered(lambda x: x.l10n_it_pension_fund_type)
            vat_taxes = line.tax_ids - withholding_taxes - pension_fund_taxes
            self.assertEqual([1, 1, 0], [len(x) for x in (vat_taxes, withholding_taxes, pension_fund_taxes)])
        self.assertEqual(765.00, invoice.amount_total)

    def test_pension_fund_taxes_export(self):
        """
            Invoice
            -------------------------------------------------------------
            Ordinary accounting service for the year               350.00
            Balance deposit for the past year                      300.00
            Ordinary accounting service for the trimester           50.00
            Electronic invoices management                          50.00
            -------------------------------------------------------------
            Total untaxed:                                         750.00
            Pension fund:    4% of Untaxed Amount                   30.00
            Withholding:     20% of Untaxed Amount                -150.00
            VAT:             22% of Untaxed Amount + Pension fund  171.60
            Document total:  Taxed Amount                          951.60
            Payment amount:  Document total - Withholding          801.60
        """
        invoice_etree = etree.fromstring(self.edi_format._l10n_it_edi_export_invoice_as_xml(self.pension_fund_tax_invoice))
        invoice_data = self.get_real_client_invoice_data()
        expected_etree = self.with_applied_xpath(
            etree.fromstring(self.edi_basis_xml),
            '''
            <xpath expr="//FatturaElettronicaBody//DatiBeniServizi" position="replace">
                <DatiBeniServizi>
            ''' + ''.join(f'''
                  <DettaglioLinee>
                    <NumeroLinea>{n}</NumeroLinea>
                    <Descrizione>{name}</Descrizione>
                    <Quantita>1.00</Quantita>
                    <PrezzoUnitario>{price:.6f}</PrezzoUnitario>
                    <PrezzoTotale>{price:.2f}</PrezzoTotale>
                    <AliquotaIVA>22.00</AliquotaIVA>
                    <Ritenuta>SI</Ritenuta>
                  </DettaglioLinee>
             ''' for n, (name, price) in enumerate(invoice_data.lines, 1)) + f'''
                  <DatiRiepilogo>
                    <AliquotaIVA>22.00</AliquotaIVA>
                    <ImponibileImporto>{invoice_data.base + invoice_data.pension_fund_amount:.2f}</ImponibileImporto>
                    <Imposta>{invoice_data.tax_amount_with_pension_fund :.2f}</Imposta>
                    <EsigibilitaIVA>I</EsigibilitaIVA>
                  </DatiRiepilogo>
                </DatiBeniServizi>
            </xpath>
            <xpath expr="//DettaglioPagamento//ImportoPagamento" position="inside">
                {invoice_data.payment_amount:.2f}
            </xpath>
            <xpath expr="//DatiGeneraliDocumento//ImportoTotaleDocumento" position="before">
                <DatiRitenuta>
                    <TipoRitenuta>RT02</TipoRitenuta>
                    <ImportoRitenuta>{invoice_data.withholding_amount:.2f}</ImportoRitenuta>
                    <AliquotaRitenuta>20.00</AliquotaRitenuta>
                    <CausalePagamento>A</CausalePagamento>
                </DatiRitenuta>
            </xpath>
            <xpath expr="//DatiGeneraliDocumento//ImportoTotaleDocumento" position="before">
                <DatiCassaPrevidenziale>
                    <TipoCassa>TC01</TipoCassa>
                    <AlCassa>4.00</AlCassa>
                    <ImportoContributoCassa>{invoice_data.pension_fund_amount:.2f}</ImportoContributoCassa>
                    <ImponibileCassa>{invoice_data.base:.2f}</ImponibileCassa>
                    <AliquotaIVA>22.00</AliquotaIVA>
                    <RiferimentoAmministrazione>___ignore___</RiferimentoAmministrazione>
                </DatiCassaPrevidenziale>
            </xpath>
            <xpath expr="//DatiGeneraliDocumento//ImportoTotaleDocumento" position="inside">
                {invoice_data.with_pension_fund:.2f}
            </xpath>
            '''
        )
        invoice_etree = self.with_applied_xpath(invoice_etree, "<xpath expr='.//Allegati' position='replace'/>")
        self.assertXmlTreeEqual(invoice_etree, expected_etree)

    def test_pension_fund_taxes_import(self):
        imported_etree = etree.fromstring(self.edi_pension_fund_tax_xml)
        invoice = self.edi_format._create_invoice_from_xml_tree("IT00470550013_pfund.xml", imported_etree, self.purchase_journal)
        invoice_data = self.get_real_client_invoice_data()
        for line in invoice.line_ids.filtered(lambda x: x.name in [data[0] for data in invoice_data.lines]):
            withholding_taxes = line.tax_ids.filtered(lambda x: x.l10n_it_withholding_type)
            pension_fund_taxes = line.tax_ids.filtered(lambda x: x.l10n_it_pension_fund_type)
            vat_taxes = line.tax_ids - withholding_taxes - pension_fund_taxes
            self.assertEqual([1, 1, 1], [len(x) for x in (vat_taxes, withholding_taxes, pension_fund_taxes)])
            self.assertEqual(795.60, invoice.amount_total)

    def test_enasarco_tax_export(self):
        """
            Invoice
            -----------------------------------------------------------------
            Ordinary accounting service for the year                   350.00
            Balance deposit for the past year                          300.00
            Ordinary accounting service for the trimester               50.00
            Electronic invoices management                              50.00
            -----------------------------------------------------------------
            Total untaxed:                                             750.00
            VAT:             22% of Untaxed Amount                     165.00
            ENASARCO:        8.5% of Untaxed Amount                    -63.75
            Withholding Tax: 23% on 50% of Untaxed Amount              -86.25
            Document total:  Taxed Amount                              915.00
            Payment amount:  Document total - Withholding - Enasarco   765.00
        """
        invoice_etree = etree.fromstring(self.edi_format._l10n_it_edi_export_invoice_as_xml(self.enasarco_tax_invoice))
        invoice_data = self.get_real_client_invoice_data()
        expected_etree = self.with_applied_xpath(
            etree.fromstring(self.edi_basis_xml),
            '''
            <xpath expr="//FatturaElettronicaBody//DatiBeniServizi" position="replace">
                <DatiBeniServizi>
            ''' + ''.join(f'''
                  <DettaglioLinee>
                    <NumeroLinea>{n}</NumeroLinea>
                    <Descrizione>{name}</Descrizione>
                    <Quantita>1.00</Quantita>
                    <PrezzoUnitario>{price:.6f}</PrezzoUnitario>
                    <PrezzoTotale>{price:.2f}</PrezzoTotale>
                    <AliquotaIVA>22.00</AliquotaIVA>
                    <Ritenuta>SI</Ritenuta>
                    <AltriDatiGestionali>
                        <TipoDato>CASSA-PREV</TipoDato>
                        <RiferimentoTesto>TC07 - ENASARCO (8.5%)</RiferimentoTesto>
                        <RiferimentoNumero>{price * 8.5 / 100:.2f}</RiferimentoNumero>
                    </AltriDatiGestionali>
                  </DettaglioLinee>
             ''' for n, (name, price) in enumerate(invoice_data.lines, 1)) + f'''
                  <DatiRiepilogo>
                    <AliquotaIVA>22.00</AliquotaIVA>
                    <ImponibileImporto>{invoice_data.base:.2f}</ImponibileImporto>
                    <Imposta>165.00</Imposta>
                    <EsigibilitaIVA>I</EsigibilitaIVA>
                  </DatiRiepilogo>
                </DatiBeniServizi>
            </xpath>
            <xpath expr="//DettaglioPagamento//ImportoPagamento" position="inside">
                765.00
            </xpath>
            <xpath expr="//DatiGeneraliDocumento//ImportoTotaleDocumento" position="before">
                <DatiRitenuta>
                    <TipoRitenuta>RT02</TipoRitenuta>
                    <ImportoRitenuta>86.25</ImportoRitenuta>
                    <AliquotaRitenuta>23.00</AliquotaRitenuta>
                    <CausalePagamento>ZO</CausalePagamento>
                </DatiRitenuta>
            </xpath>
            <xpath expr="//DatiGeneraliDocumento//ImportoTotaleDocumento" position="inside">
                915.00
            </xpath>
            '''
        )
        invoice_etree = self.with_applied_xpath(invoice_etree, "<xpath expr='.//Allegati' position='replace'/>")
        self.assertXmlTreeEqual(invoice_etree, expected_etree)

    def test_enasarco_tax_import(self):
        imported_etree = etree.fromstring(self.edi_enasarco_tax_xml)
        invoice = self.edi_format._create_invoice_from_xml_tree("IT00470550013_enasa.xml", imported_etree, self.purchase_journal)
        self.assertTrue(invoice)
        invoice_data = self.get_real_client_invoice_data()
        for line in invoice.line_ids.filtered(lambda x: x.name in [data[0] for data in invoice_data.lines]):
            enasarco_imported_tax = line.tax_ids.filtered(lambda x: x.l10n_it_pension_fund_type == 'TC07')
            self.assertEqual(self.enasarco_purchase_tax, enasarco_imported_tax)
            self.assertEqual(-8.5, enasarco_imported_tax.amount)
            self.assertEqual(self.withholding_purchase_tax_23, line.tax_ids.filtered(lambda x: x.l10n_it_withholding_reason == 'ZO'))
