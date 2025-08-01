# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import UserError
from odoo.tests import tagged, users
from odoo import fields, Command
from dateutil.relativedelta import relativedelta
from itertools import product
from unittest.mock import patch

from odoo import fields, Command
from odoo.exceptions import UserError
from odoo.tests import tagged, Form
from odoo.tests.common import Like

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.payment.tests.common import PaymentCommon


@tagged('post_install', '-at_install')
class TestAccountPaymentRegister(AccountTestInvoicingCommon, PaymentCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.current_year = fields.Date.today().year

        cls.other_currency = cls.setup_other_currency('EUR')
        cls.other_currency_2 = cls.setup_other_currency('CAD', rates=[('2016-01-01', 3.0), ('2017-01-01', 0.01)])

        cls.payment_debit_account_id = cls.copy_account(cls.inbound_payment_method_line.payment_account_id)
        cls.payment_credit_account_id = cls.copy_account(cls.outbound_payment_method_line.payment_account_id)

        cls.bank_journal_1 = cls.company_data['default_journal_bank']
        cls.bank_journal_2 = cls.company_data['default_journal_bank'].copy()

        cls.invoice_payment_term_1 = cls.env['account.payment.term'].create({
            'name': '2% 10 Net 30',
            'early_discount': True,
            'discount_days': 10,
            'discount_percentage': 2,
            'line_ids': [
                Command.create({
                    'value': 'percent',
                    'value_amount': 100,
                    'delay_type': 'days_after',
                    'nb_days': 30,
                }),
            ],
        })
        cls.term_advance_60days = cls.env.ref('account.account_payment_term_advance_60days')
        cls.term_0_5_10_days = cls.env['account.payment.term'].create({
            'name': 'term_0_5_10_days',
            'line_ids': [
                Command.create({'value': 'percent', 'value_amount': 10.0, 'nb_days': 0}),
                Command.create({'value': 'percent', 'value_amount': 30.0, 'nb_days': 5}),
                Command.create({'value': 'percent', 'value_amount': 60.0, 'nb_days': 10}),
            ],
        })

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
            'currency_id': cls.other_currency.id,
            'invoice_line_ids': [(0, 0, {'product_id': cls.product_a.id, 'price_unit': 1000.0, 'tax_ids': []})],
        })
        cls.out_invoice_2 = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'partner_id': cls.partner_a.id,
            'currency_id': cls.other_currency.id,
            'invoice_line_ids': [(0, 0, {'product_id': cls.product_a.id, 'price_unit': 2000.0, 'tax_ids': []})],
        })
        cls.out_invoice_3 = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'partner_id': cls.partner_a.id,
            'currency_id': cls.other_currency.id,
            'invoice_line_ids': [(0, 0, {'product_id': cls.product_a.id, 'price_unit': 24.02, 'tax_ids': []})],
        })
        cls.out_invoice_4 = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'partner_id': cls.partner_a.id,
            'currency_id': cls.other_currency.id,
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
            'currency_id': cls.other_currency.id,
            'invoice_line_ids': [(0, 0, {'product_id': cls.product_a.id, 'price_unit': 3000.0, 'tax_ids': []})],
        })
        cls.in_invoice_epd_applied = cls.env['account.move'].create({
            'move_type': 'in_invoice',
            'date': fields.Date.today(),
            'invoice_date': fields.Date.today(),
            'partner_id': cls.partner_b.id,
            'invoice_payment_term_id': cls.invoice_payment_term_1.id,
            'invoice_line_ids': [Command.create({'product_id': cls.product_a.id, 'price_unit': 25.0, 'tax_ids': []})],
        })
        cls.in_invoice_epd_not_applied = cls.env['account.move'].create({
            'move_type': 'in_invoice',
            'date': fields.Date.today() - relativedelta(days=11),
            'invoice_date': fields.Date.today() - relativedelta(days=11),
            'partner_id': cls.partner_b.id,
            'invoice_payment_term_id': cls.invoice_payment_term_1.id,
            'invoice_line_ids': [Command.create({'product_id': cls.product_a.id, 'price_unit': 25.0, 'tax_ids': []})],
        })
        (cls.in_invoice_1 + cls.in_invoice_2 + cls.in_invoice_3 + cls.in_invoice_epd_applied + cls.in_invoice_epd_not_applied).action_post()

        # Credit note
        cls.in_refund_1 = cls.env['account.move'].create({
            'move_type': 'in_refund',
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'partner_id': cls.partner_a.id,
            'invoice_line_ids': [(0, 0, {'product_id': cls.product_a.id, 'price_unit': 1600.0, 'tax_ids': []})],
        })
        cls.in_refund_2 = cls.env['account.move'].create({
            'move_type': 'in_refund',
            'date': fields.Date.today(),
            'invoice_date': fields.Date.today(),
            'partner_id': cls.partner_b.id,
            'invoice_line_ids': [Command.create({'product_id': cls.product_a.id, 'price_unit': 10.0, 'tax_ids': []})],
        })
        (cls.in_refund_1 + cls.in_refund_2).action_post()

        cls.branch = cls._create_company(name="Branch", parent_id=cls.env.company.id)
        cls.user_branch = cls.env['res.users'].create({
            'name': 'Branch User',
            'login': 'user_branch',
            'group_ids': [
                Command.link(cls.env.ref('base.group_user').id),
                Command.link(cls.env.ref('account.group_account_user').id),
                Command.link(cls.env.ref('account.group_account_manager').id),
            ],
            'company_id': cls.branch.id,
            'company_ids': [Command.set(cls.branch.ids)],
        })

    @classmethod
    def get_wizard_available_journals(cls, wizard):
        return wizard.available_journal_ids.filtered_domain([
            *cls.env['account.journal']._check_company_domain(wizard.company_id),
        ])

    def test_register_payment_single_batch_grouped_keep_open_lower_amount(self):
        ''' Pay 800.0 with 'open' as payment difference handling on two customer invoices (1000 + 2000). '''
        active_ids = (self.out_invoice_1 + self.out_invoice_2).ids
        payments = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=active_ids).create({
            'amount': 800.0,
            'group_payment': True,
            'payment_difference_handling': 'open',
            'currency_id': self.other_currency.id,
            'payment_method_line_id': self.inbound_payment_method_line.id,
        })._create_payments()

        self.assertRecordValues(payments, [{
            'memo': Like(f'GROUP/{self.current_year}/...'),
            'payment_method_line_id': self.inbound_payment_method_line.id,
        }])
        self.assertRecordValues(payments.move_id.line_ids.sorted('balance'), [
            # Receivable line:
            {
                'debit': 0.0,
                'credit': 400.0,
                'currency_id': self.other_currency.id,
                'amount_currency': -800.0,
                'reconciled': True,
            },
            # Liquidity line:
            {
                'debit': 400.0,
                'credit': 0.0,
                'currency_id': self.other_currency.id,
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
            'currency_id': self.other_currency.id,
            'payment_method_line_id': self.inbound_payment_method_line.id,
        })._create_payments()

        self.assertRecordValues(payments, [{
            'memo': Like(f'GROUP/{self.current_year}/...'),
            'payment_method_line_id': self.inbound_payment_method_line.id,
        }])
        self.assertRecordValues(payments.move_id.line_ids.sorted('balance'), [
            # Receivable line:
            {
                'debit': 0.0,
                'credit': 1550.0,
                'currency_id': self.other_currency.id,
                'amount_currency': -3100.0,
                'reconciled': False,
            },
            # Liquidity line:
            {
                'debit': 1550.0,
                'credit': 0.0,
                'currency_id': self.other_currency.id,
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
            'memo': Like(f'GROUP/{self.current_year}/...'),
            'payment_method_line_id': self.inbound_payment_method_line.id,
        }])
        self.assertRecordValues(payments.move_id.line_ids.sorted('balance'), [
            # Receivable line:
            {
                'debit': 0.0,
                'credit': 1500.0,
                'currency_id': self.other_currency.id,
                'amount_currency': -3000.0,
                'reconciled': True,
            },
            # Liquidity line:
            {
                'debit': 400.0,
                'credit': 0.0,
                'currency_id': self.other_currency.id,
                'amount_currency': 800.0,
                'reconciled': False,
            },
            # Writeoff line:
            {
                'debit': 1100.0,
                'credit': 0.0,
                'currency_id': self.other_currency.id,
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
            'memo': Like(f'GROUP/{self.current_year}/...'),
            'payment_method_line_id': self.inbound_payment_method_line.id,
        }])
        self.assertRecordValues(payments.move_id.line_ids.sorted('balance'), [
            # Receivable line:
            {
                'debit': 0.0,
                'credit': 1500.0,
                'currency_id': self.other_currency.id,
                'amount_currency': -3000.0,
                'reconciled': True,
            },
            # Writeoff line:
            {
                'debit': 0.0,
                'credit': 50.0,
                'currency_id': self.other_currency.id,
                'amount_currency': -100.0,
                'reconciled': False,
            },
            # Liquidity line:
            {
                'debit': 1550.0,
                'credit': 0.0,
                'currency_id': self.other_currency.id,
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
            'payment_method_line_id': self.outbound_payment_method_line.id,
        })._create_payments()

        self.assertRecordValues(payments, [{
            'memo': Like(f'GROUP/{self.current_year}/...'),
            'payment_method_line_id': self.outbound_payment_method_line.id,
        }])
        self.assertRecordValues(payments.move_id.line_ids.sorted('balance'), [
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
            'payment_method_line_id': self.outbound_payment_method_line.id,
        })._create_payments()

        self.assertRecordValues(payments, [{
            'memo': Like(f'GROUP/{self.current_year}/...'),
            'payment_method_line_id': self.outbound_payment_method_line.id,
        }])
        self.assertRecordValues(payments.move_id.line_ids.sorted('balance'), [
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
        payments = payment_register._create_payments()
        self.assertRecordValues(payments, [
            {
                'memo': 'INV/2017/00001',
                'payment_method_line_id': self.inbound_payment_method_line.id,
            },
            {
                'memo': 'INV/2017/00002',
                'payment_method_line_id': self.inbound_payment_method_line.id,
            },
        ])
        self.assertRecordValues(payments[0].move_id.line_ids.sorted('balance') + payments[1].move_id.line_ids.sorted('balance'), [
            # == Payment 1: to pay out_invoice_1 ==
            # Receivable line:
            {
                'debit': 0.0,
                'credit': 500.0,
                'currency_id': self.other_currency.id,
                'amount_currency': -1000.0,
                'reconciled': True,
            },
            # Liquidity line:
            {
                'debit': 500.0,
                'credit': 0.0,
                'currency_id': self.other_currency.id,
                'amount_currency': 1000.0,
                'reconciled': False,
            },
            # == Payment 2: to pay out_invoice_2 ==
            # Receivable line:
            {
                'debit': 0.0,
                'credit': 1000.0,
                'currency_id': self.other_currency.id,
                'amount_currency': -2000.0,
                'reconciled': True,
            },
            # Liquidity line:
            {
                'debit': 1000.0,
                'credit': 0.0,
                'currency_id': self.other_currency.id,
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
                'memo': 'BILL/2017/01/0001',
                'payment_type': 'outbound',
            }
        ])

        self.assertRecordValues(payments[1], [
            {
                'memo': 'RBILL/2017/01/0001',
                'payment_type': 'inbound',
            },
        ])

        self.assertRecordValues(payments[0].move_id.line_ids.sorted('balance'), [
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
        self.assertRecordValues(payments[1].move_id.line_ids.sorted('balance'), [
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
                'memo': Like(f'GROUP/{self.current_year}/...'),
                'payment_method_line_id': self.outbound_payment_method_line.id,
            },
        ])
        self.assertRecordValues(payments[0].move_id.line_ids.sorted('balance'), [
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

        self.in_invoice_1.with_context(skip_readonly_check=True).partner_bank_id = bank1
        self.in_invoice_2.with_context(skip_readonly_check=True).partner_bank_id = bank2

        active_ids = (self.in_invoice_1 + self.in_invoice_2 + self.in_refund_1).ids
        payments = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=active_ids).create({
            'group_payment': True,
        })._create_payments()

        self.assertRecordValues(payments, [
            {
                'memo': 'BILL/2017/01/0001',
                'payment_method_line_id': self.outbound_payment_method_line.id,
            },
            {
                'memo': 'BILL/2017/01/0002',
                'payment_method_line_id': self.outbound_payment_method_line.id,
            },
            {
                'memo': 'RBILL/2017/01/0001',
                'payment_method_line_id': self.inbound_payment_method_line.id,
            },
        ])
        self.assertRecordValues(payments[0].move_id.line_ids.sorted('balance') + payments[1].move_id.line_ids.sorted('balance') + payments[2].move_id.line_ids.sorted('balance'), [
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
            })
        payments = payment_register._create_payments()

        self.assertRecordValues(payments, [
            {
                'memo': Like(f'GROUP/{self.current_year}/...'),
                'payment_method_line_id': self.outbound_payment_method_line.id,
            },
            {
                'memo': 'BILL/2017/01/0003',
                'payment_method_line_id': self.outbound_payment_method_line.id,
            },
        ])
        self.assertRecordValues(payments[0].move_id.line_ids.sorted('balance') + payments[1].move_id.line_ids.sorted('balance'), [
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
                'currency_id': self.other_currency.id,
                'amount_currency': -3000.0,
                'reconciled': False,
            },
            # Payable line:
            {
                'debit': 1500.0,
                'credit': 0.0,
                'currency_id': self.other_currency.id,
                'amount_currency': 3000.0,
                'reconciled': True,
            },
        ])

    def test_register_payment_multi_batches_not_grouped(self):
        ''' Choose to pay multiple batches, one with two customer invoices (1000 + 2000)
         and one with a vendor bill of 600, by splitting payments.
         '''
        self.in_invoice_1.with_context(skip_readonly_check=True).partner_bank_id = self.partner_bank_account1
        self.in_invoice_2.with_context(skip_readonly_check=True).partner_bank_id = self.partner_bank_account2

        active_ids = (self.in_invoice_1 + self.in_invoice_2 + self.in_invoice_3).ids
        payments = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=active_ids).create({
            'group_payment': False,
        })._create_payments()

        self.assertRecordValues(payments, [
            {
                'journal_id': self.bank_journal_1.id,
                'memo': 'BILL/2017/01/0001',
                'payment_method_line_id': self.outbound_payment_method_line.id,
                'partner_bank_id': self.partner_bank_account1.id,
            },
            {
                'journal_id': self.bank_journal_1.id,
                'memo': 'BILL/2017/01/0002',
                'payment_method_line_id': self.outbound_payment_method_line.id,
                'partner_bank_id': self.partner_bank_account2.id,
            },
            {
                'journal_id': self.bank_journal_1.id,
                'memo': 'BILL/2017/01/0003',
                'payment_method_line_id': self.outbound_payment_method_line.id,
                'partner_bank_id': False,
            },
        ])
        self.assertRecordValues(payments[0].move_id.line_ids.sorted('balance') + payments[1].move_id.line_ids.sorted('balance') + payments[2].move_id.line_ids.sorted('balance'), [
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
                'currency_id': self.other_currency.id,
                'amount_currency': -3000.0,
                'reconciled': False,
            },
            # Payable line:
            {
                'debit': 1500.0,
                'credit': 0.0,
                'currency_id': self.other_currency.id,
                'amount_currency': 3000.0,
                'reconciled': True,
            },
        ])

    def test_register_payment_constraints(self):
        # Test to register a payment for an already fully reconciled journal entry.
        self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=self.out_invoice_2.ids)\
            .create({})\
            ._create_payments()
        with self.assertRaises(UserError):
            self.env['account.payment.register']\
                .with_context(active_model='account.move', active_ids=self.out_invoice_2.ids)\
                .create({})

    def test_register_payment_doesnt_send_email(self):
        ''' When registering a payment manually with a payment register,
        we shouldn't sent email notification automatically.
        '''
        self.env['ir.config_parameter'].set_param('sale.automatic_invoice', True)
        payment_token = self._create_token(provider_id=self._prepare_provider(code='demo').id,
                                           demo_simulated_state='done')
        payment_register = self.env['account.payment.register']\
                               .with_context(active_model='account.move', active_ids=self.out_invoice_4.ids)\
                               .create({'payment_token_id': payment_token.id})
        with patch(
            'odoo.addons.sale.models.payment_transaction.PaymentTransaction'
            '._send_invoice'
        ) as patched:
            payment_register._create_payments()
            patched.assert_not_called()

    def test_register_payment_multi_currency_rounding_issue_positive_delta(self):
        ''' When registering a payment using a different currency than the invoice one, the invoice must be fully paid
        at the end whatever the currency rate.
        '''
        payment = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=self.out_invoice_3.ids)\
            .create({
                'currency_id': self.other_currency_2.id,
                'amount': 0.12,
            })\
            ._create_payments()

        self.assertRecordValues(payment.move_id.line_ids.sorted('balance'), [
            # Receivable line:
            {
                'debit': 0.0,
                'credit': 12.01,
                'currency_id': self.other_currency_2.id,
                'amount_currency': -0.12,
                'reconciled': True,
            },
            # Liquidity line:
            {
                'debit': 12.01,
                'credit': 0.0,
                'currency_id': self.other_currency_2.id,
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
                'currency_id': self.other_currency_2.id,
                'amount': 0.12,
            })\
            ._create_payments()

        self.assertRecordValues(payment.move_id.line_ids.sorted('balance'), [
            # Receivable line:
            {
                'debit': 0.0,
                'credit': 11.99,
                'currency_id': self.other_currency_2.id,
                'amount_currency': -0.12,
                'reconciled': True,
            },
            # Liquidity line:
            {
                'debit': 11.99,
                'credit': 0.0,
                'currency_id': self.other_currency_2.id,
                'amount_currency': 0.12,
                'reconciled': False,
            },
        ])

    def test_register_payment_multi_currency_rounding_issue_writeoff_lower_amount_keep_open(self):
        payment = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=self.out_invoice_3.ids)\
            .create({
                'currency_id': self.other_currency_2.id,
                'amount': 0.08,
                'payment_difference_handling': 'open',
            })\
            ._create_payments()

        self.assertRecordValues(payment.move_id.line_ids.sorted('balance'), [
            # Receivable line:
            {
                'debit': 0.0,
                'credit': 8.0,
                'currency_id': self.other_currency_2.id,
                'amount_currency': -0.08,
                'reconciled': True,
            },
            # Liquidity line:
            {
                'debit': 8.0,
                'credit': 0.0,
                'currency_id': self.other_currency_2.id,
                'amount_currency': 0.08,
                'reconciled': False,
            },
        ])

    def test_register_payment_multi_currency_rounding_issue_writeoff_lower_amount_reconcile_positive_delta(self):
        payment = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=self.out_invoice_3.ids)\
            .create({
                'currency_id': self.other_currency_2.id,
                'amount': 0.08,
                'payment_difference_handling': 'reconcile',
                'writeoff_account_id': self.company_data['default_account_revenue'].id,
                'writeoff_label': 'writeoff',
            })\
            ._create_payments()

        self.assertRecordValues(payment.move_id.line_ids.sorted('balance'), [
            # Receivable line:
            {
                'debit': 0.0,
                'credit': 12.01,
                'currency_id': self.other_currency_2.id,
                'amount_currency': -0.12,
                'reconciled': True,
            },
            # Write-off line:
            {
                'debit': 4.0,
                'credit': 0.0,
                'currency_id': self.other_currency_2.id,
                'amount_currency': 0.04,
                'reconciled': False,
            },
            # Liquidity line:
            {
                'debit': 8.01,
                'credit': 0.0,
                'currency_id': self.other_currency_2.id,
                'amount_currency': 0.08,
                'reconciled': False,
            },
        ])

    def test_register_payment_multi_currency_rounding_issue_writeoff_lower_amount_reconcile_negative_delta(self):
        payment = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=self.out_invoice_4.ids)\
            .create({
                'currency_id': self.other_currency_2.id,
                'amount': 0.08,
                'payment_difference_handling': 'reconcile',
                'writeoff_account_id': self.company_data['default_account_revenue'].id,
                'writeoff_label': 'writeoff',
            })\
            ._create_payments()

        self.assertRecordValues(payment.move_id.line_ids.sorted('balance'), [
            # Receivable line:
            {
                'debit': 0.0,
                'credit': 11.99,
                'currency_id': self.other_currency_2.id,
                'amount_currency': -0.12,
                'reconciled': True,
            },
            # Write-off line:
            {
                'debit': 4.0,
                'credit': 0.0,
                'currency_id': self.other_currency_2.id,
                'amount_currency': 0.04,
                'reconciled': False,
            },
            # Liquidity line:
            {
                'debit': 7.99,
                'credit': 0.0,
                'currency_id': self.other_currency_2.id,
                'amount_currency': 0.08,
                'reconciled': False,
            },
        ])

    def test_register_payment_multi_currency_rounding_issue_writeoff_higher_amount_reconcile_positive_delta(self):
        payment = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=self.out_invoice_3.ids)\
            .create({
                'currency_id': self.other_currency_2.id,
                'amount': 0.16,
                'payment_difference_handling': 'reconcile',
                'writeoff_account_id': self.company_data['default_account_revenue'].id,
                'writeoff_label': 'writeoff',
            })\
            ._create_payments()

        self.assertRecordValues(payment.move_id.line_ids.sorted('balance'), [
            # Receivable line:
            {
                'debit': 0.0,
                'credit': 12.01,
                'currency_id': self.other_currency_2.id,
                'amount_currency': -0.12,
                'reconciled': True,
            },
            # Write-off line:
            {
                'debit': 0.0,
                'credit': 4.0,
                'currency_id': self.other_currency_2.id,
                'amount_currency': -0.04,
                'reconciled': False,
            },
            # Liquidity line:
            {
                'debit': 16.01,
                'credit': 0.0,
                'currency_id': self.other_currency_2.id,
                'amount_currency': 0.16,
                'reconciled': False,
            },
        ])

    def test_register_payment_multi_currency_rounding_issue_writeoff_higher_amount_reconcile_negative_delta(self):
        payment = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=self.out_invoice_4.ids)\
            .create({
                'currency_id': self.other_currency_2.id,
                'amount': 0.16,
                'payment_difference_handling': 'reconcile',
                'writeoff_account_id': self.company_data['default_account_revenue'].id,
                'writeoff_label': 'writeoff',
            })\
            ._create_payments()

        self.assertRecordValues(payment.move_id.line_ids.sorted('balance'), [
            # Receivable line:
            {
                'debit': 0.0,
                'credit': 11.99,
                'currency_id': self.other_currency_2.id,
                'amount_currency': -0.12,
                'reconciled': True,
            },
            # Write-off line:
            {
                'debit': 0.0,
                'credit': 4.0,
                'currency_id': self.other_currency_2.id,
                'amount_currency': -0.04,
                'reconciled': False,
            },
            # Liquidity line:
            {
                'debit': 15.99,
                'credit': 0.0,
                'currency_id': self.other_currency_2.id,
                'amount_currency': 0.16,
                'reconciled': False,
            },
        ])

    def test_register_foreign_currency_on_payment_exchange_writeoff_account(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({'product_id': self.product_a.id, 'price_unit': 1000.0, 'tax_ids': []})],
        })
        invoice.action_post()
        # 1998 GOL = 999 USD
        payment = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({
                'currency_id': self.other_currency.id,
                'amount': 1998,
                'payment_difference_handling': 'reconcile',
                'writeoff_account_id': self.env.company.expense_currency_exchange_account_id.id,
            })\
            ._create_payments()

        self.assertRecordValues(payment.move_id.line_ids.sorted('balance'), [
            # Receivable line:
            {
                'debit': 0.0,
                'credit': 1000.0,
                'currency_id': self.other_currency.id,
                'amount_currency': -1998.0,
                'reconciled': True,
            },
            # Liquidity line:
            {
                'debit': 1000.0,
                'credit': 0.0,
                'currency_id': self.other_currency.id,
                'amount_currency': 1998.0,
                'reconciled': False,
            },
        ])

    def test_register_foreign_currency_on_invoice_exchange_writeoff_account(self):
        self.env.company.tax_exigibility = True
        self.env.company.account_cash_basis_base_account_id = self.env['account.account'].create({
            'code': 'cash.basis.base.account',
            'name': 'cash_basis_base_account',
            'account_type': 'income',
        })

        default_tax = self.company_data['default_tax_sale']
        default_tax.cash_basis_transition_account_id = self.env['account.account'].create({
            'code': 'cash.basis.transfer.account',
            'name': 'cash_basis_transfer_account',
            'account_type': 'income',
            'reconcile': True,
        })
        default_tax.tax_exigibility = 'on_payment'

        # 1150 GOL = 575 USD
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'partner_id': self.partner_a.id,
            'currency_id': self.other_currency.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 1000.0,
                'tax_ids': [Command.set(default_tax.ids)],
            })],
        })
        invoice.action_post()

        # 1110 GOL = 370 USD
        payment = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({
                'currency_id': self.env.company.currency_id.id,
                'amount': 370.0,
                'payment_date': '2016-01-01',
                'payment_difference_handling': 'reconcile',
                'writeoff_account_id': self.env.company.expense_currency_exchange_account_id.id,
            })\
            ._create_payments()

        self.assertRecordValues(payment.move_id.line_ids.sorted('balance'), [
            # Receivable line:
            {
                'balance': -370.0,
                'currency_id': self.env.company.currency_id.id,
                'amount_currency': -370.0,
                'reconciled': True,
            },
            # Liquidity line:
            {
                'balance': 370.0,
                'currency_id': self.env.company.currency_id.id,
                'amount_currency': 370.0,
                'reconciled': False,
            },
        ])
        self.assertRecordValues(invoice.line_ids.matched_credit_ids, [
            {
                'amount': 370.0,
                'debit_amount_currency': 1150.0,
                'credit_amount_currency': 370.0,
            },
            {
                'amount': 205.00,
                'debit_amount_currency': 0.0,
                'credit_amount_currency': 0.0,
            },
        ])

        # Cash basis.
        caba_move = self.env['account.move'].search([('tax_cash_basis_origin_move_id', '=', invoice.id)])
        self.assertRecordValues(caba_move.line_ids.sorted('balance'), [
            {
                'balance': -321.74,
                'currency_id': self.other_currency.id,
                'amount_currency': -1000.0,
            },
            {
                'balance': -48.26,
                'currency_id': self.other_currency.id,
                'amount_currency': -150.0,
            },
            {
                'balance': 48.26,
                'currency_id': self.other_currency.id,
                'amount_currency': 150.0,
            },
            {
                'balance': 321.74,
                'currency_id': self.other_currency.id,
                'amount_currency': 1000.0,
            },
        ])

    def test_suggested_default_partner_bank_inbound_payment(self):
        """ Test the suggested bank account on the wizard for inbound payment. """
        self.out_invoice_1.with_context(skip_readonly_check=True).partner_bank_id = False

        ctx = {'active_model': 'account.move', 'active_ids': self.out_invoice_1.ids}
        wizard = self.env['account.payment.register'].with_context(**ctx).create({})
        self.assertRecordValues(wizard, [{
            'journal_id': self.bank_journal_1.id,
            'available_partner_bank_ids': [],
            'partner_bank_id': False,
        }])

        self.out_invoice_1.with_context(skip_readonly_check=True).partner_bank_id = self.comp_bank_account2
        self.bank_journal_2.bank_account_id = self.comp_bank_account2
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
        self.in_invoice_1.with_context(skip_readonly_check=True).partner_bank_id = False

        ctx = {'active_model': 'account.move', 'active_ids': self.in_invoice_1.ids}
        wizard = self.env['account.payment.register'].with_context(**ctx).create({})
        self.assertRecordValues(wizard, [{
            'journal_id': self.bank_journal_1.id,
            'available_partner_bank_ids': self.partner_a.bank_ids.ids,
            'partner_bank_id': self.partner_bank_account1.id,
        }])

        self.in_invoice_1.with_context(skip_readonly_check=True).partner_bank_id = self.partner_bank_account2
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
        self.out_invoice_1.with_context(skip_readonly_check=True).partner_bank_id = self.comp_bank_account1
        self.out_invoice_2.with_context(skip_readonly_check=True).partner_bank_id = self.comp_bank_account2
        self.bank_journal_2.bank_account_id = self.comp_bank_account2

        ctx = {'active_model': 'account.move', 'active_ids': (self.out_invoice_1 + self.out_invoice_2).ids}
        wizard = self.env['account.payment.register'].with_context(**ctx).create({'journal_id': self.bank_journal_2.id})
        payments = wizard._create_payments()

        self.assertRecordValues(payments, [
            {
                'journal_id': self.bank_journal_2.id,
                'memo': 'INV/2017/00001',
                'partner_bank_id': self.comp_bank_account2.id,
            },
            {
                'journal_id': self.bank_journal_2.id,
                'memo': 'INV/2017/00002',
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
            'currency_id': self.other_currency.id,
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
            'currency_id': self.company_data['currency'].id,
        }])

        payment = wizard._create_payments()
        lines = (invoice + payment.move_id).line_ids.filtered(lambda x: x.account_type == 'asset_receivable')
        self.assertRecordValues(lines, [
            {'amount_residual': 0.0, 'amount_residual_currency': 0.0, 'currency_id': self.other_currency.id, 'reconciled': True},
            {'amount_residual': 0.0, 'amount_residual_currency': 0.0, 'currency_id': self.company_data['currency'].id, 'reconciled': True},
        ])

    def test_register_payment_invoice_comp_curr_payment_foreign_curr(self):
        # Invoice of 600 USD (equivalent to 1200 Gol in 2017).
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2016-01-01',
            'invoice_date': '2016-01-01',
            'partner_id': self.partner_a.id,
            'currency_id': self.company_data['currency'].id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 600.0,
                'tax_ids': [],
            })],
        })
        invoice.action_post()

        # Payment of 600 USD = 1200 Gol.
        # 1200.0 Gol should be computed correctly to fully paid the invoices.
        wizard = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({
                'currency_id': self.other_currency.id,
                'payment_date': '2017-01-01',
            })

        self.assertRecordValues(wizard, [{
            'amount': 1200.0,
            'currency_id': self.other_currency.id,
        }])

        payment = wizard._create_payments()
        lines = (invoice + payment.move_id).line_ids.filtered(lambda x: x.account_type == 'asset_receivable')
        self.assertRecordValues(lines, [
            {'amount_residual': 0.0, 'amount_residual_currency': 0.0, 'currency_id': self.company_data['currency'].id, 'reconciled': True},
            {'amount_residual': 0.0, 'amount_residual_currency': 0.0, 'currency_id': self.other_currency.id, 'reconciled': True},
        ])

    def test_payment_method_different_type_single_batch_not_grouped(self):
        """ Test payment methods when paying a bill and a refund with separated payments (1000 + -2000)."""
        invoice_1 = self.in_invoice_1
        invoice_2 = invoice_1.copy({'invoice_date': invoice_1.invoice_date, 'partner_id': self.partner_b.id})
        refund_1, refund_2 = self.env['account.move'].create([
            {
                'move_type': 'in_refund',
                'date': '2017-01-01',
                'invoice_date': '2017-01-01',
                'partner_id': self.partner_a.id,
                'invoice_line_ids': [(0, 0, {'product_id': self.product_a.id, 'price_unit': 1600.0, 'tax_ids': False})],
            },
            {
                'move_type': 'in_refund',
                'date': '2017-01-01',
                'invoice_date': '2017-01-01',
                'partner_id': self.partner_b.copy({'property_account_position_id': False}).id,
                'invoice_line_ids': [(0, 0, {'product_id': self.product_a.id, 'price_unit': 1600.0, 'tax_ids': False})],
            },
        ])
        (invoice_2 + refund_1 + refund_2).action_post()

        for moves in ((invoice_1 + invoice_2), (refund_1 + refund_2)):
            wizard = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=moves.ids).create({
                'group_payment': False,
            })

            expected_available_payment_method_lines = wizard.journal_id.inbound_payment_method_line_ids if moves[0].move_type == 'in_refund' else wizard.journal_id.outbound_payment_method_line_ids

            self.assertRecordValues(wizard, [
                {
                    'available_payment_method_line_ids': expected_available_payment_method_lines.ids,
                    'payment_method_line_id': expected_available_payment_method_lines[:1].id,
                }
            ])

        active_ids = (invoice_1 + invoice_2 + refund_1 + refund_2).ids
        payments = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=active_ids).create({
            'group_payment': False,
        })._create_payments()

        self.assertRecordValues(payments[0], [
            {
                'memo': 'BILL/2017/01/0001',
                'payment_method_line_id': self.bank_journal_1.outbound_payment_method_line_ids[0].id,
                'payment_type': 'outbound',
            }
        ])

        self.assertRecordValues(payments[1], [
            {
                'memo': 'BILL/2017/01/0004',
                'payment_method_line_id': self.bank_journal_1.outbound_payment_method_line_ids[0].id,
                'payment_type': 'outbound',
            }
        ])

        self.assertRecordValues(payments[2], [
            {
                'memo': 'RBILL/2017/01/0002',
                'payment_method_line_id': self.bank_journal_1.inbound_payment_method_line_ids[0].id,
                'payment_type': 'inbound',
            },
        ])

        self.assertRecordValues(payments[3], [
            {
                'memo': 'RBILL/2017/01/0003',
                'payment_method_line_id': self.bank_journal_1.inbound_payment_method_line_ids[0].id,
                'payment_type': 'inbound',
            },
        ])

        self.assertRecordValues(payments[0].move_id.line_ids.sorted('balance'), [
            # == Payment 1: to pay invoice_1 ==
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

        self.assertRecordValues(payments[1].move_id.line_ids.sorted('balance'), [
            # == Payment 2: to pay invoice_2 ==
            # Payable line:
            {
                'debit': 0.0,
                'credit': 1000.0,
                'currency_id': self.company_data['currency'].id,
                'amount_currency': -1000.0,
                'reconciled': False,
            },
            # Liquidity line:
            {
                'debit': 1000.0,
                'credit': 0.0,
                'currency_id': self.company_data['currency'].id,
                'amount_currency': 1000.0,
                'reconciled': True,
            },
        ])

        self.assertRecordValues(payments[2].move_id.line_ids.sorted('balance'), [
            # == Payment 3: to pay refund_1 ==
            # Liquidity line:
            {
                'debit': 0.0,
                'credit': 1600.0,
                'currency_id': self.company_data['currency'].id,
                'amount_currency': -1600.0,
                'reconciled': True,
            },
            # Payable line:
            {
                'debit': 1600.0,
                'credit': 0.0,
                'currency_id': self.company_data['currency'].id,
                'amount_currency': 1600.0,
                'reconciled': False,
            },
        ])

        self.assertRecordValues(payments[3].move_id.line_ids.sorted('balance'), [
            # == Payment 4: to pay refund_2 ==
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

    def test_group_payment_method_with_and_without_discount(self):
        """ Test payment methods when creating group payment for discounted and non-discounted bills"""
        active_ids = (self.in_invoice_epd_applied + self.in_invoice_epd_not_applied).ids

        wizard = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=active_ids).create({
            'group_payment': True,
        })

        self.assertEqual(wizard.amount, 49.50)

    def test_group_payment_method_with_and_without_discount_and_refund(self):
        """ Test payment methods when creating group payment for discounted and non-discounted bills with a refund"""
        active_ids = (self.in_invoice_epd_applied + self.in_invoice_epd_not_applied + self.in_refund_2).ids

        wizard = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=active_ids).create({
            'group_payment': True,
        })

        self.assertEqual(
            wizard.amount, 46.50,
            "Due to the payment term on partner_b, only 3 is removed for in_refund_2, as it is the first installment"
        )
        self.assertEqual(wizard.installments_switch_amount, 39.50, "With the full refund and the epd")

    def test_keep_user_amount(self):
        comp_curr = self.env.company.currency_id
        foreign_curr = self.other_currency

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2016-01-01',
            'invoice_payment_term_id': self.term_advance_60days.id,
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({'product_id': self.product_a.id})],
        })
        invoice.action_post()
        self.assertRecordValues(invoice.line_ids.sorted().filtered('date_maturity'), [
            {'date_maturity': fields.Date.from_string('2016-01-01'), 'amount_currency': 345.0},
            {'date_maturity': fields.Date.from_string('2016-03-01'), 'amount_currency': 805.0},
        ])

        wizard = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({'payment_date': '2016-01-01'})
        self.assertRecordValues(wizard, [{
            'amount': 345.0,
            'currency_id': comp_curr.id,
            'custom_user_amount': 0.0,
            'custom_user_currency_id': False,
            'payment_difference': 0.0,
            'installments_mode': 'next',
            'installments_switch_amount': 1150.0,
        }])

        # Custom amount.
        with Form(wizard) as wizard_form:
            wizard_form.amount = 300.0
        self.assertRecordValues(wizard, [{
            'amount': 300.0,
            'currency_id': comp_curr.id,
            'custom_user_amount': 300.0,
            'custom_user_currency_id': comp_curr.id,
            'payment_difference': 850.0,
            'installments_mode': 'full',
            'installments_switch_amount': 345.0,
        }])

        # Custom currency.
        with Form(wizard) as wizard_form:
            wizard_form.currency_id = foreign_curr
        self.assertRecordValues(wizard, [{
            'amount': 900.0,
            'currency_id': foreign_curr.id,
            'custom_user_amount': 900.0,
            'custom_user_currency_id': foreign_curr.id,
            'payment_difference': 2550.0,
            'installments_mode': 'full',
            'installments_switch_amount': 1035.0,
        }])

        # Switch to full installment amount.
        with Form(wizard) as wizard_form:
            wizard_form.amount = wizard.installments_switch_amount
        self.assertRecordValues(wizard, [{
            'amount': 1035.0,
            'currency_id': foreign_curr.id,
            'custom_user_amount': 0.0,
            'custom_user_currency_id': False,
            'payment_difference': 0.0,
            'installments_mode': 'next',
            'installments_switch_amount': 3450.0,
        }])

        # Custom amount.
        with Form(wizard) as wizard_form:
            wizard_form.amount = 3000.0
        self.assertRecordValues(wizard, [{
            'amount': 3000.0,
            'currency_id': foreign_curr.id,
            'custom_user_amount': 3000.0,
            'custom_user_currency_id': foreign_curr.id,
            'payment_difference': 450.0,
            'installments_mode': 'full',
            'installments_switch_amount': 1035.0,
        }])

        # Change the date (rate changed from 1:3 to 1:2).
        with Form(wizard) as wizard_form:
            wizard_form.payment_date = fields.Date.from_string('2017-01-01')
        self.assertRecordValues(wizard, [{
            'amount': 3000.0,
            'currency_id': foreign_curr.id,
            'custom_user_amount': 3000.0,
            'custom_user_currency_id': foreign_curr.id,
            'payment_difference': -700.0,
            'installments_mode': 'full',
            'installments_switch_amount': 2300.0,
        }])

    def test_installment_mode_single_batch(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2016-01-01',
            'invoice_payment_term_id': self.term_0_5_10_days.id,
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({'product_id': self.product_a.id})],
        })
        invoice.action_post()
        self.assertRecordValues(invoice.line_ids.sorted().filtered('date_maturity'), [
            {'date_maturity': fields.Date.from_string('2016-01-01'), 'amount_currency': 115.0},
            {'date_maturity': fields.Date.from_string('2016-01-06'), 'amount_currency': 345.0},
            {'date_maturity': fields.Date.from_string('2016-01-11'), 'amount_currency': 690.0},
        ])

        term_lines = invoice.line_ids.filtered('date_maturity').sorted('date_maturity')

        wizard = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({'payment_date': '2015-12-31'})

        self.assertRecordValues(wizard, [{
            'amount': 115.0,
            'payment_difference': 0.0,
            'installments_mode': 'next',
            'installments_switch_amount': 1150.0,
            'communication': wizard._get_communication(term_lines[0]),
        }])

        # Paying less switch the wizard in full mode.
        wizard.amount = 114.0
        self.assertRecordValues(wizard, [{
            'amount': 114.0,
            'payment_difference': 1036.0,
            'installments_mode': 'full',
            'installments_switch_amount': 115.0,
            'communication': invoice.name,
        }])

        # Case when at date of the first installment.
        wizard.payment_date = '2016-01-01'
        self.assertRecordValues(wizard, [{
            'amount': 115.0,
            'payment_difference': 0.0,
            'installments_mode': 'next',
            'installments_switch_amount': 1150.0,
            'communication': wizard._get_communication(term_lines[0]),
        }])

        # Paying more switch the wizard in full mode.
        wizard.amount = 116.0
        self.assertRecordValues(wizard, [{
            'amount': 116.0,
            'payment_difference': 1034.0,
            'installments_mode': 'full',
            'installments_switch_amount': 115.0,
            'communication': invoice.name,
        }])

        # First installment is overdue.
        wizard.payment_date = '2016-01-02'
        self.assertRecordValues(wizard, [{
            'amount': 115.0,
            'payment_difference': 0.0,
            'installments_mode': 'overdue',
            'installments_switch_amount': 1150.0,
            'communication': wizard._get_communication(term_lines[0]),
        }])

        # Second installment is overdue.
        wizard.payment_date = '2016-01-07'
        self.assertRecordValues(wizard, [{
            'amount': 460.0,
            'payment_difference': 0.0,
            'installments_mode': 'overdue',
            'installments_switch_amount': 1150.0,
            'communication': invoice.name,
        }])

        # Third installment is overdue.
        wizard.payment_date = '2016-01-12'
        self.assertRecordValues(wizard, [{
            'amount': 1150.0,
            'payment_difference': 0.0,
            'installments_mode': 'full',
            'installments_switch_amount': 0.0,
            'communication': invoice.name,
        }])

    def test_installment_mode_multiple_batches(self):
        """ Tests the wizard values if you select several invoices that produce several batches, with installments """
        in_invoice_cad_with_payment_term, in_invoice_cad_copy = self.env['account.move'].create([
            {
                'move_type': 'in_invoice',
                'invoice_date': '2016-01-01',
                'invoice_payment_term_id': self.term_0_5_10_days.id,
                'currency_id': self.other_currency_2.id,
                'partner_id': self.partner_a.id,
                'invoice_line_ids': [Command.create({'product_id': self.product_a.id, 'price_unit': 1000.0, 'tax_ids': []})],
            },
            {
                'move_type': 'in_invoice',
                'invoice_date': '2016-01-01',
                'invoice_payment_term_id': self.term_0_5_10_days.id,
                'currency_id': self.other_currency_2.id,
                'partner_id': self.partner_a.id,
                'invoice_line_ids': [Command.create({'product_id': self.product_a.id, 'price_unit': 1000.0, 'tax_ids': []})],
            },
        ])
        (in_invoice_cad_with_payment_term + in_invoice_cad_copy).action_post()

        wizard = self.env['account.payment.register'].with_context(
            active_model='account.move', active_ids=(self.in_invoice_1 + in_invoice_cad_with_payment_term).ids
        ).create({'payment_date': '2016-01-01'})

        self.assertRecordValues(wizard, [{
            'amount': 1033.33,  # 1000 from in_invoice_1 + 1000 * 0.1 (payment_term) / 3 (rate of CAD) for second one
            'payment_difference': 0.0,
            'installments_mode': 'next',
            'installments_switch_amount': 1333.33,
            'currency_id': self.company.currency_id.id,  # Different currencies, so we get the company's one
            'communication': Like(f'GROUP/{self.current_year}/...'),
        }])

        wizard = self.env['account.payment.register'].with_context(
            active_model='account.move', active_ids=(self.in_invoice_1 + in_invoice_cad_with_payment_term).ids
        ).create({'payment_date': '2016-01-07'})

        # Some installments are overdue for the second bill, but not the first one, so it is in next
        self.assertRecordValues(wizard, [{
            'amount': 1133.33,  # 1000 from in_invoice_1 + 1000 * 0.4 (payment_term) / 3 (rate of CAD) for second one
            'payment_difference': 0.0,
            'installments_mode': 'next',
            'installments_switch_amount': 1333.33,
        }])

        wizard = self.env['account.payment.register'].with_context(
            active_model='account.move', active_ids=(in_invoice_cad_with_payment_term + in_invoice_cad_copy).ids
        ).create({'payment_date': '2016-01-07'})

        # Some installments are overdue for the second bill, but not the first one, so it is in next
        self.assertRecordValues(wizard, [{
            'amount': 800,  # both invoices have the payment term at 40%
            'payment_difference': 0.0,
            'installments_mode': 'overdue',
            'currency_id': self.other_currency_2.id,  # Same currency, so we can provide the right one
            'installments_switch_amount': 2000,
        }])

        wizard = self.env['account.payment.register'].with_context(
            active_model='account.move', active_ids=(self.in_invoice_epd_applied + in_invoice_cad_with_payment_term).ids
        ).create({'payment_date': '2016-01-01'})

        self.assertRecordValues(wizard, [{
            'amount': 57.83,  # 24.5 for in_invoice_epd_applied + 1000 * 0.1 (payment_term) / 3 (rate) for the second
            'payment_difference': 0.5,
            'installments_mode': 'next',
            'installments_switch_amount': 357.83,  # 24.5 for in_invoice_epd_applied + 1000 / 3 (rate) for the second
            'communication': Like(f'GROUP/{self.current_year}/...'),
        }])

        # Clicking on the button to full gets the amount from js, so we need to put it by hand here
        wizard.write({
            'installments_mode': 'full',
            'amount': 357.83,
        })

        self.assertRecordValues(wizard, [{
            'amount': 357.83,  # The switch amount computed above
            'payment_difference': 0.5,
            'installments_mode': 'full',
            'installments_switch_amount': 57.83,  # The previous 'next' amount
            'communication': Like(f'GROUP/{self.current_year}/...'),
        }])

    def test_payment_register_with_next_payment_date(self):
        invoice_2 = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'invoice_payment_term_id': self.term_0_5_10_days.id,
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [(0, 0, {'product_id': self.product_a.id, 'price_unit': 1000.0, 'tax_ids': []})],
        })
        wizard = self.env['account.payment.register'].with_context(
            active_domain=[['next_payment_date', '=', '2017-01-07']],  # To mimick next_payment date in the search
            active_model='account.move', active_ids=invoice_2.ids
        ).create({'payment_date': '2017-01-01'})

        # as we have next_payment_date in the search domain, we go in before_date and pay all installments before this
        # date (and not taken the payment_date into account there)
        self.assertRecordValues(wizard, [{
            'amount': 400,  # The switch amount computed above
            'installments_mode': 'before_date',
            'installments_switch_amount': 1000,  # The full amount
        }])

    def test_payment_with_branch(self):
        """
        Test register payment with branches when different receivable accounts are used in each branch with combinations of invoices and selected companies
        """
        def test_register_payment_flow(cases):
            for group_payment, case in product((False, True), cases):
                invoices, selected_companies, expected_companies, expected_pmnt_comp, should_raise = case.values()
                with self.subTest(invoices=invoices.mapped('name'), selected_companies=selected_companies.mapped('name')):
                    wizard = self.env['account.payment.register'].with_context(allowed_company_ids=selected_companies.ids, active_model='account.move', active_ids=invoices.ids).create({'group_payment': group_payment})
                    available_journals = self.get_wizard_available_journals(wizard)
                    self.assertEqual(available_journals.company_id, expected_companies)
                    if should_raise:
                        with self.assertRaisesRegex(UserError, 'got some company inconsistencies here:'):
                            wizard._create_payments()
                    else:
                        payments = wizard._create_payments()
                        self.assertEqual(payments.company_id, expected_pmnt_comp)
                        invoices.line_ids.filtered(lambda l: l.display_type == 'payment_term').remove_move_reconcile()

        # create a new branch and other company
        self._create_company(name='New Branch', parent_id=self.env.company.id)
        branches = self.env.company.child_ids
        self.user_branch.company_ids = branches
        company_2 = self._create_company(name='New Company')

        # PART 1: Basic cases
        # create invoices on branches
        branch_invoices = self.env['account.move']
        for branch in branches:
            self.env["account.journal"].create({
                'code': 'TEST',
                'company_id': branch.id,
                'name': f'{branch.name} journal',
                'type': 'bank',
            })
            branch_invoices |= self.init_invoice('out_invoice', products=self.product_a, company=branch)

        parent_invoice = self.init_invoice('out_invoice', products=self.product_a)
        other_company_invoice = self.init_invoice('out_invoice', products=self.product_a, company=company_2)
        (branch_invoices | parent_invoice | other_company_invoice).action_post()

        # test first branches invoices with branch user
        with self.with_user('user_branch'):
            with self.assertRaisesRegex(UserError, 'branches without access to parent company.'):
                self.env['account.payment.register'].with_context(allowed_company_ids=branches.ids, active_model='account.move', active_ids=branch_invoices.ids).create({})

        # test also with two differents companies
        with (self.assertRaisesRegex(UserError, 'for entries belonging to different companies.')):
            for group_payment in [False, True]:
                self.env['account.payment.register'].with_context(
                    allowed_company_ids=(self.env.company + company_2).ids,
                    active_model='account.move',
                    active_ids=(parent_invoice + other_company_invoice).ids
                ).create({'group_payment': group_payment})

        cases = [
            {
                'invoices': branch_invoices[0] + parent_invoice,
                'selected_companies': (self.branch + self.env.company),
                'expected_companies': self.env.company,
                'expected_pmnt_comp': self.env.company,
                'should_raise': False,
            },
            {
                'invoices': branch_invoices,
                'selected_companies': branches,
                'expected_companies': self.env.company,
                'expected_pmnt_comp': self.env.company,
                'should_raise': False,
            },
            {
                'invoices': branch_invoices + parent_invoice,
                'selected_companies': self.env.company._accessible_branches(),
                'expected_companies': self.env.company,
                'expected_pmnt_comp': self.env.company,
                'should_raise': False,
            },
            {
                'invoices': branch_invoices[0],
                'selected_companies': self.branch,
                'expected_companies': (self.env.company + self.branch),
                'expected_pmnt_comp': self.branch,
                'should_raise': False,
            },
            {
                'invoices': branch_invoices,
                'selected_companies': self.env.company._accessible_branches(),
                'expected_companies': self.env.company,
                'expected_pmnt_comp': self.env.company,
                'should_raise': False,
            },
        ]

        test_register_payment_flow(cases)

        # PART 2: Test the same cases with different receivable accounts for each branch
        # An error should be raised as the receivable account doesn't belong to the wizard's company, except for the case where we register payment only for one branch
        branch_invoices.button_draft()
        for branch in branches:
            receivable_account = self.company_data['default_account_receivable'].with_company(branch).copy({'company_ids': branch.ids})
            branch_invoice = branch_invoices.filtered(lambda inv: inv.company_id == branch)
            # To mock the situation where the partner has his own receivable account depending on the branch
            branch_invoice.line_ids.filtered(lambda l: l.display_type == 'payment_term').account_id = receivable_account
        branch_invoices.action_post()
        new_cases = [
            {
                'invoices': branch_invoices[0] + parent_invoice,
                'expected_pmnt_comp': False,
                'should_raise': True,
            },
            {
                'invoices': branch_invoices,
                'expected_pmnt_comp': False,
                'should_raise': True,
            },
            {
                'invoices': branch_invoices + parent_invoice,
                'expected_pmnt_comp': False,
                'should_raise': True,
            },
            {
                'invoices': branch_invoices[0],
                'expected_pmnt_comp': self.branch,
                'should_raise': False,
            },
            {
                'invoices': branch_invoices,
                'expected_pmnt_comp': False,
                'should_raise': True,
            },
        ]
        cases = [{**case, **new_case} for case, new_case in zip(cases, new_cases)]

        test_register_payment_flow(cases)

    def test_epd_and_cash_rounding(self):
        cash_rounding = self.env['account.cash.rounding'].create({
            'name': 'add_invoice_line',
            'rounding': 0.05,
            'strategy': 'add_invoice_line',
            'profit_account_id': self.company_data['default_account_revenue'].copy().id,
            'loss_account_id': self.company_data['default_account_expense'].copy().id,
            'rounding_method': 'UP',
        })
        payment_term = self.env.ref('account.account_payment_term_30days_early_discount')
        tax = self.env['account.tax'].create({
            'name': "21",
            'amount_type': 'percent',
            'amount': 21.0,
        })
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2024-01-01',
            'invoice_payment_term_id': payment_term.id,
            'invoice_cash_rounding_id': cash_rounding.id,
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 11,
                'tax_ids': [Command.set(tax.ids)],
            })]
        })
        invoice.action_post()

        self.assertRecordValues(invoice, [{'amount_total': 13.35}])

        self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({'payment_date': '2024-01-01'})\
            ._create_payments()
        self.assertRecordValues(invoice, [{'amount_residual': 0.0}])

    @users('user_branch')
    def test_branch_user_register_payment(self):
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'invoice_date': '2024-05-01',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'name': 'line',
                'price_unit': 1000,
                'quantity': 1,
            })]
        })
        bill.action_post()

        wizard = self.env['account.payment.register'].with_context(allowed_company_ids=self.env.company.ids, active_model='account.move', active_ids=bill.ids).create({
            'amount': bill.amount_total,
            'currency_id': bill.currency_id.id,
            'payment_method_line_id': self.inbound_payment_method_line.id,
        })
        self.env.company.parent_ids.invalidate_recordset()
        payment = wizard._create_payments()
        self.assertTrue(payment)
