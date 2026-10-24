# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAccountBaseDocumentLayout(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_partner = cls.env.company.partner_id
        cls.company_partner.bank_ids.unlink()
        cls.bank = cls.env['res.partner.bank'].create({
            'acc_number': 'BE71096123456769',
            'partner_id': cls.company_partner.id,
            'company_id': cls.env.company.id,
        })
        cls.acc_number = cls.bank.acc_number

    def test_account_number_can_be_cleared(self):
        layout = self.env['base.document.layout'].create({})
        self.assertEqual(layout.account_number, self.acc_number)

        layout.account_number = ''
        layout.flush_recordset()
        layout.invalidate_recordset()

        self.assertFalse(layout.account_number)
        self.assertFalse(self.bank.active)
        self.assertEqual(self.bank.acc_number, self.acc_number)

    def test_account_number_can_be_edited(self):
        layout = self.env['base.document.layout'].create({})
        layout.account_number = '0123456789'
        layout.flush_recordset()
        layout.invalidate_recordset()

        self.assertEqual(layout.account_number, '0123456789')
        self.assertEqual(self.bank.acc_number, '0123456789')
        self.assertTrue(self.bank.active)

    def test_account_number_cleared_without_bank_account(self):
        self.bank.action_archive()
        layout = self.env['base.document.layout'].create({})
        layout.account_number = ''
        layout.flush_recordset()
        layout.invalidate_recordset()

        self.assertFalse(layout.account_number)
