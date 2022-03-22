# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import logging
from collections import namedtuple
from unittest.mock import patch
from lxml import etree
from freezegun import freeze_time

from odoo import tools
from odoo.tests import tagged
from odoo.addons.account_edi.tests.common import AccountEdiTestCommon
from odoo.addons.l10n_it_edi.tools.remove_signature import remove_signature

_logger = logging.getLogger(__name__)

@tagged('post_install_l10n', 'post_install', '-at_install')
class PecMailServerTests(AccountEdiTestCommon):
    """ Main test class for the l10n_it_edi vendor bills XML import from a PEC mail account"""

    fake_test_content = """<?xml version="1.0" encoding="UTF-8"?>
        <p:FatturaElettronica versione="FPR12" xmlns:ds="http://www.w3.org/2000/09/xmldsig#" 
        xmlns:p="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2" 
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
        xsi:schemaLocation="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2 http://www.fatturapa.gov.it/export/fatturazione/sdi/fatturapa/v1.2/Schema_del_file_xml_FatturaPA_versione_1.2.xsd">
          <FatturaElettronicaHeader>
            <CessionarioCommittente>
              <DatiAnagrafici>
                <CodiceFiscale>01234560157</CodiceFiscale>
              </DatiAnagrafici>
            </CessionarioCommittente>
          </FatturaElettronicaHeader>
          <FatturaElettronicaBody>
            <DatiGenerali>
              <DatiGeneraliDocumento>
                <TipoDocumento>TD02</TipoDocumento>
              </DatiGeneraliDocumento>
            </DatiGenerali>
          </FatturaElettronicaBody>
        </p:FatturaElettronica>"""

    @classmethod
    def setUpClass(cls):
        """ Setup the test class with a PEC mail server and a fake fatturaPA content """

        super().setUpClass(chart_template_ref='l10n_it.l10n_it_chart_template_generic',
                           edi_format_ref='l10n_it_edi.edi_fatturaPA')

        # Use the company_data_2 to test that the e-invoice is imported for the right company
        cls.company = cls.company_data_2['company']

        # Initialize the company's codice fiscale
        cls.company.l10n_it_codice_fiscale = '01234560157'
        cls.company.vat = 'IT01234560157'

        # Build test data.
        # invoice_filename1 is used for vendor bill receipts tests
        # invoice_filename2 is used for vendor bill tests
        cls.invoice_filename1 = 'IT01234567890_FPR01.xml'
        cls.invoice_filename2 = 'IT01234567890_FPR02.xml'
        cls.signed_invoice_filename = 'IT01234567890_FPR01.xml.p7m'
        cls.invoice_content = cls._get_test_file_content(cls.invoice_filename1)
        cls.signed_invoice_content = cls._get_test_file_content(cls.signed_invoice_filename)
        cls.invoice = cls.env['account.move'].create({
            'move_type': 'in_invoice',
            'ref': '01234567890'
        })
        cls.attachment = cls.env['ir.attachment'].create({
            'name': cls.invoice_filename1,
            'raw': cls.invoice_content,
            'res_id': cls.invoice.id,
            'res_model': 'account.move',
        })
        cls.edi_document = cls.env['account.edi.document'].create({
            'edi_format_id': cls.edi_format.id,
            'move_id': cls.invoice.id,
            'attachment_id': cls.attachment.id,
            'state': 'sent'
        })

        # Initialize the fetchmail server that has to be tested
        cls.server = cls.env['fetchmail.server'].sudo().create({
            'name': 'test_server',
            'server_type': 'imap',
            'l10n_it_is_pec': True})

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
            'company_id': cls.company.id,
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
            'invoice_line_ids': [
                (0, 0, {
                    **cls.standard_line,
                    'name': 'nothing shady just a gift for my friend',
                    'discount': 100,
                }),
            ],
        })
        # post the invoices
        cls.price_included_invoice._post()
        cls.partial_discount_invoice._post()
        cls.full_discount_invoice._post()

        cls.test_invoice_xmls = {k: cls._get_test_file_content(v) for k, v in [
            ('normal_1', 'IT01234567890_FPR01.xml'),
            ('signed', 'IT01234567890_FPR01.xml.p7m'),
            ('export_basis', 'IT00470550013_basis.xml'),
        ]}

    @classmethod
    def _get_test_file_content(cls, filename):
        """ Get the content of a test file inside this module """
        path = 'l10n_it_edi/tests/expected_xmls/' + filename
        with tools.file_open(path, mode='rb') as test_file:
            return test_file.read()

    def _create_invoice(self, content, filename):
        """ Create an invoice from given attachment content """
        with patch.object(self.server._cr, 'commit', return_value=None):
            if filename.endswith(".p7m"):
                content = remove_signature(content)
            return self.server._create_invoice_from_mail(content, filename, 'fake@address.be')

    # -----------------------------
    #
    # Vendor bills
    #
    # -----------------------------

    def test_receive_vendor_bill(self):
        """ Test a sample e-invoice file from https://www.fatturapa.gov.it/export/documenti/fatturapa/v1.2/IT01234567890_FPR01.xml """
        invoices = self._create_invoice(self.invoice_content, self.invoice_filename2)
        self.assertTrue(bool(invoices))

    def test_receive_signed_vendor_bill(self):
        """ Test a signed (P7M) sample e-invoice file from https://www.fatturapa.gov.it/export/documenti/fatturapa/v1.2/IT01234567890_FPR01.xml """
        with freeze_time('2020-04-06'):
            invoices = self._create_invoice(self.signed_invoice_content, self.signed_invoice_filename)
            self.assertRecordValues(invoices, [{
                'company_id': self.company.id,
                'name': 'BILL/2014/12/0001',
                'invoice_date': datetime.date(2014, 12, 18),
                'ref': '01234567890',
            }])

    def test_receive_same_vendor_bill_twice(self):
        """ Test that the second time we are receiving a PEC mail with the same attachment, the second is discarded """
        content = self.fake_test_content.encode()
        for result in [True, False]:
            invoice = self._create_invoice(content, self.invoice_filename2)
            self.assertEqual(result, bool(invoice))

    # -----------------------------
    #
    # Receipts
    #
    # -----------------------------

    def _test_receipt(self, receipt_type, source_state, destination_state):
        """ Test a receipt from the ones in the module's test files """

        # Simulate the 'sent' state of the move, even if we didn't actually send an email in this test
        self.invoice.l10n_it_send_state = source_state

        # Create a fake receipt from the test file
        receipt_filename = 'IT01234567890_FPR01_%s_001.xml' % receipt_type
        receipt_content = self._get_test_file_content(receipt_filename).decode()

        create_mail_attachment = namedtuple('Attachment', ('fname', 'content', 'info'))
        receipt_mail_attachment = create_mail_attachment(receipt_filename, receipt_content, {})

        # Simulate the arrival of the receipt
        with patch.object(self.server._cr, 'commit', return_value=None):
            self.server._message_receipt_invoice(receipt_type, receipt_mail_attachment)

        # Check the Destination state of the edi_document
        self.assertTrue(destination_state, self.edi_document.state)

    def test_ricevuta_consegna(self):
        """ Test a receipt adapted from https://www.fatturapa.gov.it/export/documenti/messaggi/v1.0/IT01234567890_11111_RC_001.xml """
        self._test_receipt('RC', 'sent', 'delivered')

    def test_decorrenza_termini(self):
        """ Test a receipt adapted from https://www.fatturapa.gov.it/export/documenti/messaggi/v1.0/IT01234567890_11111_DT_001.xml """
        self._test_receipt('DT', 'delivered', 'delivered_expired')

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
            etree.fromstring(self.test_invoice_xmls['export_basis']),
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
            etree.fromstring(self.test_invoice_xmls['export_basis']),
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
            etree.fromstring(self.test_invoice_xmls['export_basis']),
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
