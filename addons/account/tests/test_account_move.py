from datetime import date

from openerp.tests.common import TransactionCase
from openerp.osv.orm import except_orm

class TestPeriodState(TransactionCase):
    """
    Forbid creation of Journal Entries for a closed period.
    """

    def setUp(self):
        super(TestPeriodState, self).setUp()
        cr, uid = self.cr, self.uid
        self.wizard_period_close = self.registry('account.period.close')
        self.wizard_period_close_id = self.wizard_period_close.create(cr, uid, {'sure': 1})
        _, self.sale_journal_id = self.registry("ir.model.data").get_object_reference(cr, uid, "account", "sales_journal")
        _, self.period_9_id = self.registry("ir.model.data").get_object_reference(cr, uid, "account", "period_9")

    def test_period_state(self):
        cr, uid = self.cr, self.uid
        self.wizard_period_close.data_save(cr, uid, [self.wizard_period_close_id], {
            'lang': 'en_US',
            'active_model': 'account.period',
            'active_ids': [self.period_9_id],
            'tz': False,
            'active_id': self.period_9_id
        })
        with self.assertRaises(except_orm):
            self.registry('account.move').create(cr, uid, {
                'name': '/',
                'period_id': self.period_9_id,
                'journal_id': self.sale_journal_id,
                'date': date.today(),
                'line_id': [(0, 0, {
                        'name': 'foo',
                        'debit': 10,
                    }), (0, 0, {
                        'name': 'bar',
                        'credit': 10,
                    })]
            })


class TestAutoPost(TransactionCase):
    """
    Entries generated with a journal at auto-post should be posted as soon as the move is validated
    """

    def setUp(self):
        super(TestAutoPost, self).setUp()
        self.account_move = self.env['account.move']
        self.journal = self.env['account.journal'].create({
            'name': 'Auto-posted journal',
            'code': 'APJ',
            'type': 'sale',
            'entry_posted': True,
            'default_credit_account_id': self.env.ref('account.a_sale').id,
            'default_debit_account_id': self.env.ref('account.a_sale').id,
        })

    def test_move_create(self):
        move = self.account_move.create({
            'journal_id': self.journal.id,
            'line_id': [(0, 0, {
                        'name': 'foo',
                        'debit': 10,
                    }), (0, 0, {
                        'name': 'bar',
                        'credit': 10,
                    })]
        })
        self.assertEqual(move.state, 'posted', "Creating move with balanced lines should be posted")

        move = self.account_move.create({
            'journal_id': self.journal.id,
            'line_id': [(0, 0, {
                        'name': 'foo',
                        'debit': 10,
                    }), (0, 0, {
                        'name': 'bar',
                        'credit': 20,
                    })]
        })
        self.assertNotEqual(move.state, 'posted', "Creating move with unbalanced lines should not be posted")

    def test_move_write(self):
        move = self.account_move.create({
            'journal_id': self.journal.id
        })
        self.assertNotEqual(move.state, 'posted', "Creating move without lines should not be posted")
        move.write({
            'line_id': [(0, 0, {
                        'name': 'foo',
                        'debit': 10,
                    }), (0, 0, {
                        'name': 'bar',
                        'credit': 10,
                    })]
        })
        self.assertEqual(move.state, 'posted', "Adding balanced lines should post the move")

        move = self.account_move.create({
            'journal_id': self.journal.id
        })
        move.write({
            'line_id': [(0, 0, {
                        'name': 'foo',
                        'debit': 10,
                    }), (0, 0, {
                        'name': 'bar',
                        'credit': 20,
                    })]
        })
        self.assertNotEqual(move.state, 'posted', "Adding unbalanced lines should not post the move")

    def test_multiple_move_create(self):
        move1 = self.account_move.create({
            'journal_id': self.journal.id,
            'line_id': [(0, 0, {
                        'name': 'foo',
                        'credit': 0,
                        'debit': 10,
                    })]
        })
        move2 = self.account_move.create({
            'journal_id': self.journal.id,
            'line_id': [(0, 0, {
                'name': 'foo',
                'credit': 0,
                'debit': 20,
            })]
        })

        move_set = move1 + move2
        move_set.write({
            'line_id': [(0, 0, {
                        'name': 'bar',
                        'credit': 10,
                    })]
        })
        self.assertEqual(move1.state, 'posted', "Adding balancing line should post the move")
        self.assertNotEqual(move2.state, 'posted', "Only balanced move should be posted after write")
