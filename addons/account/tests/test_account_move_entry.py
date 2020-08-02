# -*- coding: utf-8 -*-
from odoo.addons.account.tests.account_test_savepoint import AccountTestInvoicingCommon
from odoo.tests import tagged, new_test_user
from odoo.tests.common import Form
from odoo import fields
from odoo.exceptions import ValidationError, UserError


@tagged('post_install', '-at_install')
class TestAccountMove(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        tax_repartition_line = cls.company_data['default_tax_sale'].refund_repartition_line_ids\
            .filtered(lambda line: line.repartition_type == 'tax')
        cls.test_move = cls.env['account.move'].create({
            'type': 'entry',
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

        copy_move = self.test_move.copy()

        # Try to add a new journal entry prior to the lock date.
        with self.assertRaises(UserError), self.cr.savepoint():
            copy_move.post()

        # You can change the date as the journal entry is not posted.
        copy_move.date = fields.Date.from_string('2018-01-01')
        copy_move.post()

        # You can't change the date to one being in a locked period.
        with self.assertRaises(UserError), self.cr.savepoint():
            copy_move.date = fields.Date.from_string('2017-01-01')

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
                'type': 'entry',
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
                'type': 'entry',
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

    def test_misc_unique_sequence_number(self):
        ''' Ensure two journal entries can't share the same name when using the same sequence. '''
        self.test_move.post()

        # Edit the sequence to force the next move to get the same name.
        self.test_move.journal_id\
            .sequence_id.date_range_ids\
            .filtered(lambda seq: seq.date_from == fields.Date.from_string('2016-01-01')).number_next -= 1

        test_move2 = self.test_move.copy()
        with self.assertRaises(ValidationError):
            test_move2.post()

    def test_add_followers_on_post(self):
        # Add some existing partners, some from another company
        company = self.env['res.company'].create({'name': 'Oopo'})
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
