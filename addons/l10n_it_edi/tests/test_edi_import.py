# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import uuid
from unittest.mock import patch

from odoo import fields, sql_db, tools
from odoo.tests import tagged
from odoo.addons.l10n_it_edi.tests.common import TestItEdi


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

    def test_receive_vendor_bill(self):
        """ Test a sample e-invoice file from
        https://www.fatturapa.gov.it/export/documenti/fatturapa/v1.2/IT01234567890_FPR01.xml
        """
        self._assert_import_invoice('IT01234567890_FPR01.xml', [{
            'invoice_date': fields.Date.from_string('2014-12-18'),
            'amount_untaxed': 5.0,
            'amount_tax': 1.1,
            'invoice_line_ids': [{
                'quantity': 5.0,
                'price_unit': 1.0,
            }],
        }])

    def test_receive_signed_vendor_bill(self):
        """ Test a signed (P7M) sample e-invoice file from
        https://www.fatturapa.gov.it/export/documenti/fatturapa/v1.2/IT01234567890_FPR01.xml
        """
        self._assert_import_invoice('IT01234567890_FPR01.xml.p7m', [{
            'name': 'BILL/2014/12/0001',
            'ref': '01234567890',
            'invoice_date': fields.Date.from_string('2014-12-18'),
            'amount_untaxed': 5.0,
            'amount_tax': 1.1,
            'invoice_line_ids': [{
                'quantity': 5.0,
                'price_unit': 1.0,
            }],
        }])

    def test_receive_same_vendor_bill_twice(self):
        """ Test that the second time we are receiving an SdiCoop invoice, the second is discarded """

        # Our test content is not encrypted
        ProxyUser = self.env['account_edi_proxy_client.user']
        proxy_user = ProxyUser.create({
            'company_id': self.company.id,
            'proxy_type': 'l10n_it_edi',
            'id_client': str(uuid.uuid4()),
            'edi_identification': ProxyUser._get_proxy_identification(self.company, 'l10n_it_edi'),
            'private_key': str(uuid.uuid4()),
        })

        filename = 'IT01234567890_FPR02.xml'

        def mock_commit(self):
            pass

        with (patch.object(proxy_user.__class__, '_decrypt_data', return_value=self.fake_test_content),
              patch.object(sql_db.Cursor, "commit", mock_commit),
              tools.mute_logger("odoo.addons.l10n_it_edi.models.account_move")):
            for dummy in range(2):
                self.env['account.move']._l10n_it_edi_process_downloads({
                    '999999999': {
                        'filename': filename,
                        'file': self.fake_test_content,
                        'key': str(uuid.uuid4()),
                    }},
                    proxy_user,
                )

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
