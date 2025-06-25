from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestMergePartner(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.Partner = cls.env['res.partner']
        cls.Bank = cls.env['res.partner.bank']
        cls.Payment = cls.env['account.payment']

        # Create partners
        cls.partner1 = cls.Partner.create({'name': 'Partner 1', 'email': 'partner1@example.com'})
        cls.partner2 = cls.Partner.create({'name': 'Partner 2', 'email': 'partner2@example.com'})
        cls.partner3 = cls.Partner.create({'name': 'Partner 3', 'email': 'partner3@example.com'})

        # Create bank accounts
        cls.bank1 = cls.Bank.create({'acc_number': '12345', 'partner_id': cls.partner1.id})
        cls.bank2 = cls.Bank.create({'acc_number': '67890', 'partner_id': cls.partner2.id})
        cls.bank3 = cls.Bank.create({'acc_number': '12345', 'partner_id': cls.partner3.id})

        # Create payments linked to bank accounts
        cls.payment1 = cls.Payment.create({
            'partner_id': cls.partner1.id,
            'partner_bank_id': cls.bank1.id,
            'amount': 100,
            'payment_type': 'outbound',
            'payment_method_id': cls.env.ref('account.account_payment_method_manual_out').id,
            'journal_id': cls.company_data['default_journal_bank'].id,
        })
        cls.payment2 = cls.Payment.create({
            'partner_id': cls.partner2.id,
            'partner_bank_id': cls.bank2.id,
            'amount': 200,
            'payment_type': 'outbound',
            'payment_method_id': cls.env.ref('account.account_payment_method_manual_out').id,
            'journal_id': cls.company_data['default_journal_bank'].id,
        })
        cls.payment3 = cls.Payment.create({
            'partner_id': cls.partner3.id,
            'partner_bank_id': cls.bank3.id,
            'amount': 200,
            'payment_type': 'outbound',
            'payment_method_id': cls.env.ref('account.account_payment_method_manual_out').id,
            'journal_id': cls.company_data['default_journal_bank'].id,
        })

    def test_merge_partners_with_bank_accounts_linked_to_payments(self):
        wizard = self.env['base.partner.merge.automatic.wizard'].create({})
        wizard._merge([self.partner1.id, self.partner2.id], self.partner1)

        self.assertFalse(self.partner2.exists(), "Source partner should be deleted after merge")
        self.assertTrue(self.partner1.exists(), "Destination partner should exist after merge")
        self.assertEqual(self.payment1.partner_id, self.partner1, "Payment should be linked to the destination partner")
        self.assertEqual(self.payment2.partner_id, self.partner1, "Payment should be linked to the destination partner")
        self.assertEqual(self.payment1.partner_bank_id.partner_id, self.partner1, "Payment's bank account should belong to the destination partner")
        self.assertEqual(self.payment2.partner_bank_id.partner_id, self.partner1, "Payment's bank account should belong to the destination partner")

    def test_merge_partners_with_duplicate_bank_accounts_linked_to_payments(self):
        wizard = self.env['base.partner.merge.automatic.wizard'].create({})
        wizard._merge([self.partner1.id, self.partner3.id], self.partner1)

        self.assertFalse(self.partner3.exists(), "Source partner should be deleted after merge")
        self.assertTrue(self.partner1.exists(), "Destination partner should exist after merge")
        self.assertEqual(self.payment1.partner_id, self.partner1, "Payment should be linked to the destination partner")
        self.assertEqual(self.payment3.partner_id, self.partner1, "Payment should be linked to the destination partner")
        self.assertEqual(self.payment1.partner_bank_id.partner_id, self.partner1, "Payment's bank account should belong to the destination partner")
        self.assertEqual(self.payment3.partner_bank_id.partner_id, self.partner1, "Payment's bank account should belong to the destination partner")
