from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.l10n_tr_edi.tests.test_xml_ubl_tr_common import TestUBLTRCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestCancel(TestUBLTRCommon):

    def test_an_export_cannot_be_cancelled(self):
        # An export is sent as an e-Invoice, even to a foreign customer whose GİB status is e-Archive.
        export = self._generate_invoice(self.earchive_partner, l10n_tr_is_export_invoice=True)
        export._l10n_tr_edi_set_document_state('sent', False)
        self.assertEqual(export.l10n_tr_edi_document_ids.document_type, 'einvoice')
        self.assertFalse(export.l10n_tr_edi_can_cancel)
        with self.assertRaises(UserError):
            export._l10n_tr_edi_cancel()

    def test_an_earchive_stays_one_when_its_customer_changes(self):
        earchive = self._generate_invoice(self.earchive_partner)
        earchive._l10n_tr_edi_set_document_state('sent', False)
        # The customer becomes an e-Invoice user: the invoice sent as an e-Archive stays one, and cancellable.
        self.earchive_partner.l10n_tr_edi_customer_status = 'einvoice'
        self.assertTrue(earchive.l10n_tr_edi_can_cancel)
        # Until the GİB rejects it: the rejection is recorded on that e-Archive.
        earchive._l10n_tr_edi_set_document_state('error', False)
        self.assertRecordValues(earchive.l10n_tr_edi_document_ids, [{'document_type': 'earchive', 'state': 'error'}])
        self.assertFalse(earchive.l10n_tr_edi_can_cancel)
