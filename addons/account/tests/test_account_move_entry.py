# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged, new_test_user
from odoo.tests.common import Form
from odoo import fields
from odoo.exceptions import ValidationError, UserError

from dateutil.relativedelta import relativedelta
from functools import reduce
import json


@tagged('post_install', '-at_install')
class TestAccountMove(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super(TestAccountMove, cls).setUpClass()

        tax_repartition_line = cls.company_data['default_tax_sale'].invoice_repartition_line_ids\
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
        self.test_move.post()

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

    def test_misc_tax_lock_date_1(self):
        self.test_move.post()

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

        copy_move = self.test_move.copy()

        # /!\ The date is changed automatically to the next available one during the post.
        copy_move.post()

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
        draft_moves.post()
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

    def test_journal_sequence(self):
        self.assertEqual(self.test_move.name, 'MISC/2016/01/0001')
        self.test_move.post()
        self.assertEqual(self.test_move.name, 'MISC/2016/01/0001')

        copy1 = self.test_move.copy()
        self.assertEqual(copy1.name, '/')
        copy1.post()
        self.assertEqual(copy1.name, 'MISC/2016/01/0002')

        copy2 = self.test_move.copy()
        new_journal = self.test_move.journal_id.copy()
        new_journal.code = "MISC2"
        copy2.journal_id = new_journal
        self.assertEqual(copy2.name, 'MISC2/2016/01/0001')
        with Form(copy2) as move_form:  # It is editable in the form
            move_form.name = 'MyMISC/2099/0001'
        copy2.post()
        self.assertEqual(copy2.name, 'MyMISC/2099/0001')

        copy3 = copy2.copy()
        self.assertEqual(copy3.name, '/')
        with self.assertRaises(AssertionError):
            with Form(copy2) as move_form:  # It is not editable in the form
                move_form.name = 'MyMISC/2099/0002'
        copy3.post()
        self.assertEqual(copy3.name, 'MyMISC/2099/0002')
        copy3.name = 'MISC2/2016/00002'

        copy4 = copy2.copy()
        copy4.post()
        self.assertEqual(copy4.name, 'MyMISC/2099/0002')

        copy5 = copy2.copy()
        copy5.date = '2021-02-02'
        copy5.post()
        self.assertEqual(copy5.name, 'MyMISC/2021/0001')
        copy5.name = 'N\'importe quoi?'

        copy6 = copy5.copy()
        copy6.post()
        self.assertEqual(copy6.name, '1N\'importe quoi?')

    def test_journal_sequence_format(self):
        """Test different format of sequences and what it becomes on another period"""
        sequences = [
            ('JRNL/2016/00001', 'JRNL/2016/00002', 'JRNL/2016/00003', 'JRNL/2017/00001'),
            ('1234567', '1234568', '1234569', '1234570'),
            ('20190910', '20190911', '20190912', '20190913'),
            ('2019-0910', '2019-0911', '2019-0912', '2017-0001'),
            ('201909-10', '201909-11', '201604-01', '201703-01'),
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
        next_moves.post()

        for sequence_init, sequence_next, sequence_next_month, sequence_next_year in sequences:
            init_move.name = sequence_init
            next_moves.name = False
            next_moves._compute_name()
            self.assertEqual(next_move.name, sequence_next)
            self.assertEqual(next_move_month.name, sequence_next_month)
            self.assertEqual(next_move_year.name, sequence_next_year)

    def test_journal_override_sequence_regex(self):
        other_moves = self.env['account.move'].search([('journal_id', '=', self.test_move.journal_id.id)]) - self.test_move
        other_moves.unlink()  # Do not interfere when trying to get the highest name for new periods
        self.test_move.name = '00000876-G 0002'
        next = self.test_move.copy()
        next.post()
        self.assertEqual(next.name, '00000876-G 0003')  # Wait, I didn't want this!

        next.journal_id.sequence_override_regex = r'^(?P<prefix1>)(?P<seq>\d*)(?P<suffix>.*)$'
        next.name = '/'
        next._compute_name()
        self.assertEqual(next.name, '00000877-G 0002')  # Pfew, better!

    def test_journal_sequence_ordering(self):
        self.test_move.name = 'XMISC/2016/00001'
        copies = reduce((lambda x, y: x+y), [self.test_move.copy() for i in range(6)])

        copies[0].date = '2019-03-05'
        copies[1].date = '2019-03-06'
        copies[2].date = '2019-03-07'
        copies[3].date = '2019-03-04'
        copies[4].date = '2019-03-05'
        copies[5].date = '2019-03-05'
        # that entry is actualy the first one of the period, so it already has a name
        # set it to '/' so that it is recomputed at post to be ordered correctly.
        copies[0].name = '/'
        copies.post()

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

        move.post()
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
