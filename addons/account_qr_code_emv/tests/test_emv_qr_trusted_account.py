# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestEmvQrTrustedAccount(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.bank_account = cls.env['res.partner.bank'].create({
            'account_number': '123456789',
            'partner_id': cls.company_data['company'].partner_id.id,
            'proxy_value': '0123456789',
            'allow_out_payment': True,
        })

    def test_trusted_account_locks_qr_settings(self):
        self.assertTrue(self.bank_account.allow_out_payment)
        with self.assertRaisesRegex(UserError, "payment settings"):
            self.bank_account.proxy_value = '9876543210'

        # Re-writing the same value (e.g. force_save in the form view) and editing non-sensitive fields is allowed.
        self.bank_account.write({'proxy_value': '0123456789', 'proxy_type': 'none', 'include_reference': True})
        self.assertTrue(self.bank_account.include_reference)

    def test_untrusted_account_allows_qr_settings_change(self):
        self.bank_account.allow_out_payment = False
        self.bank_account.proxy_value = '9876543210'
        self.assertEqual(self.bank_account.proxy_value, '9876543210')

    def test_untrusting_account_allows_qr_settings_change(self):
        self.bank_account.write({'allow_out_payment': False, 'proxy_value': '9876543210'})
        self.assertEqual(self.bank_account.proxy_value, '9876543210')
        self.assertFalse(self.bank_account.allow_out_payment)
