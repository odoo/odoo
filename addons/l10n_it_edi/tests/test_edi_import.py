# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import logging
from freezegun import freeze_time
from lxml import etree

from odoo import tools
from odoo.tests import tagged
from odoo.addons.l10n_it_edi.tests.common import TestItEdi, patch_proxy_user
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
        super().setUpClass(chart_template_ref='l10n_it.l10n_it_chart_template_generic',
                           edi_format_ref='l10n_it_edi.edi_fatturaPA')

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

    @patch_proxy_user
    def test_receive_same_vendor_bill_twice(self):
        """ Test that the second time we are receiving an SdiCoop invoice, the second is discarded """

        # The make_request function is called twice when running the _cron_receive_fattura_pa
        # first to the /in/RicezioneInvoice endpoint (to find new incoming invoices)
        # second to the /api/l10n_it_edi/1/ack to acknowledge the invoices have been recieved
        content = self.fake_test_content.encode()
        fake_responses = [
            # Response of the format id_transaction: fattura dict
            {'9999999999': {'filename': self.invoice_filename2, 'key': '123', 'file': content}},
            # The response from the _make_request for the ack can be None
            None,
        ] * 2 # Since the cron is run twice, and we want the fake results both times
        self.proxy_user._make_request.side_effect = fake_responses
        # When calling the decrypt function, the file we're accessing is already decrypted, just return the file
        self.proxy_user._decrypt_data.side_effect = lambda file, _key: file
        # In order for the cron function to progress to the point that it imports, we cannot be in demo mode
        self.proxy_user._get_demo_state.return_value = 'unit_test'

        self.edi_format.with_context({'test_skip_commit': True})._cron_receive_fattura_pa()
        # There should be one attachement with this filename
        attachment = self.env['ir.attachment'].search([('name', '=', self.invoice_filename2)])
        self.assertEqual(len(attachment), 1)
        invoice = self.env['account.move'].search([('payment_reference', '=', 'TWICE_TEST')])
        self.assertEqual(len(invoice), 1)
