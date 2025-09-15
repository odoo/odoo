# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, Command
from odoo.tests import Form, HttpCase, new_test_user
from odoo.tools.float_utils import float_round

from odoo.addons.product.tests.common import ProductCommon

import json
import base64
import logging
from contextlib import contextmanager
from functools import wraps
from lxml import etree
from unittest import SkipTest
from unittest.mock import patch

_logger = logging.getLogger(__name__)


class AccountTestInvoicingCommon(ProductCommon):
    # to override by the helper methods setup_country and setup_chart_template to adapt to a localization
    chart_template = False
    country_code = False

    @classmethod
    def safe_copy(cls, record):
        return record and record.copy()

    @staticmethod
    def setup_country(country_code):

        def _decorator(function):
            @wraps(function)
            def wrapper(self):
                self.country_code = country_code.upper()
                function(self)
            return wrapper

        return _decorator

    @staticmethod
    def setup_chart_template(chart_template):
        def _decorator(function):
            @wraps(function)
            def wrapper(self):
                self.chart_template = chart_template
                function(self)
            return wrapper

        return _decorator

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.maxDiff = None
        cls.company_data = cls.collect_company_accounting_data(cls.env.company)
        cls.tax_number = 0

        # ==== Taxes ====
        cls.tax_sale_a = cls.company_data['default_tax_sale']
        cls.tax_sale_b = cls.company_data['default_tax_sale'] and cls.company_data['default_tax_sale'].copy()
        cls.tax_purchase_a = cls.company_data['default_tax_purchase']
        cls.tax_purchase_b = cls.company_data['default_tax_purchase'] and cls.company_data['default_tax_purchase'].copy()
        cls.tax_armageddon = cls.setup_armageddon_tax('complex_tax', cls.company_data)

        # ==== Products ====
        cls.product_a = cls._create_product(
            name='product_a',
            lst_price=1000.0,
            standard_price=800.0
        )
        cls.product_b = cls._create_product(
            name='product_b',
            uom_id=cls.uom_dozen.id,
            uom_po_id=cls.uom_dozen.id,
            lst_price=200.0,
            standard_price=160.0,
            property_account_income_id=cls.copy_account(cls.company_data['default_account_revenue']).id,
            property_account_expense_id=cls.copy_account(cls.company_data['default_account_expense']).id,
            taxes_id=[Command.set((cls.tax_sale_a + cls.tax_sale_b).ids)],
            supplier_taxes_id=[Command.set((cls.tax_purchase_a + cls.tax_purchase_b).ids)],
        )

        # ==== Fiscal positions ====
        cls.fiscal_pos_a = cls.env['account.fiscal.position'].create({
            'name': 'fiscal_pos_a',
            'tax_ids': ([(0, None, {
                    'tax_src_id': cls.tax_sale_a.id,
                    'tax_dest_id': cls.tax_sale_b.id,
            })] if cls.tax_sale_b else []) + ([(0, None, {
                    'tax_src_id': cls.tax_purchase_a.id,
                    'tax_dest_id': cls.tax_purchase_b.id,
            })] if cls.tax_purchase_b else []),
            'account_ids': [
                (0, None, {
                    'account_src_id': cls.product_a.property_account_income_id.id,
                    'account_dest_id': cls.product_b.property_account_income_id.id,
                }),
                (0, None, {
                    'account_src_id': cls.product_a.property_account_expense_id.id,
                    'account_dest_id': cls.product_b.property_account_expense_id.id,
                }),
            ],
        })

        # ==== Payment terms ====
        cls.pay_terms_a = cls.env.ref('account.account_payment_term_immediate')
        cls.pay_terms_b = cls.env['account.payment.term'].create({
            'name': '30% Advance End of Following Month',
            'note': 'Payment terms: 30% Advance End of Following Month',
            'line_ids': [
                (0, 0, {
                    'value': 'percent',
                    'value_amount': 30.0,
                    'nb_days': 0,
                }),
                (0, 0, {
                    'value': 'percent',
                    'value_amount': 70.0,
                    'delay_type': 'days_after_end_of_next_month',
                    'nb_days': 0,
                }),
            ],
        })

        # ==== Partners ====
        cls.partner_a = cls.env['res.partner'].create({
            'name': 'partner_a',
            'invoice_sending_method': 'manual',
            'invoice_edi_format': False,
            'property_payment_term_id': cls.pay_terms_a.id,
            'property_supplier_payment_term_id': cls.pay_terms_a.id,
            'property_account_receivable_id': cls.company_data['default_account_receivable'].id,
            'property_account_payable_id': cls.company_data['default_account_payable'].id,
            'company_id': False,
        })
        cls.partner_b = cls.env['res.partner'].create({
            'name': 'partner_b',
            'invoice_sending_method': 'manual',
            'invoice_edi_format': False,
            'property_payment_term_id': cls.pay_terms_b.id,
            'property_supplier_payment_term_id': cls.pay_terms_b.id,
            'property_account_position_id': cls.fiscal_pos_a.id,
            'property_account_receivable_id': cls.company_data['default_account_receivable'].copy().id,
            'property_account_payable_id': cls.company_data['default_account_payable'].copy().id,
            'company_id': False,
        })

        # ==== Cash rounding ====
        cls.cash_rounding_a = cls.env['account.cash.rounding'].create({
            'name': 'add_invoice_line',
            'rounding': 0.05,
            'strategy': 'add_invoice_line',
            'profit_account_id': cls.company_data['default_account_revenue'].copy().id,
            'loss_account_id': cls.company_data['default_account_expense'].copy().id,
            'rounding_method': 'UP',
        })
        cls.cash_rounding_b = cls.env['account.cash.rounding'].create({
            'name': 'biggest_tax',
            'rounding': 0.05,
            'strategy': 'biggest_tax',
            'rounding_method': 'DOWN',
        })

        # ==== Payment methods ====
        bank_journal = cls.company_data['default_journal_bank']
        in_outstanding_account = cls.env['account.chart.template'].ref('account_journal_payment_debit_account_id')
        out_outstanding_account = cls.env['account.chart.template'].ref('account_journal_payment_credit_account_id')
        cls.inbound_payment_method_line = bank_journal.inbound_payment_method_line_ids[0]
        cls.inbound_payment_method_line.payment_account_id = in_outstanding_account
        cls.outbound_payment_method_line = bank_journal.outbound_payment_method_line_ids[0]
        cls.outbound_payment_method_line.payment_account_id = out_outstanding_account

        # user with restricted groups
        cls.simple_accountman = cls.env['res.users'].create({
            'name': 'simple accountman',
            'login': 'simple_accountman',
            'password': 'simple_accountman',
            'groups_id': [
                # the `account` specific groups from get_default_groups()
                Command.link(cls.env.ref('account.group_account_manager').id),
                Command.link(cls.env.ref('account.group_account_user').id),
            ],
        })

    @classmethod
    def change_company_country(cls, company, country):
        company.country_id = country
        company.account_fiscal_country_id = country
        for model in ('account.tax', 'account.tax.group'):
            cls.env.add_to_compute(
                cls.env[model]._fields['country_id'],
                cls.env[model].search([('company_id', '=', company.id)]),
            )

    @classmethod
    def setup_other_company(cls, **kwargs):
        # OVERRIDE
        company = cls._create_company(**{'name': 'company_2'} | kwargs)
        return cls.collect_company_accounting_data(company)

    @classmethod
    def setup_independent_company(cls, **kwargs):
        return cls._create_company(name='company_1_data', **kwargs)

    @classmethod
    def setup_independent_user(cls):
        return new_test_user(
            cls.env,
            name='Because I am accountman!',
            login='accountman',
            password='accountman',
            email='accountman@test.com',
            groups_id=cls.get_default_groups().ids,
            company_id=cls.env.company.id,
        )

    @classmethod
    def _create_company(cls, **create_values):
        if cls.country_code:
            country = cls.env['res.country'].search([('code', '=', cls.country_code.upper())])
            if not country:
                raise ValueError('Invalid country code')
            if 'country_id' not in create_values:
                create_values['country_id'] = country.id
            if 'currency_id' not in create_values:
                create_values['currency_id'] = country.currency_id.id
        company = super()._create_company(**create_values)
        cls._use_chart_template(company, cls.chart_template)
        # if the currency_id was defined explicitly (or via the country), it should override the one from the coa
        if create_values.get('currency_id'):
            company.currency_id = create_values['currency_id']
        return company

    @classmethod
    def _create_product(cls, **create_values):
        # OVERRIDE
        create_values.setdefault('property_account_income_id', cls.company_data['default_account_revenue'].id)
        create_values.setdefault('property_account_expense_id', cls.company_data['default_account_expense'].id)
        create_values.setdefault('taxes_id', [Command.set(cls.tax_sale_a.ids)])
        return super()._create_product(**create_values)

    @classmethod
    def get_default_groups(cls):
        groups = super().get_default_groups()
        return groups | cls.env.ref('account.group_account_manager') | cls.env.ref('account.group_account_user')

    @classmethod
    def setup_other_currency(cls, code, **kwargs):
        if 'rates' not in kwargs:
            return super().setup_other_currency(code, rates=[
                ('1900-01-01', 1.0),
                ('2016-01-01', 3.0),
                ('2017-01-01', 2.0),
            ], **kwargs)
        return super().setup_other_currency(code, **kwargs)

    @classmethod
    def _use_chart_template(cls, company, chart_template_ref=None):
        chart_template_ref = chart_template_ref or cls.env['account.chart.template']._guess_chart_template(company.country_id)
        template_vals = cls.env['account.chart.template']._get_chart_template_mapping()[chart_template_ref]
        template_module = cls.env['ir.module.module']._get(template_vals['module'])
        if template_module.state != 'installed':
            raise SkipTest(f"Module required for the test is not installed ({template_module.name})")

        # Install the chart template
        cls.env['account.chart.template'].try_loading(chart_template_ref, company=company, install_demo=False)
        if not company.account_fiscal_country_id:
            company.account_fiscal_country_id = cls.env.ref('base.us')

    @classmethod
    def collect_company_accounting_data(cls, company):
        # Need to have the right company when searching accounts with limit=1, since the ordering depends on the account code.
        AccountAccount = cls.env['account.account'].with_company(company)
        account_company_domain = cls.env['account.account']._check_company_domain(company)
        journal_company_domain = cls.env['account.journal']._check_company_domain(company)
        return {
            'company': company,
            'currency': company.currency_id,
            'default_account_revenue': AccountAccount.search([
                    *account_company_domain,
                    ('account_type', '=', 'income'),
                    ('id', '!=', company.account_journal_early_pay_discount_gain_account_id.id)
                ], limit=1),
            'default_account_expense': AccountAccount.search([
                    *account_company_domain,
                    ('account_type', '=', 'expense'),
                    ('id', '!=', company.account_journal_early_pay_discount_loss_account_id.id)
                ], limit=1),
            'default_account_receivable': cls.env['res.partner']._fields['property_account_receivable_id'].get_company_dependent_fallback(
                cls.env['res.partner'].with_company(company)
            ),
            'default_account_payable': AccountAccount.search([
                    *account_company_domain,
                    ('account_type', '=', 'liability_payable')
                ], limit=1),
            'default_tax_account_receivable': company.account_purchase_tax_id.tax_group_id.tax_receivable_account_id,
            'default_tax_account_payable': company.account_sale_tax_id.tax_group_id.tax_payable_account_id,
            'default_account_assets': AccountAccount.search([
                    *account_company_domain,
                    ('account_type', '=', 'asset_fixed')
                ], limit=1),
            'default_account_deferred_expense': AccountAccount.search([
                    *account_company_domain,
                    ('account_type', '=', 'asset_current')
                ], limit=1),
            'default_account_deferred_revenue': AccountAccount.search([
                    *account_company_domain,
                    ('account_type', '=', 'liability_current')
                ], limit=1),
            'default_account_tax_sale': company.account_sale_tax_id.mapped('invoice_repartition_line_ids.account_id'),
            'default_account_tax_purchase': company.account_purchase_tax_id.mapped('invoice_repartition_line_ids.account_id'),
            'default_journal_misc': cls.env['account.journal'].search([
                    *journal_company_domain,
                    ('type', '=', 'general')
                ], limit=1),
            'default_journal_sale': cls.env['account.journal'].search([
                    *journal_company_domain,
                    ('type', '=', 'sale')
                ], limit=1),
            'default_journal_purchase': cls.env['account.journal'].search([
                    *journal_company_domain,
                    ('type', '=', 'purchase')
                ], limit=1),
            'default_journal_bank': cls.env['account.journal'].search([
                    *journal_company_domain,
                    ('type', '=', 'bank')
                ], limit=1),
            'default_journal_cash': cls.env['account.journal'].search([
                    *journal_company_domain,
                    ('type', '=', 'cash')
                ], limit=1),
            'default_journal_credit': cls.env['account.journal'].create({
                'name': 'Credit Journal',
                'type': 'credit',
                'code': 'CCD1',
                'company_id': company.id,
            }),
            'default_tax_sale': company.account_sale_tax_id,
            'default_tax_purchase': company.account_purchase_tax_id,
        }

    @classmethod
    def copy_account(cls, account, default=None):
        suffix_nb = 1
        while True:
            new_code = '%s.%s' % (account.code, suffix_nb)
            if account.search_count([('code', '=', new_code)]):
                suffix_nb += 1
            else:
                return account.copy(default={'code': new_code, 'name': account.name, **(default or {})})

    def group_of_taxes(self, taxes, **kwargs):
        self.tax_number += 1
        return self.env['account.tax'].create({
            **kwargs,
            'name': f"group_({self.tax_number})",
            'amount_type': 'group',
            'children_tax_ids': [Command.set(taxes.ids)],
        })

    def percent_tax(self, amount, **kwargs):
        self.tax_number += 1
        return self.env['account.tax'].create({
            **kwargs,
            'name': f"percent_{amount}_({self.tax_number})",
            'amount_type': 'percent',
            'amount': amount,
        })

    def division_tax(self, amount, **kwargs):
        self.tax_number += 1
        return self.env['account.tax'].create({
            **kwargs,
            'name': f"division_{amount}_({self.tax_number})",
            'amount_type': 'division',
            'amount': amount,
        })

    def fixed_tax(self, amount, **kwargs):
        self.tax_number += 1
        return self.env['account.tax'].create({
            **kwargs,
            'name': f"fixed_{amount}_({self.tax_number})",
            'amount_type': 'fixed',
            'amount': amount,
        })

    def python_tax(self, formula, **kwargs):
        account_tax_python = self.env['ir.module.module']._get('account_tax_python')
        if account_tax_python.state != 'installed':
            raise SkipTest("Module 'account_tax_python' is not installed!")

        self.tax_number += 1
        return self.env['account.tax'].create({
            **kwargs,
            'name': f"code_({self.tax_number})",
            'amount_type': 'code',
            'amount': 0.0,
            'formula': formula,
        })

    @classmethod
    def setup_armageddon_tax(cls, tax_name, company_data, **kwargs):
        type_tax_use = kwargs.get('type_tax_use', 'sale')
        cash_basis_transition_account = company_data['default_account_tax_sale'] and company_data['default_account_tax_sale'].copy()
        return cls.env['account.tax'].create({
            'name': '%s (group)' % tax_name,
            'amount_type': 'group',
            'amount': 0.0,
            'country_id': company_data['company'].account_fiscal_country_id.id,
            'children_tax_ids': [
                (0, 0, {
                    'name': '%s (child 1)' % tax_name,
                    'amount_type': 'percent',
                    'amount': 20.0,
                    'type_tax_use': type_tax_use,
                    'country_id': company_data['company'].account_fiscal_country_id.id,
                    'price_include_override': 'tax_included',
                    'include_base_amount': True,
                    'tax_exigibility': 'on_invoice',
                    'invoice_repartition_line_ids': [
                        (0, 0, {
                            'repartition_type': 'base',
                        }),
                        (0, 0, {
                            'factor_percent': 40,
                            'repartition_type': 'tax',
                            'account_id': company_data['default_account_tax_sale'].id,
                        }),
                        (0, 0, {
                            'factor_percent': 60,
                            'repartition_type': 'tax',
                            # /!\ No account set.
                        }),
                    ],
                    'refund_repartition_line_ids': [
                        (0, 0, {
                            'repartition_type': 'base',
                        }),
                        (0, 0, {
                            'factor_percent': 40,
                            'repartition_type': 'tax',
                            'account_id': company_data['default_account_tax_sale'].id,
                        }),
                        (0, 0, {
                            'factor_percent': 60,
                            'repartition_type': 'tax',
                            # /!\ No account set.
                        }),
                    ],
                }),
                (0, 0, {
                    'name': '%s (child 2)' % tax_name,
                    'amount_type': 'percent',
                    'amount': 10.0,
                    'type_tax_use': type_tax_use,
                    'country_id': company_data['company'].account_fiscal_country_id.id,
                    'tax_exigibility': 'on_payment',
                    'cash_basis_transition_account_id': cash_basis_transition_account.id,
                    'invoice_repartition_line_ids': [
                        (0, 0, {
                            'repartition_type': 'base',
                        }),
                        (0, 0, {
                            'repartition_type': 'tax',
                            'account_id': company_data['default_account_tax_sale'].id,
                        }),
                    ],
                    'refund_repartition_line_ids': [
                        (0, 0, {
                            'repartition_type': 'base',
                        }),

                        (0, 0, {
                            'repartition_type': 'tax',
                            'account_id': company_data['default_account_tax_sale'].id,
                        }),
                    ],
                }),
            ],
            **kwargs,
        })

    @classmethod
    def init_invoice(cls, move_type, partner=None, invoice_date=None, post=False, products=None, amounts=None, taxes=None, company=False, currency=None, journal=None):
        products = [] if products is None else products
        amounts = [] if amounts is None else amounts
        move_form = Form(cls.env['account.move'] \
                    .with_company(company or cls.env.company) \
                    .with_context(default_move_type=move_type))
        move_form.invoice_date = invoice_date or fields.Date.from_string('2019-01-01')
        # According to the state or type of the invoice, the date field is sometimes visible or not
        # Besides, the date field can be put multiple times in the view
        # "invisible": "['|', ('state', '!=', 'draft'), ('auto_post', '!=', 'at_date')]"
        # "invisible": ['|', '|', ('state', '!=', 'draft'), ('auto_post', '=', 'no'), ('auto_post', '=', 'at_date')]
        # "invisible": "['&', ('move_type', 'in', ['out_invoice', 'out_refund', 'out_receipt']), ('quick_edit_mode', '=', False)]"
        # :TestAccountMoveOutInvoiceOnchanges, :TestAccountMoveOutRefundOnchanges, .test_00_debit_note_out_invoice, :TestAccountEdi
        if not move_form._get_modifier('date', 'invisible'):
            move_form.date = move_form.invoice_date
        move_form.partner_id = partner or cls.partner_a
        if journal:
            move_form.journal_id = journal
        if currency:
            move_form.currency_id = currency

        for product in (products or []):
            with move_form.invoice_line_ids.new() as line_form:
                line_form.product_id = product
                if taxes is not None:
                    line_form.tax_ids.clear()
                    for tax in taxes:
                        line_form.tax_ids.add(tax)

        for amount in (amounts or []):
            with move_form.invoice_line_ids.new() as line_form:
                line_form.name = "test line"
                line_form.price_unit = amount
                if taxes is not None:
                    line_form.tax_ids.clear()
                    for tax in taxes:
                        line_form.tax_ids.add(tax)

        rslt = move_form.save()

        if post:
            rslt.action_post()

        return rslt

    @classmethod
    def init_payment(cls, amount, post=False, date=None, partner=None, currency=None):
        payment = cls.env['account.payment'].create({
            'amount': abs(amount),
            'date': date or fields.Date.from_string('2019-01-01'),
            'payment_type': 'inbound' if amount >= 0 else 'outbound',
            'partner_type': 'customer' if amount >= 0 else 'supplier',
            'partner_id': (partner or cls.partner_a).id,
            'currency_id': (currency or cls.company_data['currency']).id,
        })
        if post:
            payment.action_post()
        return payment

    def create_line_for_reconciliation(self, balance, amount_currency, currency, move_date, account_1=None, partner=None):
        write_off_account_to_be_reconciled = account_1 if account_1 else self.receivable_account
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': move_date,
            'line_ids': [
                Command.create({
                    'debit': balance if balance > 0.0 else 0.0,
                    'credit': -balance if balance < 0.0 else 0.0,
                    'amount_currency': amount_currency,
                    'account_id': write_off_account_to_be_reconciled.id,
                    'currency_id': currency.id,
                    'partner_id': partner.id if partner else None,
                }),
                Command.create({
                    'debit': -balance if balance < 0.0 else 0.0,
                    'credit': balance if balance > 0.0 else 0.0,
                    'amount_currency': -amount_currency,
                    'account_id': self.company_data['default_account_revenue'].id,
                    'currency_id': currency.id,
                    'partner_id': partner.id if partner else None,
                }),
            ],
        })
        move.action_post()
        line = move.line_ids.filtered(lambda x: x.account_id == write_off_account_to_be_reconciled)

        self.assertRecordValues(line, [{
            'amount_residual': balance,
            'amount_residual_currency': amount_currency,
            'reconciled': False,
        }])

        return line

    def assertInvoiceValues(self, move, expected_lines_values, expected_move_values):
        def sort_lines(lines):
            return lines.sorted(lambda line: (line.sequence, not bool(line.tax_line_id), line.name or line.product_id.display_name or '', line.balance))
        self.assertRecordValues(sort_lines(move.line_ids.sorted()), expected_lines_values, field_names=expected_lines_values[0].keys())
        self.assertRecordValues(move, [expected_move_values], field_names=expected_move_values.keys())

    def assert_invoice_outstanding_to_reconcile_widget(self, invoice, expected_amounts):
        """ Check the outstanding widget before the reconciliation.
        :param invoice:             An invoice.
        :param expected_amounts:    A map <move_id> -> <amount>
        """
        invoice.invalidate_recordset(['invoice_outstanding_credits_debits_widget'])
        widget_vals = invoice.invoice_outstanding_credits_debits_widget

        if widget_vals:
            current_amounts = {vals['move_id']: vals['amount'] for vals in widget_vals['content']}
        else:
            current_amounts = {}
        self.assertDictEqual(current_amounts, expected_amounts)

    def assert_invoice_outstanding_reconciled_widget(self, invoice, expected_amounts):
        """ Check the outstanding widget after the reconciliation.
        :param invoice:             An invoice.
        :param expected_amounts:    A map <move_id> -> <amount>
        """
        invoice.invalidate_recordset(['invoice_payments_widget'])
        widget_vals = invoice.invoice_payments_widget

        if widget_vals:
            current_amounts = {vals['move_id']: vals['amount'] for vals in widget_vals['content']}
        else:
            current_amounts = {}
        self.assertDictEqual(current_amounts, expected_amounts)

    def _assert_tax_totals_summary(self, tax_totals, expected_results, soft_checking=False):
        """ Assert the tax totals.
        :param tax_totals:          The tax totals computed from _get_tax_totals_summary in account.tax.
        :param expected_results:    The expected values.
        :param soft_checking:       Limit the asserted values to the ones in 'expected_results' and don't go deeper inside the dictionary.
        """
        def fix_monetary_value(current_values, expected_values, monetary_fields):
            for key, current_value in current_values.items():
                if not isinstance(expected_values.get(key), float):
                    continue
                expected_value = expected_values[key]
                currency = monetary_fields.get(key)
                if current_value is not None and currency.is_zero(current_value - expected_value):
                    current_values[key] = expected_value

        currency = self.env['res.currency'].browse(tax_totals['currency_id'])
        company_currency = self.env['res.currency'].browse(tax_totals['company_currency_id'])
        multi_currency = tax_totals['currency_id'] != tax_totals['company_currency_id']
        excluded_fields = set() if multi_currency else {
            'tax_amount',
            'base_amount',
            'display_base_amount',
            'company_currency_id',
            'total_amount',
        }
        excluded_fields.add('display_in_company_currency')
        excluded_fields.add('group_name')
        excluded_fields.add('group_label')
        excluded_fields.add('involved_tax_ids')
        excluded_fields.add('company_currency_pd')
        excluded_fields.add('currency_pd')
        excluded_fields.add('has_tax_groups')
        monetary_fields = {
            'tax_amount_currency': currency,
            'tax_amount': company_currency,
            'base_amount_currency': currency,
            'base_amount': company_currency,
            'display_base_amount_currency': currency,
            'display_base_amount': company_currency,
            'total_amount_currency': currency,
            'total_amount': company_currency,
            'cash_rounding_base_amount_currency': currency,
            'cash_rounding_base_amount': company_currency,
        }

        current_values = {k: len(v) if k == 'subtotals' else v for k, v in tax_totals.items() if k not in excluded_fields}
        expected_values = {k: len(v) if k == 'subtotals' else v for k, v in expected_results.items()}
        if soft_checking:
            current_values = {k: v for k, v in current_values.items() if k in expected_values}

        fix_monetary_value(current_values, expected_values, monetary_fields)
        self.assertEqual(current_values, expected_values)
        if soft_checking:
            return

        for subtotal, expected_subtotal in zip(tax_totals['subtotals'], expected_results['subtotals']):
            current_values = {k: len(v) if k == 'tax_groups' else v for k, v in subtotal.items() if k not in excluded_fields}
            expected_values = {k: len(v) if k == 'tax_groups' else v for k, v in expected_subtotal.items()}
            fix_monetary_value(current_values, expected_values, monetary_fields)
            self.assertEqual(current_values, expected_values)
            for tax_group, expected_tax_group in zip(subtotal['tax_groups'], expected_subtotal['tax_groups']):
                current_tax_group = {k: v for k, v in tax_group.items() if k not in excluded_fields}
                fix_monetary_value(current_tax_group, expected_tax_group, monetary_fields)
                self.assertDictEqual(current_tax_group, expected_tax_group)

    ####################################################
    # Xml Comparison
    ####################################################

    def _turn_node_as_dict_hierarchy(self, node, path=''):
        ''' Turn the node as a python dictionary to be compared later with another one.
        :param node:    A node inside an xml tree.
        :param path:    The optional path of tags for recursive call.
        :return:        A python dictionary.
        '''
        tag_split = node.tag.split('}')
        tag_wo_ns = tag_split[-1]
        full_path = f'{path}/{tag_wo_ns}'
        return {
            'node': node,
            'tag': node.tag,
            'full_path': full_path,
            'namespace': None if len(tag_split) < 2 else tag_split[0],
            'text': (node.text or '').strip(),
            'attrib': dict(node.attrib.items()),
            'children': [
                self._turn_node_as_dict_hierarchy(child_node, path=full_path)
                for child_node in node.getchildren()
            ],
        }

    def assertXmlTreeEqual(self, xml_tree, expected_xml_tree):
        ''' Compare two lxml.etree.
        :param xml_tree:            The current tree.
        :param expected_xml_tree:   The expected tree.
        '''

        def assertNodeDictEqual(node_dict, expected_node_dict):
            ''' Compare nodes created by the `_turn_node_as_dict_hierarchy` method.
            :param node_dict:           The node to compare with.
            :param expected_node_dict:  The expected node.
            '''
            if expected_node_dict['text'] == '___ignore___':
                return
            # Check tag.
            self.assertEqual(node_dict['tag'], expected_node_dict['tag'])

            # Check attributes.
            for k, v in expected_node_dict['attrib'].items():
                if v == '___ignore___':
                    node_dict['attrib'][k] = '___ignore___'

            self.assertDictEqual(
                node_dict['attrib'],
                expected_node_dict['attrib'],
                f"Element attributes are different for node {node_dict['full_path']}",
            )

            # Check text.
            if expected_node_dict['text'] != '___ignore___':
                self.assertEqual(
                    node_dict['text'],
                    expected_node_dict['text'],
                    f"Element text are different for node {node_dict['full_path']}",
                )

            # Check children.
            children = [child['tag'] for child in node_dict['children']]
            expected_children = [child['tag'] for child in expected_node_dict['children']]
            if children != expected_children:
                for child in node_dict['children']:
                    if child['tag'] not in expected_children:
                        _logger.warning('Non-expected child: \n%s', etree.tostring(child['node']).decode())
                for child in expected_node_dict['children']:
                    if child['tag'] not in children:
                        _logger.warning('Missing child: \n%s', etree.tostring(child['node']).decode())

            self.assertEqual(
                children,
                expected_children,
                f"Number of children elements for node {node_dict['full_path']} is different.",
            )

            for child_node_dict, expected_child_node_dict in zip(node_dict['children'], expected_node_dict['children']):
                assertNodeDictEqual(child_node_dict, expected_child_node_dict)

        assertNodeDictEqual(
            self._turn_node_as_dict_hierarchy(xml_tree),
            self._turn_node_as_dict_hierarchy(expected_xml_tree),
        )

    def with_applied_xpath(self, xml_tree, xpath):
        ''' Applies the xpath to the xml_tree passed as parameter.
        :param xml_tree:    An instance of etree.
        :param xpath:       The xpath to apply as a string.
        :return:            The resulting etree after applying the xpaths.
        '''
        diff_xml_tree = etree.fromstring('<data>%s</data>' % xpath)
        return self.env['ir.ui.view'].apply_inheritance_specs(xml_tree, diff_xml_tree)

    def get_xml_tree_from_attachment(self, attachment):
        ''' Extract an instance of etree from an ir.attachment.
        :param attachment:  An ir.attachment.
        :return:            An instance of etree.
        '''
        return etree.fromstring(base64.b64decode(attachment.with_context(bin_size=False).datas))

    def get_xml_tree_from_string(self, xml_tree_str):
        ''' Convert the string passed as parameter to an instance of etree.
        :param xml_tree_str:    A string representing an xml.
        :return:                An instance of etree.
        '''
        return etree.fromstring(xml_tree_str)

    @contextmanager
    def enter_test_mode(self):
        """
        Make so that all new cursors opened on this database registry
        reuse the one currently used by the test.

        Useful for printing PDFs inside a TransactionCase test when
        using a HttpCase is not possible/desirable.
        """
        self.env.registry.enter_test_mode(self.env.cr)
        try:
            yield
        finally:
            self.env.registry.leave_test_mode()


