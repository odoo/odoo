# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import logging
from lxml import etree
from freezegun import freeze_time

from odoo import tools
from odoo.tests import tagged
from odoo.addons.account_edi.tests.common import AccountEdiTestCommon

_logger = logging.getLogger(__name__)

@tagged('post_install_l10n', 'post_install', '-at_install')
class TestItEdi(AccountEdiTestCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass(chart_template_ref='l10n_it.l10n_it_chart_template_generic',
                           edi_format_ref='l10n_it_edi.edi_fatturaPA')

        # Use the company_data_2 to test that the e-invoice is imported for the right company
        cls.company = cls.company_data_2['company']

        cls.company.l10n_it_codice_fiscale = '01234560157'
        cls.company.vat = 'IT01234560157'
        cls.test_bank = cls.env['res.partner.bank'].with_company(cls.company).create({
                'partner_id': cls.company.partner_id.id,
                'acc_number': 'IT1212341234123412341234123',
                'bank_name': 'BIG BANK',
                'bank_bic': 'BIGGBANQ',
        })
        cls.company.l10n_it_tax_system = "RF01"
        cls.company.street = "1234 Test Street"
        cls.company.zip = "12345"
        cls.company.city = "Prova"
        cls.company.country_id = cls.env.ref('base.it')

        cls.price_included_tax = cls.env['account.tax'].create({
            'name': '22% price included tax',
            'amount': 22.0,
            'amount_type': 'percent',
            'price_include': True,
            'include_base_amount': True,
            'company_id': cls.company.id,
        })

        cls.italian_partner_a = cls.env['res.partner'].create({
            'name': 'Alessi',
            'vat': 'IT00465840031',
            'l10n_it_codice_fiscale': '00465840031',
            'country_id': cls.env.ref('base.it').id,
            'street': 'Via Privata Alessi 6',
            'zip': '28887',
            'city': 'Milan',
            'company_id': cls.company.id,
            'is_company': True,
        })

        cls.standard_line = {
            'name': 'standard_line',
            'quantity': 1,
            'price_unit': 800.40,
            'tax_ids': [(6, 0, [cls.company.account_sale_tax_id.id])]
        }

        cls.price_included_invoice = cls.env['account.move'].with_company(cls.company).create({
            'move_type': 'out_invoice',
            'invoice_date': datetime.date(2022, 3, 24),
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

        # We create this because we are unable to post without a proxy user existing
        cls.proxy_user = cls.env['account_edi_proxy_client.user'].create({
            'id_client': 'l10n_it_edi_sdicoop_test',
            'company_id': cls.company.id,
            'edi_format_id': cls.edi_format.id,
            'edi_identification': 'l10n_it_edi_sdicoop_test',
            'private_key': 'l10n_it_edi_sdicoop_test',
        })

        # post the invoices
        cls.price_included_invoice._post()
        cls.partial_discount_invoice._post()
        cls.full_discount_invoice._post()
        cls.non_latin_and_latin_invoice._post()

        cls.edi_basis_xml = cls._get_test_file_content('IT00470550013_basis.xml')

    @classmethod
    def _get_test_file_content(cls, filename):
        """ Get the content of a test file inside this module """
        path = 'l10n_it_edi_sdicoop/tests/expected_xmls/' + filename
        with tools.file_open(path, mode='rb') as test_file:
            return test_file.read()

    @freeze_time('2020-03-24')
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
        self.assertEqual(price_included_tax_line.price_total, 288.66)

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
            ''')
        invoice_etree = etree.fromstring(self.price_included_invoice._export_as_xml())
        # Remove the attachment and its details
        invoice_etree = self.with_applied_xpath(invoice_etree, "<xpath expr='.//Allegati' position='replace'/>")
        self.assertXmlTreeEqual(invoice_etree, expected_etree)

    @freeze_time('2020-03-24')
    def test_partially_discounted_invoice(self):
        # The EDI can account for discounts, but a line with, for example, a 100% discount should still have
        # a corresponding tax with a base amount of 0

        invoice_etree = etree.fromstring(self.partial_discount_invoice._export_as_xml())
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
            ''')
        invoice_etree = self.with_applied_xpath(invoice_etree, "<xpath expr='.//Allegati' position='replace'/>")
        self.assertXmlTreeEqual(invoice_etree, expected_etree)

    @freeze_time('2020-03-24')
    def test_fully_discounted_inovice(self):
        invoice_etree = etree.fromstring(self.full_discount_invoice._export_as_xml())
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
            ''')
        invoice_etree = self.with_applied_xpath(invoice_etree, "<xpath expr='.//Allegati' position='replace'/>")
        self.assertXmlTreeEqual(invoice_etree, expected_etree)

    @freeze_time('2020-03-24')
    def test_non_latin_and_latin_inovice(self):
        invoice_etree = etree.fromstring(self.non_latin_and_latin_invoice._export_as_xml())
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
                <Imposta>528.27</Imposta>
                <EsigibilitaIVA>I</EsigibilitaIVA>
              </DatiRiepilogo>
            </DatiBeniServizi>
            </xpath>
            <xpath expr="//DettaglioPagamento//ImportoPagamento" position="inside">
              2929.47
            </xpath>
            ''')
        invoice_etree = self.with_applied_xpath(invoice_etree, "<xpath expr='.//Allegati' position='replace'/>")
        self.assertXmlTreeEqual(invoice_etree, expected_etree)
