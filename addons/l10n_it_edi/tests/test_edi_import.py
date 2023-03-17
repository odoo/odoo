# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import logging
from freezegun import freeze_time
from lxml import etree
from unittest.mock import MagicMock, patch

from odoo import sql_db
from odoo.tests import tagged
from odoo.addons.l10n_it_edi.tests.common import TestItEdi
from odoo.addons.l10n_it_edi.tools.remove_signature import remove_signature

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

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

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

        cls.test_invoice_xmls = {k: cls._get_test_file_content(v) for k, v in [
            ('normal_1', 'IT01234567890_FPR01.xml'),
            ('signed', 'IT01234567890_FPR01.xml.p7m'),
        ]}

    def mock_commit(self):
        pass

    # -----------------------------
    #
    # Vendor bills
    #
    # -----------------------------

    def test_receive_vendor_bill(self):
        """ Test a sample e-invoice file from https://www.fatturapa.gov.it/export/documenti/fatturapa/v1.2/IT01234567890_FPR01.xml """
        content = etree.fromstring(self.invoice_content)
        invoices = self.edi_format._create_invoice_from_xml_tree(self.invoice_filename2, content)
        self.assertTrue(bool(invoices))

    def test_receive_signed_vendor_bill(self):
        """ Test a signed (P7M) sample e-invoice file from https://www.fatturapa.gov.it/export/documenti/fatturapa/v1.2/IT01234567890_FPR01.xml """
        with freeze_time('2020-04-06'):
            content = etree.fromstring(remove_signature(self.signed_invoice_content))
            invoices = self.edi_format._create_invoice_from_xml_tree(self.signed_invoice_filename, content)

            self.assertRecordValues(invoices, [{
                'company_id': self.company.id,
                'name': 'BILL/2014/12/0001',
                'invoice_date': datetime.date(2014, 12, 18),
                'ref': '01234567890',
            }])

    def test_receive_same_vendor_bill_twice(self):
        """ Test that the second time we are receiving an SdiCoop invoice, the second is discarded """

        fattura_pa = self.env.ref('l10n_it_edi.edi_fatturaPA')
        content = self.fake_test_content.encode()

        # Our test content is not encrypted
        proxy_user = MagicMock()
        proxy_user.company_id = self.company
        proxy_user._decrypt_data.return_value = content

        with patch.object(sql_db.Cursor, "commit", self.mock_commit):
            for dummy in range(2):
                fattura_pa._save_incoming_attachment_fattura_pa(
                    proxy_user=proxy_user,
                    id_transaction='9999999999',
                    filename=self.invoice_filename2,
                    content=content,
                    key=None)

        # There should be one attachement with this filename
        attachments = self.env['ir.attachment'].search([('name', '=', self.invoice_filename2)])
        self.assertEqual(len(attachments), 1)
        invoices = self.env['account.move'].search([('payment_reference', '=', 'TWICE_TEST')])
        self.assertEqual(len(invoices), 1)