class AccountTestMockOnlineSyncCommon(HttpCase):
    def start_tour(self, url_path, tour_name, step_delay=None, **kwargs):
        with self.mock_online_sync_favorite_institutions():
            super().start_tour(url_path, tour_name, step_delay, **kwargs)

    @classmethod
    @contextmanager
    def mock_online_sync_favorite_institutions(cls):
        def get_institutions(*args, **kwargs):
            return [
                {
                    'country': 'US',
                    'id': 3245,
                    'name': 'BMO Business Banking',
                    'picture': '/base/static/img/logo_white.png',
                },
                {
                    'country': 'US',
                    'id': 8192,
                    'name': 'Banc of California',
                    'picture': '/base/static/img/logo_white.png'
                },
            ]
        with patch.object(
             target=cls.registry['account.journal'],
             attribute='fetch_online_sync_favorite_institutions',
             new=get_institutions,
             create=True):
            yield


class AccountTestInvoicingHttpCommon(AccountTestInvoicingCommon, AccountTestMockOnlineSyncCommon):
    pass


class TestTaxCommon(AccountTestInvoicingHttpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.number = 0
        cls.maxDiff = None

    def setUp(self):
        super().setUp()
        self.js_tests = []

    def new_currency(self, rounding):
        self.number += 1
        return self.env.company.currency_id.copy({
            'name': f"{self.number}",
            'rounding': rounding,
        })

    @contextmanager
    def with_tax_calculation_rounding_method(self, rounding_method):
        self.env.company.tax_calculation_rounding_method = rounding_method
        yield

    def _create_assert_test(
        self,
        expected_values,
        py_function,
        js_function,
        assert_function,
        *args,
        extra_function=None,
    ):
        if py_function:
            py_results = py_function(*args)
            if extra_function:
                extra_function(py_results)
            assert_function(py_results, expected_values)
        if js_function:
            js_test = js_function(*args)
            if extra_function:
                extra_function(js_test)
            self.js_tests.append((js_test, expected_values, assert_function))

    def _jsonify_product(self, product, taxes):
        if not product:
            return {}
        return taxes._eval_taxes_computation_turn_to_product_values(product=product)

    def _jsonify_product_uom(self, uom):
        return {
            'id': uom.id,
            'name': uom.name,
        }

    def _jsonify_tax_group(self, tax_group):
        return {
            'id': tax_group.id,
            'name': tax_group.name,
            'preceding_subtotal': tax_group.preceding_subtotal,
            'pos_receipt_label': tax_group.pos_receipt_label,
        }

    def _jsonify_tax(self, tax):
        return {
            'id': tax.id,
            'name': tax.name,
            'amount_type': tax.amount_type,
            'sequence': tax.sequence,
            'amount': tax.amount,
            'price_include': tax.price_include,
            'include_base_amount': tax.include_base_amount,
            'is_base_affected': tax.is_base_affected,
            'has_negative_factor': tax.has_negative_factor,
            'children_tax_ids': [self._jsonify_tax(child) for child in tax.children_tax_ids],
            'tax_group_id': self._jsonify_tax_group(tax.tax_group_id),
        }

    def _jsonify_country(self, country):
        return {
            'id': country.id,
            'code': country.code,
        }

    def _jsonify_currency(self, currency):
        return {
            'id': currency.id,
            'rounding': currency.rounding,
            'decimal_places': currency.decimal_places,
        }

    def _jsonify_cash_rounding(self, cash_rounding):
        if not cash_rounding:
            return None

        return {
            'id': cash_rounding.id,
            'strategy': cash_rounding.strategy,
            'rounding': cash_rounding.rounding,
        }

    def _jsonify_document_line(self, document, index, line):
        return {
            'record': None,
            'id': index,
            'currency_id': self._jsonify_currency(line.get('currency_id') or document['currency']),
            'rate': line['rate'] if 'rate' in line else document['rate'],
            'product_id': self._jsonify_product(line['product_id'], line['tax_ids']),
            'product_uom_id': self._jsonify_product_uom(line['product_uom_id']),
            'tax_ids': [self._jsonify_tax(tax) for tax in line['tax_ids']],
            'price_unit': line['price_unit'],
            'quantity': line['quantity'],
            'discount': line['discount'],
            'sign': line['sign'],
            'special_mode': line['special_mode'],
            'special_type': line['special_type'],

            # Not implemented:
            'partner_id': None,
        }

    def _jsonify_document(self, document):
        return {
            **document,
            'company': self._jsonify_company(self.env.company),
            'currency': self._jsonify_currency(document['currency']),
            'cash_rounding': self._jsonify_cash_rounding(document['cash_rounding']),
            'lines': [self._jsonify_document_line(document, index, line) for index, line in enumerate(document['lines'])],
        }

    def _jsonify_company(self, company):
        return {
            'id': company.id,
            'tax_calculation_rounding_method': company.tax_calculation_rounding_method,
            'account_fiscal_country_id': self._jsonify_country(company.account_fiscal_country_id),
            'currency_id': self._jsonify_currency(company.currency_id),
        }

    def convert_base_line_to_invoice_line(self, document, base_line):
        values = {
            'price_unit': base_line['price_unit'],
            'discount': base_line['discount'],
            'quantity': base_line['quantity'],
        }
        if base_line['product_id']:
            values['product_id'] = base_line['product_id'].id
        if base_line['product_uom_id']:
            values['product_uom_id'] = base_line['product_uom_id'].id
        if base_line['tax_ids']:
            values['tax_ids'] = [Command.set(base_line['tax_ids'].ids)]
        return values

    def convert_document_to_invoice(self, document):
        invoice_date = '2020-01-01'
        currency = self.setup_other_currency(document['currency'].name.upper(), rates=[(invoice_date, document['rate'])])
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': invoice_date,
            'currency_id': currency.id,
            'invoice_cash_rounding_id': document['cash_rounding'] and document['cash_rounding'].id,
            'invoice_line_ids': [
                Command.create(self.convert_base_line_to_invoice_line(document, base_line))
                for base_line in document['lines']
            ],
        })
        return invoice

    def _run_js_tests(self):
        if not self.js_tests:
            return

        self.env['ir.config_parameter'].set_param(
            'account.tests_shared_js_python',
            json.dumps([test for test, _expected_values, _assert_function in self.js_tests]),
        )

        self.start_tour('/account/init_tests_shared_js_python', 'tests_shared_js_python', login=self.env.user.login)
        results = json.loads(self.env['ir.config_parameter'].get_param('account.tests_shared_js_python', '[]'))

        self.assertEqual(len(results), len(self.js_tests))
        index = 1
        for (js_test, expected_values, assert_function), results in zip(self.js_tests, results):
            js_test.update(results)
            with self.subTest(test=js_test['test'], index=index):
                assert_function(js_test, expected_values)
            index += 1

    # -------------------------------------------------------------------------
    # Multi-lines document creation
    # -------------------------------------------------------------------------

    def init_document(self, lines, currency=None, rate=None, cash_rounding=None):
        return {
            'currency': currency or self.env.company.currency_id,
            'rate': rate if rate is not None else 1.0,
            'lines': lines,
            'cash_rounding': cash_rounding,
        }

    def populate_document(self, document):
        AccountTax = self.env['account.tax']
        base_lines = [
            AccountTax._prepare_base_line_for_taxes_computation(
                None,
                id=i,
                rate=line['rate'] if 'rate' in line else document['rate'],
                **{
                    'currency_id': line.get('currency_id') or document['currency'],
                    'quantity': 1.0,
                    **line,
                },
            )
            for i, line in enumerate(document['lines'])
        ]
        AccountTax._add_tax_details_in_base_lines(base_lines, self.env.company)
        AccountTax._round_base_lines_tax_details(base_lines, self.env.company)
        return {
            **document,
            'lines': base_lines,
        }

    # -------------------------------------------------------------------------
    # taxes_computation
    # -------------------------------------------------------------------------

    def _assert_sub_test_taxes_computation(self, results, expected_values):

        def compare_taxes_computation_values(sub_results, rounding):
            self.assertEqual(
                float_round(sub_results['total_included'], precision_rounding=rounding),
                float_round(expected_values['total_included'], precision_rounding=rounding),
            )
            self.assertEqual(
                float_round(sub_results['total_excluded'], precision_rounding=rounding),
                float_round(expected_values['total_excluded'], precision_rounding=rounding),
            )
            self.assertEqual(len(sub_results['taxes_data']), len(expected_values['taxes_data']))
            for tax_data, (expected_base, expected_tax) in zip(sub_results['taxes_data'], expected_values['taxes_data']):
                self.assertEqual(
                    float_round(tax_data['base_amount'], precision_rounding=rounding),
                    float_round(expected_base, precision_rounding=rounding),
                )
                self.assertEqual(
                    float_round(tax_data['tax_amount'], precision_rounding=rounding),
                    float_round(expected_tax, precision_rounding=rounding),
                )

        is_round_globally = results['rounding_method'] == 'round_globally'
        excluded_special_modes = results['excluded_special_modes'] or []
        rounding = 0.000001 if is_round_globally else 0.01
        compare_taxes_computation_values(results['results'], rounding)

        # Check the special modes in case of round_globally.
        if is_round_globally:
            # special_mode == 'total_excluded'.
            if 'total_excluded' not in excluded_special_modes:
                compare_taxes_computation_values(results['total_excluded_results'], rounding)
                delta = sum(
                    x['tax_amount']
                    for x in results['total_excluded_results']['taxes_data']
                    if x['tax']['price_include']
                )

                self.assertEqual(
                    float_round(
                        (results['total_excluded_results']['total_excluded'] + delta) / results['quantity'],
                        precision_rounding=rounding,
                    ),
                    float_round(results['price_unit'], precision_rounding=rounding),
                )

            # special_mode == 'total_included'.
            if 'total_included' not in excluded_special_modes:
                compare_taxes_computation_values(results['total_included_results'], rounding)
                delta = sum(
                    x['tax_amount']
                    for x in results['total_included_results']['taxes_data']
                    if not x['tax']['price_include']
                )

                self.assertEqual(
                    float_round(
                        (results['total_included_results']['total_included'] - delta) / results['quantity'],
                        precision_rounding=rounding,
                    ),
                    float_round(results['price_unit'], precision_rounding=rounding),
                )

    def _create_py_sub_test_taxes_computation(self, taxes, price_unit, quantity, product, precision_rounding, rounding_method, excluded_tax_ids):
        kwargs = {
            'product': product,
            'precision_rounding': precision_rounding,
            'rounding_method': rounding_method,
            'filter_tax_function': (lambda tax: tax.id not in excluded_tax_ids) if excluded_tax_ids else None,
        }
        results = {'results': taxes._get_tax_details(price_unit, quantity, **kwargs)}
        if rounding_method == 'round_globally':
            results['total_excluded_results'] = taxes._get_tax_details(
                price_unit=results['results']['total_excluded'] / quantity,
                quantity=quantity,
                special_mode='total_excluded',
                **kwargs,
            )
            results['total_included_results'] = taxes._get_tax_details(
                price_unit=results['results']['total_included'] / quantity,
                quantity=quantity,
                special_mode='total_included',
                **kwargs,
            )
        return results

    def _create_js_sub_test_taxes_computation(self, taxes, price_unit, quantity, product, precision_rounding, rounding_method, excluded_tax_ids):
        return {
            'test': 'taxes_computation',
            'taxes': [self._jsonify_tax(tax) for tax in taxes],
            'price_unit': price_unit,
            'quantity': quantity,
            'product': self._jsonify_product(product, taxes),
            'precision_rounding': precision_rounding,
            'rounding_method': rounding_method,
            'excluded_tax_ids': excluded_tax_ids,
        }

    def assert_taxes_computation(
        self,
        taxes,
        price_unit,
        expected_values,
        quantity=1,
        product=None,
        precision_rounding=0.01,
        rounding_method='round_per_line',
        excluded_special_modes=None,
        excluded_tax_ids=None,
    ):
        def extra_function(results):
            results['excluded_special_modes'] = excluded_special_modes
            results['rounding_method'] = rounding_method
            results['price_unit'] = price_unit
            results['quantity'] = quantity

        self._create_assert_test(
            expected_values,
            self._create_py_sub_test_taxes_computation,
            self._create_js_sub_test_taxes_computation,
            self._assert_sub_test_taxes_computation,
            taxes,
            price_unit,
            quantity,
            product,
            precision_rounding,
            rounding_method,
            excluded_tax_ids,
            extra_function=extra_function,
        )

    # -------------------------------------------------------------------------
    # adapt_price_unit_to_another_taxes
    # -------------------------------------------------------------------------

    def _assert_sub_test_adapt_price_unit_to_another_taxes(self, results, expected_price_unit):
        self.assertEqual(results['price_unit'], expected_price_unit)

    def _create_py_sub_test_adapt_price_unit_to_another_taxes(self, price_unit, original_taxes, new_taxes, product):
        return {'price_unit': self.env['account.tax']._adapt_price_unit_to_another_taxes(price_unit, product, original_taxes, new_taxes)}

    def _create_js_sub_test_adapt_price_unit_to_another_taxes(self, price_unit, original_taxes, new_taxes, product):
        return {
            'test': 'adapt_price_unit_to_another_taxes',
            'price_unit': price_unit,
            'product': self._jsonify_product(product, original_taxes + new_taxes),
            'original_taxes': [self._jsonify_tax(tax) for tax in original_taxes],
            'new_taxes': [self._jsonify_tax(tax) for tax in new_taxes],
        }

    def assert_adapt_price_unit_to_another_taxes(self, price_unit, original_taxes, new_taxes, expected_price_unit, product=None):
        self._create_assert_test(
            expected_price_unit,
            self._create_py_sub_test_adapt_price_unit_to_another_taxes,
            self._create_js_sub_test_adapt_price_unit_to_another_taxes,
            self._assert_sub_test_adapt_price_unit_to_another_taxes,
            price_unit,
            original_taxes,
            new_taxes,
            product,
        )

    # -------------------------------------------------------------------------
    # base_lines_tax_details
    # -------------------------------------------------------------------------

    def _assert_sub_test_base_lines_tax_details(self, results, expected_values):
        self.assertEqual(len(results['base_lines_tax_details']), len(expected_values['base_lines_tax_details']))
        for result, expected in zip(results['base_lines_tax_details'], expected_values['base_lines_tax_details']):
            self.assertDictEqual(result, expected)

    def _create_py_sub_test_base_lines_tax_details(self, document):
        base_lines = document['lines']
        return {
            'base_lines_tax_details': [
                {
                    'total_excluded_currency': base_line['tax_details']['total_excluded_currency'],
                    'total_excluded': base_line['tax_details']['total_excluded'],
                    'total_included_currency': base_line['tax_details']['total_included_currency'],
                    'total_included': base_line['tax_details']['total_included'],
                    'delta_total_excluded_currency': base_line['tax_details']['delta_total_excluded_currency'],
                    'delta_total_excluded': base_line['tax_details']['delta_total_excluded'],
                    'taxes_data': [
                        {
                            'tax_id': tax_data['tax'].id,
                            'tax_amount_currency': tax_data['tax_amount_currency'],
                            'tax_amount': tax_data['tax_amount'],
                            'base_amount_currency': tax_data['base_amount_currency'],
                            'base_amount': tax_data['base_amount'],
                        }
                        for tax_data in base_line['tax_details']['taxes_data']
                    ],
                }
                for base_line in base_lines
            ]
        }

    def _create_js_sub_test_base_lines_tax_details(self, document):
        return {
            'test': 'base_lines_tax_details',
            'document': self._jsonify_document(document),
        }

    def assert_base_lines_tax_details(self, document, expected_values):
        self._create_assert_test(
            expected_values,
            self._create_py_sub_test_base_lines_tax_details,
            self._create_js_sub_test_base_lines_tax_details,
            self._assert_sub_test_base_lines_tax_details,
            document,
        )

    # -------------------------------------------------------------------------
    # tax_totals_summary
    # -------------------------------------------------------------------------

    def _assert_sub_test_tax_totals_summary(self, results, expected_results):
        self._assert_tax_totals_summary(results['tax_totals'], expected_results, soft_checking=results['soft_checking'])

    def _create_py_sub_test_tax_totals_summary(self, document, excluded_tax_group_ids, soft_checking):
        AccountTax = self.env['account.tax']
        tax_totals = AccountTax._get_tax_totals_summary(
            base_lines=document['lines'],
            currency=document['currency'],
            company=self.env.company,
            cash_rounding=document['cash_rounding'],
        )
        if excluded_tax_group_ids:
            tax_totals = AccountTax._exclude_tax_groups_from_tax_totals_summary(tax_totals, excluded_tax_group_ids)
        return {'tax_totals': tax_totals, 'soft_checking': soft_checking}

    def _create_js_sub_test_tax_totals_summary(self, document, excluded_tax_group_ids, soft_checking):
        return {
            'test': 'tax_totals_summary',
            'document': self._jsonify_document(document),
            'soft_checking': soft_checking,
        }

    def assert_tax_totals_summary(self, document, expected_values, excluded_tax_group_ids=None, soft_checking=False):
        self._create_assert_test(
            expected_values,
            self._create_py_sub_test_tax_totals_summary,
            self._create_js_sub_test_tax_totals_summary,
            self._assert_sub_test_tax_totals_summary,
            document,
            excluded_tax_group_ids or set(),
            soft_checking,
        )

    # -------------------------------------------------------------------------
    # invoice tax_totals_summary
    # -------------------------------------------------------------------------

    def assert_invoice_tax_totals_summary(self, invoice, expected_values, soft_checking=False):
        self._assert_tax_totals_summary(invoice.tax_totals, expected_values, soft_checking=soft_checking)
        cash_rounding_base_amount_currency = invoice.tax_totals.get('cash_rounding_base_amount_currency', 0.0)
        self.assertRecordValues(invoice, [{
            'amount_untaxed': expected_values['base_amount_currency'] + cash_rounding_base_amount_currency,
            'amount_tax': expected_values['tax_amount_currency'],
            'amount_total': expected_values['total_amount_currency'],
        }])


