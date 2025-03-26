from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo import Command
from odoo.addons.account.tests.test_account_journal_dashboard_common import TestAccountJournalDashboardCommon
from odoo.tests import tagged
from odoo.tools.misc import format_amount

@tagged('post_install', '-at_install')
class TestAccountJournalDashboard(TestAccountJournalDashboardCommon):

    @freeze_time("2019-01-22")
    def test_customer_invoice_dashboard(self):
        # This test is defined in the account_3way_match module with different values, so we skip it when the module is installed
        if self.env['ir.module.module'].search([('name', '=', 'account_3way_match')]).state == 'installed':
            self.skipTest("This test won't work if account_3way_match is installed")

        journal = self.company_data['default_journal_sale']

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'journal_id': journal.id,
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-21',
            'date': '2019-01-21',
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_a.id,
                'quantity': 40.0,
                'name': 'product test 1',
                'discount': 10.00,
                'price_unit': 2.27,
                'tax_ids': [],
            })]
        })
        refund = self.env['account.move'].create({
            'move_type': 'out_refund',
            'journal_id': journal.id,
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-21',
            'date': '2019-01-21',
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_a.id,
                'quantity': 1.0,
                'name': 'product test 1',
                'price_unit': 13.3,
                'tax_ids': [],
            })]
        })

        # Check Draft
        dashboard_data = journal._get_journal_dashboard_data_batched()[journal.id]

        self.assertEqual(dashboard_data['number_draft'], 2)
        self.assertIn('68.42', dashboard_data['sum_draft'])

        self.assertEqual(dashboard_data['number_waiting'], 0)
        self.assertIn('0.00', dashboard_data['sum_waiting'])

        # Check Both
        invoice.action_post()

        dashboard_data = journal._get_journal_dashboard_data_batched()[journal.id]
        self.assertEqual(dashboard_data['number_draft'], 1)
        self.assertIn('-\N{ZERO WIDTH NO-BREAK SPACE}13.30', dashboard_data['sum_draft'])

        self.assertEqual(dashboard_data['number_waiting'], 1)
        self.assertIn('81.72', dashboard_data['sum_waiting'])

        # Check partial on invoice
        partial_payment = self.env['account.payment'].create({
            'amount': 13.3,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_a.id,
        })
        partial_payment.action_post()

        (invoice + partial_payment.move_id).line_ids.filtered(lambda line: line.account_type == 'asset_receivable').reconcile()

        dashboard_data = journal._get_journal_dashboard_data_batched()[journal.id]
        self.assertEqual(dashboard_data['number_draft'], 1)
        self.assertIn('13.3', dashboard_data['sum_draft'])

        self.assertEqual(dashboard_data['number_waiting'], 1)
        self.assertIn('68.42', dashboard_data['sum_waiting'])

        # Check waiting payment
        refund.action_post()

        dashboard_data = journal._get_journal_dashboard_data_batched()[journal.id]
        self.assertEqual(dashboard_data['number_draft'], 0)
        self.assertIn('0.00', dashboard_data['sum_draft'])

        self.assertEqual(dashboard_data['number_waiting'], 2)
        self.assertIn('55.12', dashboard_data['sum_waiting'])

        # Check partial on refund
        payment = self.env['account.payment'].create({
            'amount': 10.0,
            'payment_type': 'outbound',
            'partner_type': 'customer',
            'partner_id': self.partner_a.id,
        })
        payment.action_post()

        (refund + payment.move_id).line_ids\
            .filtered(lambda line: line.account_type == 'asset_receivable')\
            .reconcile()

        dashboard_data = journal._get_journal_dashboard_data_batched()[journal.id]
        self.assertEqual(dashboard_data['number_draft'], 0)
        self.assertIn('0.00', dashboard_data['sum_draft'])

        self.assertEqual(dashboard_data['number_waiting'], 2)
        self.assertIn('65.12', dashboard_data['sum_waiting'])

        dashboard_data = journal._get_journal_dashboard_data_batched()[journal.id]
        self.assertEqual(dashboard_data['number_late'], 2)
        self.assertIn('65.12', dashboard_data['sum_late'])

    def test_sale_purchase_journal_for_purchase(self):
        """
        Test different purchase journal setups with or without multicurrency:
            1) Journal with no currency, bills in foreign currency -> dashboard data should be displayed in company currency
            2) Journal in foreign currency, bills in foreign currency -> dashboard data should be displayed in foreign currency
            3) Journal in foreign currency, bills in company currency -> dashboard data should be displayed in foreign currency
            4) Journal in company currency, bills in company currency -> dashboard data should be displayed in company currency
            5) Journal in company currency, bills in foreign currency -> dashboard data should be displayed in company currency
        """
        # This test is defined in the account_3way_match module with different values, so we skip it when the module is installed
        if self.env['ir.module.module'].search([('name', '=', 'account_3way_match')]).state == 'installed':
            self.skipTest("This test won't work if account_3way_match is installed")

        foreign_currency = self.other_currency
        company_currency = self.company_data['currency']

        setup_values = [
            [self.company_data['default_journal_purchase'], foreign_currency],
            [self.company_data['default_journal_purchase'].copy({'currency_id': foreign_currency.id, 'default_account_id': self.company_data['default_account_expense'].id}), foreign_currency],
            [self.company_data['default_journal_purchase'].copy({'currency_id': foreign_currency.id, 'default_account_id': self.company_data['default_account_expense'].id}), company_currency],
            [self.company_data['default_journal_purchase'].copy({'currency_id': company_currency.id, 'default_account_id': self.company_data['default_account_expense'].id}), company_currency],
            [self.company_data['default_journal_purchase'].copy({'currency_id': company_currency.id, 'default_account_id': self.company_data['default_account_expense'].id}), foreign_currency],
        ]

        expected_vals_list = [
            # number_draft, sum_draft, number_waiting, sum_waiting, number_late, sum_late, currency
            [            1,       100,              1,          55,            1,      55, company_currency],
            [            1,       200,              1,         110,            1,     110, foreign_currency],
            [            1,       400,              1,         220,            1,     220, foreign_currency],
            [            1,       200,              1,         110,            1,     110, company_currency],
            [            1,       100,              1,          55,            1,      55, company_currency],
        ]

        for (purchase_journal, bill_currency), expected_vals in zip(setup_values, expected_vals_list):
            with self.subTest(purchase_journal_currency=purchase_journal.currency_id, bill_currency=bill_currency, expected_vals=expected_vals):
                bill = self.init_invoice('in_invoice', invoice_date='2017-01-01', post=True, amounts=[200], currency=bill_currency, journal=purchase_journal)
                _draft_bill = self.init_invoice('in_invoice', invoice_date='2017-01-01', post=False, amounts=[200], currency=bill_currency, journal=purchase_journal)

                payment = self.init_payment(-90, post=True, date='2017-01-01', currency=bill_currency)
                (bill + payment.move_id).line_ids.filtered_domain([
                    ('account_id', '=', self.company_data['default_account_payable'].id)
                ]).reconcile()

                self.assertDashboardPurchaseSaleData(purchase_journal, *expected_vals)

    def test_sale_purchase_journal_for_multi_currency_sale(self):
        # This test is defined in the account_3way_match module with different values, so we skip it when the module is installed
        if self.env['ir.module.module'].search([('name', '=', 'account_3way_match')]).state == 'installed':
            self.skipTest("This test won't work if account_3way_match is installed")

        currency = self.other_currency
        company_currency = self.company_data['currency']

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2017-01-01',
            'date': '2017-01-01',
            'partner_id': self.partner_a.id,
            'currency_id': currency.id,
            'invoice_line_ids': [
                (0, 0, {'name': 'test', 'price_unit': 200})
            ],
        })
        invoice.action_post()

        payment = self.env['account.payment'].create({
            'amount': 90.0,
            'date': '2016-01-01',
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_a.id,
            'currency_id': currency.id,
        })
        payment.action_post()

        (invoice + payment.move_id).line_ids.filtered_domain([
            ('account_id', '=', self.company_data['default_account_receivable'].id)
        ]).reconcile()

        default_journal_sale = self.company_data['default_journal_sale']
        dashboard_data = default_journal_sale._get_journal_dashboard_data_batched()[default_journal_sale.id]
        self.assertEqual(format_amount(self.env, 55, company_currency), dashboard_data['sum_waiting'])
        self.assertEqual(format_amount(self.env, 55, company_currency), dashboard_data['sum_late'])

    @freeze_time("2023-03-15")
    def test_purchase_journal_numbers_and_sums(self):
        # This test is defined in the account_3way_match module with different values, so we skip it when the module is installed
        if self.env['ir.module.module'].search([('name', '=', 'account_3way_match')]).state == 'installed':
            self.skipTest("This test won't work if account_3way_match is installed")

        company_currency = self.company_data['currency']
        journal = self.company_data['default_journal_purchase']

        self._create_test_vendor_bills(journal)
        dashboard_data = journal._get_journal_dashboard_data_batched()[journal.id]
        # Expected behavior is to have three moves waiting for payment for a total amount of 4440$ one of which would be late
        # for a total amount of 40$ (second move has one of three lines late but that's not enough to make the move late)
        self.assertEqual(3, dashboard_data['number_waiting'])
        self.assertEqual(format_amount(self.env, 4440, company_currency), dashboard_data['sum_waiting'])
        self.assertEqual(1, dashboard_data['number_late'])
        self.assertEqual(format_amount(self.env, 40, company_currency), dashboard_data['sum_late'])

    def test_gap_in_sequence_warning(self):
        journal = self.company_data['default_journal_sale']
        self.assertFalse(journal._query_has_sequence_holes())  # No moves so no gap
        moves = self.env['account.move'].create([{
            'move_type': 'out_invoice',
            'journal_id': journal.id,
            'partner_id': self.partner_a.id,
            'invoice_date': f'1900-01-{i+1:02d}',
            'date': f'2019-01-{i+1:02d}',
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'quantity': 40.0,
                'name': 'product test 1',
                'price_unit': 2.27,
                'tax_ids': [],
            })]
        } for i in range(10)]).sorted('date')
        gap_date = moves[3].date

        moves[:8].action_post()  # Only post 8 moves and keep 2 draft moves
        self.assertFalse(journal._query_has_sequence_holes())  # no gap, no gap warning, and draft moves shouldn't trigger the warning

        moves[2:4].button_draft()
        self.assertTrue(journal._query_has_sequence_holes())  # gap due to draft moves using sequence numbers, gap warning
        moves[3].unlink()
        self.assertTrue(journal._query_has_sequence_holes())  # gap due to missing sequence, gap warning

        moves[2].action_post()
        self.company_data['company'].write({'fiscalyear_lock_date': gap_date + relativedelta(days=1)})
        self.assertFalse(journal._query_has_sequence_holes())  # gap but prior to lock-date, no gap warning

        moves[6].button_draft()
        moves[6].button_cancel()
        self.assertTrue(journal._query_has_sequence_holes())  # gap due to canceled move using a sequence, gap warning

    def test_bank_journal_with_default_account_as_outstanding_account_payments(self):
        """
        Test that payments are excluded from the miscellaneaous operations and are included in the balance
        when having the default_account_id set as outstanding account on the journal
        """
        bank_journal = self.company_data['default_journal_bank'].copy()
        bank_journal.outbound_payment_method_line_ids[0].payment_account_id = bank_journal.default_account_id
        bank_journal.inbound_payment_method_line_ids[0].payment_account_id = bank_journal.default_account_id
        payment = self.env['account.payment'].create({
            'amount': 100,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'journal_id': bank_journal.id,
        })
        payment.action_post()

        dashboard_data = bank_journal._get_journal_dashboard_data_batched()[bank_journal.id]
        self.assertEqual(dashboard_data['nb_misc_operations'], 0)
        self.assertEqual(dashboard_data['account_balance'], (bank_journal.currency_id or self.env.company.currency_id).format(100))

    def test_bank_journal_different_currency(self):
        """Test that the misc operations amount on the dashboard is correct
        for a bank account in another currency."""
        foreign_currency = self.other_currency
        bank_journal = self.company_data['default_journal_bank'].copy({'currency_id': foreign_currency.id})

        self.assertNotEqual(bank_journal.currency_id, bank_journal.company_id.currency_id)

        move = self.env['account.move'].create({
            'journal_id': self.company_data['default_journal_misc'].id,
            'line_ids': [
                Command.create({
                    'account_id': bank_journal.default_account_id.id,
                    'currency_id': foreign_currency.id,
                    'amount_currency': 100,
                }),
                Command.create({
                    'account_id': self.company_data['default_account_assets'].id,
                    'currency_id': foreign_currency.id,
                    'amount_currency': -100,
                })
            ]
        })
        move.action_post()

        dashboard_data = bank_journal._get_journal_dashboard_data_batched()[bank_journal.id]
        self.assertEqual(dashboard_data.get('misc_operations_balance', 0), foreign_currency.format(100))

        bank_journal.default_account_id.currency_id = False  # not a normal case
        company_currency_move = self.env['account.move'].create({
            'journal_id': self.company_data['default_journal_misc'].id,
            'line_ids': [
                Command.create({
                    'account_id': bank_journal.default_account_id.id,
                    'debit': 100,
                }),
                Command.create({
                    'account_id': self.company_data['default_account_assets'].id,
                    'credit': 100,
                })
            ]
        })
        company_currency_move.action_post()
        dashboard_data = bank_journal._get_journal_dashboard_data_batched()[bank_journal.id]

        self.assertEqual(dashboard_data.get('misc_operations_balance', 0), None)
        self.assertEqual(dashboard_data.get('misc_class', ''), 'text-warning')

    def test_to_check_amount_different_currency(self):
        """
        We want the to_check amount to be displayed in the journal currency
        Company currency = $
        Journal's currency = €
        Inv01 of 100 EUR; rate: 2€/1$
        Inv02 of 100 CHF; rate: 4CHF/1$

        => to check = 150 €
        """
        self.env['res.currency.rate'].create({
            'currency_id': self.env.ref('base.EUR').id,
            'name': '2024-12-01',
            'rate': 2.0,
        })
        self.env['res.currency.rate'].create({
            'currency_id': self.env.ref('base.CHF').id,
            'name': '2024-12-01',
            'rate': 4.0,
        })
        journal = self.env['account.journal'].create({
            'name': 'Test Foreign Currency Journal',
            'type': 'sale',
            'code': 'TEST',
            'currency_id': self.env.ref('base.EUR').id,
            'company_id': self.env.company.id,
        })
        self.env['account.move'].create([{
            'move_type': 'out_invoice',
            'journal_id': journal.id,
            'partner_id': self.partner_a.id,
            'currency_id': currency.id,
            'checked': False,
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'quantity': 1,
                    'price_unit': 100,
                    'tax_ids': [],
                })
            ]
        } for currency in (self.env.ref('base.EUR'), self.env.ref('base.CHF'))])

        dashboard_data = journal._get_journal_dashboard_data_batched()[journal.id]
        self.assertEqual(dashboard_data['to_check_balance'], journal.currency_id.format(150))
