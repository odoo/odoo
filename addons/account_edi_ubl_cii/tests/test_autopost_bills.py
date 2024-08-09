import base64
from datetime import datetime

from odoo import fields
from odoo.tests import tagged
from odoo.tools import file_open

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestAutoPostBills(AccountTestInvoicingCommon):

    def import_facturx(self, filename='facturx_out_invoice.xml'):
        self.env.cr._now = datetime.now()  # reset transaction's NOW, otherwise all move will have the same create_date
        with file_open(f"account_edi_ubl_cii/tests/test_files/{filename}", 'rb', filter_ext=('.xml',)) as file:
            attachment = self.env['ir.attachment'].create({
                'name': 'test_file.xml',
                'datas': base64.encodebytes(file.read()),
            })
            return self.company_data['default_journal_purchase'].with_context(disable_abnormal_invoice_detection=False)._create_document_from_attachment(attachment.id)

    def assert_wizard(self, post_result, expected_nb_bills):
        self.assertEqual(post_result.get('res_model'), 'account.autopost.bills.wizard')
        wizard = self.env[post_result.get('res_model')].browse(post_result.get('res_id'))
        self.assertEqual(wizard.nb_unmodified_bills, expected_nb_bills)
        return wizard

    def test_autopost_bills(self):
        """
        When invoices from a same vendor are input thrice in a row without changing anything,
        so for invoice coming from OCR or e-Invoicing, we should show a banner to the user
        and allow him to automatically post future invoices from this vendor.
        - If there is a significant difference (see abnormal_amount), don't autopost and show the banner !
        - Not applicable to hashed journals
        """
        # Create 1st bill ever for this partner, should NOT show popup
        move = self.import_facturx()
        autopost_bills_wizard = move.action_post()
        self.assertFalse(autopost_bills_wizard)
        self.assertFalse(move.is_manually_modified)

        # Create 2nd bill without changes for this partner, should NOT show popup
        move = self.import_facturx()
        autopost_bills_wizard = move.action_post()
        self.assertFalse(autopost_bills_wizard)
        self.assertFalse(move.is_manually_modified)

        # Create 3rd bill without changes for this partner, should show popup on posting
        move = self.import_facturx()
        autopost_bills_wizard = move.action_post()
        self.assertFalse(move.is_manually_modified)
        wizard = self.assert_wizard(autopost_bills_wizard, 3)
        wizard.action_ask_later()  # Nothing changes, we should still show the popup

        # Create 4th bill without changes for this partner, should show popup on posting
        move = self.import_facturx()
        autopost_bills_wizard = move.action_post()
        self.assertFalse(move.is_manually_modified)
        wizard = self.assert_wizard(autopost_bills_wizard, 4)
        wizard.action_ask_later()  # Nothing changes, we should still show the popup

        # Create 5th bill with changes, should NOT show popup on posting
        move = self.import_facturx()
        move.invoice_date_due = fields.Date.today()
        autopost_bills_wizard = move.action_post()
        self.assertFalse(autopost_bills_wizard)
        self.assertTrue(move.is_manually_modified)

        # Create again 3 bills without any changes
        for _ in range(3):
            move = self.import_facturx()
            autopost_bills_wizard = move.action_post()
        wizard = self.assert_wizard(autopost_bills_wizard, 3)
        wizard.action_automate_partner()

        # Create 4th bill without changes with automation enabled => should automatically post, no popup
        move = self.import_facturx()
        self.assertEqual(move.state, 'posted')

        # Reset
        move.partner_id.autopost_bills = 'ask'

        # Create 5th bill without changes, should show popup on posting
        move = self.import_facturx()
        autopost_bills_wizard = move.action_post()
        wizard = self.assert_wizard(autopost_bills_wizard, 5)
        wizard.action_never_automate_partner()

        # Create 6th bill without changes, should not show popup, and move should stay in draft
        move = self.import_facturx()
        self.assertEqual(move.state, 'draft')
        autopost_bills_wizard = move.action_post()
        self.assertFalse(autopost_bills_wizard)

        # Reset
        move.partner_id.autopost_bills = 'ask'

        # Create 7th bill without changes, should show popup on posting
        move = self.import_facturx()
        autopost_bills_wizard = move.action_post()
        wizard = self.assert_wizard(autopost_bills_wizard, 7)
        wizard.action_ask_later()

        # Deactivate the feature fully from the settings
        # => Should never show popup, nor autopost (even if partner is on 'always')
        move.company_id.autopost_bills = False
        move.partner_id.autopost_bills = 'always'
        move = self.import_facturx()
        self.assertEqual(move.state, 'draft')
        autopost_bills_wizard = move.action_post()
        self.assertFalse(autopost_bills_wizard)

        # Reset
        move.company_id.autopost_bills = True
        move.partner_id.autopost_bills = 'always'

        # If there is a significant difference (see abnormal_amount), don't autopost even if 'always' is set
        for _ in range(10):  # See test_unexpected_invoice
            move = self.import_facturx()  # automatically posted
            self.assertEqual(move.state, "posted")

        move = self.import_facturx(filename='facturx_out_invoice_abnormal.xml')  # amounts * 100 here, a bit abnormal...
        self.assertEqual(move.state, "draft")  # even if partner's autopost is always
        res = move.action_post()
        self.assertEqual(res.get('res_model'), 'validate.account.move')
        wizard = self.env[res.get('res_model')].browse(res.get('res_id'))
        self.assertEqual(wizard.move_ids, move)

        # Not applicable to hashed journals
        self.company_data['default_journal_purchase'].restrict_mode_hash_table = True
        move = self.import_facturx()
        self.assertEqual(move.state, "draft")
        res = move.action_post()
        self.assertFalse(res)
