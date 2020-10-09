# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests.common import Form
from odoo.tests import tagged, new_test_user
from odoo import fields
from odoo.exceptions import UserError, ValidationError

from dateutil.relativedelta import relativedelta
from freezegun import freeze_time


@tagged('post_install', '-at_install')
class TestAccountMoveMisc(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        tax_repartition_line = cls.company_data['default_tax_sale'].invoice_repartition_line_ids\
            .filtered(lambda line: line.repartition_type == 'tax')
        cls.test_move = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': '2016-01-01',
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

    # -------------------------------------------------------------------------
    # POST
    # -------------------------------------------------------------------------

    @freeze_time('2017-01-01')
    def test_invoice_post_no_invoice_date(self):
        ''' Check the invoice_date will be set automatically at the post date. '''

        # Create an invoice with rate 1/3.
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': False,
            'date': '2016-01-01',
            'currency_id': self.currency_data['currency'].id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_a.id,
                'tax_ids': [(6, 0, (self.tax_sale_a + self.tax_sale_b).ids)],
            })],
        })

        # Remove the invoice_date to check:
        # - The invoice_date must be set automatically at today during the post.
        # - As the invoice_date changed, date did too so the currency rate has changed (1/3 => 1/2).
        # - A different invoice_date implies also a new date_maturity.
        # Add a manual edition of a tax line:
        # - The modification must be preserved in the business fields.
        # - The journal entry must be balanced before / after the post.
        tax_line_1 = invoice.line_ids.filtered(lambda line: line.tax_line_id == self.tax_sale_a)
        tax_line_2 = invoice.line_ids.filtered(lambda line: line.tax_line_id == self.tax_sale_b)
        invoice.write({
            'line_ids': [
                (1, tax_line_1.id, {'amount_currency': tax_line_1.amount_currency + 10.0}),
                (1, tax_line_2.id, {'amount_currency': tax_line_2.amount_currency - 10.0}),
            ],
        })

        # Post when the currency conversion rate is 1/2.
        invoice.action_post()

        self.assertInvoiceValues(invoice, [
            {
                'product_id': self.product_a.id,
                'tax_line_id': False,
                'tax_ids': (self.tax_sale_a + self.tax_sale_b).ids,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -3000.0,
                'credit': 1500.0,
                'debit': 0.0,
            },
            {
                'product_id': False,
                'tax_line_id': self.tax_sale_a.id,
                'tax_ids': [],
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -440.0,
                'credit': 220.0,
                'debit': 0.0,
            },
            {
                'product_id': False,
                'tax_line_id': self.tax_sale_b.id,
                'tax_ids': [],
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -460.0,
                'credit': 230.0,
                'debit': 0.0,
            },
            {
                'product_id': False,
                'tax_line_id': False,
                'tax_ids': [],
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 3900.0,
                'credit': 0.0,
                'debit': 1950.0,
            },
        ], {
            'currency_id': self.currency_data['currency'].id,
            'date': fields.Date.from_string('2017-01-01'),
            'invoice_date': fields.Date.from_string('2017-01-01'),
            'invoice_date_due': fields.Date.from_string('2017-01-01'),
            'amount_untaxed': 3000.0,
            'amount_tax': 900.0,
            'amount_total': 3900.0,
        })

    def test_invoice_post_tax_lock_date(self):
        ''' Check the date will be set automatically at the next available post date due to the tax lock date. '''

        # Create an invoice with rate 1/3.
        # Create an invoice with rate 1/3.
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2016-01-01',
            'date': '2016-01-01',
            'currency_id': self.currency_data['currency'].id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_a.id,
                'tax_ids': [(6, 0, (self.tax_sale_a + self.tax_sale_b).ids)],
            })],
        })

        # Add a manual edition of a tax line:
        # - The modification must be preserved in the business fields.
        # - The journal entry must be balanced before / after the post.
        tax_line_1 = invoice.line_ids.filtered(lambda line: line.tax_line_id == self.tax_sale_a)
        tax_line_2 = invoice.line_ids.filtered(lambda line: line.tax_line_id == self.tax_sale_b)
        invoice.write({
            'line_ids': [
                (1, tax_line_1.id, {'amount_currency': tax_line_1.amount_currency + 30.0}),
                (1, tax_line_2.id, {'amount_currency': tax_line_2.amount_currency - 30.0}),
            ],
        })

        # Set the tax lock date:
        # - The date must be set automatically at the date after the tax_lock_date.
        # - As the date changed, the currency rate has changed (1/3 => 1/2).
        invoice.company_id.tax_lock_date = fields.Date.from_string('2016-12-31')

        invoice.action_post()

        self.assertInvoiceValues(invoice, [
            {
                'product_id': self.product_a.id,
                'tax_line_id': False,
                'tax_ids': (self.tax_sale_a + self.tax_sale_b).ids,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -3000.0,
                'credit': 1500.0,
                'debit': 0.0,
            },
            {
                'product_id': False,
                'tax_line_id': self.tax_sale_a.id,
                'tax_ids': [],
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -420.0,
                'credit': 210.0,
                'debit': 0.0,
            },
            {
                'product_id': False,
                'tax_line_id': self.tax_sale_b.id,
                'tax_ids': [],
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -480.0,
                'credit': 240.0,
                'debit': 0.0,
            },
            {
                'product_id': False,
                'tax_line_id': False,
                'tax_ids': [],
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 3900.0,
                'credit': 0.0,
                'debit': 1950.0,
            },
        ], {
            'currency_id': self.currency_data['currency'].id,
            'date': fields.Date.from_string('2017-01-01'),
            'invoice_date': fields.Date.from_string('2016-01-01'),
            'invoice_date_due': fields.Date.from_string('2016-01-01'),
            'amount_untaxed': 3000.0,
            'amount_tax': 900.0,
            'amount_total': 3900.0,
        })

    def test_add_followers_on_post(self):
        # Add some existing partners, some from another company
        existing_partners = self.env['res.partner'].create([
            {'name': 'Jean', 'company_id': self.company_data_2['company'].id},
            {'name': 'Paulus'},
        ])
        self.test_move.message_subscribe(existing_partners.ids)

        user = new_test_user(self.env, login='jag', groups='account.group_account_invoice')

        move = self.test_move.with_user(user)
        partner = self.env['res.partner'].create({'name': 'Belouga'})
        move.partner_id = partner

        move.action_post()
        self.assertEqual(move.message_partner_ids, self.env.user.partner_id | existing_partners | partner)

    # -------------------------------------------------------------------------
    # LOAD FROM PAST VENDOR BILL
    # -------------------------------------------------------------------------

    def test_load_from_past_vendor_bill(self):
        ''' Test the loading of a previous vendor bill using the 'invoice_vendor_bill_id' field. '''

        old_vendor_bill = self.env['account.move'].create({
            'invoice_date': '2016-01-01',
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'currency_id': self.currency_data['currency'].id,
            'invoice_payment_term_id': self.pay_terms_b.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_a.id,
                'quantity': 5.0,
                'price_unit': 200.0,
                'tax_ids': [(6, 0, self.tax_purchase_a.ids)],
            })],
        })

        move_form = Form(self.env['account.move'].with_context(default_move_type='in_invoice'))
        move_form.invoice_date = fields.Date.from_string('2017-01-01')
        move_form.partner_id = self.partner_a
        move_form.invoice_vendor_bill_id = old_vendor_bill
        new_vendor_bill = move_form.save()

        self.assertInvoiceValues(new_vendor_bill, [
            {
                'product_id': self.product_a.id,
                'quantity': 5,
                'price_unit': 200.0,
                'tax_line_id': False,
                'tax_ids': self.tax_purchase_a.ids,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 1000.0,
                'credit': 0.0,
                'debit': 500.0,
            },
            {
                'product_id': False,
                'quantity': 1.0,
                'price_unit': 0.0,
                'tax_line_id': self.tax_purchase_a.id,
                'tax_ids': [],
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 150.0,
                'credit': 0.0,
                'debit': 75.0,
            },
            {
                'product_id': False,
                'quantity': 1.0,
                'price_unit': 0.0,
                'tax_line_id': False,
                'tax_ids': [],
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -805.0,
                'credit': 402.5,
                'debit': 0.0,
            },
            {
                'product_id': False,
                'quantity': 1.0,
                'price_unit': 0.0,
                'tax_line_id': False,
                'tax_ids': [],
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -345.0,
                'credit': 172.5,
                'debit': 0.0,
            },
        ], {
            'invoice_vendor_bill_id': False,
            'partner_id': self.partner_a.id,
            'currency_id': self.currency_data['currency'].id,
            'invoice_payment_term_id': self.pay_terms_b.id,
            'amount_untaxed': 1000.0,
            'amount_tax': 150.0,
            'amount_total': 1150.0,
        })

    # -------------------------------------------------------------------------
    # CONSTRAINTS
    # -------------------------------------------------------------------------

    def test_invoice_writing_bad_account(self):
        ''' Ensure to not messing the invoice when writing a bad account type. '''

        copy_receivable = self.copy_account(self.company_data['default_account_receivable'])
        copy_revenue = self.copy_account(self.company_data['default_account_revenue'])

        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_a.id,
                'tax_ids': [(6, 0, self.product_a.taxes_id.ids)],
            })],
        })

        receivable_line = move.line_ids.filtered(lambda line: line.account_id.user_type_id.type == 'receivable')
        revenue_line = move.invoice_line_ids

        # Write a receivable account on a not-receivable line.
        with self.assertRaises(UserError), self.cr.savepoint():
            revenue_line.write({'account_id': copy_receivable.id})

        # Write a not-receivable account on a receivable line.
        with self.assertRaises(UserError), self.cr.savepoint():
            receivable_line.write({'account_id': copy_revenue.id})

        # Write another receivable account on a receivable line.
        receivable_line.write({'account_id': copy_receivable.id})

    def test_duplicate_supplier_reference(self):
        ''' Ensure two vendor bills can't share the same vendor reference. '''
        vendor_bill_1 = self.env['account.move'].create({
            'ref': 'a supplier reference',
            'invoice_date': '2016-01-01',
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [(0, 0, {'product_id': self.product_a.id})],
        })
        vendor_bill_2 = vendor_bill_1.copy(default={'invoice_date': '2016-01-01'})

        with self.assertRaises(ValidationError):
            vendor_bill_2.ref = 'a supplier reference'

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

    def test_fiscalyear_lock_date(self):
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

    def test_tax_lock_date(self):
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
                    'name': 'revenue line 3',
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
        copy_move.action_post()

        # You can't change the date to one being in a locked period.
        with self.assertRaises(UserError), self.cr.savepoint():
            copy_move.date = fields.Date.from_string('2017-01-01')

    def test_draft_entry_already_reconciled_entries(self):
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

    def test_always_balanced_move(self):
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

    def test_prevent_unlink_posted_items(self):
        self.test_move.action_post()

        # You cannot remove journal items if the related journal entry is posted.
        with self.assertRaises(UserError), self.cr.savepoint():
            self.test_move.line_ids.unlink()

    # -------------------------------------------------------------------------
    # OTHERS
    # -------------------------------------------------------------------------

    def test_orm_computed_currency_rounding(self):
        '''Whatever arguments we give to the creation of an account move,
        in every case the amounts should be properly rounded to the currency's precision.
        In other words, we don't fall victim of the limitation introduced by 9d87d15db6dd40

        Here the rounding should be done according to company_currency_id, which is a related
        on move_id.company_id.currency_id.
        In principle, it should not be necessary to add it to the create values,
        since it is supposed to be computed by the ORM...
        '''
        random_account = self.company_data['default_account_revenue']
        move = self.env['account.move'].create({
            'line_ids': [
                (0, 0, {'name': 'debit_line',   'account_id': random_account.id,    'debit': 33.3333333}),
                (0, 0, {'name': 'credit_line',  'account_id': random_account.id,    'credit': 33.3333333}),
            ],
        })

        self.cr.execute('''
            SELECT debit, credit
            FROM account_move_line
            WHERE move_id = %s
            ORDER BY debit, credit
        ''', [move.id])
        res = self.cr.fetchall()
        self.assertEqual(res[0], (0.0, 33.33))
        self.assertEqual(res[1], (33.33, 0.0))

    def test_out_invoice_recomputation_receivable_lines(self):
        ''' Test a tricky specific case caused by some framework limitations. Indeed, when
        saving a record, some fields are written to the records even if the value is the same
        as the previous one. It could lead to an unbalanced journal entry when the recomputed
        line is the receivable/payable one.

        For example, the computed price_subtotal are the following:
        1471.95 / 0.14 = 10513.93
        906468.18 / 0.14 = 6474772.71
        1730.84 / 0.14 = 12363.14
        17.99 / 0.14 = 128.50
        SUM = 6497778.28

        But when recomputing the receivable line:
        909688.96 / 0.14 = 6497778.285714286 => 6497778.29

        This recomputation was made because the framework was writing the same 'price_unit'
        as the previous value leading to a recomputation of the debit/credit.
        '''
        self.env['decimal.precision'].search([
            ('name', '=', self.env['account.move.line']._fields['price_unit']._digits),
        ]).digits = 5

        self.env['res.currency.rate'].create({
            'name': '2019-01-01',
            'rate': 0.14,
            'currency_id': self.currency_data['currency'].id,
            'company_id': self.company_data['company'].id,
        })

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2019-01-01',
            'date': '2019-01-01',
            'partner_id': self.partner_a.id,
            'currency_id': self.currency_data['currency'].id,
            'invoice_payment_term_id': self.env.ref('account.account_payment_term_immediate').id,
            'invoice_line_ids': [
                (0, 0, {'name': 'line1', 'price_unit': 38.73553, 'quantity': 38.0}),
                (0, 0, {'name': 'line2', 'price_unit': 4083.19000, 'quantity': 222.0}),
                (0, 0, {'name': 'line3', 'price_unit': 49.45257, 'quantity': 35.0}),
                (0, 0, {'name': 'line4', 'price_unit': 17.99000, 'quantity': 1.0}),
            ],
        })

        # assertNotUnbalancedEntryWhenSaving
        with Form(invoice) as move_form:
            move_form.invoice_payment_term_id = self.env.ref('account.account_payment_term_30days')

    def test_out_invoice_rounding_recomputation_receivable_lines(self):
        ''' Test rounding error due to the fact that subtracting then rounding is different from
        rounding then subtracting.
        '''
        self.env['decimal.precision'].search([
            ('name', '=', self.env['account.move.line']._fields['price_unit']._digits),
        ]).digits = 5

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2019-01-01',
            'date': '2019-01-01',
            'partner_id': self.partner_a.id,
            'invoice_payment_term_id': self.env.ref('account.account_payment_term_immediate').id,
        })

        # assertNotUnbalancedEntryWhenSaving
        with Form(invoice) as move_form:
            with move_form.invoice_line_ids.new() as line_form:
                line_form.name = 'line1'
                line_form.account_id = self.company_data['default_account_revenue']
                line_form.tax_ids.clear()
                line_form.price_unit = 0.89500
        move_form.save()
