from odoo.tests import tagged

from .test_xml_ubl_tr_common import TestUBLTRCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestAccountMoveSend(TestUBLTRCommon):

    def test_send_email_with_recipient_bank(self):
        """
        invoice xml generation should work when company has bank account with bank information
        in order to send email with invoice xml to recipient's bank
        """
        bank = self.env['res.bank'].create({
            'name': 'Test Bank',
            'bic': 'TESTTRISXXX',
        })
        self.company_data['company'].bank_ids.bank_id = bank.id

        self.assertTrue(self._generate_invoice_xml(self.einvoice_partner), "XML generation failed")