class TestAccountMergeCommon(AccountTestInvoicingCommon):
    def _create_account_merge_wizard(self, accounts):
        """ Open an account.merge.wizard with the given accounts. """
        return self.env['account.merge.wizard'].with_context({
            'allowed_company_ids': accounts.company_ids.ids,
            'active_model': 'account.account',
            'active_ids': accounts.ids
        }).create({'is_group_by_name': False})

    def _create_references_to_account(self, account):
        """ Create records that reference the given account using different types
        of reference fields: Many2one, Many2many, company-dependent Many2one,
        and Many2oneReference.

        The Many2one, Many2many and Many2oneReference records are created with a
        `company_id` set to `account.company_ids`.

        The company-dependent Many2one record is created with the context company
        set to `account.company_ids`.

        This allows correct testing of merging and de-merging accounts.

        :return: a dict {record: account_field} of all created records and the
                 field names on the records that reference the account.
        """
        # Many2one
        move = self.env['account.move'].create({
            'journal_id': self.env['account.journal'].search([('company_id', '=', account.company_ids.id)], limit=1).id,
            'date': '2024-07-20',
            'line_ids': [
                Command.create({
                    'account_id': account.id,
                    'balance': 10.0,
                }),
                Command.create({
                    'account_id': self.env['account.account'].search([('company_ids', '=', account.company_ids.id)], limit=1).id,
                    'balance': -10.0,
                })
            ]
        })

        # Many2many (note that merging the accounts will technically
        # break the check_company constraint on journal.account_control_ids,
        # but we still test this as this is the easiest way to test that
        # M2M fields are merged correctly.)
        journal = self.env['account.journal'].create({
            'name': f'For account {account.id}',
            'code': f'T{account.id}',
            'type': 'general',
            'company_id': account.company_ids.id,
            'account_control_ids': [Command.set(account.ids)],
        })

        # Company-dependent Many2one.
        # We must set (and check) the 'property_account_receivable_id' on the right company.
        partner = self.env['res.partner'].with_company(account.company_ids).create({
            'name': 'Some Partner name',
            'property_account_receivable_id': account.id,
        })

        # Many2oneReference
        attachment = self.env['ir.attachment'].create({
            'res_model': 'account.account',
            'res_id': account.id,
            'name': 'attachment',
            'company_id': account.company_ids.id,
        })

        return {
            move.line_ids[0]: 'account_id',
            journal: 'account_control_ids',
            partner: 'property_account_receivable_id',
            attachment: 'res_id',
        }
