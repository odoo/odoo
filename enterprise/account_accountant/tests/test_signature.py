import base64

from odoo import Command
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestInvoiceSignature(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if cls.env.ref('base.module_sign').state != 'installed':
            cls.skipTest(cls, "`sign` module not installed")

        cls.env.company.sign_invoice = True

        cls.signature_fake_1 = base64.b64encode(b"fake_signature_1")
        cls.signature_fake_2 = base64.b64encode(b"fake_signature_2")

        cls.user.sign_signature = cls.signature_fake_1
        cls.another_user = cls.env['res.users'].create({
            'name': 'another accountant',
            'login': 'another_accountant',
            'password': 'another_accountant',
            'groups_id': [
                Command.set(cls.env.ref('account.group_account_user').ids),
            ],
            'sign_signature': cls.signature_fake_2,
        })

        cls.invoice = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner_a.id,
            'journal_id': cls.company_data['default_journal_sale'].id,
            'invoice_line_ids': [
                Command.create({
                    'product_id': cls.product_a.id,
                    'quantity': 1,
                    'price_unit': 1,
                })
            ]
        })

    def test_draft_invoice_shouldnt_have_signature(self):
        self.assertEqual(self.invoice.state, 'draft')
        self.assertFalse(self.invoice.show_signature_area, "the signature area shouldn't appear on a draft invoice")

    def test_posted_invoice_should_have_signature(self):
        self.invoice.action_post()
        self.assertTrue(self.invoice.show_signature_area,
                        "the signature area should appear on posted invoice when the `sign_invoice` settings is True")

    def test_invoice_from_company_without_signature_settings_shouldnt_have_signature(self):
        self.env.company.sign_invoice = False
        self.invoice.action_post()
        self.assertFalse(self.invoice.show_signature_area,
                         "the signature area shouldn't appear when the `sign_invoice` settings is False")

    def test_invoice_signing_user_should_be_the_user_that_posted_it(self):
        self.assertFalse(self.invoice.signing_user,
                         "invoice that weren't created by automated action shouldn't have a signing user")
        self.assertEqual(self.invoice.signature, False, "There shouldn't be any signature if there isn't a signing user")
        self.invoice.action_post()
        self.assertEqual(self.invoice.signing_user, self.user, "The signing user should be the user that posted the invoice")
        self.assertEqual(self.invoice.signature, self.signature_fake_1, "The signature should be from `self.user`")

        self.invoice.button_draft()
        self.invoice.with_user(self.another_user).action_post()
        self.assertEqual(self.invoice.signing_user, self.another_user,
                         "The signing user should be the user that posted the invoice")
        self.assertEqual(self.invoice.signature, self.signature_fake_2, "The signature should be from `self.another_user`")

    def test_invoice_signing_user_should_be_reprensative_user_if_there_is_one(self):
        self.env.company.signing_user = self.user  # set the representative user of the company
        invoice = self.invoice.with_user(self.another_user)
        invoice.action_post()
        self.assertEqual(invoice.signing_user, self.user, "The signing user should be the representative person set in the settings")
        self.assertEqual(invoice.signature, self.signature_fake_1, "The signature should be from `self.another_user`, the representative user")

    def test_setting_representative_user_shouldnt_change_signer_of_already_posted_invoice(self):
        # Note: Changing this behavior might not be a good idea as having all account.move updated at once
        # would be very costly
        self.invoice.action_post()
        self.env.company.signing_user = self.another_user  # set the representative user of the company
        self.assertEqual(self.invoice.signing_user, self.user,
                         "The signing user should be the one that posted the invoice even if a representative has been added later on")
        self.assertEqual(self.invoice.signature, self.signature_fake_1, "The signature should be from `self.user`")
