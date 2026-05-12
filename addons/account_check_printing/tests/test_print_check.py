# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.account_check_printing.models.account_payment import INV_LINES_PER_STUB
from odoo.tests import tagged
from odoo.tools.misc import NON_BREAKING_SPACE
from odoo import Command
from odoo.exceptions import ValidationError

import math


@tagged('post_install', '-at_install')
class TestPrintCheck(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.other_currency = cls.setup_other_currency('EUR')

        bank_journal = cls.company_data['default_journal_bank']

        cls.payment_method_line_check = bank_journal.outbound_payment_method_line_ids\
            .filtered(lambda l: l.code == 'check_printing')
        cls.payment_method_line_check.payment_account_id = cls.inbound_payment_method_line.payment_account_id

        cls.epd_term = cls.env['account.payment.term'].create({
            'name': '5% 10 Net 30',
            'early_discount': True,
            'discount_days': 10,
            'discount_percentage': 5.0,
            'line_ids': [Command.create({
                'value': 'percent',
                'value_amount': 100,
                'delay_type': 'days_after',
                'nb_days': 30,
            })],
        })

    def test_in_invoice_check_manual_sequencing(self):
        ''' Test the check generation for vendor bills. '''
        nb_invoices_to_test = INV_LINES_PER_STUB + 1

        self.company_data['default_journal_bank'].write({
            'check_manual_sequencing': True,
            'check_next_number': '00042',
        })

        # Create 10 customer invoices.
        in_invoices = self.env['account.move'].create([{
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 100.0,
                'tax_ids': []
            })]
        } for i in range(nb_invoices_to_test)])
        in_invoices.action_post()

        # Create a single payment.
        payment = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=in_invoices.ids).create({
            'group_payment': True,
            'payment_method_line_id': self.payment_method_line_check.id,
        })._create_payments()

        # Check created payment.
        self.assertRecordValues(payment, [{
            'payment_method_line_id': self.payment_method_line_check.id,
            'check_amount_in_words': payment.currency_id.amount_to_text(100.0 * nb_invoices_to_test),
            'check_number': '00042',
        }])

        # Check pages.
        self.company_data['company'].account_check_printing_multi_stub = True
        report_pages = payment._check_get_pages()
        self.assertEqual(len(report_pages), int(math.ceil(len(in_invoices) / INV_LINES_PER_STUB)))

        self.company_data['company'].account_check_printing_multi_stub = False
        report_pages = payment._check_get_pages()
        self.assertEqual(len(report_pages), 1)

    def test_out_refund_check_manual_sequencing(self):
        ''' Test the check generation for refunds. '''
        nb_invoices_to_test = INV_LINES_PER_STUB + 1

        self.company_data['default_journal_bank'].write({
            'check_manual_sequencing': True,
            'check_next_number': '00042',
        })

        # Create 10 refunds.
        out_refunds = self.env['account.move'].create([{
            'move_type': 'out_refund',
            'partner_id': self.partner_a.id,
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 100.0,
                'tax_ids': []
            })]
        } for i in range(nb_invoices_to_test)])
        out_refunds.action_post()

        # Create a single payment.
        payment = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=out_refunds.ids).create({
            'group_payment': True,
            'payment_method_line_id': self.payment_method_line_check.id,
        })._create_payments()

        # Check created payment.
        self.assertRecordValues(payment, [{
            'payment_method_line_id': self.payment_method_line_check.id,
            'check_amount_in_words': payment.currency_id.amount_to_text(100.0 * nb_invoices_to_test),
            'check_number': '00042',
        }])

        # Check pages.
        self.company_data['company'].account_check_printing_multi_stub = True
        report_pages = payment._check_get_pages()
        self.assertEqual(len(report_pages), int(math.ceil(len(out_refunds) / INV_LINES_PER_STUB)))

        self.company_data['company'].account_check_printing_multi_stub = False
        report_pages = payment._check_get_pages()
        self.assertEqual(len(report_pages), 1)

    def test_multi_currency_stub_lines(self):
        # Invoice in company's currency: 100$
        invoice = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'date': '2016-01-01',
            'invoice_date': '2016-01-01',
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 150.0,
                'tax_ids': []
            })]
        })
        invoice.action_post()

        # Partial payment in foreign currency.
        payment = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=invoice.ids).create({
            'payment_method_line_id': self.payment_method_line_check.id,
            'currency_id': self.other_currency.id,
            'amount': 150.0,
            'payment_date': '2017-01-01',
        })._create_payments()

        stub_pages = payment._check_make_stub_pages()

        self.assertEqual(stub_pages, [[{
            'due_date': '01/01/2016',
            'number': invoice.name,
            'amount_total': f'${NON_BREAKING_SPACE}150.00',
            'amount_residual': f'${NON_BREAKING_SPACE}75.00',
            'amount_paid': f'150.00{NON_BREAKING_SPACE}€',
            'amount_discount': None,
            'amount_writeoff': None,
            'currency': invoice.currency_id,
        }]])

    def test_in_invoice_check_manual_sequencing_with_multiple_payments(self):
        """
           Test the check generation for vendor bills with multiple payments.
        """
        nb_invoices_to_test = INV_LINES_PER_STUB + 1

        self.company_data['default_journal_bank'].write({
            'check_manual_sequencing': True,
            'check_next_number': '11111',
        })

        in_invoices = self.env['account.move'].create([{
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 100.0,
                'tax_ids': []
            })]
        } for i in range(nb_invoices_to_test)])
        in_invoices.action_post()

        payments = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=in_invoices.ids).create({
            'group_payment': False,
            'payment_method_line_id': self.payment_method_line_check.id,
        })._create_payments()

        self.assertEqual(set(payments.mapped('check_number')), {str(x) for x in range(11111, 11111 + nb_invoices_to_test)})

    def test_check_label(self):
        payment = self.env['account.payment'].create({
            'check_number': '2147483647',
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'amount': 100.0,
            'journal_id': self.company_data['default_journal_bank'].id,
            'payment_method_line_id': self.payment_method_line_check.id,
        })
        payment.action_post()

        for move in payment.move_id:
            self.assertRecordValues(move.line_ids, [{'name': "Checks - 2147483647"}] * len(move.line_ids))

    def test_print_great_pre_number_check(self):
        """
        Make sure we can use integer of more than 2147483647 in check sequence
         limit of `integer` type in psql: https://www.postgresql.org/docs/current/datatype-numeric.html
        """
        vals = {
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'amount': 100.0,
            'journal_id': self.company_data['default_journal_bank'].id,
            'payment_method_line_id': self.payment_method_line_check.id,
        }
        payment = self.env['account.payment'].create(vals)
        payment.action_post()
        self.assertTrue(payment.write({'check_number': '2147483647'}))
        self.assertTrue(payment.write({'check_number': '2147483648'}))

        payment_2 = self.env['account.payment'].create(vals)
        payment_2.action_post()
        action_window = payment_2.print_checks()
        self.assertEqual(action_window['context']['default_next_check_number'], '2147483649', "Check number should have been incremented without error.")

    def test_print_check_with_branch(self):
        """
        Test that we don't get access error when printing a check with a branch
        """
        company = self.env.company
        branch = self.env['res.company'].create({
            'name': 'Branch',
            'parent_id': company.id,
        })
        self.cr.precommit.run()  # load the CoA
        self.env.user.write({'company_id': company.id, 'company_ids': [Command.set(company.ids)]})

        vals = {
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'amount': 100.0,
            'journal_id': self.company_data['default_journal_bank'].id,
            'payment_method_line_id': self.payment_method_line_check.id,
        }
        payment = self.env['account.payment'].create(vals)
        payment.action_post()
        self.assertTrue(payment.write({'check_number': '00001'}))
        payment.invalidate_recordset(['check_number'])

        self.env.user.write({'company_id': branch.id, 'company_ids': [Command.set(branch.ids)]})

        payment_2 = self.env['account.payment'].create(vals)
        payment_2.action_post()

        action_window = payment_2.print_checks()
        self.assertTrue(action_window)

    def test_draft_invoice_payment_check_printing(self):
        nb_invoices_to_test = INV_LINES_PER_STUB + 1

        accounting_installed = self.env['account.move']._get_invoice_in_payment_state() == 'in_payment'
        if not accounting_installed:
            self.skipTest('Accounting not installed')  # There is an implicit outstanding account in this case, which makes it avoid the error

        self.company_data['default_journal_bank'].write({
            'check_manual_sequencing': True,
            'check_next_number': '00042',
        })
        self.payment_method_line_check.payment_account_id = None  # Needed to trigger the error

        in_invoices = self.env['account.move'].create([{
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 100.0,
                'tax_ids': []
            })]
        } for _ in range(nb_invoices_to_test)])
        payment = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=in_invoices.ids).create({
            'group_payment': True,
            'payment_method_line_id': self.payment_method_line_check.id,
        })._create_payments()
        self.assertRecordValues(payment, [{
            'payment_method_line_id': self.payment_method_line_check.id,
            'check_amount_in_words': payment.currency_id.amount_to_text(100.0 * nb_invoices_to_test),
            'check_number': '00042',
        }])

        report_pages = payment._check_get_pages()
        self.assertEqual(len(report_pages), 1)

    def test_multiple_payments_check_number_uniqueness(self):
        """Test that when multiple payments are created at once with check printing,
        each payment gets a unique check number when posted.
        """
        # Configure the bank journal with manual check sequencing
        self.company_data['default_journal_bank'].write({
            'check_manual_sequencing': True,
            'check_next_number': '10001',
        })

        # Create three vendor bills
        in_invoices = self.env['account.move'].create([
            {
                'move_type': 'in_invoice',
                'partner_id': self.partner_a.id,
                'date': '2023-01-01',
                'invoice_date': '2023-01-01',
                'invoice_line_ids': [Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 100.0,
                    'tax_ids': []
                })]
            },
            {
                'move_type': 'in_invoice',
                'partner_id': self.partner_a.id,
                'date': '2023-01-01',
                'invoice_date': '2023-01-01',
                'invoice_line_ids': [Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 200.0,
                    'tax_ids': []
                })]
            },
            {
                'move_type': 'in_invoice',
                'partner_id': self.partner_b.id,
                'date': '2023-01-01',
                'invoice_date': '2023-01-01',
                'invoice_line_ids': [Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 200.0,
                    'tax_ids': []
                })]
            }
        ])
        in_invoices.action_post()

        # Create grouped payments , using the check payment method
        payments = self.env['account.payment.register'].with_context(
            active_model='account.move',
            active_ids=in_invoices.ids
        ).create({
            'group_payment': True,
            'payment_method_line_id': self.payment_method_line_check.id,
        })._create_payments()

        # Check that the payments have different check numbers
        check_numbers = payments.mapped('check_number')
        self.assertEqual(len(check_numbers), 2, "Both payments should have a check number")
        self.assertEqual(set(check_numbers), {'10001', '10002'}, "Check numbers should be sequential")

        move_names = payments.move_id.line_ids.mapped('name')
        self.assertIn(f"Checks - 10001: {payments[0].memo}", move_names)
        self.assertIn(f"Checks - 10002: {payments[1].memo}", move_names)

    def test_epd_stub_line_splits_payment_and_discount(self):
        """ Test that a check paying a bill within the discount window splits the
        stub line into the discounted amount paid and the discount.
        """
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'date': '2026-01-01',
            'invoice_date': '2026-01-01',
            'invoice_payment_term_id': self.epd_term.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 100.0,
                'tax_ids': [],
            })],
        })
        bill.action_post()

        payment = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=bill.ids).create({
            'payment_method_line_id': self.payment_method_line_check.id,
            'payment_date': '2026-01-05',
        })._create_payments()

        [[stub_line]] = payment._check_make_stub_pages()
        self.assertEqual(stub_line['amount_paid'], f'${NON_BREAKING_SPACE}95.00')
        self.assertEqual(stub_line['amount_discount'], f'${NON_BREAKING_SPACE}5.00')
        self.assertEqual(stub_line['amount_total'], f'${NON_BREAKING_SPACE}100.00')

    def test_writeoff_stub_line_splits_payment_and_writeoff(self):
        """ Test that a check below a bill's total splits the stub line into the
        amount paid and the write-off.
        """
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'date': '2026-01-01',
            'invoice_date': '2026-01-01',
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 200.0,
                'tax_ids': [],
            })],
        })
        bill.action_post()

        payment = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=bill.ids).create({
            'payment_method_line_id': self.payment_method_line_check.id,
            'amount': 150.0,
            'payment_difference_handling': 'reconcile',
            'writeoff_account_id': self.company_data['default_account_revenue'].id,
            'writeoff_label': 'Write-Off',
            'payment_date': '2026-01-05',
        })._create_payments()

        [[stub_line]] = payment._check_make_stub_pages()
        self.assertEqual(stub_line['amount_paid'], f'${NON_BREAKING_SPACE}150.00')
        self.assertEqual(stub_line['amount_writeoff'], f'${NON_BREAKING_SPACE}50.00')
        self.assertEqual(stub_line['amount_total'], f'${NON_BREAKING_SPACE}200.00')

    def test_grouped_writeoff_stub_rounding(self):
        """ Test that the amounts paid and written off on the stub lines add up
        to the check amount and the total write-off.
        """
        bills = self.env['account.move'].create([{
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'date': '2026-01-01',
            'invoice_date': '2026-01-01',
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 100.0,
                'tax_ids': [],
            })],
        } for _ in range(3)])
        bills.action_post()

        payment = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=bills.ids).create({
            'payment_method_line_id': self.payment_method_line_check.id,
            'group_payment': True,
            'amount': 200.0,
            'payment_difference_handling': 'reconcile',
            'writeoff_account_id': self.company_data['default_account_revenue'].id,
            'writeoff_label': 'Write-Off',
            'payment_date': '2026-01-15',
        })._create_payments()

        def to_float(amount_str):
            return float(amount_str.replace('$', '').replace(NON_BREAKING_SPACE, '').replace(',', ''))

        [stub_lines] = payment._check_make_stub_pages()
        self.assertAlmostEqual(sum(to_float(line['amount_paid']) for line in stub_lines), 200.0)
        self.assertAlmostEqual(sum(to_float(line['amount_writeoff']) for line in stub_lines), 100.0)

    def test_grouped_discount_split_per_bill(self):
        """ Test that a grouped check applies each bill's own discount and leaves
        a bill without an early payment discount untouched.
        """
        epd_bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'date': '2026-01-01',
            'invoice_date': '2026-01-01',
            'invoice_payment_term_id': self.epd_term.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 100.0,
                'tax_ids': [],
            })],
        })
        plain_bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'date': '2026-01-01',
            'invoice_date': '2026-01-01',
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 100.0,
                'tax_ids': [],
            })],
        })
        (epd_bill + plain_bill).action_post()

        payment = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=(epd_bill + plain_bill).ids).create({
            'payment_method_line_id': self.payment_method_line_check.id,
            'group_payment': True,
            'payment_date': '2026-01-05',
        })._create_payments()

        [stub_lines] = payment._check_make_stub_pages()
        lines = {line['number']: line for line in stub_lines}

        self.assertEqual(lines[epd_bill.name]['amount_paid'], f'${NON_BREAKING_SPACE}95.00')
        self.assertEqual(lines[epd_bill.name]['amount_discount'], f'${NON_BREAKING_SPACE}5.00')

        self.assertEqual(lines[plain_bill.name]['amount_paid'], f'${NON_BREAKING_SPACE}100.00')
        self.assertIsNone(lines[plain_bill.name]['amount_writeoff'])

    def test_epd_stub_line_outside_discount_window(self):
        """ Test that no discount is split off when the check is past the discount
        window or the bill has no early payment discount.
        """
        late_bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'date': '2026-01-01',
            'invoice_date': '2026-01-01',
            'invoice_payment_term_id': self.epd_term.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 100.0,
                'tax_ids': [],
            })],
        })
        plain_bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'date': '2026-01-01',
            'invoice_date': '2026-01-01',
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 100.0,
                'tax_ids': [],
            })],
        })
        (late_bill + plain_bill).action_post()

        late_payment = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=late_bill.ids).create({
            'payment_method_line_id': self.payment_method_line_check.id,
            'payment_date': '2026-02-15',
        })._create_payments()
        plain_payment = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=plain_bill.ids).create({
            'payment_method_line_id': self.payment_method_line_check.id,
            'payment_date': '2026-01-05',
        })._create_payments()

        [[late_stub]] = late_payment._check_make_stub_pages()
        self.assertIsNone(late_stub['amount_discount'])
        self.assertEqual(late_stub['amount_paid'], f'${NON_BREAKING_SPACE}100.00')

        [[plain_stub]] = plain_payment._check_make_stub_pages()
        self.assertIsNone(plain_stub['amount_discount'])
        self.assertEqual(plain_stub['amount_paid'], f'${NON_BREAKING_SPACE}100.00')

    def test_writeoff_on_epd_account_outside_discount_window(self):
        """ Test that a late payment whose discount is written off on the cash
        discount account still splits the stub line into the amount paid and the
        write-off.
        """
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'date': '2026-01-01',
            'invoice_date': '2026-01-01',
            'invoice_payment_term_id': self.epd_term.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 100.0,
                'tax_ids': [],
            })],
        })
        bill.action_post()

        gain_account = self.env.company.account_journal_early_pay_discount_gain_account_id
        payment = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=bill.ids).create({
            'payment_method_line_id': self.payment_method_line_check.id,
            'amount': 95.0,
            'payment_difference_handling': 'reconcile',
            'writeoff_account_id': gain_account.id,
            'writeoff_label': 'Write-Off',
            'payment_date': '2026-02-15',
        })._create_payments()

        [[stub_line]] = payment._check_make_stub_pages()
        self.assertEqual(stub_line['amount_paid'], f'${NON_BREAKING_SPACE}95.00')
        self.assertEqual(stub_line['amount_writeoff'], f'${NON_BREAKING_SPACE}5.00')
        self.assertEqual(stub_line['amount_total'], f'${NON_BREAKING_SPACE}100.00')

    def test_number_exceeds_int32_limit(self):
        """Numbers greater than 2,147,483,647 should raise a ValidationError."""
        self.journal = self.env['account.journal'].create({
            'name': 'Test Bank Journal',
            'type': 'bank',
            'code': 'TBJ',
            'bank_statements_source': 'manual',
            'check_manual_sequencing': True,
        })

        check_number_too_big = str(2_147_483_648)
        check_number_normal = str(2_147_483_647)
        with self.assertRaisesRegex(ValidationError, "The check number you entered .* exceeds the maximum allowed value"):
            self.journal.check_next_number = check_number_too_big
        self.journal.check_next_number = check_number_normal
        self.assertEqual(self.journal.check_sequence_id.number_next_actual, int(check_number_normal), "The check sequence should be updated correctly")

    def test_set_non_numeric_check_next_number_on_journal(self):
        """
        Test that setting a non-numeric value as the journal's
        Next Check Number raises a ValidationError.
        """
        bank_journal = self.company_data['default_journal_bank']
        with self.assertRaisesRegex(ValidationError, "Next Check Number should only contains numbers."):
            bank_journal.check_next_number = "F1234"
