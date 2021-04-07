# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from unittest.mock import patch
from collections import namedtuple

from odoo.modules.module import get_module_resource
from odoo.tests import common
from odoo import tools

_logger = logging.getLogger(__name__)


class MailServerTests(common.TransactionCase):
    """ Main test class for the l10n_it_edi ir_mail_server class """

    test_content = """<?xml version="1.0" encoding="UTF-8"?>
<p:FatturaElettronica versione="FPR12" xmlns:ds="http://www.w3.org/2000/09/xmldsig#" 
xmlns:p="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2" 
xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
xsi:schemaLocation="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2 http://www.fatturapa.gov.it/export/fatturazione/sdi/fatturapa/v1.2/Schema_del_file_xml_FatturaPA_versione_1.2.xsd">
  <FatturaElettronicaHeader></FatturaElettronicaHeader>
  <FatturaElettronicaBody>
    <DatiGenerali>
      <DatiGeneraliDocumento>
        <TipoDocumento>TD02</TipoDocumento>
      </DatiGeneraliDocumento>
    </DatiGenerali>
  </FatturaElettronicaBody>
</p:FatturaElettronica>"""

    def setUp(self):
        """ Setup the test class with a PEC mail server and a fake fatturaPA content """
        super().setUp()
        self.env.company.l10n_it_codice_fiscale = "IT01234560157"
        self.invoice_filename = "IT01234567890_FPR01.xml"
        self.invoice_content = self._get_test_content(self.invoice_filename)
        self.invoice_ref = "01234567890"
        self.server = self.env["fetchmail.server"].create({
            "name": "test_server",
            "server_type": "imap",
            "l10n_it_is_pec": True
        })

    def _create_invoice(self, content, filename):
        """ Create an invoice from given attachment content """
        with patch.object(self.server._cr, "commit", return_value=None):
            return self.server._create_invoice_from_mail(content, filename, "fake@address.be")

    def _get_test_content(self, filename):
        """ Get the content of a test file inside this module """
        path = get_module_resource("l10n_it_edi", "tests", "expected_xmls", filename)
        with tools.file_open(path, mode="rb") as test_file:
            return test_file.read()

    def test_attachment_invoice_already_received(self):
        """ Test that the second time we are receiving a PEC mail with the same attachment, the second is discarded """
        content = self.test_content.encode("utf-8")
        for result in [True, False]:
            self.assertEqual(result, bool(self._create_invoice(content, "AZ123123123_12345.xml")))

    def test_receive_vendor_bill(self):
        """ Test a sample e-invoice file from https://www.fatturapa.gov.it/export/documenti/fatturapa/v1.2/IT01234567890_FPR01.xml """
        # Simulate the reception of an einvoice
        invoices = self._create_invoice(self.invoice_content, self.invoice_filename)
        self.assertTrue(bool(invoices))

    def _test_receipt(self, receipt_type, source_state, destination_state):
        """ Test a receipt from the ones in the module's test files """

        # Simulate the 'sent' state of the move, even if we didn't actually send an email in this test
        move = self.env["account.move"].search([("ref", "=", self.invoice_ref)])
        move.l10n_it_send_state = source_state

        # Create the attachment and the account.edi.document just as if we sent the email
        attachment = self.env["ir.attachment"].search([("name", "=", self.invoice_filename)])
        edi_document = self.env["account.edi.document"].create({
            "edi_format_id": self.env.ref("l10n_it_edi.edi_fatturaPA").id,
            "move_id": move.id,
            "state": "sent",
            "attachment_id": attachment.id
        })

        # Create a fake receipt from the test file
        receipt_filename = "IT01234567890_FPR01_%s_001.xml" % receipt_type
        receipt_content = self._get_test_content(receipt_filename).decode("utf-8")

        create_mail_attachment = namedtuple('Attachment', ('fname', 'content', 'info'))
        receipt_mail_attachment = create_mail_attachment(receipt_filename, receipt_content, {})

        # Simulate the arraival of the receipt
        with patch.object(self.server._cr, "commit", return_value=None):
            self.server._message_receipt_invoice(receipt_type, receipt_mail_attachment)

        # Check the Destination state of the edi_document
        self.assertTrue(destination_state, edi_document.state)

    def test_ricevuta_consegna(self):
        """ Test a receipt adapted from https://www.fatturapa.gov.it/export/documenti/messaggi/v1.0/IT01234567890_11111_RC_001.xml """

        # Prepare the invoice in the system
        self.test_receive_vendor_bill()

        # Simulate the receipt arrival
        self._test_receipt("RC", "sent", "delivered")

    def test_decorrenza_termini(self):
        """ Test a receipt adapted from https://www.fatturapa.gov.it/export/documenti/messaggi/v1.0/IT01234567890_11111_DT_001.xml """

        # Prepare the invoice in the system
        self.test_receive_vendor_bill()

        # Simulate the receipt arrival
        self._test_receipt("DT", "delivered", "delivered_expired")
