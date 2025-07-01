# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import uuid
from freezegun import freeze_time
from unittest.mock import patch

from odoo import fields, sql_db, tools, Command
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
            <ProgressivoInvio>TWICE_TEST</ProgressivoInvio>
          </DatiTrasmissione>
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

    # -----------------------------
    # Vendor bills
    # -----------------------------

    def test_receive_invalid_xml(self):
        xml_decode = self.env['ir.attachment']._decode_edi_l10n_it_edi
        with tools.mute_logger("odoo.addons.l10n_it_edi.models.ir_attachment"):
            self.assertEqual([], xml_decode("none.xml", None))
            self.assertEqual([], xml_decode("empty.xml", ""))
            self.assertEqual([], xml_decode("invalid.xml", "invalid"))
            self.assertEqual([], xml_decode("invalid2.xml", "<invalid/>"))

    def test_receive_vendor_bill(self):
        """ Test a sample e-invoice file from
        https://www.fatturapa.gov.it/export/documenti/fatturapa/v1.2/IT01234567890_FPR01.xml
        """
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
        }])

    def test_receive_vendor_bill_sconto_maggiorazione(self):
        """ Test a sample e-invoice file with
        ScontoMaggiorazione on lines
        """
        self._assert_import_invoice('IT01234567890_DISC1.xml', [{
            'move_type': 'in_invoice',
            'invoice_date': fields.Date.from_string('2014-12-18'),
            'amount_untaxed': 28.75,
            'amount_tax': 6.32,
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
                'amount_untaxed': 57.54,
                'amount_tax': 3.95,
            }])

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
            'datas': self.fake_test_content,
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
            for dummy in range(2):
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
        invoices = self.env['account.move'].search([('payment_reference', '=', 'TWICE_TEST')])
        self.assertEqual(len(invoices), 1)

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
            'amount_untaxed': 3.0,
            'amount_tax': 1.1,
            'invoice_line_ids': [
                {
                    'quantity': 5.0,
                    'name': 'DESCRIZIONE DELLA FORNITURA',
                    'price_unit': 1.0,
                },
                {
                    'quantity': 1.0,
                    'name': 'SCONTO',
                    'price_unit': -2,
                }
            ],
        }], applied_xml)

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

    def test_invoice_user_can_compute_is_self_invoice(self):
        """Ensure that a user having only group_account_invoice can compute field l10n_it_edi_is_self_invoice"""
        user = new_test_user(self.env, login='jag', groups='account.group_account_invoice')
        move = self.env['account.move'].create({'move_type': 'in_invoice'})
        move.with_user(user).read(['l10n_it_edi_is_self_invoice'])  # should not raise
