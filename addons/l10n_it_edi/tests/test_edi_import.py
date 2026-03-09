# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from base64 import b64encode
import uuid
from freezegun import freeze_time
from lxml import etree
from unittest.mock import patch

from odoo import fields, sql_db, tools, Command
from odoo.exceptions import ValidationError
from odoo.tests import new_test_user, tagged
from odoo.addons.l10n_it_edi.tests.common import TestItEdi

import logging
_logger = logging.getLogger(__name__)


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestItEdiImport(TestItEdi):
    """ Main test class for the l10n_it_edi vendor bills XML import"""

    fake_test_content = """<?xml version="1.0" encoding="UTF-8"?>
        <p:FatturaElettronica versione="FPR12" xmlns:ds="http://www.w3.org/2000/09/xmldsig#"
        xmlns:p="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2"
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xsi:schemaLocation="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2 http://www.fatturapa.gov.it/export/fatturazione/sdi/fatturapa/v1.2/Schema_del_file_xml_FatturaPA_versione_1.2.xsd">
        <FatturaElettronicaHeader>
          <DatiTrasmissione>
            <IdTrasmittente>
                <IdPaese>IT</IdPaese>
                <IdCodice>01234560157</IdCodice>
            </IdTrasmittente>
            <ProgressivoInvio>TWICE_TEST</ProgressivoInvio>
          </DatiTrasmissione>
          <CedentePrestatore>
            <DatiAnagrafici>
              <CodiceFiscale>10062090963</CodiceFiscale>
              <Anagrafica>
                <Denominazione>DITTA ALPHA</Denominazione>
              </Anagrafica>
            </DatiAnagrafici>
            <Sede>
                <Indirizzo>VIALE ROMA 543</Indirizzo>
                <CAP>07100</CAP>
                <Comune>SASSARI</Comune>
                <Provincia>SS</Provincia>
                <Nazione>IT</Nazione>
            </Sede>
          </CedentePrestatore>
          <CessionarioCommittente>
            <DatiAnagrafici>
              <CodiceFiscale>01234560157</CodiceFiscale>
              <Anagrafica>
                <Denominazione>DITTA BETA</Denominazione>
              </Anagrafica>
            </DatiAnagrafici>
            <Sede>
                <Indirizzo>Via Teulada</Indirizzo>
                <CAP>20100</CAP>
                <Comune>Milano</Comune>
                <Nazione>IT</Nazione>
            </Sede>
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

    # -----------------------------
    # Vendor bills
    # -----------------------------

    def test_receive_vendor_bill(self):
        """ Test a sample e-invoice file from
        https://www.fatturapa.gov.it/export/documenti/fatturapa/v1.2/IT01234567890_FPR01.xml
        """

        # Added to ensures that a 0.00 unit price from XML is preserved.
        applied_xml = """
            <xpath expr="//FatturaElettronicaBody/DatiBeniServizi/DettaglioLinee" position="after">
                <DettaglioLinee>
                    <NumeroLinea>2</NumeroLinea>
                    <Descrizione>[TEST] Test Product</Descrizione>
                    <Quantita>1.00</Quantita>
                    <PrezzoUnitario>0.00</PrezzoUnitario>
                    <PrezzoTotale>0.00</PrezzoTotale>
                    <AliquotaIVA>22.00</AliquotaIVA>
                </DettaglioLinee>
            </xpath>
        """

        self._assert_import_invoice('IT01234567890_FPR01.xml', [{
            'move_type': 'in_invoice',
            'invoice_date': fields.Date.from_string('2014-12-18'),
            'amount_untaxed': 5.0,
            'amount_tax': 1.1,
            'invoice_line_ids': [
                {
                    'quantity': 5.0,
                    'price_unit': 1.0,
                    'debit': 5.0,
                },
                {
                    'quantity': 1.0,
                    'price_unit': 0.0,
                    'debit': 0.0,
                },
            ],
        }], applied_xml)

    def test_receive_vendor_bill_sconto_maggiorazione(self):
        """ Test a sample e-invoice file with
        ScontoMaggiorazione on lines
        """
        self._assert_import_invoice('IT01234567890_DISC1.xml', [{
            'move_type': 'in_invoice',
            'invoice_date': fields.Date.from_string('2014-12-18'),
            'amount_untaxed': 28.75,
            'amount_tax': 6.33,
            'invoice_line_ids': [{
                'quantity': 5.0,
                'price_unit': 1.0,
                'discount': 0,
                'debit': 5.0,
            },
            {
                'quantity': 5.0,
                'price_unit': 10.0,
                'discount': 52.5,
                'debit': 23.75,
            },
            {
                'quantity': 1.0,
                'price_unit': 0.0,
                'discount': 0.0,
                'debit': 0.0,
            }],
        }])

    def test_receive_negative_vendor_bill(self):
        """ Same vendor bill as test_receive_vendor_bill but negative unit price """
        self._assert_import_invoice('IT01234567890_FPR02.xml', [{
            'move_type': 'in_invoice',
            'invoice_date': fields.Date.from_string('2014-12-18'),
            'amount_untaxed': -5.0,
            'amount_tax': -1.1,
            'invoice_line_ids': [{
                'quantity': 5.0,
                'price_unit': -1.0,
                'credit': 5.0,
            }],
        }])

    def test_import_refund_with_linked_po(self):
        if self.env['ir.module.module']._get('purchase').state != 'installed':
            self.skipTest("purchase module is not installed")

        product = self.env['product.product'].create({
            'name': 'DESCRIZIONE DELLA FORNITURA',
            'supplier_taxes_id': [Command.set(self.default_tax.ids)],
        })
        purchase = self.env['purchase.order'].with_company(self.company).with_context(tracking_disable=True).create(
            {
                'partner_id': self.italian_partner_a.id,
                'partner_ref': 'PO-001',
                'order_line': [
                    Command.create({
                        'product_qty': 10.0,
                        'product_id': product.id,
                        'price_unit': 1.0,
                        'name': 'DESCRIZIONE DELLA FORNITURA',
                    }),
                ],
            })
        purchase.button_confirm()

        self._assert_import_invoice('IT01234567890_FPR04.xml', [{
            'move_type': 'in_refund',
            'invoice_origin': purchase.name,
            'invoice_date': fields.Date.from_string('2014-12-18'),
            'amount_untaxed': 5.0,
            'amount_tax': 1.1,
            'is_purchase_matched': True,
            'invoice_line_ids': [{
                'display_type': 'line_section',
                'quantity': 0.0,
                'price_unit': 0.0,
                'credit': 0.0,
            }, {
                'display_type': 'product',
                'quantity': 5.0,
                'price_unit': 1.0,
                'credit': 5.0,
            }, {
                'display_type': 'line_section',
                'quantity': 0.0,
                'price_unit': 0.0,
                'credit': 0.0,
            }],
        }])

    def test_receive_signed_vendor_bill(self):
        """ Test a signed (P7M) sample e-invoice file from
        https://www.fatturapa.gov.it/export/documenti/fatturapa/v1.2/IT01234567890_FPR01.xml
        """
        self._assert_import_invoice('IT01234567890_FPR01.xml.p7m', [{
            'ref': '01234567890',
            'invoice_date': fields.Date.from_string('2014-12-18'),
            'amount_untaxed': 5.0,
            'amount_tax': 1.1,
            'invoice_line_ids': [{
                'quantity': 5.0,
                'price_unit': 1.0,
            }],
        }])

    def test_receive_wrongly_signed_vendor_bill(self):
        """
            Some of the invoices (i.e. those from Servizio Elettrico Nazionale, the
            ex-monopoly-of-energy company) have custom signatures that rely on an old
            OpenSSL implementation that breaks the current one that sees them as malformed,
            so we cannot read those files. Also, we couldn't find an alternative way to use
            OpenSSL to just get the same result without getting the error.

            A new fallback method has been added that reads the ASN1 file structure and
            takes the encoded pkcs7-data tag content out of it, regardless of the
            signature.

            Being a non-optimized pure Python implementation, it takes about 2x the time
            than the regular method, so it's better used as a fallback. We didn't use an
            existing library not to further pollute the dependencies space.

            task-3502910
        """
        with freeze_time('2019-01-01'):
            self._assert_import_invoice('IT09633951000_NpFwF.xml.p7m', [{
                'ref': '333333333333333',
                'invoice_date': fields.Date.from_string('2023-09-08'),
                'amount_untaxed': 39.54,
                'amount_tax': 3.95,
            }])

    def test_import_invoice_with_multiple_same_vat(self):
        (self.italian_partner_a | self.italian_partner_b).update({
            'vat': "IT06655971007",
            'l10n_it_codice_fiscale': '06655971007',
        })
        self._assert_import_invoice('IT01234567892_FPR01.xml', [{
            'partner_id': self.italian_partner_b.id,
        }], move_type="out_invoice")
        self.italian_partner_b.active = False
        self._assert_import_invoice('IT01234567892_FPR01.xml', [{
            'partner_id': self.italian_partner_a.id,
        }], move_type="out_invoice")

    def test_receive_bill_sequence(self):
        """ Ensure that the received bill gets assigned the right sequence. """
        def mock_commit(self):
            pass

        super_create = self.env.registry['account.move'].create
        created_moves = []

        def mock_create(self, vals_list):
            moves = super_create(self, vals_list)
            created_moves.extend(moves)
            return moves

        filename = 'IT01234567890_FPR02.xml'
        with (patch.object(self.proxy_user.__class__, '_decrypt_data', return_value=self.fake_test_content),
              patch.object(sql_db.Cursor, "commit", mock_commit),
              patch.object(self.env.registry['account.move'], 'create', mock_create),
              freeze_time('2019-01-01')):
            self.env['account.move'].with_company(self.company)._l10n_it_edi_process_downloads({
                '999999999': {
                    'filename': filename,
                    'file': self.fake_test_content,
                    'key': str(uuid.uuid4()),
                }},
                self.proxy_user,
            )
            self.assertEqual(len(created_moves), 1)

    def test_cron_receives_bill_in_preferred_journal(self):
        """ Ensure that the received bill is in the preferred journal set from the setting. """
        preferred_journal = self.company_data_2['default_journal_purchase'].copy()
        preferred_journal.default_account_id = False
        filename = 'IT01234567890_FPR02.xml'

        with self.assertRaisesRegex(ValidationError, "The Italian default purchase journal requires a default account."):
            self.company.l10n_it_edi_purchase_journal_id = preferred_journal

        preferred_journal.default_account_id = self.company_data_2['default_journal_purchase'].default_account_id.id
        # Retry setting the company's default purchase journal: no error since default_account_id is set
        self.company.l10n_it_edi_purchase_journal_id = preferred_journal

        with tools.file_open(f'{self.module}/tests/import_xmls/{filename}', mode='rb') as fd:
            fake_bill_content = fd.read()

        with (patch.object(self.env.registry['account_edi_proxy_client.user'], '_decrypt_data', return_value=fake_bill_content),
              freeze_time('2019-01-01')):
            self.env['account.move'].with_company(self.company)._l10n_it_edi_process_downloads({
                '999999999': {
                    'filename': filename,
                    'file': fake_bill_content,
                    'key': str(uuid.uuid4()),
                }},
                self.proxy_user,
            )

        imported_bill = self.env['account.move'].with_company(self.company).search([])
        self.assertEqual(len(imported_bill), 1)
        self.assertRecordValues(imported_bill.journal_id, [{
            'id': preferred_journal.id,
            'default_account_id': self.company_data_2['default_journal_purchase'].default_account_id.id,
        }])

    def test_cron_receives_bill_from_another_company(self):
        """ Ensure that when from one of your company, you bill the other, the
        import isn't impeded because of conflicts with the filename """
        other_company = self.company_data['company']
        filename = 'IT01234567890_FPR02.xml'
        def mock_commit(self):
            pass

        invoice = self.env['account.move'].with_company(other_company).create({
            'move_type': 'out_invoice',
            'invoice_line_ids': [
                Command.create({
                    'name': "something not price included",
                    'price_unit': 800.40,
                    'tax_ids': [Command.set(self.company_data['default_tax_sale'].ids)],
                }),
            ],
        })
        self.env['ir.attachment'].with_company(other_company).create({
            'name': filename,
            'raw': self.fake_test_content,
            'res_model': 'account.move',
            'res_id': invoice.id,
            'res_field': 'l10n_it_edi_attachment_file',
        })

        with (patch.object(self.proxy_user.__class__, '_decrypt_data', return_value=self.fake_test_content),
              patch.object(sql_db.Cursor, "commit", mock_commit)):
            self.env['account.move'].with_company(self.company)._l10n_it_edi_process_downloads(
                {'999999999': {
                    'filename': filename,
                    'file': self.fake_test_content,
                    'key': str(uuid.uuid4()),
                }},
                self.proxy_user,
            )

        attachment = self.env['ir.attachment'].search([
            ('name', '=', 'IT01234567890_FPR02.xml'),
            ('res_model', '=', 'account.move'),
            ('res_field', '=', 'l10n_it_edi_attachment_file'),
            ('company_id', '=', self.company.id),
        ])
        self.assertTrue(attachment)
        self.assertTrue(self.env['account.move'].browse(attachment.res_id))

    def test_receive_same_vendor_bill_twice(self):
        """ Test that the second time we are receiving an SdiCoop invoice, the second is discarded """

        # Our test content is not encrypted
        ProxyUser = self.env['account_edi_proxy_client.user']
        proxy_user = ProxyUser.create({
            'company_id': self.company.id,
            'proxy_type': 'l10n_it_edi',
            'id_client': str(uuid.uuid4()),
            'edi_identification': ProxyUser._get_proxy_identification(self.company, 'l10n_it_edi'),
            'private_key_id': self.private_key_id.id,
        })

        filename = 'IT01234567890_FPR02.xml'

        def mock_commit(self):
            pass

        with (patch.object(proxy_user.__class__, '_decrypt_data', return_value=self.fake_test_content),
              patch.object(sql_db.Cursor, "commit", mock_commit),
              tools.mute_logger("odoo.addons.l10n_it_edi.models.account_move")):
            for _dummy in range(2):
                processed = self.env['account.move']._l10n_it_edi_process_downloads({
                    '999999999': {
                        'filename': filename,
                        'file': self.fake_test_content,
                        'key': str(uuid.uuid4()),
                    }},
                    proxy_user,
                )
                # The Proxy ACK must be sent in both cases of import success and failure.
                self.assertEqual(processed['proxy_acks'], ['999999999'])

        # There should be one attachement with this filename
        attachments = self.env['ir.attachment'].search([
            ('name', '=', 'IT01234567890_FPR02.xml'),
            ('res_model', '=', 'account.move'),
            ('res_field', '=', 'l10n_it_edi_attachment_file'),
        ])
        self.assertEqual(len(attachments), 1)

    def test_receive_bill_with_global_discount(self):
        applied_xml = """
            <xpath expr="//FatturaElettronicaBody/DatiGenerali/DatiGeneraliDocumento" position="inside">
                <ScontoMaggiorazione>
                    <Tipo>SC</Tipo>
                    <Importo>2</Importo>
                </ScontoMaggiorazione>
            </xpath>
        """

        self._assert_import_invoice('IT01234567890_FPR01.xml', [{
            'invoice_date': fields.Date.from_string('2014-12-18'),
            'amount_untaxed': 5.0,
            'amount_tax': 1.1,
            'invoice_line_ids': [
                {
                    'quantity': 5.0,
                    'name': 'DESCRIZIONE DELLA FORNITURA',
                    'price_unit': 1.0,
                },
            ],
        }], applied_xml)

    def test_receive_bill_bank_account_01(self):
        """ When importing a vendor bill, if IBAN is present and the partner's found,
            the related bank account must be linked or created.
        """
        banksy_partner = self.env['res.partner'].create({
            'name': 'Banksy',
            'vat': 'IT00313371213',
            'l10n_it_codice_fiscale': '00313371213',
            'country_id': self.env.ref('base.it').id,
            'company_id': self.company.id,
            'invoice_edi_format': 'it_edi_xml',
            'is_company': False,
        })

        iban = "IT75F0200839061000400xxxxx"
        applied_xml = f"""
            <xpath expr="//FatturaElettronicaBody/DatiPagamento/DettaglioPagamento" position="inside">
                <IBAN>{iban}</IBAN>
            </xpath>
        """

        # Import but don't check yet
        invoice = self._assert_import_invoice('IT01234567889_FPR03.xml', [{}], applied_xml)

        # Check the created bank account
        partner_bank_account = self.env['res.partner.bank'].search([
            *self.env['res.company']._check_company_domain(self.company),
            ('account_number', '=', iban),
            ('partner_id', '=', banksy_partner.id),
        ])
        self.assertEqual(partner_bank_account, banksy_partner.bank_ids)
        self.assertFalse(partner_bank_account.allow_out_payment)

        # Check the bank account being correct and linked to the invoice
        self.assertRecordValues(invoice, [{
            'partner_id': banksy_partner.id,
            'partner_bank_id': partner_bank_account.id,
            'invoice_date_due': fields.Date.from_string('2015-02-28'),
        }])

        banksy_partner.invalidate_recordset(['is_company'])
        self.assertTrue(invoice.partner_id.is_company)

    def test_receive_bill_bank_account_02(self):
        """ When importing a vendor bill, if IBAN is present but the partner's not found, then:
            - Partner is created
            - Account is created
        """
        self.italian_partner_a.l10n_it_codice_fiscale = '00465840031'
        existing_partners = self.env['res.partner'].search([])
        iban = "IT75F0200839061000400xxxxx"
        invoice = self._assert_import_invoice('IT01234567889_FPR03.xml', [{}], f"""
            <xpath expr="//FatturaElettronicaBody/DatiPagamento/DettaglioPagamento" position="inside">
                <IBAN>{iban}</IBAN>
            </xpath>
        """)
        self.assertRecordValues(invoice.partner_id, [{
            'name': "SOCIETA' ALPHA SRL",
            'street': 'Viale Roma 543',
            'city': 'Sassari',
            'zip': '07100',
            'phone': '321321312',
            'email': 'vacinna@tulullu.it',
            'is_company': True,
        }])
        self.assertTrue(invoice.partner_id not in existing_partners)
        self.assertRecordValues(invoice.partner_bank_id, [{'account_number': iban, 'allow_out_payment': False}])

    def test_receive_bill_bank_account_03(self):
        """Partner retrieved by ``name``, not ``l10n_it_codice_fiscale``
           ``is_company`` must stay False, and not be updated to True
        """
        self.italian_partner_a.l10n_it_codice_fiscale = '00465840031'
        alpha_partner = self.env['res.partner'].create({
            'name': "SOCIETA' ALPHA SRL",
            'country_id': self.env.ref('base.it').id,
            'company_id': self.company.id,
            'invoice_edi_format': 'it_edi_xml',
            'is_company': False,
        })

        # Import but don't check yet
        self._assert_import_invoice('IT01234567889_FPR03.xml', [{}])

        alpha_partner.invalidate_recordset(['is_company'])
        self.assertFalse(alpha_partner.is_company)

    def test_import_due_date_on_issued_invoice(self):
        """ DataScadenzaPagamento and CodicePagamento populate
        invoice_date_due and payment_reference on out_invoice and
        in_refund too. The bank account block stays incoming-only
        and never writes the XML IBAN on res.partner.bank.
        """
        iban = "IT75F0200839061000400xxxxx"
        applied_xml = f"""
            <xpath expr="//FatturaElettronicaBody/DatiPagamento/DettaglioPagamento/DataScadenzaPagamento" position="replace">
                <DataScadenzaPagamento>2020-02-29</DataScadenzaPagamento>
            </xpath>
            <xpath expr="//FatturaElettronicaBody/DatiPagamento/DettaglioPagamento" position="inside">
                <CodicePagamento>REF-OUT-2020-001</CodicePagamento>
                <IBAN>{iban}</IBAN>
            </xpath>
        """
        self._assert_import_invoice(
            'IT01234567890_FPR01.xml',
            [{
                'invoice_date_due': fields.Date.from_string('2020-02-29'),
                'payment_reference': 'REF-OUT-2020-001',
            }],
            applied_xml,
            move_type='out_invoice',
        )
        # Bank account block stays incoming-only: no res.partner.bank
        # carries the XML IBAN.
        self.assertFalse(self.env['res.partner.bank'].search([
            ('account_number', '=', iban),
        ]))

    def test_receive_bill_with_multiple_discounts_in_line(self):
        applied_xml = """
            <xpath expr="//FatturaElettronicaBody/DatiBeniServizi/DettaglioLinee[1]" position="inside">
                <ScontoMaggiorazione>
                    <Tipo>SC</Tipo>
                    <Percentuale>50.00</Percentuale>
                </ScontoMaggiorazione>
                <ScontoMaggiorazione>
                    <Tipo>SC</Tipo>
                    <Percentuale>25.00</Percentuale>
                </ScontoMaggiorazione>
                <ScontoMaggiorazione>
                    <Tipo>SC</Tipo>
                    <Percentuale>20.00</Percentuale>
                </ScontoMaggiorazione>
            </xpath>

            <xpath expr="//FatturaElettronicaBody/DatiBeniServizi/DettaglioLinee[1]/PrezzoTotale" position="replace">
                <PrezzoTotale>1.50000000</PrezzoTotale>
            </xpath>
        """

        self._assert_import_invoice('IT01234567890_FPR01.xml', [{
            'invoice_date': fields.Date.from_string('2014-12-18'),
            'amount_untaxed': 1.5,
            'amount_tax': 0.33,
            'invoice_line_ids': [
                {
                    'quantity': 5.0,
                    'name': 'DESCRIZIONE DELLA FORNITURA',
                    'price_unit': 1.0,
                    'discount': 70.0,
                }
            ],
        }], applied_xml)

    def test_receive_two_bills_in_one_file(self):
        self._assert_import_invoice('IT01234567890_FPR03.xml', [
        {
            'invoice_date': fields.Date.from_string('2014-12-18'),
            'amount_tax': 5.5,
            'amount_untaxed': 25.0,
            'invoice_line_ids': [
                {
                    'name': 'DESCRIZIONE DELLA FORNITURA',
                    'price_unit': 1.0,
                    'quantity': 5.0,
                },
                {
                    'name': 'FORNITURE VARIE PER UFFICIO',
                    'price_unit': 2.0,
                    'quantity': 10.0,
                }
            ],
        },
        {
            'invoice_date': fields.Date.from_string('2014-12-20'),
            'amount_untaxed': 2000.0,
            'amount_tax': 440.0,
            'invoice_line_ids': [{
                'name': 'DESCRIZIONE DEL SERVIZIO',
                'price_unit': 2000.0,
                'quantity': 1.0,
            }],
        },
    ])

    def test_receive_bill_with_maggiorazione_discount(self):
        """ Test a sample e-invoice file with a discount of type MG (Maggiorazione). """
        applied_xml = """
            <xpath expr="//FatturaElettronicaBody/DatiBeniServizi/DettaglioLinee[1]" position="inside">
                <ScontoMaggiorazione>
                    <Tipo>MG</Tipo>
                    <Percentuale>10.00</Percentuale>
                </ScontoMaggiorazione>
            </xpath>

            <xpath expr="//FatturaElettronicaBody/DatiBeniServizi/DettaglioLinee[1]/PrezzoTotale" position="replace">
                <PrezzoTotale>5.50</PrezzoTotale>
            </xpath>
        """

        self._assert_import_invoice('IT01234567890_FPR01.xml', [{
            'invoice_date': fields.Date.from_string('2014-12-18'),
            'amount_untaxed': 5.5,
            'amount_tax': 1.21,
            'invoice_line_ids': [
                {
                    'quantity': 5.0,
                    'name': 'DESCRIZIONE DELLA FORNITURA',
                    'price_unit': 1.0,
                    'discount': -10.0,
                },
            ],
        }], applied_xml)

    def test_receive_bill_with_discount_rounding_issue(self):
        applied_xml = """
            <xpath expr="//FatturaElettronicaBody/DatiBeniServizi/DettaglioLinee[1]" position="inside">
                <ScontoMaggiorazione>
                    <Tipo>SC</Tipo>
                    <Percentuale>50.00</Percentuale>
                </ScontoMaggiorazione>
            </xpath>

            <xpath expr="//FatturaElettronicaBody/DatiBeniServizi/DettaglioLinee[1]/PrezzoUnitario" position="replace">
                <PrezzoUnitario>11.85</PrezzoUnitario>
            </xpath>
            <xpath expr="//FatturaElettronicaBody/DatiBeniServizi/DettaglioLinee[1]/Quantita" position="replace">
                <Quantita>3</Quantita>
            </xpath>
            <xpath expr="//FatturaElettronicaBody/DatiBeniServizi/DettaglioLinee[1]/PrezzoTotale" position="replace">
                <PrezzoTotale>17.78</PrezzoTotale>
            </xpath>
        """

        self._assert_import_invoice('IT01234567890_FPR01.xml', [{
            'invoice_date': fields.Date.from_string('2014-12-18'),
            'amount_untaxed': 17.78,
            'amount_tax': 3.91,
            'invoice_line_ids': [
                {
                    'quantity': 3.0,
                    'name': 'DESCRIZIONE DELLA FORNITURA',
                    'price_unit': 11.85,
                    'discount': 50.0,
                },
            ],
        }], applied_xml)

    def test_invoice_user_can_compute_is_self_invoice(self):
        """Ensure that a user having only group_account_invoice can compute field l10n_it_edi_is_self_invoice"""
        user = new_test_user(self.env, login='jag', groups='account.group_account_invoice')
        move = self.env['account.move'].create({'move_type': 'in_invoice'})
        move.with_user(user).read(['l10n_it_edi_is_self_invoice'])  # should not raise

    def test_l10n_it_payment_method_correctly_imported(self):
        self._assert_import_invoice('IT01234567890_FPR01.xml', [{
            'move_type': 'in_invoice',
            'invoice_date': fields.Date.from_string('2014-12-18'),
            'amount_untaxed': 5.0,
            'amount_tax': 1.1,
            'invoice_line_ids': [{
                'quantity': 5.0,
                'price_unit': 1.0,
                'debit': 5.0,
            }],
            'l10n_it_payment_method': 'MP01',
        }])

    def test_import_vendor_bill_with_ref_service_valid_tax(self):
        """Ensure that importing vendor bill with a referenced service product, with a service tax of 22% S
        only applies one tax on the product
        """
        sale_tax = self.env['account.tax'].search([('display_name', '=', '22%'), ('company_id', '=', self.company.id)])[0]
        supplier_tax = self.env['account.tax'].search([('display_name', '=', '22% S'), ('company_id', '=', self.company.id)])[0]
        self.env['product.product'].create({
            'name': 'Servizio tecnico',
            'default_code': 'abcdefgh',
            'type': 'service',
            'list_price': 150.0,
            'taxes_id': [Command.set([sale_tax.id])],
            'supplier_taxes_id': [Command.set([supplier_tax.id])],
        })

        self._assert_import_invoice('IT01234567889_FPR03.xml', [{
            'move_type': 'in_invoice',
            'invoice_date': fields.Date.from_string('2014-12-18'),
            'amount_untaxed': 25.0,
            'amount_tax': 5.5,
        }])

    def test_cron_import_bill_from_another_company_without_conflicts(self):
        """
        Ensure that in a multi-company environment, importing a bill containing products
        restricted to another company does not fail due to company inconsistencies.
        """
        test_product = self.env['product.product'].create({
            'name': 'Test Product',
            'default_code': 'TEST',
            'barcode': 'TEST',
            'standard_price': 75.0,
            'company_id': self.company_data['company'].id,
        })
        self.env['product.supplierinfo'].create({
            'product_id': test_product.id,
            'product_code': 'TEST',
            'partner_id': self.company_data_2["company"].partner_id.id,
        })

        applied_xml = """
            <xpath expr="//FatturaElettronicaBody/DatiBeniServizi/DettaglioLinee" position="after">
                <DettaglioLinee>
                    <NumeroLinea>2</NumeroLinea>
                    <CodiceArticolo>
                        <CodiceTipo>EAN</CodiceTipo>
                        <CodiceValore>TEST</CodiceValore>
                    </CodiceArticolo>
                    <Descrizione>[TEST] Test Product</Descrizione>
                    <Quantita>1.00</Quantita>
                    <PrezzoUnitario>5.00</PrezzoUnitario>
                    <PrezzoTotale>5.00</PrezzoTotale>
                    <AliquotaIVA>22.00</AliquotaIVA>
                </DettaglioLinee>
                <DettaglioLinee>
                    <NumeroLinea>3</NumeroLinea>
                    <CodiceArticolo>
                        <CodiceTipo>INTERNAL</CodiceTipo>
                        <CodiceValore>TEST</CodiceValore>
                    </CodiceArticolo>
                    <Descrizione>[TEST] Test Product</Descrizione>
                    <Quantita>2.00</Quantita>
                    <PrezzoUnitario>4.00</PrezzoUnitario>
                    <PrezzoTotale>8.00</PrezzoTotale>
                    <AliquotaIVA>22.00</AliquotaIVA>
                </DettaglioLinee>
            </xpath>
        """

        self._assert_import_invoice('IT01234567890_FPR01.xml', [{
            'move_type': 'in_invoice',
            'invoice_date': fields.Date.from_string('2014-12-18'),
            'amount_untaxed': 18.0,
            'amount_tax': 3.96,
            'invoice_line_ids': [
                {
                    "product_id": False,
                    'name': 'DESCRIZIONE DELLA FORNITURA',
                    'quantity': 5.0,
                    'price_unit': 1.0,
                    'debit': 5.0,
                },
                {
                    'product_id': False,
                    'name': '[TEST] Test Product',
                    'quantity': 1.0,
                    'price_unit': 5.0,
                    'debit': 5.0,
                },
                {
                    'product_id': False,
                    'name': '[TEST] Test Product',
                    'quantity': 2.0,
                    'price_unit': 4.0,
                    'debit': 8.0,
                },
            ],
        }], applied_xml)

    def test_receive_bill_with_attachment(self):
        """ Test that a bill with embedded attachments saves attachments and original xml file."""
        # must build file from scratch in order to check l10n_it_edi_attachment_file
        filename = 'IT01234567890_FPR02.xml'
        embedded_files = {
            'testfile.txt': ('TXT', 'This is a test file.'),
            'testfile2.txt': ('', 'Test file without FormatoAttachment.'),
            'testfile3.xml': ('XML', '<hello>How are you?</hello>'),
        }
        attachments_data = [
            f"""
                <Allegati>
                    <NomeAttachment>{filename}</NomeAttachment>
                    <FormatoAttachment>{extension}</FormatoAttachment>
                    <DescrizioneAttachment>An embedded attachment.</DescrizioneAttachment>
                    <Attachment>{b64encode(raw.encode()).decode()}</Attachment>
                </Allegati>
            """
            for filename, (extension, raw) in embedded_files.items()
        ]
        attachments_str = "\n".join(attachments_data)
        applied_xml = f'<xpath expr="//FatturaElettronicaBody/DatiGenerali" position="after">{attachments_str}</xpath>'

        tree = self.with_applied_xpath(
            etree.fromstring(self.fake_test_content.encode()),
            applied_xml
        )
        import_content = etree.tostring(tree)

        # import the xml
        move = self.env['account.move']._l10n_it_edi_process_downloads_attachments(
            self.company,
            [{
                'name': filename,
                'raw': import_content.decode(),
                'type': 'binary',
            }])

        # There should be one attachment with this filename, and it should match the original XML.
        # TODO: During bill import, we bypass the ORM to manually create the
        # `ir.attachment` with `res_field`. This requires cache invalidation,
        # (or commit) as the Binary field isn't updated automatically.
        # In `master`, we should fix the import by letting the Binary field
        # handle attachment creation on write.
        move.invalidate_recordset(fnames=['l10n_it_edi_attachment_file'])
        it_edi_attachment = self.env['ir.attachment'].search([
            ('name', '=', filename),
            ('res_model', '=', 'account.move'),
            ('res_field', '=', 'l10n_it_edi_attachment_file'),
        ])
        self.assertEqual(len(it_edi_attachment), 1)
        self.assertEqual(move.l10n_it_edi_attachment_name, 'IT01234567890_FPR02.xml')
        self.assertEqual(move.l10n_it_edi_attachment_file, b64encode(import_content))

        # ensure that the embedded files are imported correctly
        for filename, (extension, raw) in embedded_files.items():
            chatter_attachments = self.env['ir.attachment'].search([
                ('name', '=', filename),
                ('res_model', '=', 'account.move'),
                ('res_id', '=', move.id),
                ('res_field', '=', False),
            ])
            self.assertEqual(len(chatter_attachments), 1)
            self.assertEqual(chatter_attachments.raw.decode(), raw)

    def test_transaction_id_several_bills_in_fewer_files(self):
        invoices_data = {}
        transaction_ids = [f'{1:0>11}', f'{2:0>11}']
        for filename, transaction_id in zip(('IT01234567890_FPR03.xml', 'IT01234567890_FPR02.xml.p7m'), transaction_ids):
            invoices_data.update({
                transaction_id: {
                    'filename': filename,
                    'file': '',
                    'key': str(uuid.uuid4()),
            }})

        # import the xml
        path = f'{self.module}/tests/import_xmls/IT01234567890_FPR03.xml'
        with tools.file_open(path, mode='rb') as fd:
            import_content = fd.read()

        def mock_commit(self):
            pass

        super_create = self.env.registry['account.move'].create
        created_moves = []

        def mock_create(self, vals_list):
            moves = super_create(self, vals_list)
            created_moves.extend(moves)
            return moves

        with (patch.object(self.proxy_user.__class__, '_decrypt_data', return_value=import_content),
              patch.object(sql_db.Cursor, "commit", mock_commit),
              patch.object(self.env.registry['account.move'], 'create', mock_create),
              freeze_time('2019-01-01')):
            self.env['account.move'].with_company(self.company)._l10n_it_edi_process_downloads(
                invoices_data,
                self.proxy_user,
            )
        moves = self.env['account.move']
        for m in created_moves:
            moves |= m
        self.assertRecordValues(moves, [
            {'l10n_it_edi_attachment_name': 'IT01234567890_FPR03.xml',
            'l10n_it_edi_transaction': f'{1:0>11}',
            },
            {'l10n_it_edi_attachment_name': 'IT01234567890_FPR02.xml.p7m',
            'l10n_it_edi_transaction': f'{2:0>11}',
            },
            {'l10n_it_edi_attachment_name': 'IT01234567890_FPR03_2.xml',
            'l10n_it_edi_transaction': f'{1:0>11}',
            },
            {'l10n_it_edi_attachment_name': 'IT01234567890_FPR02.xml_2.p7m',
            'l10n_it_edi_transaction': f'{2:0>11}',
            },
        ])

    def test_receive_multiple_body_bill_xml_and_p7m(self):
        """ Test the correct import of an XML file containing multiple bodies."""
        single_body_data = {
            'invoice_date': fields.Date.from_string('2026-03-26'),
            'ref': 'INV/2026/00010',
            'amount_untaxed': 750.0,
            'amount_tax': 165.0,
            'amount_total': 915.0,
            'invoice_line_ids': [
                {
                    'name': '[DESK0006] Customizable Desk (Black, Custom) 160x80cm, with large legs',
                    'quantity': 1.0,
                    'price_unit': 750.0,
                },
            ],
        }
        # Check xml file
        self._assert_import_invoice('IT01654010345_10099.xml', [single_body_data] * 3)
        # Check p7m file
        self._assert_import_invoice('IT01654010345_10099.xml.p7m', [single_body_data] * 3)

    def test_import_simplified_invoice_zero_base(self):
        """Test the import of a xml bill where the total amount equals the tax amount (Importo == Imposta)."""

        self._assert_import_invoice('IT01234567890_FPR05.xml', [{
            'move_type': 'in_refund',
            'amount_untaxed': 0.0,
            'invoice_line_ids': [
                {
                    'name': 'IVA ANNO PRECEDENTE',
                    'quantity': 1.0,
                    'price_unit': 9.20,
                },
                {
                    'name': 'TOTALE IMPORTO IN ADDEBITO',
                    'quantity': 1.0,
                    'price_unit': -9.20,
                }
            ],
        }])
