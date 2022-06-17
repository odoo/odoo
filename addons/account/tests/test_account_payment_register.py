# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import UserError
from odoo.tests import tagged, Form
from odoo import Command


@tagged('post_install', '-at_install')
class TestAccountPaymentRegister(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.currency_data_3 = cls.setup_multi_currency_data({
            'name': "Umbrella",
            'symbol': '☂',
            'currency_unit_label': "Umbrella",
            'currency_subunit_label': "Broken Umbrella",
        }, rate2017=0.01)

        cls.payment_debit_account_id = cls.company_data['default_journal_bank'].company_id.account_journal_payment_debit_account_id.copy()
        cls.payment_credit_account_id = cls.company_data['default_journal_bank'].company_id.account_journal_payment_credit_account_id.copy()

        cls.bank_journal_1 = cls.company_data['default_journal_bank']
        cls.bank_journal_2 = cls.company_data['default_journal_bank'].copy()

        cls.partner_bank_account1 = cls.env['res.partner.bank'].create({
            'acc_number': "0123456789",
            'partner_id': cls.partner_a.id,
            'acc_type': 'bank',
        })
        cls.partner_bank_account2 = cls.env['res.partner.bank'].create({
            'acc_number': "9876543210",
            'partner_id': cls.partner_a.id,
            'acc_type': 'bank',
        })
        cls.comp_bank_account1 = cls.env['res.partner.bank'].create({
            'acc_number': "985632147",
            'partner_id': cls.env.company.partner_id.id,
            'acc_type': 'bank',
        })
        cls.comp_bank_account2 = cls.env['res.partner.bank'].create({
            'acc_number': "741258963",
            'partner_id': cls.env.company.partner_id.id,
            'acc_type': 'bank',
        })

        # Customer invoices sharing the same batch.
        cls.out_invoice_1 = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'partner_id': cls.partner_a.id,
            'currency_id': cls.currency_data['currency'].id,
            'invoice_line_ids': [(0, 0, {'product_id': cls.product_a.id, 'price_unit': 1000.0, 'tax_ids': []})],
        })
        cls.out_invoice_2 = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'partner_id': cls.partner_a.id,
            'currency_id': cls.currency_data['currency'].id,
            'invoice_line_ids': [(0, 0, {'product_id': cls.product_a.id, 'price_unit': 2000.0, 'tax_ids': []})],
        })
        cls.out_invoice_3 = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'partner_id': cls.partner_a.id,
            'currency_id': cls.currency_data['currency'].id,
            'invoice_line_ids': [(0, 0, {'product_id': cls.product_a.id, 'price_unit': 24.02, 'tax_ids': []})],
        })
        cls.out_invoice_4 = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'partner_id': cls.partner_a.id,
            'currency_id': cls.currency_data['currency'].id,
            'invoice_line_ids': [(0, 0, {'product_id': cls.product_a.id, 'price_unit': 23.98, 'tax_ids': []})],
        })
        (cls.out_invoice_1 + cls.out_invoice_2 + cls.out_invoice_3 + cls.out_invoice_4).action_post()

        # Vendor bills, in_invoice_1 + in_invoice_2 are sharing the same batch but not in_invoice_3.
        cls.in_invoice_1 = cls.env['account.move'].create({
            'move_type': 'in_invoice',
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'partner_id': cls.partner_a.id,
            'invoice_line_ids': [(0, 0, {'product_id': cls.product_a.id, 'price_unit': 1000.0, 'tax_ids': []})],
        })
        cls.in_invoice_2 = cls.env['account.move'].create({
            'move_type': 'in_invoice',
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'partner_id': cls.partner_a.id,
            'invoice_line_ids': [(0, 0, {'product_id': cls.product_a.id, 'price_unit': 2000.0, 'tax_ids': []})],
        })
        cls.in_invoice_3 = cls.env['account.move'].create({
            'move_type': 'in_invoice',
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'partner_id': cls.partner_b.id,
            'invoice_payment_term_id': False,
            'currency_id': cls.currency_data['currency'].id,
            'invoice_line_ids': [(0, 0, {'product_id': cls.product_a.id, 'price_unit': 3000.0, 'tax_ids': []})],
        })
        (cls.in_invoice_1 + cls.in_invoice_2 + cls.in_invoice_3).action_post()

        # Credit note
        cls.in_refund_1 = cls.env['account.move'].create({
            'move_type': 'in_refund',
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'partner_id': cls.partner_a.id,
            'invoice_line_ids': [(0, 0, {'product_id': cls.product_a.id, 'price_unit': 1600.0, 'tax_ids': []})],
        })
        cls.in_refund_1.action_post()

    def test_register_payment_single_batch_grouped_keep_open_lower_amount(self):
        ''' Pay 800.0 with 'open' as payment difference handling on two customer invoices (1000 + 2000). '''
        active_ids = (self.out_invoice_1 + self.out_invoice_2).ids
        payments = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=active_ids).create({
            'amount': 800.0,
            'group_payment': True,
            'payment_difference_handling': 'open',
            'currency_id': self.currency_data['currency'].id,
            'payment_method_line_id': self.inbound_payment_method_line.id,
        })._create_payments()

        self.assertRecordValues(payments, [{
            'ref': 'INV/2017/00001 INV/2017/00002',
            'payment_method_line_id': self.inbound_payment_method_line.id,
        }])
        self.assertRecordValues(payments.line_ids.sorted('balance'), [
            # Receivable line:
            {
                'debit': 0.0,
                'credit': 400.0,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -800.0,
                'reconciled': True,
            },
            # Liquidity line:
            {
                'debit': 400.0,
                'credit': 0.0,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 800.0,
                'reconciled': False,
            },
        ])

    def test_register_payment_single_batch_grouped_keep_open_higher_amount(self):
        ''' Pay 3100.0 with 'open' as payment difference handling on two customer invoices (1000 + 2000). '''
        active_ids = (self.out_invoice_1 + self.out_invoice_2).ids
        payments = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=active_ids).create({
            'amount': 3100.0,
            'group_payment': True,
            'payment_difference_handling': 'open',
            'currency_id': self.currency_data['currency'].id,
            'payment_method_line_id': self.inbound_payment_method_line.id,
        })._create_payments()

        self.assertRecordValues(payments, [{
            'ref': 'INV/2017/00001 INV/2017/00002',
            'payment_method_line_id': self.inbound_payment_method_line.id,
        }])
        self.assertRecordValues(payments.line_ids.sorted('balance'), [
            # Receivable line:
            {
                'debit': 0.0,
                'credit': 1550.0,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -3100.0,
                'reconciled': False,
            },
            # Liquidity line:
            {
                'debit': 1550.0,
                'credit': 0.0,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 3100.0,
                'reconciled': False,
            },
        ])

    def test_register_payment_single_batch_grouped_writeoff_lower_amount_debit(self):
        ''' Pay 800.0 with 'reconcile' as payment difference handling on two customer invoices (1000 + 2000). '''
        active_ids = (self.out_invoice_1 + self.out_invoice_2).ids
        payments = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=active_ids).create({
            'amount': 800.0,
            'group_payment': True,
            'payment_difference_handling': 'reconcile',
            'writeoff_account_id': self.company_data['default_account_revenue'].id,
            'writeoff_label': 'writeoff',
            'payment_method_line_id': self.inbound_payment_method_line.id,
        })._create_payments()

        self.assertRecordValues(payments, [{
            'ref': 'INV/2017/00001 INV/2017/00002',
            'payment_method_line_id': self.inbound_payment_method_line.id,
        }])
        self.assertRecordValues(payments.line_ids.sorted('balance'), [
            # Receivable line:
            {
                'debit': 0.0,
                'credit': 1500.0,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -3000.0,
                'reconciled': True,
            },
            # Liquidity line:
            {
                'debit': 400.0,
                'credit': 0.0,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 800.0,
                'reconciled': False,
            },
            # Writeoff line:
            {
                'debit': 1100.0,
                'credit': 0.0,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 2200.0,
                'reconciled': False,
            },
        ])

    def test_register_payment_single_batch_grouped_writeoff_higher_amount_debit(self):
        ''' Pay 3100.0 with 'reconcile' as payment difference handling on two customer invoices (1000 + 2000). '''
        active_ids = (self.out_invoice_1 + self.out_invoice_2).ids
        payments = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=active_ids).create({
            'amount': 3100.0,
            'group_payment': True,
            'payment_difference_handling': 'reconcile',
            'writeoff_account_id': self.company_data['default_account_revenue'].id,
            'writeoff_label': 'writeoff',
            'payment_method_line_id': self.inbound_payment_method_line.id,
        })._create_payments()

        self.assertRecordValues(payments, [{
            'ref': 'INV/2017/00001 INV/2017/00002',
            'payment_method_line_id': self.inbound_payment_method_line.id,
        }])
        self.assertRecordValues(payments.line_ids.sorted('balance'), [
            # Receivable line:
            {
                'debit': 0.0,
                'credit': 1500.0,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -3000.0,
                'reconciled': True,
            },
            # Writeoff line:
            {
                'debit': 0.0,
                'credit': 50.0,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -100.0,
                'reconciled': False,
            },
            # Liquidity line:
            {
                'debit': 1550.0,
                'credit': 0.0,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 3100.0,
                'reconciled': False,
            },
        ])

    def test_register_payment_single_batch_grouped_writeoff_lower_amount_credit(self):
        ''' Pay 800.0 with 'reconcile' as payment difference handling on two vendor billes (1000 + 2000). '''
        active_ids = (self.in_invoice_1 + self.in_invoice_2).ids
        payments = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=active_ids).create({
            'amount': 800.0,
            'group_payment': True,
            'payment_difference_handling': 'reconcile',
            'writeoff_account_id': self.company_data['default_account_revenue'].id,
            'writeoff_label': 'writeoff',
            'payment_method_line_id': self.inbound_payment_method_line.id,
        })._create_payments()

        self.assertRecordValues(payments, [{
            'ref': 'BILL/2017/01/0001 BILL/2017/01/0002',
            'payment_method_line_id': self.inbound_payment_method_line.id,
        }])
        self.assertRecordValues(payments.line_ids.sorted('balance'), [
            # Writeoff line:
            {
                'debit': 0.0,
                'credit': 2200.0,
                'currency_id': self.company_data['currency'].id,
                'amount_currency': -2200.0,
                'reconciled': False,
            },
            # Liquidity line:
            {
                'debit': 0.0,
                'credit': 800.0,
                'currency_id': self.company_data['currency'].id,
                'amount_currency': -800.0,
                'reconciled': False,
            },
            # Payable line:
            {
                'debit': 3000.0,
                'credit': 0.0,
                'currency_id': self.company_data['currency'].id,
                'amount_currency': 3000.0,
                'reconciled': True,
            },
        ])

    def test_register_payment_single_batch_grouped_writeoff_higher_amount_credit(self):
        ''' Pay 3100.0 with 'reconcile' as payment difference handling on two vendor billes (1000 + 2000). '''
        active_ids = (self.in_invoice_1 + self.in_invoice_2).ids
        payments = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=active_ids).create({
            'amount': 3100.0,
            'group_payment': True,
            'payment_difference_handling': 'reconcile',
            'writeoff_account_id': self.company_data['default_account_revenue'].id,
            'writeoff_label': 'writeoff',
            'payment_method_line_id': self.inbound_payment_method_line.id,
        })._create_payments()

        self.assertRecordValues(payments, [{
            'ref': 'BILL/2017/01/0001 BILL/2017/01/0002',
            'payment_method_line_id': self.inbound_payment_method_line.id,
        }])
        self.assertRecordValues(payments.line_ids.sorted('balance'), [
            # Liquidity line:
            {
                'debit': 0.0,
                'credit': 3100.0,
                'currency_id': self.company_data['currency'].id,
                'amount_currency': -3100.0,
                'reconciled': False,
            },
            # Writeoff line:
            {
                'debit': 100.0,
                'credit': 0.0,
                'currency_id': self.company_data['currency'].id,
                'amount_currency': 100.0,
                'reconciled': False,
            },
            # Payable line:
            {
                'debit': 3000.0,
                'credit': 0.0,
                'currency_id': self.company_data['currency'].id,
                'amount_currency': 3000.0,
                'reconciled': True,
            },
        ])

    def test_register_payment_single_batch_not_grouped(self):
        ''' Choose to pay two customer invoices with separated payments (1000 + 2000). '''
        active_ids = (self.out_invoice_1 + self.out_invoice_2).ids
        payment_register = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=active_ids)\
            .create({
                'group_payment': False,
                'amount': 1200.0
            })
        self.assertRecordValues(payment_register, [{'payment_difference': 1800.0}])
        payments = payment_register._create_payments()
        self.assertRecordValues(payments, [
            {
                'ref': 'INV/2017/00001',
                'payment_method_line_id': self.inbound_payment_method_line.id,
            },
            {
                'ref': 'INV/2017/00002',
                'payment_method_line_id': self.inbound_payment_method_line.id,
            },
        ])
        self.assertRecordValues(payments[0].line_ids.sorted('balance') + payments[1].line_ids.sorted('balance'), [
            # == Payment 1: to pay out_invoice_1 ==
            # Receivable line:
            {
                'debit': 0.0,
                'credit': 500.0,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -1000.0,
                'reconciled': True,
            },
            # Liquidity line:
            {
                'debit': 500.0,
                'credit': 0.0,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 1000.0,
                'reconciled': False,
            },
            # == Payment 2: to pay out_invoice_2 ==
            # Receivable line:
            {
                'debit': 0.0,
                'credit': 1000.0,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -2000.0,
                'reconciled': True,
            },
            # Liquidity line:
            {
                'debit': 1000.0,
                'credit': 0.0,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 2000.0,
                'reconciled': False,
            },
        ])

    def test_register_payment_different_type_single_batch_not_grouped(self):
        """ Choose to pay a bill and a refund with separated payments (1000 + -2000)."""
        active_ids = (self.in_invoice_1 + self.in_refund_1).ids
        payments = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=active_ids).create({
            'group_payment': False,
        })._create_payments()

        self.assertRecordValues(payments[0], [
            {
                'ref': 'BILL/2017/01/0001',
                'payment_type': 'outbound',
            }
        ])

        self.assertRecordValues(payments[1], [
            {
                'ref': 'RBILL/2017/01/0001',
                'payment_type': 'inbound',
            },
        ])

        self.assertRecordValues(payments[0].line_ids.sorted('balance'), [
            # == Payment 1: to pay in_invoice_1 ==
            # Liquidity line:
            {
                'debit': 0.0,
                'credit': 1000.0,
                'currency_id': self.company_data['currency'].id,
                'amount_currency': -1000.0,
                'reconciled': False,
            },
            # Payable line:
            {
                'debit': 1000.0,
                'credit': 0.0,
                'currency_id': self.company_data['currency'].id,
                'amount_currency': 1000.0,
                'reconciled': True,
            },
        ])
        self.assertRecordValues(payments[1].line_ids.sorted('balance'), [
            # == Payment 2: to pay in_refund_1 ==
            # Payable line:
            {
                'debit': 0.0,
                'credit': 1600.0,
                'currency_id': self.company_data['currency'].id,
                'amount_currency': -1600.0,
                'reconciled': True,
            },
            # Liquidity line:
            {
                'debit': 1600.0,
                'credit': 0.0,
                'currency_id': self.company_data['currency'].id,
                'amount_currency': 1600.0,
                'reconciled': False,
            },
        ])

    def test_register_payment_single_batch_grouped_with_credit_note(self):
        ''' Pay 1400.0 on two vendor bills (1000.0 + 2000.0) and one credit note (1600.0). '''
        active_ids = (self.in_invoice_1 + self.in_invoice_2 + self.in_refund_1).ids
        payments = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=active_ids).create({
            'group_payment': True,
        })._create_payments()

        self.assertRecordValues(payments, [
            {
                'ref': 'BILL/2017/01/0001 BILL/2017/01/0002 RBILL/2017/01/0001',
                'payment_method_line_id': self.outbound_payment_method_line.id,
            },
        ])
        self.assertRecordValues(payments[0].line_ids.sorted('balance'), [
            # Liquidity line:
            {
                'debit': 0.0,
                'credit': 1400.0,
                'currency_id': self.company_data['currency'].id,
                'amount_currency': -1400.0,
                'reconciled': False,
            },
            # Payable line:
            {
                'debit': 1400.0,
                'credit': 0.0,
                'currency_id': self.company_data['currency'].id,
                'amount_currency': 1400.0,
                'reconciled': True,
            },
        ])

    def test_register_payment_multiple_batch_grouped_with_credit_note(self):
        ''' Do not batch payments if multiple partner_bank_id '''
        bank1 = self.env['res.partner.bank'].create({
            'acc_number': 'BE43798822936101',
            'partner_id': self.partner_a.id,
        })
        bank2 = self.env['res.partner.bank'].create({
            'acc_number': 'BE85812541345906',
            'partner_id': self.partner_a.id,
        })

        self.in_invoice_1.partner_bank_id = bank1
        self.in_invoice_2.partner_bank_id = bank2

        active_ids = (self.in_invoice_1 + self.in_invoice_2 + self.in_refund_1).ids
        payments = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=active_ids).create({
            'group_payment': True,
        })._create_payments()

        self.assertRecordValues(payments, [
            {
                'ref': 'BILL/2017/01/0001',
                'payment_method_line_id': self.outbound_payment_method_line.id,
            },
            {
                'ref': 'BILL/2017/01/0002',
                'payment_method_line_id': self.outbound_payment_method_line.id,
            },
            {
                'ref': 'RBILL/2017/01/0001',
                'payment_method_line_id': self.outbound_payment_method_line.id,
            },
        ])
        self.assertRecordValues(payments[0].line_ids.sorted('balance') + payments[1].line_ids.sorted('balance') + payments[2].line_ids.sorted('balance'), [
            # Liquidity line:
            {
                'debit': 0.0,
                'credit': 1000.0,
                'currency_id': self.company_data['currency'].id,
                'amount_currency': -1000.0,
                'reconciled': False,
            },
            # Payable line:
            {
                'debit': 1000.0,
                'credit': 0.0,
                'currency_id': self.company_data['currency'].id,
                'amount_currency': 1000.0,
                'reconciled': True,
            },
            # Liquidity line:
            {
                'debit': 0.0,
                'credit': 2000.0,
                'currency_id': self.company_data['currency'].id,
                'amount_currency': -2000.0,
                'reconciled': False,
            },
            # Payable line:
            {
                'debit': 2000.0,
                'credit': 0.0,
                'currency_id': self.company_data['currency'].id,
                'amount_currency': 2000.0,
                'reconciled': True,
            },
            # Receivable line:
            {
                'debit': 0.0,
                'credit': 1600.0,
                'currency_id': self.company_data['currency'].id,
                'amount_currency': -1600.0,
                'reconciled': True,
            },
            # Liquidity line:
            {
                'debit': 1600.0,
                'credit': 0.0,
                'currency_id': self.company_data['currency'].id,
                'amount_currency': 1600.0,
                'reconciled': False,
            },
        ])

    def test_register_payment_multi_batches_grouped(self):
        ''' Choose to pay multiple batches, one with two customer invoices (1000 + 2000)
        and one with a vendor bill of 600, by grouping payments.
        '''
        active_ids = (self.in_invoice_1 + self.in_invoice_2 + self.in_invoice_3).ids
        payment_register = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=active_ids)\
            .create({
                'group_payment': True,
                'amount': 1000.0
                # Test _compute_payment_difference. Since the partners_ids are not the same, this should be without effect.
            })
        payments = payment_register._create_payments()

        self.assertRecordValues(payment_register, [{
            'payment_difference': 0.0
        }])

        self.assertRecordValues(payments, [
            {
                'ref': 'BILL/2017/01/0001 BILL/2017/01/0002',
                'payment_method_line_id': self.outbound_payment_method_line.id,
            },
            {
                'ref': 'BILL/2017/01/0003',
                'payment_method_line_id': self.outbound_payment_method_line.id,
            },
        ])
        self.assertRecordValues(payments[0].line_ids.sorted('balance') + payments[1].line_ids.sorted('balance'), [
            # == Payment 1: to pay in_invoice_1 & in_invoice_2 ==
            # Liquidity line:
            {
                'debit': 0.0,
                'credit': 3000.0,
                'currency_id': self.company_data['currency'].id,
                'amount_currency': -3000.0,
                'reconciled': False,
            },
            # Payable line:
            {
                'debit': 3000.0,
                'credit': 0.0,
                'currency_id': self.company_data['currency'].id,
                'amount_currency': 3000.0,
                'reconciled': True,
            },
            # == Payment 2: to pay in_invoice_3 ==
            # Liquidity line:
            {
                'debit': 0.0,
                'credit': 1500.0,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -3000.0,
                'reconciled': False,
            },
            # Payable line:
            {
                'debit': 1500.0,
                'credit': 0.0,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 3000.0,
                'reconciled': True,
            },
        ])

    def test_register_payment_multi_batches_not_grouped(self):
        ''' Choose to pay multiple batches, one with two customer invoices (1000 + 2000)
         and one with a vendor bill of 600, by splitting payments.
         '''
        self.in_invoice_1.partner_bank_id = self.partner_bank_account1
        self.in_invoice_2.partner_bank_id = self.partner_bank_account2

        active_ids = (self.in_invoice_1 + self.in_invoice_2 + self.in_invoice_3).ids
        payments = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=active_ids).create({
            'group_payment': False,
        })._create_payments()

        self.assertRecordValues(payments, [
            {
                'journal_id': self.bank_journal_1.id,
                'ref': 'BILL/2017/01/0001',
                'payment_method_line_id': self.outbound_payment_method_line.id,
                'partner_bank_id': self.partner_bank_account1.id,
            },
            {
                'journal_id': self.bank_journal_1.id,
                'ref': 'BILL/2017/01/0002',
                'payment_method_line_id': self.outbound_payment_method_line.id,
                'partner_bank_id': self.partner_bank_account2.id,
            },
            {
                'journal_id': self.bank_journal_1.id,
                'ref': 'BILL/2017/01/0003',
                'payment_method_line_id': self.outbound_payment_method_line.id,
                'partner_bank_id': False,
            },
        ])
        self.assertRecordValues(payments[0].line_ids.sorted('balance') + payments[1].line_ids.sorted('balance') + payments[2].line_ids.sorted('balance'), [
            # == Payment 1: to pay in_invoice_1 ==
            # Liquidity line:
            {
                'debit': 0.0,
                'credit': 1000.0,
                'currency_id': self.company_data['currency'].id,
                'amount_currency': -1000.0,
                'reconciled': False,
            },
            # Payable line:
            {
                'debit': 1000.0,
                'credit': 0.0,
                'currency_id': self.company_data['currency'].id,
                'amount_currency': 1000.0,
                'reconciled': True,
            },
            # == Payment 2: to pay in_invoice_2 ==
            # Liquidity line:
            {
                'debit': 0.0,
                'credit': 2000.0,
                'currency_id': self.company_data['currency'].id,
                'amount_currency': -2000.0,
                'reconciled': False,
            },
            # Payable line:
            {
                'debit': 2000.0,
                'credit': 0.0,
                'currency_id': self.company_data['currency'].id,
                'amount_currency': 2000.0,
                'reconciled': True,
            },
            # == Payment 3: to pay in_invoice_3 ==
            # Liquidity line:
            {
                'debit': 0.0,
                'credit': 1500.0,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -3000.0,
                'reconciled': False,
            },
            # Payable line:
            {
                'debit': 1500.0,
                'credit': 0.0,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 3000.0,
                'reconciled': True,
            },
        ])

    def test_register_payment_constraints(self):
        # Test to register a payment for a draft journal entry.
        self.out_invoice_1.button_draft()
        with self.assertRaises(UserError), self.cr.savepoint():
            self.env['account.payment.register']\
                .with_context(active_model='account.move', active_ids=self.out_invoice_1.ids)\
                .create({})

        # Test to register a payment for an already fully reconciled journal entry.
        self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=self.out_invoice_2.ids)\
            .create({})\
            ._create_payments()
        with self.assertRaises(UserError), self.cr.savepoint():
            self.env['account.payment.register']\
                .with_context(active_model='account.move', active_ids=self.out_invoice_2.ids)\
                .create({})

    def test_register_payment_multi_currency_rounding_issue_positive_delta(self):
        ''' When registering a payment using a different currency than the invoice one, the invoice must be fully paid
        at the end whatever the currency rate.
        '''
        payment = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=self.out_invoice_3.ids)\
            .create({
                'currency_id': self.currency_data_3['currency'].id,
                'amount': 0.12,
            })\
            ._create_payments()

        self.assertRecordValues(payment.line_ids.sorted('balance'), [
            # Receivable line:
            {
                'debit': 0.0,
                'credit': 12.01,
                'currency_id': self.currency_data_3['currency'].id,
                'amount_currency': -0.12,
                'reconciled': True,
            },
            # Liquidity line:
            {
                'debit': 12.01,
                'credit': 0.0,
                'currency_id': self.currency_data_3['currency'].id,
                'amount_currency': 0.12,
                'reconciled': False,
            },
        ])

    def test_register_payment_multi_currency_rounding_issue_negative_delta(self):
        ''' When registering a payment using a different currency than the invoice one, the invoice must be fully paid
        at the end whatever the currency rate.
        '''
        payment = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=self.out_invoice_4.ids)\
            .create({
                'currency_id': self.currency_data_3['currency'].id,
                'amount': 0.12,
            })\
            ._create_payments()

        self.assertRecordValues(payment.line_ids.sorted('balance'), [
            # Receivable line:
            {
                'debit': 0.0,
                'credit': 11.99,
                'currency_id': self.currency_data_3['currency'].id,
                'amount_currency': -0.12,
                'reconciled': True,
            },
            # Liquidity line:
            {
                'debit': 11.99,
                'credit': 0.0,
                'currency_id': self.currency_data_3['currency'].id,
                'amount_currency': 0.12,
                'reconciled': False,
            },
        ])

    def test_register_payment_multi_currency_rounding_issue_writeoff_lower_amount_keep_open(self):
        payment = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=self.out_invoice_3.ids)\
            .create({
                'currency_id': self.currency_data_3['currency'].id,
                'amount': 0.08,
                'payment_difference_handling': 'open',
            })\
            ._create_payments()

        self.assertRecordValues(payment.line_ids.sorted('balance'), [
            # Receivable line:
            {
                'debit': 0.0,
                'credit': 8.0,
                'currency_id': self.currency_data_3['currency'].id,
                'amount_currency': -0.08,
                'reconciled': True,
            },
            # Liquidity line:
            {
                'debit': 8.0,
                'credit': 0.0,
                'currency_id': self.currency_data_3['currency'].id,
                'amount_currency': 0.08,
                'reconciled': False,
            },
        ])

    def test_register_payment_multi_currency_rounding_issue_writeoff_lower_amount_reconcile_positive_delta(self):
        payment = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=self.out_invoice_3.ids)\
            .create({
                'currency_id': self.currency_data_3['currency'].id,
                'amount': 0.08,
                'payment_difference_handling': 'reconcile',
                'writeoff_account_id': self.company_data['default_account_revenue'].id,
                'writeoff_label': 'writeoff',
            })\
            ._create_payments()

        self.assertRecordValues(payment.line_ids.sorted('balance'), [
            # Receivable line:
            {
                'debit': 0.0,
                'credit': 12.01,
                'currency_id': self.currency_data_3['currency'].id,
                'amount_currency': -0.12,
                'reconciled': True,
            },
            # Write-off line:
            {
                'debit': 4.0,
                'credit': 0.0,
                'currency_id': self.currency_data_3['currency'].id,
                'amount_currency': 0.04,
                'reconciled': False,
            },
            # Liquidity line:
            {
                'debit': 8.01,
                'credit': 0.0,
                'currency_id': self.currency_data_3['currency'].id,
                'amount_currency': 0.08,
                'reconciled': False,
            },
        ])

    def test_register_payment_multi_currency_rounding_issue_writeoff_lower_amount_reconcile_negative_delta(self):
        payment = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=self.out_invoice_4.ids)\
            .create({
                'currency_id': self.currency_data_3['currency'].id,
                'amount': 0.08,
                'payment_difference_handling': 'reconcile',
                'writeoff_account_id': self.company_data['default_account_revenue'].id,
                'writeoff_label': 'writeoff',
            })\
            ._create_payments()

        self.assertRecordValues(payment.line_ids.sorted('balance'), [
            # Receivable line:
            {
                'debit': 0.0,
                'credit': 11.99,
                'currency_id': self.currency_data_3['currency'].id,
                'amount_currency': -0.12,
                'reconciled': True,
            },
            # Write-off line:
            {
                'debit': 4.0,
                'credit': 0.0,
                'currency_id': self.currency_data_3['currency'].id,
                'amount_currency': 0.04,
                'reconciled': False,
            },
            # Liquidity line:
            {
                'debit': 7.99,
                'credit': 0.0,
                'currency_id': self.currency_data_3['currency'].id,
                'amount_currency': 0.08,
                'reconciled': False,
            },
        ])

    def test_register_payment_multi_currency_rounding_issue_writeoff_higher_amount_reconcile_positive_delta(self):
        payment = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=self.out_invoice_3.ids)\
            .create({
                'currency_id': self.currency_data_3['currency'].id,
                'amount': 0.16,
                'payment_difference_handling': 'reconcile',
                'writeoff_account_id': self.company_data['default_account_revenue'].id,
                'writeoff_label': 'writeoff',
            })\
            ._create_payments()

        self.assertRecordValues(payment.line_ids.sorted('balance'), [
            # Receivable line:
            {
                'debit': 0.0,
                'credit': 12.01,
                'currency_id': self.currency_data_3['currency'].id,
                'amount_currency': -0.12,
                'reconciled': True,
            },
            # Write-off line:
            {
                'debit': 0.0,
                'credit': 4.0,
                'currency_id': self.currency_data_3['currency'].id,
                'amount_currency': -0.04,
                'reconciled': False,
            },
            # Liquidity line:
            {
                'debit': 16.01,
                'credit': 0.0,
                'currency_id': self.currency_data_3['currency'].id,
                'amount_currency': 0.16,
                'reconciled': False,
            },
        ])

    def test_register_payment_multi_currency_rounding_issue_writeoff_higher_amount_reconcile_negative_delta(self):
        payment = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=self.out_invoice_4.ids)\
            .create({
                'currency_id': self.currency_data_3['currency'].id,
                'amount': 0.16,
                'payment_difference_handling': 'reconcile',
                'writeoff_account_id': self.company_data['default_account_revenue'].id,
                'writeoff_label': 'writeoff',
            })\
            ._create_payments()

        self.assertRecordValues(payment.line_ids.sorted('balance'), [
            # Receivable line:
            {
                'debit': 0.0,
                'credit': 11.99,
                'currency_id': self.currency_data_3['currency'].id,
                'amount_currency': -0.12,
                'reconciled': True,
            },
            # Write-off line:
            {
                'debit': 0.0,
                'credit': 4.0,
                'currency_id': self.currency_data_3['currency'].id,
                'amount_currency': -0.04,
                'reconciled': False,
            },
            # Liquidity line:
            {
                'debit': 15.99,
                'credit': 0.0,
                'currency_id': self.currency_data_3['currency'].id,
                'amount_currency': 0.16,
                'reconciled': False,
            },
        ])

    def test_suggested_default_partner_bank_inbound_payment(self):
        """ Test the suggested bank account on the wizard for inbound payment. """
        self.out_invoice_1.partner_bank_id = False

        ctx = {'active_model': 'account.move', 'active_ids': self.out_invoice_1.ids}
        wizard = self.env['account.payment.register'].with_context(**ctx).create({})
        self.assertRecordValues(wizard, [{
            'journal_id': self.bank_journal_1.id,
            'available_partner_bank_ids': [],
            'partner_bank_id': False,
        }])

        self.bank_journal_2.bank_account_id = self.out_invoice_1.partner_bank_id = self.comp_bank_account2
        wizard = self.env['account.payment.register'].with_context(**ctx).create({})
        self.assertRecordValues(wizard, [{
            'journal_id': self.bank_journal_2.id,
            'available_partner_bank_ids': self.comp_bank_account2.ids,
            'partner_bank_id': self.comp_bank_account2.id,
        }])

        wizard.journal_id = self.bank_journal_1
        self.assertRecordValues(wizard, [{
            'journal_id': self.bank_journal_1.id,
            'available_partner_bank_ids': [],
            'partner_bank_id': False,
        }])

    def test_suggested_default_partner_bank_outbound_payment(self):
        """ Test the suggested bank account on the wizard for outbound payment. """
        self.in_invoice_1.partner_bank_id = False

        ctx = {'active_model': 'account.move', 'active_ids': self.in_invoice_1.ids}
        wizard = self.env['account.payment.register'].with_context(**ctx).create({})
        self.assertRecordValues(wizard, [{
            'journal_id': self.bank_journal_1.id,
            'available_partner_bank_ids': self.partner_a.bank_ids.ids,
            'partner_bank_id': self.partner_bank_account1.id,
        }])

        self.in_invoice_1.partner_bank_id = self.partner_bank_account2
        wizard = self.env['account.payment.register'].with_context(**ctx).create({})
        self.assertRecordValues(wizard, [{
            'journal_id': self.bank_journal_1.id,
            'available_partner_bank_ids': self.partner_a.bank_ids.ids,
            'partner_bank_id': self.partner_bank_account2.id,
        }])

        wizard.journal_id = self.bank_journal_2
        self.assertRecordValues(wizard, [{
            'journal_id': self.bank_journal_2.id,
            'available_partner_bank_ids': self.partner_a.bank_ids.ids,
            'partner_bank_id': self.partner_bank_account2.id,
        }])

    def test_register_payment_inbound_multiple_bank_account(self):
        """ Pay customer invoices with different bank accounts. """
        self.out_invoice_1.partner_bank_id = self.comp_bank_account1
        self.out_invoice_2.partner_bank_id = self.comp_bank_account2
        self.bank_journal_2.bank_account_id = self.comp_bank_account2

        ctx = {'active_model': 'account.move', 'active_ids': (self.out_invoice_1 + self.out_invoice_2).ids}
        wizard = self.env['account.payment.register'].with_context(**ctx).create({'journal_id': self.bank_journal_2.id})
        payments = wizard._create_payments()

        self.assertRecordValues(payments, [
            {
                'journal_id': self.bank_journal_2.id,
                'ref': 'INV/2017/00001',
                'partner_bank_id': self.comp_bank_account2.id,
            },
            {
                'journal_id': self.bank_journal_2.id,
                'ref': 'INV/2017/00002',
                'partner_bank_id': self.comp_bank_account2.id,
            },
        ])

    def test_register_payment_invoice_foreign_curr_payment_comp_curr(self):
        # Invoice 1200 Gol = 400 USD
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2016-01-01',
            'invoice_date': '2016-01-01',
            'partner_id': self.partner_a.id,
            'currency_id': self.currency_data['currency'].id,
            'invoice_line_ids': [Command.create(
                {'product_id': self.product_a.id,
                'price_unit': 1200.0,
                'tax_ids': [],
            })],
        })
        invoice.action_post()

        # Payment of 600 USD (equivalent to 1200 Gol in 2017).
        # 600.0 USD should be computed correctly to fully paid the invoices.
        wizard = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({
                'currency_id': self.company_data['currency'].id,
                'payment_date': '2017-01-01',
            })

        self.assertRecordValues(wizard, [{
            'amount': 600.0,
            'payment_difference': 0.0,
            'currency_id': self.company_data['currency'].id,
        }])

        payment = wizard._create_payments()
        lines = (invoice + payment.move_id).line_ids.filtered(lambda x: x.account_type == 'asset_receivable')
        self.assertRecordValues(lines, [
            {'amount_residual': 0.0, 'amount_residual_currency': 0.0, 'currency_id': self.currency_data['currency'].id, 'reconciled': True},
            {'amount_residual': 0.0, 'amount_residual_currency': 0.0, 'currency_id': self.company_data['currency'].id, 'reconciled': True},
        ])

    def test_register_payment_invoice_comp_curr_payment_foreign_curr(self):
        # Invoice of 400 USD (equivalent to 1200 Gol in 2016).
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2016-01-01',
            'invoice_date': '2016-01-01',
            'partner_id': self.partner_a.id,
            'currency_id': self.company_data['currency'].id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 400.0,
                'tax_ids': [],
            })],
        })
        invoice.action_post()

        # Payment of 600 USD = 1200 Gol.
        # 1200.0 Gol should be computed correctly to fully paid the invoices.
        wizard = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({
                'currency_id': self.currency_data['currency'].id,
                'payment_date': '2017-01-01',
            })

        self.assertRecordValues(wizard, [{
            'amount': 1200.0,
            'payment_difference': 0.0,
            'currency_id': self.currency_data['currency'].id,
        }])

        payment = wizard._create_payments()
        lines = (invoice + payment.move_id).line_ids.filtered(lambda x: x.account_type == 'asset_receivable')
        self.assertRecordValues(lines, [
            {'amount_residual': 0.0, 'amount_residual_currency': 0.0, 'currency_id': self.company_data['currency'].id, 'reconciled': True},
            {'amount_residual': 0.0, 'amount_residual_currency': 0.0, 'currency_id': self.currency_data['currency'].id, 'reconciled': True},
        ])
