# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged, new_test_user
from odoo.tests.common import Form
from odoo import fields, api, SUPERUSER_ID
from odoo.exceptions import ValidationError, UserError, RedirectWarning
from odoo.tools import mute_logger

from dateutil.relativedelta import relativedelta
from functools import reduce
import json
import psycopg2


@tagged('post_install', '-at_install')
class TestAccountMove(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        tax_repartition_line = cls.company_data['default_tax_sale'].refund_repartition_line_ids\
            .filtered(lambda line: line.repartition_type == 'tax')
        cls.test_move = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2016-01-01'),
            'line_ids': [
                (0, None, {
                    'name': 'revenue line 1',
                    'account_id': cls.company_data['default_account_revenue'].id,
                    'debit': 500.0,
                    'credit': 0.0,
                }),
                (0, None, {
                    'name': 'revenue line 2',
                    'account_id': cls.company_data['default_account_revenue'].id,
                    'debit': 1000.0,
                    'credit': 0.0,
                    'tax_ids': [(6, 0, cls.company_data['default_tax_sale'].ids)],
                }),
                (0, None, {
                    'name': 'tax line',
                    'account_id': cls.company_data['default_account_tax_sale'].id,
                    'debit': 150.0,
                    'credit': 0.0,
                    'tax_repartition_line_id': tax_repartition_line.id,
                }),
                (0, None, {
                    'name': 'counterpart line',
                    'account_id': cls.company_data['default_account_expense'].id,
                    'debit': 0.0,
                    'credit': 1650.0,
                }),
            ]
        })

    def test_custom_currency_on_account_1(self):
        custom_account = self.company_data['default_account_revenue'].copy()

        # The currency set on the account is not the same as the one set on the company.
        # It should raise an error.
        custom_account.currency_id = self.currency_data['currency']

        with self.assertRaises(UserError), self.cr.savepoint():
            self.test_move.line_ids[0].account_id = custom_account

        # The currency set on the account is the same as the one set on the company.
        # It should not raise an error.
        custom_account.currency_id = self.company_data['currency']

        self.test_move.line_ids[0].account_id = custom_account

    def test_misc_fiscalyear_lock_date_1(self):
        self.test_move.action_post()

        # Set the lock date after the journal entry date.
        self.test_move.company_id.fiscalyear_lock_date = fields.Date.from_string('2017-01-01')

        # lines[0] = 'counterpart line'
        # lines[1] = 'tax line'
        # lines[2] = 'revenue line 1'
        # lines[3] = 'revenue line 2'
        lines = self.test_move.line_ids.sorted('debit')

        # Editing the reference should be allowed.
        self.test_move.ref = 'whatever'

        # Try to edit a line into a locked fiscal year.
        with self.assertRaises(UserError), self.cr.savepoint():
            self.test_move.write({
                'line_ids': [
                    (1, lines[0].id, {'credit': lines[0].credit + 100.0}),
                    (1, lines[2].id, {'debit': lines[2].debit + 100.0}),
                ],
            })

        # Try to edit the account of a line.
        with self.assertRaises(UserError), self.cr.savepoint():
            self.test_move.line_ids[0].write({'account_id': self.test_move.line_ids[0].account_id.copy().id})

        # Try to edit a line.
        with self.assertRaises(UserError), self.cr.savepoint():
            self.test_move.write({
                'line_ids': [
                    (1, lines[0].id, {'credit': lines[0].credit + 100.0}),
                    (1, lines[3].id, {'debit': lines[3].debit + 100.0}),
                ],
            })

        # Try to add a new tax on a line.
        with self.assertRaises(UserError), self.cr.savepoint():
            self.test_move.write({
                'line_ids': [
                    (1, lines[2].id, {'tax_ids': [(6, 0, self.company_data['default_tax_purchase'].ids)]}),
                ],
            })

        # Try to create a new line.
        with self.assertRaises(UserError), self.cr.savepoint():
            self.test_move.write({
                'line_ids': [
                    (1, lines[0].id, {'credit': lines[0].credit + 100.0}),
                    (0, None, {
                        'name': 'revenue line 1',
                        'account_id': self.company_data['default_account_revenue'].id,
                        'debit': 100.0,
                        'credit': 0.0,
                    }),
                ],
            })

        # You can't remove the journal entry from a locked period.
        with self.assertRaises(UserError), self.cr.savepoint():
            self.test_move.date = fields.Date.from_string('2018-01-01')

        with self.assertRaises(UserError), self.cr.savepoint():
            self.test_move.unlink()

        with self.assertRaises(UserError), self.cr.savepoint():
            self.test_move.button_draft()

        # Try to add a new journal entry prior to the lock date.
        copy_move = self.test_move.copy({'date': '2017-01-01'})
        # The date has been changed to the first valid date.
        self.assertEqual(copy_move.date, copy_move.company_id.fiscalyear_lock_date + relativedelta(days=1))

    def test_misc_fiscalyear_lock_date_2(self):
        self.test_move.action_post()

        # Create a bank statement to get a balance in the suspense account.
        statement = self.env['account.bank.statement'].create({
            'journal_id': self.company_data['default_journal_bank'].id,
            'date': '2016-01-01',
            'line_ids': [
                (0, 0, {'payment_ref': 'test', 'amount': 10.0})
            ],
        })
        statement.button_post()

        # You can't lock the fiscal year if there is some unreconciled statement.
        with self.assertRaises(RedirectWarning), self.cr.savepoint():
            self.test_move.company_id.fiscalyear_lock_date = fields.Date.from_string('2017-01-01')

    def test_misc_tax_lock_date_1(self):
        self.test_move.action_post()

        # Set the tax lock date after the journal entry date.
        self.test_move.company_id.tax_lock_date = fields.Date.from_string('2017-01-01')

        # lines[0] = 'counterpart line'
        # lines[1] = 'tax line'
        # lines[2] = 'revenue line 1'
        # lines[3] = 'revenue line 2'
        lines = self.test_move.line_ids.sorted('debit')

        # Try to edit a line not affecting the taxes.
        self.test_move.write({
            'line_ids': [
                (1, lines[0].id, {'credit': lines[0].credit + 100.0}),
                (1, lines[2].id, {'debit': lines[2].debit + 100.0}),
            ],
        })

        # Try to edit the account of a line.
        self.test_move.line_ids[0].write({'account_id': self.test_move.line_ids[0].account_id.copy().id})

        # Try to edit a line having some taxes.
        with self.assertRaises(UserError), self.cr.savepoint():
            self.test_move.write({
                'line_ids': [
                    (1, lines[0].id, {'credit': lines[0].credit + 100.0}),
                    (1, lines[3].id, {'debit': lines[3].debit + 100.0}),
                ],
            })

        # Try to add a new tax on a line.
        with self.assertRaises(UserError), self.cr.savepoint():
            self.test_move.write({
                'line_ids': [
                    (1, lines[2].id, {'tax_ids': [(6, 0, self.company_data['default_tax_purchase'].ids)]}),
                ],
            })

        # Try to edit a tax line.
        with self.assertRaises(UserError), self.cr.savepoint():
            self.test_move.write({
                'line_ids': [
                    (1, lines[0].id, {'credit': lines[0].credit + 100.0}),
                    (1, lines[1].id, {'debit': lines[1].debit + 100.0}),
                ],
            })

        # Try to create a line not affecting the taxes.
        self.test_move.write({
            'line_ids': [
                (1, lines[0].id, {'credit': lines[0].credit + 100.0}),
                (0, None, {
                    'name': 'revenue line 1',
                    'account_id': self.company_data['default_account_revenue'].id,
                    'debit': 100.0,
                    'credit': 0.0,
                }),
            ],
        })

        # Try to create a line affecting the taxes.
        with self.assertRaises(UserError), self.cr.savepoint():
            self.test_move.write({
                'line_ids': [
                    (1, lines[0].id, {'credit': lines[0].credit + 100.0}),
                    (0, None, {
                        'name': 'revenue line 2',
                        'account_id': self.company_data['default_account_revenue'].id,
                        'debit': 1000.0,
                        'credit': 0.0,
                        'tax_ids': [(6, 0, self.company_data['default_tax_sale'].ids)],
                    }),
                ],
            })

        # You can't remove the journal entry from a locked period.
        with self.assertRaises(UserError), self.cr.savepoint():
            self.test_move.date = fields.Date.from_string('2018-01-01')

        with self.assertRaises(UserError), self.cr.savepoint():
            self.test_move.unlink()

        with self.assertRaises(UserError), self.cr.savepoint():
            self.test_move.button_draft()

        copy_move = self.test_move.copy({'date': self.test_move.date})

        # /!\ The date is changed automatically to the next available one during the post.
        copy_move.action_post()

        # You can't change the date to one being in a locked period.
        with self.assertRaises(UserError), self.cr.savepoint():
            copy_move.date = fields.Date.from_string('2017-01-01')

    def test_misc_draft_reconciled_entries_1(self):
        draft_moves = self.env['account.move'].create([
            {
                'move_type': 'entry',
                'line_ids': [
                    (0, None, {
                        'name': 'move 1 receivable line',
                        'account_id': self.company_data['default_account_receivable'].id,
                        'debit': 1000.0,
                        'credit': 0.0,
                    }),
                    (0, None, {
                        'name': 'move 1 counterpart line',
                        'account_id': self.company_data['default_account_expense'].id,
                        'debit': 0.0,
                        'credit': 1000.0,
                    }),
                ]
            },
            {
                'move_type': 'entry',
                'line_ids': [
                    (0, None, {
                        'name': 'move 2 receivable line',
                        'account_id': self.company_data['default_account_receivable'].id,
                        'debit': 0.0,
                        'credit': 2000.0,
                    }),
                    (0, None, {
                        'name': 'move 2 counterpart line',
                        'account_id': self.company_data['default_account_expense'].id,
                        'debit': 2000.0,
                        'credit': 0.0,
                    }),
                ]
            },
        ])

        # lines[0] = 'move 2 receivable line'
        # lines[1] = 'move 1 counterpart line'
        # lines[2] = 'move 1 receivable line'
        # lines[3] = 'move 2 counterpart line'
        draft_moves.action_post()
        lines = draft_moves.mapped('line_ids').sorted('balance')

        (lines[0] + lines[2]).reconcile()

        # You can't write something impacting the reconciliation on an already reconciled line.
        with self.assertRaises(UserError), self.cr.savepoint():
            draft_moves[0].write({
                'line_ids': [
                    (1, lines[1].id, {'credit': lines[1].credit + 100.0}),
                    (1, lines[2].id, {'debit': lines[2].debit + 100.0}),
                ]
            })

        # The write must not raise anything because the rounding of the monetary field should ignore such tiny amount.
        draft_moves[0].write({
            'line_ids': [
                (1, lines[1].id, {'credit': lines[1].credit + 0.0000001}),
                (1, lines[2].id, {'debit': lines[2].debit + 0.0000001}),
            ]
        })

        # You can't unlink an already reconciled line.
        with self.assertRaises(UserError), self.cr.savepoint():
            draft_moves.unlink()

    def test_misc_always_balanced_move(self):
        ''' Ensure there is no way to make '''
        # You can't remove a journal item making the journal entry unbalanced.
        with self.assertRaises(UserError), self.cr.savepoint():
            self.test_move.line_ids[0].unlink()

        # Same check using write instead of unlink.
        with self.assertRaises(UserError), self.cr.savepoint():
            balance = self.test_move.line_ids[0].balance + 5
            self.test_move.line_ids[0].write({
                'debit': balance if balance > 0.0 else 0.0,
                'credit': -balance if balance < 0.0 else 0.0,
            })

        # You can remove journal items if the related journal entry is still balanced.
        self.test_move.line_ids.unlink()

    def test_sequence_change_date(self):
        # Check setup
        self.assertEqual(self.test_move.state, 'draft')
        self.assertEqual(self.test_move.name, 'MISC/2016/01/0001')
        self.assertEqual(fields.Date.to_string(self.test_move.date), '2016-01-01')

        # Never posetd, the number must change if we change the date
        self.test_move.date = '2020-02-02'
        self.assertEqual(self.test_move.name, 'MISC/2020/02/0001')

        # We don't recompute user's input when posting
        self.test_move.name = 'MyMISC/2020/0000001'
        self.test_move.action_post()
        self.assertEqual(self.test_move.name, 'MyMISC/2020/0000001')

        # Has been posted, and it doesn't change anymore
        self.test_move.button_draft()
        self.test_move.date = '2020-01-02'
        self.test_move.action_post()
        self.assertEqual(self.test_move.name, 'MyMISC/2020/0000001')

    def test_journal_sequence(self):
        self.assertEqual(self.test_move.name, 'MISC/2016/01/0001')
        self.test_move.action_post()
        self.assertEqual(self.test_move.name, 'MISC/2016/01/0001')

        copy1 = self.test_move.copy({'date': self.test_move.date})
        self.assertEqual(copy1.name, '/')
        copy1.action_post()
        self.assertEqual(copy1.name, 'MISC/2016/01/0002')

        copy2 = self.test_move.copy({'date': self.test_move.date})
        new_journal = self.test_move.journal_id.copy()
        new_journal.code = "MISC2"
        copy2.journal_id = new_journal
        self.assertEqual(copy2.name, 'MISC2/2016/01/0001')
        with Form(copy2) as move_form:  # It is editable in the form
            move_form.name = 'MyMISC/2016/0001'
            move_form.journal_id = self.test_move.journal_id
            self.assertEqual(move_form.name, '/')
            move_form.journal_id = new_journal
            self.assertEqual(move_form.name, 'MISC2/2016/01/0001')
            move_form.name = 'MyMISC/2016/0001'
        copy2.action_post()
        self.assertEqual(copy2.name, 'MyMISC/2016/0001')

        copy3 = copy2.copy({'date': copy2.date})
        self.assertEqual(copy3.name, '/')
        with self.assertRaises(AssertionError):
            with Form(copy2) as move_form:  # It is not editable in the form
                move_form.name = 'MyMISC/2016/0002'
        copy3.action_post()
        self.assertEqual(copy3.name, 'MyMISC/2016/0002')
        copy3.name = 'MISC2/2016/00002'

        copy4 = copy2.copy({'date': copy2.date})
        copy4.action_post()
        self.assertEqual(copy4.name, 'MISC2/2016/00003')

        copy5 = copy2.copy({'date': copy2.date})
        copy5.date = '2021-02-02'
        copy5.action_post()
        self.assertEqual(copy5.name, 'MISC2/2021/00001')
        copy5.name = 'N\'importe quoi?'

        copy6 = copy5.copy({'date': copy5.date})
        copy6.action_post()
        self.assertEqual(copy6.name, 'N\'importe quoi?1')

    def test_journal_sequence_format(self):
        """Test different format of sequences and what it becomes on another period"""
        sequences = [
            ('JRNL/2016/00001', 'JRNL/2016/00002', 'JRNL/2016/00003', 'JRNL/2017/00001'),
            ('1234567', '1234568', '1234569', '1234570'),
            ('20190910', '20190911', '20190912', '20190913'),
            ('2016-0910', '2016-0911', '2016-0912', '2017-0001'),
            ('201603-10', '201603-11', '201604-01', '201703-01'),
            ('16-03-10', '16-03-11', '16-04-01', '17-03-01'),
            ('2016-10', '2016-11', '2016-12', '2017-01'),
            ('045-001-000002', '045-001-000003', '045-001-000004', '045-001-000005'),
            ('JRNL/2016/00001suffix', 'JRNL/2016/00002suffix', 'JRNL/2016/00003suffix', 'JRNL/2017/00001suffix'),
        ]
        other_moves = self.env['account.move'].search([('journal_id', '=', self.test_move.journal_id.id)]) - self.test_move
        other_moves.unlink()  # Do not interfere when trying to get the highest name for new periods

        init_move = self.test_move
        next_move = init_move.copy()
        next_move_month = init_move.copy()
        next_move_year = init_move.copy()
        init_move.date = '2016-03-12'
        next_move.date = '2016-03-12'
        next_move_month.date = '2016-04-12'
        next_move_year.date = '2017-03-12'
        next_moves = (next_move + next_move_month + next_move_year)
        next_moves.action_post()

        for sequence_init, sequence_next, sequence_next_month, sequence_next_year in sequences:
            init_move.name = sequence_init
            next_moves.name = False
            next_moves._compute_name()
            self.assertEqual(
                [next_move.name, next_move_month.name, next_move_year.name],
                [sequence_next, sequence_next_month, sequence_next_year],
            )

    def test_journal_next_sequence(self):
        prefix = "TEST_ORDER/2016/"
        self.test_move.name = f"{prefix}1"
        for c in range(2, 25):
            copy = self.test_move.copy({'date': self.test_move.date})
            copy.name = "/"
            copy.action_post()
            self.assertEqual(copy.name, f"{prefix}{c}")

    def test_journal_sequence_multiple_type(self):
        entry, entry2, invoice, invoice2, refund, refund2 = (self.test_move.copy({'date': self.test_move.date}) for i in range(6))
        (invoice + invoice2 + refund + refund2).write({
            'journal_id': self.company_data['default_journal_sale'],
            'partner_id': 1,
            'invoice_date': '2016-01-01',
        })
        (invoice + invoice2).move_type = 'out_invoice'
        (refund + refund2).move_type = 'out_refund'
        all = (entry + entry2 + invoice + invoice2 + refund + refund2)
        all.name = False
        all.action_post()
        self.assertEqual(entry.name, 'MISC/2016/01/0002')
        self.assertEqual(entry2.name, 'MISC/2016/01/0003')
        self.assertEqual(invoice.name, 'INV/2016/01/0001')
        self.assertEqual(invoice2.name, 'INV/2016/01/0002')
        self.assertEqual(refund.name, 'RINV/2016/01/0001')
        self.assertEqual(refund2.name, 'RINV/2016/01/0002')

    def test_journal_sequence_groupby_compute(self):
        # Setup two journals with a sequence that resets yearly
        journals = self.env['account.journal'].create([{
            'name': f'Journal{i}',
            'code': f'J{i}',
            'type': 'general',
        } for i in range(2)])
        account = self.env['account.account'].search([], limit=1)
        moves = self.env['account.move'].create([{
            'journal_id': journals[i].id,
            'line_ids': [(0, 0, {'account_id': account.id, 'name': 'line'})],
            'date': '2010-01-01',
        } for i in range(2)])._post()
        for i in range(2):
            moves[i].name = f'J{i}/2010/00001'

        # Check that the moves are correctly batched
        moves = self.env['account.move'].create([{
            'journal_id': journals[journal_index].id,
            'line_ids': [(0, 0, {'account_id': account.id, 'name': 'line'})],
            'date': f'2010-{month}-01',
        } for journal_index, month in [(1, 1), (0, 1), (1, 2), (1, 1)]])._post()
        self.assertEqual(
            moves.mapped('name'),
            ['J1/2010/00002', 'J0/2010/00002', 'J1/2010/00004', 'J1/2010/00003'],
        )

    def test_journal_override_sequence_regex(self):
        other_moves = self.env['account.move'].search([('journal_id', '=', self.test_move.journal_id.id)]) - self.test_move
        other_moves.unlink()  # Do not interfere when trying to get the highest name for new periods
        self.test_move.date = '2020-01-01'
        self.test_move.name = '00000876-G 0002/2020'
        next = self.test_move.copy({'date': self.test_move.date})
        next.action_post()
        self.assertEqual(next.name, '00000876-G 0002/2021')  # Wait, I didn't want this!

        next.journal_id.sequence_override_regex = r'^(?P<seq>\d*)(?P<suffix1>.*?)(?P<year>(\d{4})?)(?P<suffix2>)$'
        next.name = '/'
        next._compute_name()
        self.assertEqual(next.name, '00000877-G 0002/2020')  # Pfew, better!

        next = next = self.test_move.copy({'date': self.test_move.date})
        next.date = "2017-05-02"
        next.action_post()
        self.assertEqual(next.name, '00000001-G 0002/2017')

    def test_journal_sequence_ordering(self):
        self.test_move.name = 'XMISC/2016/00001'
        copies = reduce((lambda x, y: x+y), [self.test_move.copy({'date': self.test_move.date}) for i in range(6)])

        copies[0].date = '2019-03-05'
        copies[1].date = '2019-03-06'
        copies[2].date = '2019-03-07'
        copies[3].date = '2019-03-04'
        copies[4].date = '2019-03-05'
        copies[5].date = '2019-03-05'
        # that entry is actualy the first one of the period, so it already has a name
        # set it to '/' so that it is recomputed at post to be ordered correctly.
        copies[0].name = '/'
        copies.action_post()

        # Ordered by date
        self.assertEqual(copies[0].name, 'XMISC/2019/00002')
        self.assertEqual(copies[1].name, 'XMISC/2019/00005')
        self.assertEqual(copies[2].name, 'XMISC/2019/00006')
        self.assertEqual(copies[3].name, 'XMISC/2019/00001')
        self.assertEqual(copies[4].name, 'XMISC/2019/00003')
        self.assertEqual(copies[5].name, 'XMISC/2019/00004')

        # Can't have twice the same name
        with self.assertRaises(ValidationError):
            copies[0].name = 'XMISC/2019/00001'

        # Lets remove the order by date
        copies[0].name = 'XMISC/2019/10001'
        copies[1].name = 'XMISC/2019/10002'
        copies[2].name = 'XMISC/2019/10003'
        copies[3].name = 'XMISC/2019/10004'
        copies[4].name = 'XMISC/2019/10005'
        copies[5].name = 'XMISC/2019/10006'

        copies[4].button_draft()
        copies[4].with_context(force_delete=True).unlink()
        copies[5].button_draft()

        wizard = Form(self.env['account.resequence.wizard'].with_context(active_ids=set(copies.ids) - set(copies[4].ids), active_model='account.move'))

        new_values = json.loads(wizard.new_values)
        self.assertEqual(new_values[str(copies[0].id)]['new_by_date'], 'XMISC/2019/10002')
        self.assertEqual(new_values[str(copies[0].id)]['new_by_name'], 'XMISC/2019/10001')

        self.assertEqual(new_values[str(copies[1].id)]['new_by_date'], 'XMISC/2019/10004')
        self.assertEqual(new_values[str(copies[1].id)]['new_by_name'], 'XMISC/2019/10002')

        self.assertEqual(new_values[str(copies[2].id)]['new_by_date'], 'XMISC/2019/10005')
        self.assertEqual(new_values[str(copies[2].id)]['new_by_name'], 'XMISC/2019/10003')

        self.assertEqual(new_values[str(copies[3].id)]['new_by_date'], 'XMISC/2019/10001')
        self.assertEqual(new_values[str(copies[3].id)]['new_by_name'], 'XMISC/2019/10004')

        self.assertEqual(new_values[str(copies[5].id)]['new_by_date'], 'XMISC/2019/10003')
        self.assertEqual(new_values[str(copies[5].id)]['new_by_name'], 'XMISC/2019/10005')

        wizard.save().resequence()

        self.assertEqual(copies[3].state, 'posted')
        self.assertEqual(copies[5].name, 'XMISC/2019/10005')
        self.assertEqual(copies[5].state, 'draft')

    def test_sequence_concurency(self):
        with self.env.registry.cursor() as cr0,\
                self.env.registry.cursor() as cr1,\
                self.env.registry.cursor() as cr2:
            env0 = api.Environment(cr0, SUPERUSER_ID, {})
            env1 = api.Environment(cr1, SUPERUSER_ID, {})
            env2 = api.Environment(cr2, SUPERUSER_ID, {})

            journal = env0['account.journal'].create({
                'name': 'concurency_test',
                'code': 'CT',
                'type': 'general',
            })
            account = env0['account.account'].create({
                'code': 'CT',
                'name': 'CT',
                'user_type_id': env0.ref('account.data_account_type_fixed_assets').id,
            })
            moves = env0['account.move'].create([{
                'journal_id': journal.id,
                'date': fields.Date.from_string('2016-01-01'),
                'line_ids': [(0, 0, {'name': 'name', 'account_id': account.id})]
            }] * 3)
            moves.name = '/'
            moves[0].action_post()
            self.assertEqual(moves.mapped('name'), ['CT/2016/01/0001', '/', '/'])
            env0.cr.commit()

            # start the transactions here on cr2 to simulate concurency with cr1
            env2.cr.execute('SELECT 1')

            move = env1['account.move'].browse(moves[1].id)
            move.action_post()
            env1.cr.commit()

            move = env2['account.move'].browse(moves[2].id)
            with self.assertRaises(psycopg2.OperationalError), env2.cr.savepoint(), mute_logger('odoo.sql_db'):
                move.action_post()

            self.assertEqual(moves.mapped('name'), ['CT/2016/01/0001', 'CT/2016/01/0002', '/'])
            moves.button_draft()
            moves.posted_before = False
            moves.unlink()
            journal.unlink()
            account.unlink()
            env0.cr.commit()

    def test_add_followers_on_post(self):
        # Add some existing partners, some from another company
        company = self.env['res.company'].create({'name': 'Oopo'})
        company.flush()
        existing_partners = self.env['res.partner'].create([{
            'name': 'Jean',
            'company_id': company.id,
        },{
            'name': 'Paulus',
        }])
        self.test_move.message_subscribe(existing_partners.ids)

        user = new_test_user(self.env, login='jag', groups='account.group_account_invoice')

        move = self.test_move.with_user(user)
        partner = self.env['res.partner'].create({'name': 'Belouga'})
        move.partner_id = partner

        move.action_post()
        self.assertEqual(move.message_partner_ids, self.env.user.partner_id | existing_partners | partner)

    def test_misc_move_onchange(self):
        ''' Test the behavior on onchanges for account.move having 'entry' as type. '''

        move_form = Form(self.env['account.move'])
        # Rate 1:3
        move_form.date = fields.Date.from_string('2016-01-01')

        # New line that should get 400.0 as debit.
        with move_form.line_ids.new() as line_form:
            line_form.name = 'debit_line'
            line_form.account_id = self.company_data['default_account_revenue']
            line_form.currency_id = self.currency_data['currency']
            line_form.amount_currency = 1200.0

        # New line that should get 400.0 as credit.
        with move_form.line_ids.new() as line_form:
            line_form.name = 'credit_line'
            line_form.account_id = self.company_data['default_account_revenue']
            line_form.currency_id = self.currency_data['currency']
            line_form.amount_currency = -1200.0
        move = move_form.save()

        self.assertRecordValues(
            move.line_ids.sorted('debit'),
            [
                {
                    'currency_id': self.currency_data['currency'].id,
                    'amount_currency': -1200.0,
                    'debit': 0.0,
                    'credit': 400.0,
                },
                {
                    'currency_id': self.currency_data['currency'].id,
                    'amount_currency': 1200.0,
                    'debit': 400.0,
                    'credit': 0.0,
                },
            ],
        )

        # === Change the date to change the currency conversion's rate ===

        with Form(move) as move_form:
            move_form.date = fields.Date.from_string('2017-01-01')

        self.assertRecordValues(
            move.line_ids.sorted('debit'),
            [
                {
                    'currency_id': self.currency_data['currency'].id,
                    'amount_currency': -1200.0,
                    'debit': 0.0,
                    'credit': 600.0,
                },
                {
                    'currency_id': self.currency_data['currency'].id,
                    'amount_currency': 1200.0,
                    'debit': 600.0,
                    'credit': 0.0,
                },
            ],
        )

    def test_included_tax(self):
        '''
        Test an account.move.line is created automatically when adding a tax.
        This test uses the following scenario:
            - Create manually a debit line of 1000 having an included tax.
            - Assume a line containing the tax amount is created automatically.
            - Create manually a credit line to balance the two previous lines.
            - Save the move.

        included tax = 20%

        Name                   | Debit     | Credit    | Tax_ids       | Tax_line_id's name
        -----------------------|-----------|-----------|---------------|-------------------
        debit_line_1           | 1000      |           | tax           |
        included_tax_line      | 200       |           |               | included_tax_line
        credit_line_1          |           | 1200      |               |
        '''

        self.included_percent_tax = self.env['account.tax'].create({
            'name': 'included_tax_line',
            'amount_type': 'percent',
            'amount': 20,
            'price_include': True,
            'include_base_amount': False,
        })
        self.account = self.company_data['default_account_revenue']

        move_form = Form(self.env['account.move'].with_context(default_move_type='entry'))

        # Create a new account.move.line with debit amount.
        with move_form.line_ids.new() as debit_line:
            debit_line.name = 'debit_line_1'
            debit_line.account_id = self.account
            debit_line.debit = 1000
            debit_line.tax_ids.clear()
            debit_line.tax_ids.add(self.included_percent_tax)

            self.assertTrue(debit_line.recompute_tax_line)

        # Create a third account.move.line with credit amount.
        with move_form.line_ids.new() as credit_line:
            credit_line.name = 'credit_line_1'
            credit_line.account_id = self.account
            credit_line.credit = 1200

        move = move_form.save()

        self.assertRecordValues(move.line_ids, [
            {'name': 'debit_line_1',             'debit': 1000.0,    'credit': 0.0,      'tax_ids': [self.included_percent_tax.id],      'tax_line_id': False},
            {'name': 'included_tax_line',        'debit': 200.0,     'credit': 0.0,      'tax_ids': [],                                  'tax_line_id': self.included_percent_tax.id},
            {'name': 'credit_line_1',            'debit': 0.0,       'credit': 1200.0,   'tax_ids': [],                                  'tax_line_id': False},
        ])

    def test_misc_prevent_unlink_posted_items(self):
        # You cannot remove journal items if the related journal entry is posted.
        self.test_move.action_post()
        with self.assertRaises(UserError), self.cr.savepoint():
            self.test_move.line_ids.unlink()

        # You can remove journal items if the related journal entry is draft.
        self.test_move.button_draft()
        self.test_move.line_ids.unlink()
