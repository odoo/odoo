from odoo import Command, fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import ValidationError
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAccountMoveJournalSuitability(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.misc_journal = cls.company_data['default_journal_misc']
        cls.bank_journal = cls.company_data['default_journal_bank']
        cls.entry = cls.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': cls.misc_journal.id,
            'date': fields.Date.from_string('2024-01-01'),
            'line_ids': [
                Command.create({'account_id': cls.company_data['default_account_revenue'].id, 'debit': 0.0, 'credit': 100.0}),
                Command.create({'account_id': cls.company_data['default_account_expense'].id, 'debit': 100.0, 'credit': 0.0}),
            ],
        })

    def test_misc_entry_cannot_be_moved_to_bank_journal_via_orm(self):
        """ The ORM (and therefore the AI) must not bypass the UI rule: a manual entry cannot use a bank journal. """
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.entry.journal_id = self.bank_journal

    def test_system_entry_can_be_created_on_bank_journal(self):
        """ Other modules (e.g. POS bank differences) create entries directly on bank journals: creation is not restricted. """
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': self.bank_journal.id,
            'date': fields.Date.from_string('2024-01-01'),
        })
        self.assertEqual(move.journal_id, self.bank_journal)

    def test_payment_entry_on_bank_journal_is_allowed(self):
        """ Payments generate move_type='entry' moves on the bank journal: they must remain valid. """
        payment = self.env['account.payment'].create({
            'amount': 100.0,
            'partner_id': self.partner_a.id,
            'journal_id': self.bank_journal.id,
        })
        payment.action_post()
        self.assertEqual(payment.move_id.journal_id, self.bank_journal)
