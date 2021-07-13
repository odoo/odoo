# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import logging
from collections import namedtuple
from unittest.mock import patch
import freezegun

from odoo import tools
from odoo.addons.account_edi.tests.common import AccountEdiTestCommon
from odoo.addons.l10n_it_edi.tools.remove_signature import remove_signature

_logger = logging.getLogger(__name__)


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
        cls.company.l10n_it_codice_fiscale = 'IT01234560157'

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
        with freezegun.freeze_time('2020-04-06'):
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
