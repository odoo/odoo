# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from lxml import etree

from odoo.tests import tagged
from odoo.addons.l10n_it_edi.tests.common import TestItEdi
from odoo.exceptions import UserError


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestItEdiExport(TestItEdi):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.price_included_tax = cls.env['account.tax'].create({
            'name': '22% price included tax',
            'amount': 22.0,
            'amount_type': 'percent',
            'price_include': True,
            'include_base_amount': True,
            'company_id': cls.company.id,
        })

        cls.tax_zero_percent_hundred_percent_repartition = cls.env['account.tax'].create({
            'name': 'all of nothing',
            'amount': 0,
            'amount_type': 'percent',
            'company_id': cls.company.id,
            'invoice_repartition_line_ids': [
                (0, 0, {'factor_percent': 100, 'repartition_type': 'base'}),
                (0, 0, {'factor_percent': 100, 'repartition_type': 'tax'}),
            ],
            'refund_repartition_line_ids': [
                (0, 0, {'factor_percent': 100, 'repartition_type': 'base'}),
                (0, 0, {'factor_percent': 100, 'repartition_type': 'tax'}),
            ],
        })

        cls.tax_zero_percent_zero_percent_repartition = cls.env['account.tax'].create({
            'name': 'none of nothing',
            'amount': 0,
            'amount_type': 'percent',
            'company_id': cls.company.id,
            'invoice_repartition_line_ids': [
                (0, 0, {'factor_percent': 100, 'repartition_type': 'base'}),
                (0, 0, {'factor_percent': 0, 'repartition_type': 'tax'}),
            ],
            'refund_repartition_line_ids': [
                (0, 0, {'factor_percent': 100, 'repartition_type': 'base'}),
                (0, 0, {'factor_percent': 0, 'repartition_type': 'tax'}),
            ],
        })

        cls.italian_partner_b = cls.env['res.partner'].create({
            'name': 'pa partner',
            'vat': 'IT06655971007',
            'l10n_it_codice_fiscale': '06655971007',
            'l10n_it_pa_index': '123456',
            'country_id': cls.env.ref('base.it').id,
            'street': 'Via Test PA',
            'zip': '32121',
            'city': 'PA Town',
            'is_company': True
        })

        cls.italian_partner_no_address_codice = cls.env['res.partner'].create({
            'name': 'Alessi',
            'l10n_it_codice_fiscale': '00465840031',
            'is_company': True,
        })

        cls.italian_partner_no_address_VAT = cls.env['res.partner'].create({
            'name': 'Alessi',
            'vat': 'IT00465840031',
            'is_company': True,
        })

        cls.american_partner = cls.env['res.partner'].create({
            'name': 'Alessi',
            'vat': '00465840031',
            'country_id': cls.env.ref('base.us').id,
            'is_company': True,
        })

        cls.standard_line_below_400 = {
            'name': 'cheap_line',
            'quantity': 1,
            'price_unit': 100.00,
            'tax_ids': [(6, 0, [cls.company.account_sale_tax_id.id])]
        }

        cls.standard_line_400 = {
            'name': '400_line',
            'quantity': 1,
            'price_unit': 327.87,
            'tax_ids': [(6, 0, [cls.company.account_sale_tax_id.id])]
        }

        cls.price_included_invoice = cls.env['account.move'].with_company(cls.company).create({
            'move_type': 'out_invoice',
            'invoice_date': datetime.date(2022, 3, 24),
            'invoice_date_due': datetime.date(2022, 3, 24),
            'partner_id': cls.italian_partner_a.id,
            'partner_bank_id': cls.test_bank.id,
            'invoice_line_ids': [
                (0, 0, {
                    **cls.standard_line,
                    'name': 'something price included',
                    'tax_ids': [(6, 0, [cls.price_included_tax.id])]
                }),
                (0, 0, {
                    **cls.standard_line,
                    'name': 'something else price included',
                    'tax_ids': [(6, 0, [cls.price_included_tax.id])]
                }),
                (0, 0, {
                    **cls.standard_line,
                    'name': 'something not price included',
                }),
            ],
        })

        cls.partial_discount_invoice = cls.env['account.move'].with_company(cls.company).create({
            'move_type': 'out_invoice',
            'invoice_date': datetime.date(2022, 3, 24),
            'invoice_date_due': datetime.date(2022, 3, 24),
            'partner_id': cls.italian_partner_a.id,
            'partner_bank_id': cls.test_bank.id,
            'invoice_line_ids': [
                (0, 0, {
                    **cls.standard_line,
                    'name': 'no discount',
                }),
                (0, 0, {
                    **cls.standard_line,
                    'name': 'special discount',
                    'discount': 50,
                }),
                (0, 0, {
                    **cls.standard_line,
                    'name': "an offer you can't refuse",
                    'discount': 100,
                }),
            ],
        })

        cls.full_discount_invoice = cls.env['account.move'].with_company(cls.company).create({
            'move_type': 'out_invoice',
            'invoice_date': datetime.date(2022, 3, 24),
            'invoice_date_due': datetime.date(2022, 3, 24),
            'partner_id': cls.italian_partner_a.id,
            'partner_bank_id': cls.test_bank.id,
            'invoice_line_ids': [
                (0, 0, {
                    **cls.standard_line,
                    'name': 'nothing shady just a gift for my friend',
                    'discount': 100,
                }),
            ],
        })

        cls.non_latin_and_latin_invoice = cls.env['account.move'].with_company(cls.company).create({
            'move_type': 'out_invoice',
            'invoice_date': datetime.date(2022, 3, 24),
            'invoice_date_due': datetime.date(2022, 3, 24),
            'partner_id': cls.italian_partner_a.id,
            'partner_bank_id': cls.test_bank.id,
            'invoice_line_ids': [
                (0, 0, {
                    **cls.standard_line,
                    'name': 'ʢ◉ᴥ◉ʡ',
                    }),
                (0, 0, {
                    **cls.standard_line,
                    'name': '–-',
                    }),
                (0, 0, {
                    **cls.standard_line,
                    'name': 'this should be the same as it was',
                    }),
                ],
            })

        cls.below_400_codice_simplified_invoice = cls.env['account.move'].with_company(cls.company).create({
            'move_type': 'out_invoice',
            'invoice_date': datetime.date(2022, 3, 24),
            'invoice_date_due': datetime.date(2022, 3, 24),
            'partner_id': cls.italian_partner_no_address_codice.id,
            'invoice_line_ids': [
                (0, 0, {
                    **cls.standard_line_below_400,
                    }),
                (0, 0, {
                    **cls.standard_line_below_400,
                    'name': 'cheap_line_2',
                    'quantity': 2,
                    'price_unit': 10.0,
                    }),
                ],
            })

        cls.total_400_VAT_simplified_invoice = cls.env['account.move'].with_company(cls.company).create({
            'move_type': 'out_invoice',
            'invoice_date': datetime.date(2022, 3, 24),
            'invoice_date_due': datetime.date(2022, 3, 24),
            'partner_id': cls.italian_partner_no_address_VAT.id,
            'invoice_line_ids': [
                (0, 0, {
                    **cls.standard_line_400,
                    }),
                ],
            })

        cls.more_400_simplified_invoice = cls.env['account.move'].with_company(cls.company).create({
            'move_type': 'out_invoice',
            'invoice_date': datetime.date(2022, 3, 24),
            'invoice_date_due': datetime.date(2022, 3, 24),
            'partner_id': cls.italian_partner_no_address_codice.id,
            'invoice_line_ids': [
                (0, 0, {
                    **cls.standard_line,
                    }),
                ],
            })

        cls.non_domestic_simplified_invoice = cls.env['account.move'].with_company(cls.company).create({
            'move_type': 'out_invoice',
            'invoice_date': datetime.date(2022, 3, 24),
            'invoice_date_due': datetime.date(2022, 3, 24),
            'partner_id': cls.american_partner.id,
            'invoice_line_ids': [
                (0, 0, {
                    **cls.standard_line_below_400,
                    }),
                ],
            })

        cls.pa_partner_invoice = cls.env['account.move'].with_company(cls.company).create({
            'move_type': 'out_invoice',
            'invoice_date': datetime.date(2022, 3, 24),
            'invoice_date_due': datetime.date(2022, 3, 24),
            'partner_id': cls.italian_partner_b.id,
            'partner_bank_id': cls.test_bank.id,
            'invoice_line_ids': [
                (0, 0, cls.standard_line),
            ],
        })

        cls.zero_tax_invoice = cls.env['account.move'].with_company(cls.company).create({
            'move_type': 'out_invoice',
            'invoice_date': datetime.date(2022, 3, 24),
            'invoice_date_due': datetime.date(2022, 3, 24),
            'partner_id': cls.italian_partner_a.id,
            'partner_bank_id': cls.test_bank.id,
            'invoice_line_ids': [
                (0, 0, {
                    **cls.standard_line,
                    'name': 'line with tax of 0% with repartition line of 100% ',
                    'tax_ids': [(6, 0, [cls.tax_zero_percent_hundred_percent_repartition.id])],
                }),
                (0, 0, {
                    **cls.standard_line,
                    'name': 'line with tax of 0% with repartition line of 0% ',
                    'tax_ids': [(6, 0, [cls.tax_zero_percent_zero_percent_repartition.id])],
                }),
            ],
        })

        cls.negative_price_invoice = cls.env['account.move'].with_company(cls.company).create({
            'move_type': 'out_invoice',
            'invoice_date': datetime.date(2022, 3, 24),
            'invoice_date_due': datetime.date(2022, 3, 24),
            'partner_id': cls.italian_partner_a.id,
            'partner_bank_id': cls.test_bank.id,
            'invoice_line_ids': [
                (0, 0, {
                    **cls.standard_line,
                    }),
                (0, 0, {
                    **cls.standard_line,
                    'name': 'negative_line',
                    'price_unit': -100.0,
                    }),
                ],
            })

        # post the invoices
        cls.price_included_invoice._post()
        cls.partial_discount_invoice._post()
        cls.full_discount_invoice._post()
        cls.non_latin_and_latin_invoice._post()
        cls.below_400_codice_simplified_invoice._post()
        cls.total_400_VAT_simplified_invoice._post()
        cls.pa_partner_invoice._post()
        cls.zero_tax_invoice._post()
        cls.negative_price_invoice._post()

    def test_price_included_taxes(self):
        """ When the tax is price included, there should be a rounding value added to the xml, if the sum(subtotals) * tax_rate is not
            equal to taxable base * tax rate (there is a constraint in the edi where taxable base * tax rate = tax amount, but also
            taxable base = sum(subtotals) + rounding amount)
        """
        # In this case, the first two lines use a price_include tax the
        # subtotals should be 800.40 / (100 + 22.0) * 100 = 656.065564..,
        # where 22.0 is the tax rate.
        #
        # Since the subtotals are rounded we actually have 656.07
        lines = self.price_included_invoice.line_ids
        price_included_lines = lines.filtered(lambda line: line.tax_ids == self.price_included_tax)
        self.assertEqual([line.price_subtotal for line in price_included_lines], [656.07, 656.07])
        # So the taxable a base the edi expects (for this tax) is actually 1312.14
        price_included_tax_line = lines.filtered(lambda line: line.tax_line_id == self.price_included_tax)
        self.assertEqual(price_included_tax_line.tax_base_amount, 1312.14)

        # The tax amount of the price included tax should be:
        #   per line: 800.40 - (800.40 / (100 + 22) * 100) = 144.33
        #   tax amount: 144.33 * 2 = 288.66
        self.assertEqual(price_included_tax_line.amount_currency, -288.66)

        expected_etree = self.with_applied_xpath(
            etree.fromstring(self.edi_basis_xml),
            '''
                <xpath expr="//FatturaElettronicaBody//DatiBeniServizi" position="replace">
                    <DatiBeniServizi>
                        <DettaglioLinee>
                          <NumeroLinea>1</NumeroLinea>
                          <Descrizione>something price included</Descrizione>
                          <Quantita>1.00</Quantita>
                          <PrezzoUnitario>656.070000</PrezzoUnitario>
                          <PrezzoTotale>656.07</PrezzoTotale>
                          <AliquotaIVA>22.00</AliquotaIVA>
                        </DettaglioLinee>
                        <DettaglioLinee>
                          <NumeroLinea>2</NumeroLinea>
                          <Descrizione>something else price included</Descrizione>
                          <Quantita>1.00</Quantita>
                          <PrezzoUnitario>656.070000</PrezzoUnitario>
                          <PrezzoTotale>656.07</PrezzoTotale>
                          <AliquotaIVA>22.00</AliquotaIVA>
                        </DettaglioLinee>
                        <DettaglioLinee>
                          <NumeroLinea>3</NumeroLinea>
                          <Descrizione>something not price included</Descrizione>
                          <Quantita>1.00</Quantita>
                          <PrezzoUnitario>800.400000</PrezzoUnitario>
                          <PrezzoTotale>800.40</PrezzoTotale>
                          <AliquotaIVA>22.00</AliquotaIVA>
                        </DettaglioLinee>
                        <DatiRiepilogo>
                          <AliquotaIVA>22.00</AliquotaIVA>
                          <Arrotondamento>-0.04909091</Arrotondamento>
                          <ImponibileImporto>1312.09</ImponibileImporto>
                          <Imposta>288.66</Imposta>
                          <EsigibilitaIVA>I</EsigibilitaIVA>
                        </DatiRiepilogo>
                        <DatiRiepilogo>
                          <AliquotaIVA>22.00</AliquotaIVA>
                          <ImponibileImporto>800.40</ImponibileImporto>
                          <Imposta>176.09</Imposta>
                          <EsigibilitaIVA>I</EsigibilitaIVA>
                        </DatiRiepilogo>
                    </DatiBeniServizi>
                </xpath>
                <xpath expr="//DettaglioPagamento//ImportoPagamento" position="inside">
                    2577.29
                </xpath>
                <xpath expr="//DatiGeneraliDocumento//ImportoTotaleDocumento" position="inside">
                    2577.29
                </xpath>
            ''')
        invoice_etree = etree.fromstring(self.edi_format._l10n_it_edi_export_invoice_as_xml(self.price_included_invoice))
        # Remove the attachment and its details
        invoice_etree = self.with_applied_xpath(invoice_etree, "<xpath expr='.//Allegati' position='replace'/>")
        self.assertXmlTreeEqual(invoice_etree, expected_etree)

    def test_partially_discounted_invoice(self):
        # The EDI can account for discounts, but a line with, for example, a 100% discount should still have
        # a corresponding tax with a base amount of 0

        invoice_etree = etree.fromstring(self.edi_format._l10n_it_edi_export_invoice_as_xml(self.partial_discount_invoice))
        expected_etree = self.with_applied_xpath(
            etree.fromstring(self.edi_basis_xml),
            '''
                <xpath expr="//FatturaElettronicaBody//DatiBeniServizi" position="replace">
                    <DatiBeniServizi>
                      <DettaglioLinee>
                        <NumeroLinea>1</NumeroLinea>
                        <Descrizione>no discount</Descrizione>
                        <Quantita>1.00</Quantita>
                        <PrezzoUnitario>800.400000</PrezzoUnitario>
                        <PrezzoTotale>800.40</PrezzoTotale>
                        <AliquotaIVA>22.00</AliquotaIVA>
                      </DettaglioLinee>
                      <DettaglioLinee>
                        <NumeroLinea>2</NumeroLinea>
                        <Descrizione>special discount</Descrizione>
                        <Quantita>1.00</Quantita>
                        <PrezzoUnitario>800.400000</PrezzoUnitario>
                        <ScontoMaggiorazione>
                          <Tipo>SC</Tipo>
                          <Percentuale>50.00</Percentuale>
                        </ScontoMaggiorazione>
                        <PrezzoTotale>400.20</PrezzoTotale>
                        <AliquotaIVA>22.00</AliquotaIVA>
                      </DettaglioLinee>
                      <DettaglioLinee>
                        <NumeroLinea>3</NumeroLinea>
                        <Descrizione>an offer you can't refuse</Descrizione>
                        <Quantita>1.00</Quantita>
                        <PrezzoUnitario>800.400000</PrezzoUnitario>
                        <ScontoMaggiorazione>
                          <Tipo>SC</Tipo>
                          <Percentuale>100.00</Percentuale>
                        </ScontoMaggiorazione>
                        <PrezzoTotale>0.00</PrezzoTotale>
                        <AliquotaIVA>22.00</AliquotaIVA>
                      </DettaglioLinee>
                      <DatiRiepilogo>
                        <AliquotaIVA>22.00</AliquotaIVA>
                        <ImponibileImporto>1200.60</ImponibileImporto>
                        <Imposta>264.13</Imposta>
                        <EsigibilitaIVA>I</EsigibilitaIVA>
                      </DatiRiepilogo>
                    </DatiBeniServizi>
                </xpath>
                <xpath expr="//DettaglioPagamento//ImportoPagamento" position="inside">
                    1464.73
                </xpath>
                <xpath expr="//DatiGeneraliDocumento//ImportoTotaleDocumento" position="inside">
                    1464.73
                </xpath>
            ''')
        invoice_etree = self.with_applied_xpath(invoice_etree, "<xpath expr='.//Allegati' position='replace'/>")
        self.assertXmlTreeEqual(invoice_etree, expected_etree)

    def test_fully_discounted_inovice(self):
        invoice_etree = etree.fromstring(self.edi_format._l10n_it_edi_export_invoice_as_xml(self.full_discount_invoice))
        expected_etree = self.with_applied_xpath(
            etree.fromstring(self.edi_basis_xml),
            '''
            <xpath expr="//FatturaElettronicaBody//DatiBeniServizi" position="replace">
            <DatiBeniServizi>
              <DettaglioLinee>
                <NumeroLinea>1</NumeroLinea>
                <Descrizione>nothing shady just a gift for my friend</Descrizione>
                <Quantita>1.00</Quantita>
                <PrezzoUnitario>800.400000</PrezzoUnitario>
                <ScontoMaggiorazione>
                  <Tipo>SC</Tipo>
                  <Percentuale>100.00</Percentuale>
                </ScontoMaggiorazione>
                <PrezzoTotale>0.00</PrezzoTotale>
                <AliquotaIVA>22.00</AliquotaIVA>
              </DettaglioLinee>
              <DatiRiepilogo>
                <AliquotaIVA>22.00</AliquotaIVA>
                <ImponibileImporto>0.00</ImponibileImporto>
                <Imposta>0.00</Imposta>
                <EsigibilitaIVA>I</EsigibilitaIVA>
              </DatiRiepilogo>
            </DatiBeniServizi>
            </xpath>
            <xpath expr="//DettaglioPagamento//ImportoPagamento" position="inside">
                0.00
            </xpath>
            <xpath expr="//DatiGeneraliDocumento//ImportoTotaleDocumento" position="inside">
                0.00
            </xpath>
            ''')
        invoice_etree = self.with_applied_xpath(invoice_etree, "<xpath expr='.//Allegati' position='replace'/>")
        self.assertXmlTreeEqual(invoice_etree, expected_etree)

    def test_non_latin_and_latin_invoice(self):
        invoice_etree = etree.fromstring(self.edi_format._l10n_it_edi_export_invoice_as_xml(self.non_latin_and_latin_invoice))
        expected_etree = self.with_applied_xpath(
            etree.fromstring(self.edi_basis_xml),
            '''
            <xpath expr="//FatturaElettronicaBody//DatiBeniServizi" position="replace">
            <DatiBeniServizi>
              <DettaglioLinee>
                <NumeroLinea>1</NumeroLinea>
                <Descrizione>?????</Descrizione>
                <Quantita>1.00</Quantita>
                <PrezzoUnitario>800.400000</PrezzoUnitario>
                <PrezzoTotale>800.40</PrezzoTotale>
                <AliquotaIVA>22.00</AliquotaIVA>
              </DettaglioLinee>
              <DettaglioLinee>
                <NumeroLinea>2</NumeroLinea>
                <Descrizione>?-</Descrizione>
                <Quantita>1.00</Quantita>
                <PrezzoUnitario>800.400000</PrezzoUnitario>
                <PrezzoTotale>800.40</PrezzoTotale>
                <AliquotaIVA>22.00</AliquotaIVA>
              </DettaglioLinee>
              <DettaglioLinee>
                <NumeroLinea>3</NumeroLinea>
                <Descrizione>this should be the same as it was</Descrizione>
                <Quantita>1.00</Quantita>
                <PrezzoUnitario>800.400000</PrezzoUnitario>
                <PrezzoTotale>800.40</PrezzoTotale>
                <AliquotaIVA>22.00</AliquotaIVA>
              </DettaglioLinee>
              <DatiRiepilogo>
                <AliquotaIVA>22.00</AliquotaIVA>
                <ImponibileImporto>2401.20</ImponibileImporto>
                <Imposta>528.26</Imposta>
                <EsigibilitaIVA>I</EsigibilitaIVA>
              </DatiRiepilogo>
            </DatiBeniServizi>
            </xpath>
            <xpath expr="//DettaglioPagamento//ImportoPagamento" position="inside">
              2929.46
            </xpath>
            <xpath expr="//DatiGeneraliDocumento//ImportoTotaleDocumento" position="inside">
              2929.46
            </xpath>
            ''')
        invoice_etree = self.with_applied_xpath(invoice_etree, "<xpath expr='.//Allegati' position='replace'/>")
        self.assertXmlTreeEqual(invoice_etree, expected_etree)

    def test_below_400_codice_simplified_invoice(self):
        invoice_etree = etree.fromstring(self.edi_format._l10n_it_edi_export_invoice_as_xml(self.below_400_codice_simplified_invoice))
        expected_etree = self.with_applied_xpath(
            etree.fromstring(self.edi_simplified_basis_xml),
            '''
            <xpath expr="//FatturaElettronicaHeader//CessionarioCommittente" position="inside">
            <IdentificativiFiscali>
                <CodiceFiscale>00465840031</CodiceFiscale>
            </IdentificativiFiscali>
            </xpath>
            <xpath expr="//FatturaElettronicaBody//DatiBeniServizi" position="replace">
            <DatiBeniServizi>
              <Descrizione>cheap_line</Descrizione>
              <Importo>122.00</Importo>
              <DatiIVA>
                <Imposta>22.00</Imposta>
              </DatiIVA>
            </DatiBeniServizi>
            <DatiBeniServizi>
              <Descrizione>cheap_line_2</Descrizione>
              <Importo>24.40</Importo>
              <DatiIVA>
                <Imposta>4.40</Imposta>
              </DatiIVA>
            </DatiBeniServizi>
            </xpath>
            ''')
        invoice_etree = self.with_applied_xpath(invoice_etree, "<xpath expr='.//Allegati' position='replace'/>")
        self.assertXmlTreeEqual(invoice_etree, expected_etree)

    def test_total_400_VAT_simplified_invoice(self):
        invoice_etree = etree.fromstring(self.edi_format._l10n_it_edi_export_invoice_as_xml(self.total_400_VAT_simplified_invoice))
        expected_etree = self.with_applied_xpath(
            etree.fromstring(self.edi_simplified_basis_xml),
            '''
            <xpath expr="//FatturaElettronicaHeader//CessionarioCommittente" position="inside">
            <IdentificativiFiscali>
                <IdFiscaleIVA>
                    <IdPaese>IT</IdPaese>
                    <IdCodice>00465840031</IdCodice>
                </IdFiscaleIVA>
            </IdentificativiFiscali>
            </xpath>
            <xpath expr="//FatturaElettronicaBody//DatiBeniServizi" position="replace">
            <DatiBeniServizi>
              <Descrizione>400_line</Descrizione>
              <Importo>400.00</Importo>
              <DatiIVA>
                <Imposta>72.13</Imposta>
              </DatiIVA>
            </DatiBeniServizi>
            </xpath>
            ''')
        invoice_etree = self.with_applied_xpath(invoice_etree, "<xpath expr='.//Allegati' position='replace'/>")
        self.assertXmlTreeEqual(invoice_etree, expected_etree)

    def test_more_400_simplified_invoice(self):
        with self.assertRaises(UserError):
            self.more_400_simplified_invoice._post()

    def test_non_domestic_simplified_invoice(self):
        with self.assertRaises(UserError):
            self.non_domestic_simplified_invoice._post()

    def test_send_pa_partner(self):
        res = self.edi_format._l10n_it_post_invoices_step_1(self.pa_partner_invoice)
        self.assertEqual(res[self.pa_partner_invoice], {'attachment': self.pa_partner_invoice.l10n_it_edi_attachment_id, 'success': True})

    def test_zero_percent_taxes(self):
        invoice_etree = etree.fromstring(self.edi_format._l10n_it_edi_export_invoice_as_xml(self.zero_tax_invoice))
        expected_etree = self.with_applied_xpath(
            etree.fromstring(self.edi_basis_xml),
            '''
            <xpath expr="//FatturaElettronicaBody//DatiBeniServizi" position="replace">
                <DatiBeniServizi>
                  <DettaglioLinee>
                    <NumeroLinea>1</NumeroLinea>
                    <Descrizione>line with tax of 0% with repartition line of 100%</Descrizione>
                    <Quantita>1.00</Quantita>
                    <PrezzoUnitario>800.400000</PrezzoUnitario>
                    <PrezzoTotale>800.40</PrezzoTotale>
                    <AliquotaIVA>0.00</AliquotaIVA>
                  </DettaglioLinee>
                  <DettaglioLinee>
                    <NumeroLinea>2</NumeroLinea>
                    <Descrizione>line with tax of 0% with repartition line of 0%</Descrizione>
                    <Quantita>1.00</Quantita>
                    <PrezzoUnitario>800.400000</PrezzoUnitario>
                    <PrezzoTotale>800.40</PrezzoTotale>
                    <AliquotaIVA>0.00</AliquotaIVA>
                  </DettaglioLinee>
                  <DatiRiepilogo>
                    <AliquotaIVA>0.00</AliquotaIVA>
                    <ImponibileImporto>800.40</ImponibileImporto>
                    <Imposta>0.00</Imposta>
                    <EsigibilitaIVA>I</EsigibilitaIVA>
                  </DatiRiepilogo>
                  <DatiRiepilogo>
                    <AliquotaIVA>0.00</AliquotaIVA>
                    <ImponibileImporto>800.40</ImponibileImporto>
                    <Imposta>0.00</Imposta>
                    <EsigibilitaIVA>I</EsigibilitaIVA>
                  </DatiRiepilogo>
                </DatiBeniServizi>
            </xpath>
            <xpath expr="//DettaglioPagamento//ImportoPagamento" position="inside">
                1600.80
            </xpath>
            <xpath expr="//DatiGeneraliDocumento//ImportoTotaleDocumento" position="inside">
                1600.80
            </xpath>
            '''
        )
        invoice_etree = self.with_applied_xpath(invoice_etree, "<xpath expr='.//Allegati' position='replace'/>")
        self.assertXmlTreeEqual(invoice_etree, expected_etree)

    def test_negative_price_invoice(self):
        invoice_etree = etree.fromstring(self.edi_format._l10n_it_edi_export_invoice_as_xml(self.negative_price_invoice))
        expected_etree = self.with_applied_xpath(
            etree.fromstring(self.edi_basis_xml),
            '''
                <xpath expr="//FatturaElettronicaBody//DatiBeniServizi" position="replace">
                    <DatiBeniServizi>
                      <DettaglioLinee>
                        <NumeroLinea>1</NumeroLinea>
                        <Descrizione>standard_line</Descrizione>
                        <Quantita>1.00</Quantita>
                        <PrezzoUnitario>800.400000</PrezzoUnitario>
                        <PrezzoTotale>800.40</PrezzoTotale>
                        <AliquotaIVA>22.00</AliquotaIVA>
                      </DettaglioLinee>
                      <DettaglioLinee>
                        <NumeroLinea>2</NumeroLinea>
                        <Descrizione>negative_line</Descrizione>
                        <Quantita>1.00</Quantita>
                        <PrezzoUnitario>-100.000000</PrezzoUnitario>
                        <PrezzoTotale>-100.00</PrezzoTotale>
                        <AliquotaIVA>22.00</AliquotaIVA>
                      </DettaglioLinee>
                      <DatiRiepilogo>
                        <AliquotaIVA>22.00</AliquotaIVA>
                        <ImponibileImporto>700.40</ImponibileImporto>
                        <Imposta>154.09</Imposta>
                        <EsigibilitaIVA>I</EsigibilitaIVA>
                      </DatiRiepilogo>
                    </DatiBeniServizi>
                </xpath>
                <xpath expr="//DettaglioPagamento//ImportoPagamento" position="inside">
                    854.49
                </xpath>
                <xpath expr="//DatiGeneraliDocumento//ImportoTotaleDocumento" position="inside">
                    854.49
                </xpath>
            ''')
        invoice_etree = self.with_applied_xpath(invoice_etree, "<xpath expr='.//Allegati' position='replace'/>")
        self.assertXmlTreeEqual(invoice_etree, expected_etree)
