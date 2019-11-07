from odoo.addons.account.tests.common import AccountTestCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestBankStatement(AccountTestCommon):

    def setUp(self):
        super(TestBankStatement, self).setUp()
        self.bs_model = self.env['account.bank.statement']
        self.bsl_model = self.env['account.bank.statement.line']
        self.partner = self.env['res.partner'].create({'name': 'test'})
        self.journal = self.env['account.journal'].create({
            'name': 'BnkJournal',
            'type': 'bank'
        })
        self.journal2 = self.env['account.journal'].create({
            'name': 'BnkJournal2',
            'type': 'bank'
        })
        self.cashjournal = self.env['account.journal'].create({
            'name': 'CashJournal',
            'type': 'cash'
        })
        self.number = 1

    def create_bank_statement(self, date, line_amount, balance_end_real=False, journal=False):
        vals = {
            'name': 'BNK' + str(self.number),
            'date': date,
            'line_ids': [(0, 0, {
                'name': '_',
                'amount': line_amount,
            })],
            'journal_id': journal or self.journal.id
        }
        if balance_end_real:
            vals['balance_end_real'] = balance_end_real
        self.number += 1
        return self.bs_model.create(vals)

    def test_compute_balance_end_real_with_lines(self):
        bnk1 = self.create_bank_statement('2019-01-02', 100)
        self.assertEqual(bnk1.balance_start, 0)
        # Balance is automatically computed when creating statement with the lines
        self.assertEqual(bnk1.balance_end_real, 100)
        self.assertEqual(bnk1.balance_end, 100)

    def test_compute_balance_end_real_without_lines(self):
        vals = {
            'name': 'BNK' + str(self.number),
            'date': '2019-01-01',
            'journal_id': self.journal.id
        }
        bnk1 = self.bs_model.create(vals)
        self.assertEqual(bnk1.balance_start, 0)
        self.assertEqual(bnk1.balance_end_real, 0)
        self.assertEqual(bnk1.balance_end, 0)
        # Add a line
        self.bsl_model.create({
            'name': '_',
            'amount': 10,
            'statement_id': bnk1.id
        })
        self.assertEqual(bnk1.balance_start, 0)
        # balance_end_real should not have changed
        self.assertEqual(bnk1.balance_end_real, 0)
        # Compute balance should have been computed
        self.assertEqual(bnk1.balance_end, 10)

    def test_create_new_statement(self):
        # Create first statement on 1/1/2019
        bnk1 = self.create_bank_statement('2019-01-02', 100)
        self.assertEqual(bnk1.balance_start, 0)
        # Balance is automatically computed when creating statement with the lines
        self.assertEqual(bnk1.balance_end_real, 100)
        self.assertEqual(bnk1.balance_end, 100)
        self.assertEqual(bnk1.previous_statement_id.id, False)
        
        # Create a new statement after that one
        bnk2 = self.create_bank_statement('2019-01-10', 50)
        self.assertEqual(bnk2.balance_start, 100)
        self.assertEqual(bnk2.balance_end_real, 150)
        self.assertEqual(bnk2.balance_end, 150)
        self.assertEqual(bnk2.previous_statement_id.id, bnk1.id)

        # Create new statement with given ending balance
        bnk3 = self.create_bank_statement('2019-01-15', 25, 200)
        self.assertEqual(bnk3.balance_end_real, 200)
        self.assertEqual(bnk3.balance_start, 150)
        self.assertEqual(bnk3.balance_end, 175)
        self.assertEqual(bnk3.previous_statement_id.id, bnk2.id)

        bnk4 = self.create_bank_statement('2019-01-03', 100)
        self.assertEqual(bnk4.balance_start, 100)
        self.assertEqual(bnk4.balance_end_real, 200)
        self.assertEqual(bnk4.balance_end, 200)
        self.assertEqual(bnk4.previous_statement_id.id, bnk1.id)
        # Bnk2 should have changed its previous statement
        self.assertEqual(bnk2.previous_statement_id.id, bnk4.id)
        # The starting balance and balance_end_real should have been recomputed
        self.assertEqual(bnk2.balance_start, 200)
        self.assertEqual(bnk2.balance_end_real, 250)
        self.assertEqual(bnk2.balance_end, 250)
        # The starting balance and balance_end_real of next entries should also have been recomputed
        # and since we are propagating an update, the balance_end_real should have been recomputed to
        # the correct value
        self.assertEqual(bnk3.balance_start, 250)
        self.assertEqual(bnk3.balance_end_real, 275)
        self.assertEqual(bnk3.balance_end, 275)

        # Change date of bank stmt4 to be the last
        bnk4.date = '2019-01-20'
        self.assertEqual(bnk1.previous_statement_id.id, False)
        self.assertEqual(bnk2.previous_statement_id.id, bnk1.id)
        self.assertEqual(bnk3.previous_statement_id.id, bnk2.id)
        self.assertEqual(bnk4.previous_statement_id.id, bnk3.id)
        self.assertEqual(bnk1.balance_start, 0)
        self.assertEqual(bnk2.balance_start, 100)
        self.assertEqual(bnk3.balance_start, 150)
        self.assertEqual(bnk4.balance_start, 175)
        self.assertEqual(bnk1.balance_end_real, 100)
        self.assertEqual(bnk2.balance_end_real, 150)
        self.assertEqual(bnk3.balance_end_real, 175)
        self.assertEqual(bnk4.balance_end_real, 275)

        # Move bnk3 to first position
        bnk3.date = '2019-01-01'
        self.assertEqual(bnk3.previous_statement_id.id, False)
        self.assertEqual(bnk1.previous_statement_id.id, bnk3.id)
        self.assertEqual(bnk2.previous_statement_id.id, bnk1.id)
        self.assertEqual(bnk4.previous_statement_id.id, bnk2.id)
        self.assertEqual(bnk3.balance_start, 0)
        self.assertEqual(bnk1.balance_start, 25)
        self.assertEqual(bnk2.balance_start, 125)
        self.assertEqual(bnk4.balance_start, 175)
        self.assertEqual(bnk3.balance_end_real, 25)
        self.assertEqual(bnk1.balance_end_real, 125)
        self.assertEqual(bnk2.balance_end_real, 175)
        self.assertEqual(bnk4.balance_end_real, 275)

        # Change bnk1 and bnk2
        bnk1.date = '2019-01-11'
        self.assertEqual(bnk3.previous_statement_id.id, False)
        self.assertEqual(bnk2.previous_statement_id.id, bnk3.id)
        self.assertEqual(bnk1.previous_statement_id.id, bnk2.id)
        self.assertEqual(bnk4.previous_statement_id.id, bnk1.id)
        self.assertEqual(bnk3.balance_start, 0)
        self.assertEqual(bnk2.balance_start, 25)
        self.assertEqual(bnk1.balance_start, 75)
        self.assertEqual(bnk4.balance_start, 175)
        self.assertEqual(bnk3.balance_end_real, 25)
        self.assertEqual(bnk2.balance_end_real, 75)
        self.assertEqual(bnk1.balance_end_real, 175)
        self.assertEqual(bnk4.balance_end_real, 275)

    def test_create_statements_in_different_journal(self):
        # Bank statement create in two different journal should not link with each other
        bnk1 = self.create_bank_statement('2019-01-01', 100, 100)
        bnk2 = self.create_bank_statement('2019-01-10', 50)

        bnk1other = self.create_bank_statement('2019-01-02', 20, 20, self.journal2.id)
        bnk2other = self.create_bank_statement('2019-01-12', 10, False, self.journal2.id)

        self.assertEqual(bnk1.previous_statement_id.id, False)
        self.assertEqual(bnk2.previous_statement_id.id, bnk1.id)
        self.assertEqual(bnk1.balance_start, 0)
        self.assertEqual(bnk2.balance_start, 100)
        self.assertEqual(bnk2.balance_end_real, 150)

        self.assertEqual(bnk1other.previous_statement_id.id, False)
        self.assertEqual(bnk2other.previous_statement_id.id, bnk1other.id)
        self.assertEqual(bnk1other.balance_start, 0)
        self.assertEqual(bnk2other.balance_start, 20)
        self.assertEqual(bnk2other.balance_end_real, 30)

    def test_statement_cash_journal(self):
        # Entry in cash journal should not recompute the balance_end_real
        cash1 = self.create_bank_statement('2019-01-01', 100, 100, self.cashjournal.id)
        cash2 = self.create_bank_statement('2019-01-03', 100, False, self.cashjournal.id)
        self.assertEqual(cash1.balance_start, 0)
        self.assertEqual(cash1.balance_end_real, 100)
        self.assertEqual(cash2.balance_start, 100)
        self.assertEqual(cash2.balance_end_real, 0)
        cash2.balance_end_real = 1000
        self.assertEqual(cash2.balance_end_real, 1000)
        # add cash entry in between, should recompute starting balance of cash2 entry but not ending balance
        cash3 = self.create_bank_statement('2019-01-02', 100, 200, self.cashjournal.id)
        self.assertEqual(cash3.balance_start, 100)
        self.assertEqual(cash3.balance_end_real, 200)
        self.assertEqual(cash2.balance_start, 200)
        self.assertEqual(cash2.balance_end_real, 1000)

    def test_unlink_bank_statement(self):
        bnk1 = self.create_bank_statement('2019-01-02', 100)
        bnk2 = self.create_bank_statement('2019-01-10', 50)
        bnk3 = self.create_bank_statement('2019-01-15', 25)
        bnk4 = self.create_bank_statement('2019-01-21', 100)
        bnk5 = self.create_bank_statement('2019-01-22', 100)
        self.assertEqual(bnk1.previous_statement_id.id, False)
        self.assertEqual(bnk2.previous_statement_id.id, bnk1.id)
        self.assertEqual(bnk3.previous_statement_id.id, bnk2.id)
        self.assertEqual(bnk4.previous_statement_id.id, bnk3.id)
        self.assertEqual(bnk5.previous_statement_id.id, bnk4.id)
        self.assertEqual(bnk3.balance_start, 150)
        self.assertEqual(bnk3.balance_end_real, 175)
        self.assertEqual(bnk4.balance_start, 175)
        self.assertEqual(bnk4.balance_end_real, 275)
        self.assertEqual(bnk5.balance_start, 275)
        self.assertEqual(bnk5.balance_end_real, 375)

        # Delete bnk2 and check that previous_statement_id and balance are correct
        bnk2.unlink()
        self.assertEqual(bnk1.previous_statement_id.id, False)
        self.assertEqual(bnk3.previous_statement_id.id, bnk1.id)
        self.assertEqual(bnk4.previous_statement_id.id, bnk3.id)
        self.assertEqual(bnk5.previous_statement_id.id, bnk4.id)
        self.assertEqual(bnk3.balance_start, 100)
        self.assertEqual(bnk3.balance_end_real, 125)
        self.assertEqual(bnk4.balance_start, 125)
        self.assertEqual(bnk4.balance_end_real, 225)
        self.assertEqual(bnk5.balance_start, 225)
        self.assertEqual(bnk5.balance_end_real, 325)

        # Delete bnk1 bnk3 and bnk4 at the same time and check that balance are correct
        (bnk1 + bnk3 + bnk4).unlink()
        self.assertEqual(bnk5.previous_statement_id.id, False)
        self.assertEqual(bnk5.balance_start, 0)
        self.assertEqual(bnk5.balance_end_real, 100)
