# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import Form, tagged, new_test_user
from odoo import Command, fields
from odoo.exceptions import UserError, RedirectWarning

from dateutil.relativedelta import relativedelta
from freezegun import freeze_time
from collections import defaultdict

@tagged('post_install', '-at_install')
class TestAccountMove(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company_data_2 = cls.setup_other_company()
        cls.other_currency = cls.setup_other_currency('HRK')

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
        cls.entry_line_vals_1 = {
            'name': 'Line 1',
            'account_id': cls.company_data['default_account_revenue'].id,
            'debit': 500.0,
            'credit': 0.0,
        }
        cls.entry_line_vals_2 = {
            'name': 'Line 2',
            'account_id': cls.company_data['default_account_expense'].id,
            'debit': 0.0,
            'credit': 500.0,
        }

    @classmethod
    def default_env_context(cls):
        # OVERRIDE
        return {}

    def test_out_invoice_auto_post_at_date(self):
        # Create auto-posted (but not recurring) entry
        nb_invoices = self.env['account.move'].search_count(domain=[])
        self.test_move.auto_post = 'at_date'
        self.test_move.date = fields.Date.today()
        with freeze_time(self.test_move.date - relativedelta(days=1)):
            self.env.ref('account.ir_cron_auto_post_draft_entry').method_direct_trigger()
            self.assertEqual(self.test_move.state, 'draft')  # can't be posted before its date
        with freeze_time(self.test_move.date + relativedelta(days=1)):
            self.env.ref('account.ir_cron_auto_post_draft_entry').method_direct_trigger()
            self.assertEqual(self.test_move.state, 'posted')  # can be posted after its date
        self.assertEqual(nb_invoices, self.env['account.move'].search_count(domain=[]))

    def test_posting_future_invoice_fails(self):
        # Create auto-posted, recurring entry, attempt manually posting it
        self.test_move.date = fields.Date.today() + relativedelta(days=1)
        self.test_move.auto_post = 'quarterly'
        self.test_move._post()  # default soft=True parameter filters out future moves
        self.assertEqual(self.test_move.state, 'draft')
        with self.assertRaisesRegex(UserError, "This move is configured to be auto-posted"):
            self.test_move._post(soft=False)

    def test_out_invoice_auto_post_monthly(self):
        # Create auto-posted entry, recurring monthly until two months later
        prev_invoices = self.env['account.move'].search(domain=[])
        self.test_move.auto_post = 'monthly'
        self.test_move.auto_post_until = fields.Date.from_string('2022-02-28')
        date = fields.Date.from_string('2021-12-30')
        self.test_move.invoice_date = date
        self.test_move.date = date  # invoice_date's onchange does not trigger from code
        self.test_move.invoice_date_due = date + relativedelta(days=1)

        self.env.ref('account.ir_cron_auto_post_draft_entry').method_direct_trigger()  # first recurrence
        new_invoices_1 = self.env['account.move'].search(domain=[]) - prev_invoices
        new_date_1 = fields.Date.from_string('2022-01-30')
        self.assertEqual(self.test_move.state, 'posted')
        self.assertEqual(1, len(new_invoices_1))  # following entry is created
        self.assertEqual('monthly', new_invoices_1.auto_post)
        self.assertEqual(new_date_1, new_invoices_1.date)
        self.assertEqual(new_date_1 + relativedelta(days=1), new_invoices_1.invoice_date_due)  # due date maintains delta with date

        self.env.ref('account.ir_cron_auto_post_draft_entry').method_direct_trigger()  # second recurrence
        new_invoices_2 = self.env['account.move'].search(domain=[]) - prev_invoices - new_invoices_1
        new_date_2 = fields.Date.from_string('2022-02-28')
        self.assertEqual(new_invoices_1.state, 'posted')
        self.assertEqual(1, len(new_invoices_2))
        self.assertEqual('monthly', new_invoices_2.auto_post)
        self.assertEqual(new_date_2, new_invoices_2.date)  # date does not overflow because of shorter month
        self.assertEqual(new_date_2 + relativedelta(days=1), new_invoices_2.invoice_date_due)
        self.assertEqual(new_invoices_2.invoice_user_id, self.test_move.invoice_user_id)

        self.env.ref('account.ir_cron_auto_post_draft_entry').method_direct_trigger()  # no more recurrences
        new_invoices_3 = self.env['account.move'].search(domain=[]) - prev_invoices - new_invoices_1 - new_invoices_2
        self.assertEqual(0, len(new_invoices_3))

    def test_custom_currency_on_account_1(self):
        custom_account = self.company_data['default_account_revenue'].copy()

        # The currency set on the account is not the same as the one set on the company.
        # It should raise an error.
        custom_account.currency_id = self.other_currency

        with self.assertRaises(UserError), self.cr.savepoint():
            self.test_move.line_ids[0].account_id = custom_account

        # The currency set on the account is the same as the one set on the company.
        # It should not raise an error.
        custom_account.currency_id = self.company_data['currency']

        self.test_move.line_ids[0].account_id = custom_account

    def test_fiscal_position_multicompany(self):
        """A move is assigned a fiscal position that matches its own company."""
        company1 = self.company_data["company"]
        company2 = self._create_company(name='company2')
        partner = self.env['res.partner'].create({'name': 'Belouga'})
        fpos1 = self.env["account.fiscal.position"].create(
            {
                "name": company1.name,
                "company_id": company1.id,
            }
        )
        fpos2 = self.env["account.fiscal.position"].create(
            {
                "name": company2.name,
                "company_id": company2.id,
            }
        )
        partner.with_company(company1).property_account_position_id = fpos1
        partner.with_company(company2).property_account_position_id = fpos2
        self.test_move.sudo().with_company(company2).partner_id = partner
        self.assertEqual(self.test_move.fiscal_position_id, fpos1)

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

        # Try to edit the account of a line.
        with self.assertRaises(UserError), self.cr.savepoint():
            self.test_move.line_ids[0].write({'account_id': self.test_move.line_ids[0].account_id.copy().id})

        # You can't remove the journal entry from a locked period.
        with self.assertRaises(UserError), self.cr.savepoint():
            self.test_move.date = fields.Date.from_string('2018-01-01')

        with self.assertRaises(UserError), self.cr.savepoint():
            self.test_move.name = "Othername"

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
        self.env['account.bank.statement.line'].create({
            'journal_id': self.company_data['default_journal_bank'].id,
            'date': '2016-01-01',
            'payment_ref': 'test',
            'amount': 10.0,
        })

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

        # Try to edit the account of a line.
        self.test_move.line_ids[0].write({'account_id': self.test_move.line_ids[0].account_id.copy().id})

        # You can't remove the journal entry from a locked period.
        with self.assertRaises(UserError), self.cr.savepoint():
            self.test_move.date = fields.Date.from_string('2018-01-01')

        with self.assertRaises(UserError), self.cr.savepoint():
            self.test_move.name = "Othername"

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

        # You can't unlink an already reconciled line.
        with self.assertRaises(UserError), self.cr.savepoint():
            draft_moves.unlink()

    def test_modify_posted_move_readonly_fields(self):
        self.test_move.action_post()

        readonly_fields = ('invoice_line_ids', 'line_ids', 'invoice_date', 'date', 'partner_id',
                           'invoice_payment_term_id', 'currency_id', 'fiscal_position_id', 'invoice_cash_rounding_id')
        for field in readonly_fields:
            with self.assertRaisesRegex(UserError, "You cannot modify the following readonly fields on a posted move"), \
                    self.cr.savepoint():
                self.test_move.write({field: False})

    def test_add_followers_on_post(self):
        # Add some existing partners, some from another company
        company = self.env['res.company'].create({'name': 'Oopo'})
        company.flush_recordset()
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
            line_form.currency_id = self.other_currency
            line_form.amount_currency = 1200.0

        # New line that should get 400.0 as credit.
        with move_form.line_ids.new() as line_form:
            line_form.name = 'credit_line'
            line_form.account_id = self.company_data['default_account_revenue']
            line_form.currency_id = self.other_currency
            line_form.amount_currency = -1200.0
        move = move_form.save()

        self.assertRecordValues(
            move.line_ids.sorted('debit'),
            [
                {
                    'currency_id': self.other_currency.id,
                    'amount_currency': -1200.0,
                    'debit': 0.0,
                    'credit': 400.0,
                },
                {
                    'currency_id': self.other_currency.id,
                    'amount_currency': 1200.0,
                    'debit': 400.0,
                    'credit': 0.0,
                },
            ],
        )

        # Change the date to change the currency conversion's rate
        with Form(move) as move_form:
            move_form.date = fields.Date.from_string('2017-01-01')

        self.assertRecordValues(
            move.line_ids.sorted('debit'),
            [
                {
                    'currency_id': self.other_currency.id,
                    'amount_currency': -1200.0,
                    'debit': 0.0,
                    'credit': 600.0,
                },
                {
                    'currency_id': self.other_currency.id,
                    'amount_currency': 1200.0,
                    'debit': 600.0,
                    'credit': 0.0,
                },
            ],
        )
        # You can change the balance manually without changing the currency amount
        with Form(move) as move_form:
            with move_form.line_ids.edit(0) as line_form:
                line_form.debit = 200
            with move_form.line_ids.edit(1) as line_form:
                line_form.credit = 200

        self.assertRecordValues(
            move.line_ids.sorted('debit'),
            [
                {
                    'currency_id': self.other_currency.id,
                    'amount_currency': -1200.0,
                    'debit': 0.0,
                    'credit': 200.0,
                },
                {
                    'currency_id': self.other_currency.id,
                    'amount_currency': 1200.0,
                    'debit': 200.0,
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
            'price_include_override': 'tax_included',
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

        # Create a third account.move.line with credit amount.
        with move_form.line_ids.new() as credit_line:
            credit_line.name = 'credit_line_1'
            credit_line.account_id = self.account
            credit_line.credit = 1200

        move = move_form.save()

        self.assertRecordValues(move.line_ids.sorted(lambda x: -x.balance), [
            {'name': 'debit_line_1',             'debit': 1000.0,    'credit': 0.0,      'tax_ids': [self.included_percent_tax.id],      'tax_line_id': False},
            {'name': 'included_tax_line',        'debit': 200.0,     'credit': 0.0,      'tax_ids': [],                                  'tax_line_id': self.included_percent_tax.id},
            {'name': 'credit_line_1',            'debit': 0.0,       'credit': 1200.0,   'tax_ids': [],                                  'tax_line_id': False},
        ])

    def test_misc_prevent_unlink_posted_items(self):
        def unlink_posted_items():
            self.test_move.line_ids.filtered(lambda l: not l.tax_repartition_line_id).balance = 0
            self.test_move.line_ids[0].unlink()

        # You cannot remove journal items if the related journal entry is posted.
        self.test_move.action_post()
        with self.assertRaises(UserError), self.cr.savepoint():
            unlink_posted_items()

        # You can remove journal items if the related journal entry is draft.
        self.test_move.button_draft()
        unlink_posted_items()

    def test_account_move_inactive_currency_raise_error_on_post(self):
        """ Ensure a move cannot be posted when using an inactive currency """
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'partner_id': self.partner_a.id,
            'date': fields.Date.from_string('2019-01-01'),
            'currency_id': self.other_currency.id,
            'line_ids': [
                (0, None, self.entry_line_vals_1),
                (0, None, self.entry_line_vals_2),
            ],
        })

        move.currency_id.active = False

        with self.assertRaises(UserError), self.cr.savepoint():
            move.action_post()

        # Make sure that the invoice can still be posted when the currency is active
        move.action_activate_currency()
        move.action_post()

        self.assertEqual(move.state, 'posted')

    def test_entry_reverse_storno(self):
        # Test creating journal entries and reverting them
        # while in Storno accounting
        self.env.company.account_storno = True

        move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2021-01-01'),
            'line_ids': [
                (0, None, self.entry_line_vals_1),
                (0, None, self.entry_line_vals_2),
            ]
        })
        move.action_post()

        move_reversal = self.env['account.move.reversal'].with_context(active_model="account.move", active_ids=move.ids).create({
            'date': fields.Date.from_string('2021-02-01'),
            'journal_id': move.journal_id.id,
        })
        reversal = move_reversal.refund_moves()
        reversed_move = self.env['account.move'].browse(reversal['res_id'])
        self.assertRecordValues(reversed_move.line_ids, [
            {
                **self.entry_line_vals_1,
                'debit': 0.0,
                'credit': 500.0,
            }, {
                **self.entry_line_vals_2,
                'debit': 500.0,
                'credit': 0.0,
            }
        ])

        reversed_move.is_storno = True

        self.assertRecordValues(reversed_move.line_ids, [
            {
                **self.entry_line_vals_1,
                'debit': -500.0,
                'credit': 0.0,
            }, {
                **self.entry_line_vals_2,
                'debit': 0.0,
                'credit': -500.0,
            }
        ])

    def test_invoice_like_entry_reverse_caba(self):
        tax_waiting_account = self.env['account.account'].create({
            'name': 'TAX_WAIT',
            'code': 'TWAIT',
            'account_type': 'liability_current',
            'reconcile': True,
        })
        tax_final_account = self.env['account.account'].create({
            'name': 'TAX_TO_DEDUCT',
            'code': 'TDEDUCT',
            'account_type': 'asset_current',
        })
        tax_base_amount_account = self.env['account.account'].create({
            'name': 'TAX_BASE',
            'code': 'TBASE',
            'account_type': 'asset_current',
        })
        self.env.company.account_cash_basis_base_account_id = tax_base_amount_account
        self.env.company.tax_exigibility = True
        tax_tags = defaultdict(dict)
        for line_type, repartition_type in [(l, r) for l in ('invoice', 'refund') for r in ('base', 'tax')]:
            tax_tags[line_type][repartition_type] = self.env['account.account.tag'].create({
                'name': '%s %s tag' % (line_type, repartition_type),
                'applicability': 'taxes',
                'country_id': self.env.ref('base.us').id,
            })
        tax = self.env['account.tax'].create({
            'name': 'cash basis 10%',
            'type_tax_use': 'sale',
            'amount': 10,
            'tax_exigibility': 'on_payment',
            'cash_basis_transition_account_id': tax_waiting_account.id,
            'invoice_repartition_line_ids': [
                (0, 0, {
                    'repartition_type': 'base',
                    'tag_ids': [(6, 0, tax_tags['invoice']['base'].ids)],
                }),
                (0, 0, {
                    'repartition_type': 'tax',
                    'account_id': tax_final_account.id,
                    'tag_ids': [(6, 0, tax_tags['invoice']['tax'].ids)],
                }),
            ],
            'refund_repartition_line_ids': [
                (0, 0, {
                    'repartition_type': 'base',
                    'tag_ids': [(6, 0, tax_tags['refund']['base'].ids)],
                }),
                (0, 0, {
                    'repartition_type': 'tax',
                    'account_id': tax_final_account.id,
                    'tag_ids': [(6, 0, tax_tags['refund']['tax'].ids)],
                }),
            ],
        })
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.from_string('2016-01-01'),
            'line_ids': [
                (0, None, {
                    'name': 'revenue line',
                    'account_id': self.company_data['default_account_revenue'].id,
                    'debit': 0.0,
                    'credit': 1000.0,
                    'tax_ids': [(6, 0, tax.ids)],
                    'tax_tag_ids': [(6, 0, tax_tags['invoice']['base'].ids)],
                }),
                (0, None, {
                    'name': 'tax line 1',
                    'account_id': tax_waiting_account.id,
                    'debit': 0.0,
                    'credit': 100.0,
                    'tax_tag_ids': [(6, 0, tax_tags['invoice']['tax'].ids)],
                    'tax_repartition_line_id': tax.invoice_repartition_line_ids.filtered(lambda x: x.repartition_type == 'tax').id,
                }),
                (0, None, {
                    'name': 'counterpart line',
                    'account_id': self.company_data['default_account_receivable'].id,
                    'debit': 1100.0,
                    'credit': 0.0,
                }),
            ]
        })
        move.action_post()
        # make payment
        payment = self.env['account.payment'].create({
            'payment_type': 'inbound',
            'payment_method_id': self.env.ref('account.account_payment_method_manual_in').id,
            'partner_type': 'customer',
            'partner_id': self.partner_a.id,
            'amount': 1100,
            'date': move.date,
            'journal_id': self.company_data['default_journal_bank'].id,
        })
        payment.action_post()
        (payment.move_id + move).line_ids.filtered(lambda x: x.account_id == self.company_data['default_account_receivable']).reconcile()
        # check caba move
        partial_rec = move.mapped('line_ids.matched_credit_ids')
        caba_move = self.env['account.move'].search([('tax_cash_basis_rec_id', '=', partial_rec.id)])
        expected_values = [
            {
                'tax_line_id': False,
                'tax_repartition_line_id': False,
                'tax_ids': [],
                'tax_tag_ids': [],
                'account_id': tax_base_amount_account.id,
                'debit': 1000.0,
                'credit': 0.0,
            },
            {
                'tax_line_id': False,
                'tax_repartition_line_id': False,
                'tax_ids': tax.ids,
                'tax_tag_ids': tax_tags['invoice']['base'].ids,
                'account_id': tax_base_amount_account.id,
                'debit': 0.0,
                'credit': 1000.0,
            },

            {
                'tax_line_id': False,
                'tax_repartition_line_id': False,
                'tax_ids': [],
                'tax_tag_ids': [],
                'account_id': tax_waiting_account.id,
                'debit': 100.0,
                'credit': 0.0,
            },
            {
                'tax_line_id': tax.id,
                'tax_repartition_line_id': tax.invoice_repartition_line_ids.filtered(lambda x: x.repartition_type == 'tax').id,
                'tax_ids': [],
                'tax_tag_ids': tax_tags['invoice']['tax'].ids,
                'account_id': tax_final_account.id,
                'debit': 0.0,
                'credit': 100.0,
            },
        ]
        self.assertRecordValues(caba_move.line_ids, expected_values)
        # unreconcile
        debit_aml = move.line_ids.filtered('debit')
        debit_aml.remove_move_reconcile()
        # check caba move reverse is same as caba move with only debit/credit inverted
        reversed_caba_move = self.env['account.move'].search([('reversed_entry_id', '=', caba_move.id)])
        for value in expected_values:
            value.update({
                'debit': value['credit'],
                'credit': value['debit'],
            })
        self.assertRecordValues(reversed_caba_move.line_ids, expected_values)

    def _get_cache_count(self, model_name='account.move', field_name='name'):
        model = self.env[model_name]
        field = model._fields[field_name]
        return len(self.env.cache.get_records(model, field))

    def test_cache_invalidation(self):
        self.env.invalidate_all()
        lines = self.test_move.line_ids
        # prefetch
        lines.mapped('move_id.name')
        # check account.move cache
        self.assertEqual(self._get_cache_count(), 1)
        lines.invalidate_recordset()
        self.assertEqual(self._get_cache_count(), 0)

    def test_misc_prevent_edit_tax_on_posted_moves(self):
        # You cannot remove journal items if the related journal entry is posted.
        def edit_tax_on_posted_moves():
            self.test_move.line_ids.filtered(lambda l: l.tax_ids).write({
                'balance': 1000.0,
                'tax_ids': False,
            })

        self.test_move.action_post()
        with self.assertRaisesRegex(UserError, "You cannot modify the taxes related to a posted journal item"),\
             self.cr.savepoint():
            edit_tax_on_posted_moves()

        with self.assertRaisesRegex(UserError, "You cannot modify the taxes related to a posted journal item"),\
             self.cr.savepoint():
            self.test_move.line_ids.filtered(lambda l: l.tax_line_id).tax_line_id = False

        # You can remove journal items if the related journal entry is draft.
        self.test_move.button_draft()
        edit_tax_on_posted_moves()

    def test_misc_tax_autobalance(self):
        # Saving an unbalanced entry isn't something desired but we need this piece of code to work in order to support
        # the tax auto-calculation on miscellaneous move. Indeed, the JS class `AutosaveMany2ManyTagsField` triggers the
        # saving of the record as soon as a tax base_line is modified.
        move = self.env["account.move"].create({
            "move_type": "entry",
            "line_ids": [
                Command.create({
                    "name": "revenue line",
                    "account_id": self.company_data["default_account_revenue"].id,
                    'tax_ids': [Command.set(self.company_data['default_tax_sale'].ids)],
                    "balance": -10.0,
                }),
            ]
        })
        tax_line = move.line_ids.filtered("tax_ids")
        tax_line.unlink()

        # But creating unbalanced misc entry shouldn't be allowed otherwise
        with self.assertRaisesRegex(UserError, r"The move \(.*\) is not balanced\."):
            self.env["account.move"].create({
                "move_type": "entry",
                "line_ids": [
                    Command.create({
                        "name": "revenue line",
                        "account_id": self.company_data["default_account_revenue"].id,
                        "balance": -10.0,
                    }),
                ]
            })

    def test_reset_draft_exchange_move(self):
        """ Ensure you can't reset to draft an exchange journal entry """
        moves = self.env['account.move'].create([
            {
                'date': '2016-01-01',
                'line_ids': [
                    Command.create({
                        'name': "line1",
                        'account_id': self.company_data['default_account_receivable'].id,
                        'currency_id': self.other_currency.id,
                        'balance': 400.0,
                        'amount_currency': 1200.0,
                    }),
                    Command.create({
                        'name': "line2",
                        'account_id': self.company_data['default_account_expense'].id,
                        'balance': -400.0,
                    }),
                ]
            },
            {
                'date': '2017-01-01',
                'line_ids': [
                    Command.create({
                        'name': "line1",
                        'account_id': self.company_data['default_account_receivable'].id,
                        'currency_id': self.other_currency.id,
                        'balance': -600.0,
                        'amount_currency': -1200.0,
                    }),
                    Command.create({
                        'name': "line2",
                        'account_id': self.company_data['default_account_expense'].id,
                        'balance': 600.0,
                    }),
                ]
            },
        ])
        moves.action_post()

        moves.line_ids\
            .filtered(lambda x: x.account_id == self.company_data['default_account_receivable'])\
            .reconcile()

        exchange_diff = moves.line_ids.matched_debit_ids.exchange_move_id
        self.assertTrue(exchange_diff)
        with self.assertRaises(UserError), self.cr.savepoint():
            exchange_diff.button_draft()

    def test_always_exigible_caba_account(self):
        """ Always exigible misc operations (so, the ones without payable/receivable line) with cash basis
        taxes should see their tax lines use the final tax account, not the transition account.
        """
        tax_account = self.company_data['default_account_tax_sale']

        caba_tax = self.env['account.tax'].create({
            'name': "CABA",
            'amount_type': 'percent',
            'amount': 20.0,
            'tax_exigibility': 'on_payment',
            'cash_basis_transition_account_id': self.safe_copy(tax_account).id,
            'invoice_repartition_line_ids': [
                (0, 0, {
                    'repartition_type': 'base',
                }),
                (0, 0, {
                    'repartition_type': 'tax',
                    'account_id': tax_account.id,
                }),
            ],
            'refund_repartition_line_ids': [
                (0, 0, {
                    'repartition_type': 'base',
                }),
                (0, 0, {
                    'repartition_type': 'tax',
                    'account_id': tax_account.id,
                }),
            ],
        })

        move_form = Form(self.env['account.move'].with_context(default_move_type='entry'))

        # Create a new account.move.line with debit amount.
        income_account = self.company_data['default_account_revenue']
        with move_form.line_ids.new() as debit_line:
            debit_line.name = 'debit'
            debit_line.account_id = income_account
            debit_line.debit = 120

        with move_form.line_ids.new() as credit_line:
            credit_line.name = 'credit'
            credit_line.account_id = income_account
            credit_line.credit = 100
            credit_line.tax_ids.clear()
            credit_line.tax_ids.add(caba_tax)

        move = move_form.save()

        self.assertTrue(move.always_tax_exigible)

        self.assertRecordValues(move.line_ids.sorted(lambda x: -x.balance), [
            # pylint: disable=C0326
            {'name': 'debit',  'debit': 120.0, 'credit': 0.0,   'account_id': income_account.id, 'tax_ids': [],           'tax_line_id': False},
            {'name': 'CABA',   'debit': 0.0,   'credit': 20.0,  'account_id': tax_account.id,    'tax_ids': [],           'tax_line_id': caba_tax.id},
            {'name': 'credit', 'debit': 0.0,   'credit': 100.0, 'account_id': income_account.id, 'tax_ids': caba_tax.ids, 'tax_line_id': False},
        ])

    def test_misc_with_taxes_reverse(self):
        test_account = self.company_data['default_account_revenue']

        # With a sale tax
        sale_tax = self.company_data['default_tax_sale']

        move_form = Form(self.env['account.move'])

        with move_form.line_ids.new() as debit_line_form:
            debit_line_form.name = 'debit'
            debit_line_form.account_id = test_account
            debit_line_form.debit = 115

        with move_form.line_ids.new() as credit_line_form:
            credit_line_form.name = 'credit'
            credit_line_form.account_id = test_account
            credit_line_form.credit = 100
            credit_line_form.tax_ids.clear()
            credit_line_form.tax_ids.add(sale_tax)

        sale_move = move_form.save()

        sale_invoice_rep_line = sale_tax.invoice_repartition_line_ids.filtered(lambda x: x.repartition_type == 'tax')

        self.assertRecordValues(sale_move.line_ids.sorted(lambda x: -x.balance), [
            # pylint: disable=C0326
            {'name': 'debit',  'debit': 115.0, 'credit':   0.0, 'account_id': test_account.id,                                  'tax_ids': [],           'tax_base_amount': 0,   'tax_tag_invert': False, 'tax_repartition_line_id': False},
            {'name': '15%',    'debit':   0.0, 'credit':  15.0, 'account_id': self.company_data['default_account_tax_sale'].id, 'tax_ids': [],           'tax_base_amount': 100, 'tax_tag_invert': True,  'tax_repartition_line_id': sale_invoice_rep_line.id},
            {'name': 'credit', 'debit':   0.0, 'credit': 100.0, 'account_id': test_account.id,                                  'tax_ids': sale_tax.ids, 'tax_base_amount': 0,   'tax_tag_invert': True,  'tax_repartition_line_id': False},
        ])

        # Same with a purchase tax
        purchase_tax = self.company_data['default_tax_purchase']

        move_form = Form(self.env['account.move'])

        with move_form.line_ids.new() as credit_line_form:
            credit_line_form.name = 'credit'
            credit_line_form.account_id = test_account
            credit_line_form.credit = 115

        with move_form.line_ids.new() as debit_line_form:
            debit_line_form.name = 'debit'
            debit_line_form.account_id = test_account
            debit_line_form.debit = 100
            debit_line_form.tax_ids.clear()
            debit_line_form.tax_ids.add(purchase_tax)

        purchase_move = move_form.save()

        purchase_invoice_rep_line = purchase_tax.invoice_repartition_line_ids.filtered(lambda x: x.repartition_type == 'tax')
        self.assertRecordValues(purchase_move.line_ids.sorted(lambda x: x.balance), [
            # pylint: disable=C0326
            {'name': 'credit', 'credit': 115.0, 'debit':   0.0, 'account_id': test_account.id,                                      'tax_ids': [],               'tax_base_amount': 0,   'tax_tag_invert': False, 'tax_repartition_line_id': False},
            {'name': '15%',    'credit':   0.0, 'debit':  15.0, 'account_id': self.company_data['default_account_tax_purchase'].id, 'tax_ids': [],               'tax_base_amount': 100, 'tax_tag_invert': False,  'tax_repartition_line_id': purchase_invoice_rep_line.id},
            {'name': 'debit',  'credit':   0.0, 'debit': 100.0, 'account_id': test_account.id,                                      'tax_ids': purchase_tax.ids, 'tax_base_amount': 0,   'tax_tag_invert': False,  'tax_repartition_line_id': False},
        ])

    @freeze_time('2021-10-01 00:00:00')
    def test_change_journal_account_move(self):
        """Changing the journal should change the name of the move"""
        journal = self.env['account.journal'].create({
            'name': 'awesome journal',
            'type': 'general',
            'code': 'AJ',
        })
        move = self.env['account.move'].with_context(default_move_type='entry')
        with Form(move) as move_form:
            self.assertEqual(move_form.name_placeholder, 'MISC/2021/10/0001')
            move_form.journal_id, journal = journal, move_form.journal_id
            self.assertEqual(move_form.name_placeholder, 'AJ/2021/10/0001')
            # ensure we aren't burning any sequence by switching journal
            move_form.journal_id, journal = journal, move_form.journal_id
            self.assertEqual(move_form.name_placeholder, 'MISC/2021/10/0001')
            move_form.journal_id, journal = journal, move_form.journal_id
            self.assertEqual(move_form.name_placeholder, 'AJ/2021/10/0001')

    def test_change_journal_posted_before(self):
        """ Changes to a move posted before can only de done if move name is '/' or empty (False) """
        journal = self.env['account.journal'].create({
            'name': 'awesome journal',
            'type': 'general',
            'code': 'AJ',
        })
        self.test_move.action_post()
        self.test_move.button_draft()  # move has posted_before == True
        self.assertEqual(self.test_move.journal_id, self.company_data['default_journal_misc'])
        self.assertEqual(self.test_move.name, 'MISC/2016/01/0001')
        with self.assertRaisesRegex(UserError, 'You cannot edit the journal of an account move if it has been posted once, unless the name is removed or set to "/". This might create a gap in the sequence.'):
            self.test_move.write({'journal_id': False})
        # Once move name in draft is changed to '/', changing the journal is allowed
        self.test_move.name = '/'
        self.test_move.journal_id = journal
        self.test_move.action_post()
        self.assertEqual(self.test_move.name, 'AJ/2016/01/0001')
        self.assertEqual(self.test_move.journal_id, journal)

    def test_change_journal_sequence_number(self):
        """ Changes to an account move with a sequence number assigned can only de done
        if the move name is '/' or empty (False)
        """
        journal = self.env['account.journal'].create({
            'name': 'awesome journal',
            'type': 'general',
            'code': 'AJ',
        })
        # Post move with sequence number 1 and create new move with sequence number 2
        self.test_move.action_post()
        test_move_2 = self.test_move.copy({'name': 'TEST/2016/01/0002', 'date': '2016-01-01'})
        self.assertEqual(test_move_2.sequence_number, 2)
        self.assertEqual(test_move_2.journal_id, self.company_data['default_journal_misc'])
        with self.assertRaisesRegex(UserError, 'You cannot edit the journal of an account move with a sequence number assigned, unless the name is removed or set to "/". This might create a gap in the sequence.'):
            test_move_2.write({'journal_id': False})
        # Once move name in draft is changed to '/', changing the journal is allowed
        test_move_2.write({'name': False, 'journal_id': journal.id})
        test_move_2.action_post()
        # Sequence number is updated for the new journal
        self.assertEqual(test_move_2.sequence_number, 1)
        self.assertEqual(test_move_2.journal_id, journal)

    def test_manually_modifying_taxes(self):
        """Manually modifying taxes on a move should not automatically recompute them"""
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'line_ids': [
                Command.create({
                    'name': 'Receivable',
                    'account_id': self.company_data['default_account_receivable'].id,
                    'debit': 0.0,
                    'credit': 5531.04,
                }),
                Command.create({
                    'name': 'Revenue',
                    'account_id': self.company_data['default_account_revenue'].id,
                    'tax_ids': [Command.set(self.company_data['default_tax_sale'].ids)],
                    'debit': 4809.61,
                    'credit': 0.0,
                }),
            ]
        })
        tax_line = move.line_ids.filtered('tax_repartition_line_id')
        self.assertEqual(tax_line.debit, 721.44)
        with Form(move) as move_form:
            with move_form.line_ids.edit(2) as line_form:
                line_form.debit = 721.43
            move_form.line_ids.remove(3)
        move = move_form.save()
        tax_line = move.line_ids.filtered('tax_repartition_line_id')
        self.assertEqual(tax_line.debit, 721.43)

    def test_line_steal(self):
        honest_move = self.env['account.move'].create({
            'line_ids': [
                Command.create({
                    'name': 'receivable',
                    'account_id': self.company_data['default_account_receivable'].id,
                    'balance': 500.0,
                }),
                Command.create({
                    'name': 'tax',
                    'account_id': self.company_data['default_account_tax_sale'].id,
                    'balance': -500.0,
                }),
            ]
        })
        honest_move.action_post()

        with self.assertRaisesRegex(UserError, 'not balanced'), self.env.cr.savepoint():
            self.env['account.move'].create({'line_ids': [Command.set(honest_move.line_ids[0].ids)]})

        with self.assertRaisesRegex(UserError, 'not balanced'), self.env.cr.savepoint():
            self.env['account.move'].create({'line_ids': [Command.link(honest_move.line_ids[0].id)]})

        stealer_move = self.env['account.move'].create({})
        with self.assertRaisesRegex(UserError, 'not balanced'), self.env.cr.savepoint():
            stealer_move.write({'line_ids': [Command.set(honest_move.line_ids[0].ids)]})

        with self.assertRaisesRegex(UserError, 'not balanced'), self.env.cr.savepoint():
            stealer_move.write({'line_ids': [Command.link(honest_move.line_ids[0].id)]})

    def test_validate_move_wizard_with_auto_post_entry(self):
        """ Test that the wizard to validate a move with auto_post is working fine. """
        self.test_move.date = fields.Date.today() + relativedelta(months=3)
        self.test_move.auto_post = 'at_date'
        wizard = self.env['validate.account.move'].with_context(active_model='account.move', active_ids=self.test_move.ids).create({})
        wizard.force_post = True
        wizard.validate_move()
        self.assertTrue(self.test_move.state == 'posted')

    def test_cumulated_balance(self):
        move = self.env['account.move'].create({
            'line_ids': [Command.create({
                'balance': 100,
                'account_id': self.company_data['default_account_receivable'].id,
            }), Command.create({
                'balance': 100,
                'account_id': self.company_data['default_account_tax_sale'].id,
            }), Command.create({
                'balance': -200,
                'account_id': self.company_data['default_account_revenue'].id,
            })]
        })

        for order, expected in [
            ('balance DESC', [
                (100, 0),
                (100, -100),
                (-200, -200),
            ]),
            ('balance ASC', [
                (-200, 0),
                (100, 200),
                (100, 100),
            ]),
        ]:
            read_results = self.env['account.move.line'].search_read(
                domain=[('move_id', '=', move.id)],
                fields=['balance', 'cumulated_balance'],
                order=order,
            )
            for (balance, cumulated_balance), read_result in zip(expected, read_results):
                self.assertAlmostEqual(balance, read_result['balance'])
                self.assertAlmostEqual(cumulated_balance, read_result['cumulated_balance'])

    def test_move_line_rounding(self):
        """Whatever arguments we give to the creation of an account move,
        in every case the amounts should be properly rounded to the currency's precision.
        In other words, we don't fall victim of the limitation introduced by 9d87d15db6dd40

        Here the rounding should be done according to company_currency_id, which is a related
        on move_id.company_id.currency_id.
        In principle, it should not be necessary to add it to the create values,
        since it is supposed to be computed by the ORM...
        """
        move = self.env['account.move'].create({
            'line_ids': [
                (0, 0, {'debit': 100.0 / 3, 'account_id': self.company_data['default_account_revenue'].id}),
                (0, 0, {'credit': 100.0 / 3, 'account_id': self.company_data['default_account_revenue'].id}),
            ],
        })

        self.assertEqual(
            [(33.33, 0.0), (0.0, 33.33)],
            move.line_ids.mapped(lambda x: (x.debit, x.credit)),
            "Quantities should have been rounded according to the currency."
        )

    def test_journal_entry_clear_taxes(self):
        """
        This test checks that tax tags on journal entries lines are updated according to the taxes on each line
        In other words, removing a tax from a line should remove its tags from that line
        """
        def _create_tax_tag(tag_name):
            return self.env['account.account.tag'].create({
                'name': tag_name,
                'applicability': 'taxes',
                'country_id': self.env.company.country_id.id,
            })

        def _create_tax(tax_percent):
            return self.env['account.tax'].create({
                'name': f'VAT {tax_percent}%',
                'type_tax_use': 'sale',
                'amount': tax_percent,
                'invoice_repartition_line_ids': [
                    Command.create({
                        'repartition_type': 'base',
                        'tag_ids': _create_tax_tag(f'invoice_base_{tax_percent}').ids,
                    }),
                    Command.create({
                        'repartition_type': 'tax',
                        'tag_ids': _create_tax_tag(f'invoice_tax_{tax_percent}').ids,
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.create({
                        'repartition_type': 'base',
                        'tag_ids': _create_tax_tag(f'refund_base_{tax_percent}').ids,
                    }),
                    Command.create({
                        'repartition_type': 'tax',
                        'tag_ids': _create_tax_tag(f'refund_tax_{tax_percent}').ids,
                    }),
                ],
            })

        tax_1 = _create_tax(10)
        tax_2 = _create_tax(15)

        move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2019-01-01',
            'journal_id': self.company_data['default_journal_sale'].id,
            'line_ids': [
                Command.create({
                    'debit': 0.0,
                    'credit': 0.0,
                    'account_id': self.company_data['default_account_payable'].id,
                    'tax_ids': [Command.set([tax_1.id, tax_2.id])],
                })
            ],
        })
        line = move.line_ids[0]
        self.assertEqual(len(line.tax_ids), 2)
        self.assertEqual(len(line.tax_tag_ids), 2)

        line.tax_ids = [Command.set(tax_1.ids)]
        self.assertEqual(len(line.tax_ids), 1)
        self.assertEqual(len(line.tax_tag_ids), 1)

        line.tax_ids = [Command.clear()]
        self.assertEqual(len(line.tax_ids), 0)
        self.assertEqual(len(line.tax_tag_ids), 0)

    def test_balance_modification_auto_balancing(self):
        """ Test that amount currency is correctly recomputed when, without multicurrency enabled,
        the balance is changed """
        account = self.company_data['default_account_revenue']
        move = self.env['account.move'].create({
            'line_ids': [
                Command.create({
                    'account_id': self.company_data['default_account_receivable'].id,
                    'balance': 20,
                }), Command.create({
                    'account_id': account.id,
                    'balance': -20,
                })]
        })
        line = move.line_ids.filtered(lambda l: l.account_id == account)
        move.write({
            'line_ids': [
                Command.update(line.id, {
                    'debit': 10,
                    'credit': 0,
                    'balance': 10
                }),
                Command.create({
                    'account_id': account.id,
                    'balance': -30,
                })]
        })

        self.assertRecordValues(line, [
            {'amount_currency': 10.00, 'balance': 10.00},
        ])
