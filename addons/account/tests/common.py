# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, Command
from odoo.models import BaseModel
from odoo.tests import Form, HttpCase, new_test_user, tagged, save_test_file
from odoo.tools import config, file_path, file_open
from odoo.tools.float_utils import float_round

from odoo.addons.product.tests.common import ProductCommon

import json
import base64
import copy
import logging
import re

import difflib
import pprint
import requests
from contextlib import contextmanager
from functools import wraps
from itertools import count
from lxml import etree
from unittest import SkipTest, TestCase
from unittest.mock import patch, ANY

_logger = logging.getLogger(__name__)


def skip_unless_external(func):
    """
    Skip a test unless the test is run in external mode.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'EXTERNAL_MODE' in (config['test_tags'] or {}):
            return func(*args, **kwargs)
        else:
            raise SkipTest("Skipping this test as it is meant to run in external mode")

    return wrapper


class AccountTestInvoicingCommon(ProductCommon):
    # to override by the helper methods setup_country and setup_chart_template to adapt to a localization
    chart_template = False
    country_code = False
    extra_tags = ('-standard', 'external') if 'EXTERNAL_MODE' in (config['test_tags'] or {}) else ()

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
        cls.product_category.with_company(cls.env.company).write({
            'property_account_income_categ_id': cls.company_data['default_account_revenue'].id,
            'property_account_expense_categ_id': cls.company_data['default_account_expense'].id,
        })
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
            standard_price=800.0,
            uom_id=cls.uom_unit.id,
        )
        cls.product_b = cls._create_product(
            name='product_b',
            uom_id=cls.uom_dozen.id,
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
            'account_ids': [
                (0, None, {
                    'account_src_id': cls.product_a.property_account_income_id.id,
                    'account_dest_id': cls.product_b.property_account_income_id.id,
                }),
                (0, None, {
                    'account_src_id': cls.product_a.property_account_expense_id.id,
                    'account_dest_id': cls.product_b.property_account_expense_id.id,
                }),
            ] if cls.env.registry.loaded else [],
        })
        if cls.tax_sale_b:
            cls.tax_sale_b.fiscal_position_ids = cls.fiscal_pos_a.ids
            cls.tax_sale_b.original_tax_ids = cls.tax_sale_a
        if cls.tax_purchase_b:
            cls.tax_purchase_b.fiscal_position_ids = cls.fiscal_pos_a.ids
            cls.tax_purchase_b.original_tax_ids = cls.tax_purchase_a

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
        in_outstanding_account = cls.env['account.chart.template'].ref('account_journal_payment_debit_account_id', raise_if_not_found=False)
        out_outstanding_account = cls.env['account.chart.template'].ref('account_journal_payment_credit_account_id', raise_if_not_found=False)
        if bank_journal:
            cls.inbound_payment_method_line = bank_journal.inbound_payment_method_line_ids[0]
            cls.inbound_payment_method_line.payment_account_id = in_outstanding_account
            cls.outbound_payment_method_line = bank_journal.outbound_payment_method_line_ids[0]
            cls.outbound_payment_method_line.payment_account_id = out_outstanding_account

        # user with restricted groups
        cls.simple_accountman = cls.env['res.users'].create({
            'name': 'simple accountman',
            'login': 'simple_accountman',
            'password': 'simple_accountman',
            'group_ids': [
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
        data = cls.collect_company_accounting_data(company)
        cls.product_category.with_company(company).write({
            'property_account_income_categ_id': data['default_account_revenue'].id,
            'property_account_expense_categ_id': data['default_account_expense'].id,
        })
        return data

    @classmethod
    def setup_independent_company(cls, **kwargs):
        if cls.env.registry.loaded:
            # Only create a new company for post-install tests
            return cls._create_company(name='company_1_data', **kwargs)
        else:
            cls.env['account.tax.group'].create({
                'name': 'Test tax group',
                'company_id': cls.env.company.id,
            })
            cls.env.company.country_id = cls.quick_ref('base.be')
        return super().setup_independent_company(**kwargs)

    @classmethod
    def setup_independent_user(cls):
        return new_test_user(
            cls.env,
            name='Because I am accountman!',
            login='accountman',
            password='accountman',
            email='accountman@test.com',
            group_ids=cls.get_default_groups().ids,
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
        create_values.setdefault('property_account_income_id', cls.company_data['default_account_revenue'])
        create_values.setdefault('property_account_expense_id', cls.company_data['default_account_expense'])
        create_values.setdefault('taxes_id', cls.tax_sale_a)

        # QoL: allow passing record immediately instead of getting the id / creating [Command.set(...)] everytime
        # QoL: delete all keys with None value from create_values
        cls._prepare_record_kwargs('product.product', create_values)
        return super()._create_product(**create_values)

    @classmethod
    def get_default_groups(cls):
        no_group = cls.env['res.groups'].browse()
        return (
            super().get_default_groups()
            | (cls.env.ref('mrp.group_mrp_manager', False) or no_group)
            | (cls.env.ref('purchase.group_purchase_manager', False) or no_group)
            | (cls.env.ref('stock.group_stock_manager', False) or no_group)
            | cls.quick_ref('account.group_account_manager')
            | cls.quick_ref('account.group_account_user')
            | cls.quick_ref('account.group_validate_bank_account')
            | cls.quick_ref('base.group_system')  # company creation during setups
        )

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
        cls.ensure_installed(template_vals['module'])

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
            'default_journal_cash': cls.env['account.journal'].create({
                'type': 'cash',
                'name': 'Cash',
                'company_id': company.id,
            }),
            'default_journal_credit': cls.env['account.journal'].create({
                'name': 'Credit Journal',
                'type': 'credit',
                'code': 'CCD1',
                'company_id': company.id,
            }),
            'default_tax_sale': company.account_sale_tax_id,
            'default_tax_purchase': company.account_purchase_tax_id,
            'default_tax_return_journal': cls.env['account.journal'].create({
                'name': 'Tax Return Journal',
                'type': 'general',
                'code': 'TXRET',
                'company_id': company.id,
            }),
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

    @classmethod
    def ensure_installed(cls, module_name: str):
        if cls.env['ir.module.module']._get(module_name).state != 'installed':
            raise SkipTest(f"Module required for the test is not installed ({module_name})")

    # -------------------------------------------------------------------------
    # Helper: Generation of Tax / Invoice / Sale Order / etc.
    # -------------------------------------------------------------------------

    def group_of_taxes(self, taxes, **kwargs):
        self.tax_number += 1
        return self.env['account.tax'].create({
            'name': f"group_({self.tax_number})",
            **kwargs,
            'amount_type': 'group',
            'children_tax_ids': [Command.set(taxes.ids)],
        })

    def percent_tax(self, amount, **kwargs):
        self.tax_number += 1
        return self.env['account.tax'].create({
            'name': f"percent_{amount}_({self.tax_number})",
            **kwargs,
            'amount_type': 'percent',
            'amount': amount,
        })

    def division_tax(self, amount, **kwargs):
        self.tax_number += 1
        return self.env['account.tax'].create({
            'name': f"division_{amount}_({self.tax_number})",
            **kwargs,
            'amount_type': 'division',
            'amount': amount,
        })

    def fixed_tax(self, amount, **kwargs):
        self.tax_number += 1
        return self.env['account.tax'].create({
            'name': f"fixed_{amount}_({self.tax_number})",
            **kwargs,
            'amount_type': 'fixed',
            'amount': amount,
        })

    def python_tax(self, formula, **kwargs):
        self.ensure_installed('account_tax_python')
        self.tax_number += 1
        return self.env['account.tax'].create({
            'name': f"code_({self.tax_number})",
            **kwargs,
            'amount_type': 'code',
            'amount': 0.0,
            'formula': formula,
        })

    @classmethod
    def setup_armageddon_tax(cls, tax_name, company_data, **kwargs):
        type_tax_use = kwargs.get('type_tax_use', 'sale')
        cash_basis_transition_account = company_data['default_account_tax_sale'] and company_data['default_account_tax_sale'].copy()
        cash_basis_transition_account.reconcile = True
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
                    'tax_exigibility': 'on_payment' if cash_basis_transition_account else 'on_invoice',
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
        """ This method is deprecated. Please call ``_create_invoice`` instead. """
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
        # The journal_id field is invisible when there is only one available journal for the move type.
        if journal and not move_form._get_modifier('journal_id', 'invisible'):
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

    @classmethod
    def pay_with_statement_line(cls, move, bank_journal_id, payment_date, amount):
        statement_line = cls.env['account.bank.statement.line'].create({
            'payment_ref': 'ref',
            'journal_id': bank_journal_id,
            'amount': amount,
            'date': payment_date,
        })
        _st_liquidity_lines, st_suspense_lines, _st_other_lines = statement_line\
            .with_context(skip_account_move_synchronization=True)\
            ._seek_for_lines()
        line = move.line_ids.filtered(lambda line: line.account_type in ('asset_receivable', 'liability_payable'))

        st_suspense_lines.account_id = line.account_id
        (st_suspense_lines + line).reconcile()

        return {'move_reconciled': line, 'statement_line_reconciled': st_suspense_lines}

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

    @classmethod
    def _prepare_record_kwargs(cls, model_name: str, kwargs: dict):
        for key, value in kwargs.items():
            if isinstance(value, BaseModel):
                if cls.env[model_name]._fields[key].type in ('one2many', 'many2many'):
                    kwargs[key] = [Command.set(value.ids)]
                else:
                    kwargs[key] = value.id

        none_keys = [key for key, val in kwargs.items() if val is None]
        for key in none_keys:
            del kwargs[key]

    @classmethod
    def _prepare_invoice_line(cls, price_unit=None, product_id=None, quantity=1.0, tax_ids=None, **line_args):
        assert price_unit is not None or product_id is not None, "Either `price_unit` or `product_id` must be filled!"
        invoice_line_args = {
            'price_unit': price_unit,
            'product_id': product_id,
            'tax_ids': tax_ids,
            'quantity': quantity,
            **line_args,
        }
        cls._prepare_record_kwargs('account.move.line', invoice_line_args)
        return Command.create(invoice_line_args)

    @classmethod
    def _prepare_order_line(cls, price_unit=None, product_id=None, product_uom_qty=1.0, tax_ids=None, **line_args):
        assert price_unit is not None or product_id is not None, "Either `price_unit` or `product_id` must be filled!"
        cls.ensure_installed('sale')
        order_line_args = {
            'price_unit': price_unit,
            'product_id': product_id,
            'tax_ids': tax_ids,
            'product_uom_qty': product_uom_qty,
            **line_args,
        }
        cls._prepare_record_kwargs('sale.order.line', order_line_args)
        return Command.create(order_line_args)

    @classmethod
    def _create_invoice(cls, move_type='out_invoice', invoice_date=None, date=None, post=False, **invoice_args):
        """
        This method quickly generates an ``account.move`` record with some quality of life helpers.
        These quality of life helpers are:

        - if `invoice_date`/`date` is filled but not the other, autofill the other date fields
        - if no `date` or `invoice_date` is passed, set the `invoice_date` to today by default
        - allow passing record immediately instead of getting the id / creating [Command.set(...)] everytime for one2many/many2many fields
        - allow passing None value in `invoice_args`, they will be filtered out before calling the move `create` method

        :param post: if True, the invoice will be posted
        :param invoice_args: additional overrides on the `account.move` `create` call
        :return: the created ``account.move`` record
        """
        # QoL: if `invoice_date`/`date` is filled but not the other, autofill the other date fields
        if move_type in cls.env['account.move'].get_invoice_types():
            if invoice_date and not date:
                date = invoice_date
            elif date and not invoice_date:
                invoice_date = date
            elif not date and not invoice_date:
                invoice_date = fields.Date.today()

        invoice_args |= {'date': date, 'invoice_date': invoice_date}

        # QoL: allow passing record immediately instead of getting the id / creating [Command.set(...)] everytime
        # QoL: delete all keys with None value from invoice_args
        cls._prepare_record_kwargs('account.move', invoice_args)

        invoice = cls.env['account.move'].create([{
            'move_type': move_type,
            'partner_id': cls.partner_a.id,
            'invoice_line_ids': [  # default invoice_line_ids
                cls._prepare_invoice_line(product_id=cls.product_a),
                cls._prepare_invoice_line(product_id=cls.product_b),
            ],
            **invoice_args,
        }])

        if post:
            invoice.action_post()

        cls.env.flush_all()
        return invoice

    @classmethod
    def _create_invoice_one_line(cls, price_unit=None, product_id=None, name=None, quantity=1.0, tax_ids=None, discount=None, account_id=None, move_name=None, **invoice_args):
        return cls._create_invoice(
            invoice_line_ids=[
                cls._prepare_invoice_line(
                    price_unit=price_unit,
                    product_id=product_id,
                    name=name,
                    quantity=quantity,
                    tax_ids=tax_ids,
                    discount=discount,
                    account_id=account_id,
                )
            ],
            name=move_name,
            **invoice_args,
        )

    @classmethod
    def _create_account_move_send_wizard_single(cls, move, **kwargs):
        return cls.env['account.move.send.wizard']\
            .with_context(active_model='account.move', active_ids=move.ids)\
            .create(kwargs)

    @classmethod
    def _create_account_move_send_wizard_multi(cls, moves, **kwargs):
        return cls.env['account.move.send.batch.wizard']\
            .with_context(active_model='account.move', active_ids=moves.ids)\
            .create(kwargs)

    @classmethod
    def _reverse_invoice(cls, invoice, is_modify=False, post=False, **reversal_args):
        reverse_action_values = (
            cls.env['account.move.reversal']
            .with_context(active_model='account.move', active_ids=invoice.ids)
            .create({
                'journal_id': invoice.journal_id.id,
                **reversal_args,
            })
            .reverse_moves(is_modify=is_modify)
        )
        credit_note = cls.env['account.move'].browse(reverse_action_values['res_id'])

        if post:
            credit_note.action_post()

        return credit_note

    @classmethod
    def _create_debit_note(cls, invoice, post=False, **debit_note_args):
        cls.ensure_installed('account_debit_note')
        debit_note_values = (
            cls.env['account.debit.note']
            .with_context(
                active_model='account.move',
                active_ids=invoice.ids,
                default_copy_lines=True,
            )
            .create(debit_note_args)
            .create_debit()
        )
        debit_note = cls.env['account.move'].browse(debit_note_values['res_id'])

        if post:
            debit_note.action_post()

        return debit_note

    @classmethod
    def _register_payment(cls, record, **kwargs):
        return (
            cls.env['account.payment.register']
            .with_context(
                active_model='account.move',
                active_ids=record.ids,
            )
            .create({
                'group_payment': True,
                **kwargs,
            })
            ._create_payments()
        )

    @contextmanager
    def mocked_get_payment_method_information(self, code='none'):
        self.ensure_installed('account_payment')

        Method_get_payment_method_information = self.env['account.payment.method']._get_payment_method_information

        def _get_payment_method_information(*args, **kwargs):
            res = Method_get_payment_method_information()
            res[code] = {'mode': 'electronic', 'type': ('bank',)}
            return res

        with patch.object(self.env.registry['account.payment.method'], '_get_payment_method_information', _get_payment_method_information):
            yield

    @classmethod
    def _create_dummy_payment_method_for_provider(cls, provider, journal, **kwargs):
        cls.ensure_installed('account_payment')

        code = kwargs.get('code', 'none')

        with cls.mocked_get_payment_method_information(cls, code):
            payment_method = cls.env['account.payment.method'].sudo().create({
                'name': 'Dummy method',
                'code': code,
                'payment_type': 'inbound',
                **kwargs,
            })
            provider.journal_id = journal
            return payment_method

    @classmethod
    def _create_sale_order(cls, confirm=True, **values):
        cls.ensure_installed('sale')

        cls._prepare_record_kwargs('sale.order', values)

        sale_order = cls.env['sale.order'].create([{
            'partner_id': cls.partner_a.id,
            'order_line': [
                Command.create({'product_id': cls.product_a.id}),
                Command.create({'product_id': cls.product_b.id}),
            ],
            **values,
        }])

        if confirm:
            sale_order.action_confirm()

        return sale_order

    @classmethod
    def _create_sale_order_one_line(cls, price_unit=None, product_id=None, tax_ids=None, discount=None, name=None, product_uom_qty=1.0, **values):
        assert price_unit is not None or product_id is not None
        return cls._create_sale_order(
            order_line=[
                cls._prepare_order_line(
                    name=name,
                    price_unit=price_unit,
                    product_id=product_id,
                    tax_ids=tax_ids,
                    discount=discount,
                    product_uom_qty=product_uom_qty,
                ),
            ],
            **values,
        )

    @classmethod
    def _create_down_payment_invoice(cls, sale_order, amount_type: str, amount: float, post=False):
        """
        :param sale_order:      The SO as a sale.order record.
        :param amount_type:     The type of the global discount: ('percent'/'percentage'), 'fixed', or 'delivered'.
        :param amount:          The amount to consider.
                                For 'percent', it should be a percentage [0-100].
                                For 'fixed', any amount.
                                For 'delivered', this value is not used.
        """
        cls.ensure_installed('sale')

        if amount_type in ('percent', 'percentage'):
            create_values = {
                'advance_payment_method': 'percentage',
                'amount': amount,
            }
        elif amount_type == 'fixed':
            create_values = {
                'advance_payment_method': 'fixed',
                'fixed_amount': amount,
            }
        else:  # amount_type == 'delivered'
            create_values = {
                'advance_payment_method': 'delivered',
            }

        down_payment_wizard = (
            cls.env['sale.advance.payment.inv']
            .with_context({'active_model': sale_order._name, 'active_ids': sale_order.ids})
            .create(create_values)
        )
        action_values = down_payment_wizard.create_invoices()
        dp_invoice = cls.env['account.move'].browse(action_values['res_id'])

        if post:
            dp_invoice.action_post()

        return dp_invoice

    @classmethod
    def _create_final_invoice(cls, sale_order, post=False):
        return cls._create_down_payment_invoice(sale_order, 'delivered', 0, post=post)

    @classmethod
    def _apply_sale_order_discount(cls, sale_order, amount_type: str, amount: float):
        """
        :param sale_order:      The SO as a sale.order record.
        :param amount_type:     The type of the global discount: 'percent', 'all' (also percentage), or 'fixed'.
        :param amount:          The amount to consider.
                                For 'percent' and 'all', it should be a percentage [0-100].
                                For 'fixed', any amount.
        """
        cls.ensure_installed('sale')

        if amount_type in ('percent', 'all'):
            discount_type = 'so_discount' if amount_type == 'percent' else 'sol_discount'
            discount_percentage = amount / 100.0
            discount_amount = None
        else:  # amount_type == 'fixed'
            discount_type = 'amount'
            discount_percentage = None
            discount_amount = amount

        discount_wizard = (
            cls.env['sale.order.discount']
            .with_context({'active_model': sale_order._name, 'active_id': sale_order.id})
            .create({
                'discount_type': discount_type,
                'discount_percentage': discount_percentage,
                'discount_amount': discount_amount,
            })
        )
        discount_wizard.action_apply_discount()
        return discount_wizard

    # -------------------------------------------------------------------------
    # Assertions
    # -------------------------------------------------------------------------

    def replace_ignore(self, to_compare):
        """ Because we put jsons in separate files, we can not use ANY from unittest Mock there, so we can just apply
        this method on the dicts to be compared before doing assertDictEqual"""
        if isinstance(to_compare, dict):
            return {k: self.replace_ignore(v) for k, v in to_compare.items()}
        if isinstance(to_compare, list):
            return [self.replace_ignore(v) for v in to_compare]
        return ANY if to_compare == "___ignore___" else to_compare

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
            'non_deductible_tax_amount_currency': currency,
            'non_deductible_tax_amount': company_currency,
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
    # Xml / JSON Comparison
    ####################################################

    @classmethod
    def _get_ignore_schema(cls, subfolder: str, ignore_schema_name: str) -> bytes | None:
        subfolders = subfolder.split('/')
        ignore_schema_paths = []
        while subfolders:
            ignore_schema_paths.append(f"{cls.test_module}/tests/test_files/{'/'.join(subfolders)}/{ignore_schema_name}")
            subfolders.pop()
        ignore_schema_paths.append(f"{cls.test_module}/tests/test_files/{ignore_schema_name}")

        for ignore_schema_path in ignore_schema_paths:
            try:
                with file_open(ignore_schema_path, 'rb') as f:
                    return f.read()
            except FileNotFoundError:
                pass

    @classmethod
    def _get_xml_ignore_schema(cls, subfolder: str) -> etree._Element | None:
        """
        Recursively look for the closest `ignore_schema.xml` from the given `subfolder`, and
        return its content as an XML element object if found.

        For example, if the given `subfolder` parameter is `foo/bar/egg`, this method will search for
        an `ignore_schema.xml` file from these paths, in order:

        - /tests/test_files/foo/bar/egg/ignore_schema.xml
        - /tests/test_files/foo/bar/ignore_schema.xml
        - /tests/test_files/foo/ignore_schema.xml
        - /tests/test_files/ignore_schema.xml

        :param subfolder: the subfolder of the path of XML file to save/assert. (e.g. "folder_1", "folder_outer/folder_inner")
        :return: _Element object if an `ignore_schema.xml` file is found, otherwise nothing will be returned.
        """
        if ignore_schema_bytes := cls._get_ignore_schema(subfolder, 'ignore_schema.xml'):
            return etree.fromstring(ignore_schema_bytes)

    @classmethod
    def _get_json_ignore_schema(cls, subfolder: str) -> dict | list | None:
        if ignore_schema_bytes := cls._get_ignore_schema(subfolder, 'ignore_schema.json'):
            return json.loads(ignore_schema_bytes)

    @classmethod
    def _clear_xml_content(cls, xml_element: etree._Element, clean_namespaces=True):
        """
        Clears an _Element object by removing all its children and deleting all of their attributes and namespaces.
        """
        for child in xml_element:
            xml_element.remove(child)

        for attrib_key in xml_element.attrib:
            del xml_element.attrib[attrib_key]

        if clean_namespaces:
            etree.cleanup_namespaces(xml_element)

    @classmethod
    def _merge_two_xml(
            cls,
            primary_xml: etree._Element,
            secondary_xml: etree._Element,
            overwrite_on_conflict=True,
            add_on_absent=True,
    ):
        """
        This method takes two _Element objects, and merge the content of the second _Element to the first one recursively.
        Here, we go through every text, and attribute of the secondary_xml and its children; and apply the following operation:

        - Search for a matching child element / attribute on the `primary_xml`
        - If a match is found, overwrite the matching `primary_xml` attribute/child/text if `overwrite_on_conflict` is True
        - If a match is not found, add on `primary_xml` if `add_on_absent` is True

        Warning: The `tag` of the two `_Element` object must be the same.

        For example:
        Before calling this method,
        primary_xml
        <a attr_1="old_attr_1">
            <b>old b text</b>
        </a>

        secondary_xml
        <a attr_1="new_attr_1" attr_2="new_attr_2>
            <b attr_b="new_attr_b">new text</b>
            <c>new element</c>
        </a>

        [#1] Resulting primary_xml post call with default optional parameters (overwrite_on_conflict True, add_on_absent True)
        <a attr_1="new_attr_1" attr_2="new_attr_2>
            <b attr_b="new_attr_b">new text</b>
            <c>new element</c>
        </a>

        [#2] Resulting primary_xml post call with (overwrite_on_conflict True, add_on_absent False)
        <a attr_1="new_attr_1">
            <b>new text</b>
        </a>

        [#3] Resulting primary_xml post call with (overwrite_on_conflict False, add_on_absent True)
        <a attr_1="old_attr_1" attr_2="new_attr_2>
            <b attr_b="new_attr_b">old b text</b>
            <c>new element</c>
        </a>

        [#4] Resulting primary_xml post call with (overwrite_on_conflict False, add_on_absent False)
        No change will be made with these configuration.

        :param primary_xml: The primary _Element object to be written on to.
        :param secondary_xml: The second _Element object in which content is used as reference.
        :param overwrite_on_conflict: If True and matching attribute/child element is found, the original content is overwritten.
        :param add_on_absent: If True and matching attribute/child element is not found, it will be added on the primary_xml.
        :return:
        """
        if primary_xml.tag != secondary_xml.tag:
            return

        for new_attrib_key, new_attrib_val in secondary_xml.items():
            if (new_attrib_key not in primary_xml.attrib and add_on_absent) or (new_attrib_key in primary_xml.attrib and overwrite_on_conflict):
                primary_xml.attrib[new_attrib_key] = new_attrib_val

        if secondary_xml.text and ((not primary_xml.text and overwrite_on_conflict) or (primary_xml.text and overwrite_on_conflict)):
            primary_xml.text = secondary_xml.text

        for new_child in secondary_xml.getchildren():
            found_match = False
            for current_child in primary_xml.getchildren():
                if current_child.tag == new_child.tag:
                    cls._merge_two_xml(
                        current_child,
                        new_child,
                        overwrite_on_conflict=overwrite_on_conflict,
                        add_on_absent=add_on_absent,
                    )
                    found_match = True

            if not found_match and add_on_absent:
                primary_xml.append(new_child)

    @classmethod
    def _prepare_xml_ignore_schema(cls, xml_schema: etree._Element):
        """
        Hook method called on a found ignore schema XML element before we apply them to the main XML element to save.
        Here, we preprocess the `___inherit___` attribute of the main schema XML and process them,
        so that the final `xml_schema` contains the schema of the parent schema(s) too.

        This method can optionally be extended to modify the schema manually python-side.
        """
        # TO EXTEND
        if '___inherit___' in xml_schema.attrib:
            # Merge current XML schema with the parent(s)
            next_inherit = xml_schema.attrib['___inherit___']

            while next_inherit:
                with file_open(next_inherit, 'rb') as f:
                    xml_main_schema = etree.fromstring(f.read())
                next_inherit = xml_main_schema.attrib.get('___inherit___')

                cls._merge_two_xml(xml_main_schema, xml_schema)
                cls._clear_xml_content(xml_schema)
                cls._merge_two_xml(xml_schema, xml_main_schema)

    @classmethod
    def _rebuild_xml_with_sorted_namespaces(cls, root: etree._Element) -> etree._Element:
        # Collect all namespaces and prefixes
        all_nsmap = {
            prefix: uri
            for elem in root.iter()
            for prefix, uri in elem.nsmap.items()
        }

        # Sort all namespaces
        nsmap_str_keys = [key for key in all_nsmap if isinstance(key, str)]
        sorted_nsmap_keys = [
            *((None,) if None in all_nsmap else ()),
            *sorted(nsmap_str_keys),
        ]
        sorted_nsmap = {
            nsmap_key: all_nsmap[nsmap_key]
            for nsmap_key in sorted_nsmap_keys
        }

        # Build a new root element with the sorted namespaces and all original root attrib & children
        new_root = etree.Element(root.tag, nsmap=sorted_nsmap)
        new_root.text = root.text
        for attrib_key, attrib_val in root.attrib.items():
            new_root.attrib[attrib_key] = attrib_val
        for child in root.getchildren():
            new_root.append(child)

        return new_root

    def _get_test_file_path(self, file_name: str, subfolder=''):
        optional_subfolder = f"{subfolder}/" if subfolder else ''
        return file_path(f"{self.test_module}/tests/test_files/{optional_subfolder}{file_name}")

    @classmethod
    def _apply_json_ignore_schema(cls, data, ignore_schema):
        assert data.__class__ is ignore_schema.__class__, "Type of data and ignore_schema must match"

        if isinstance(ignore_schema, dict):
            for schema_key, schema_value in ignore_schema.items():
                if schema_key in data:
                    if schema_value == '___ignore___':
                        data[schema_key] = '___ignore___'
                    elif data[schema_key]:  # schema_value is a dict or a list, and the corresponding value is not None
                        cls._apply_json_ignore_schema(data[schema_key], schema_value)
        elif isinstance(ignore_schema, list):
            if len(ignore_schema) == 1:
                # if there's only one dictionary, apply it to every item in the `data` list
                for data_child in data:
                    cls._apply_json_ignore_schema(data_child, ignore_schema[0])
            else:
                # otherwise, the length of the schema must match the data, and go through them as pairs
                assert len(ignore_schema) == len(data), "Length of list of ignore_schema and data must match"
                for i in range(len(ignore_schema)):
                    cls._apply_json_ignore_schema(data[i], ignore_schema[i])

    def assert_json(self, content_to_assert: dict | list, test_name: str, subfolder=''):
        """
        Helper to save/assert a dictionary to a JSON file located in the corresponding module `test_files`.
        By default, this method will assert the dictionary with the JSON content.
        To switch to save mode, add a `SAVE_JSON` tag when calling the test;
        the `content_to_assert` dictionary will then be written in to the test file.

        Before asserting, the dictionary will first be serialized to ensure it is in the same format of the saved JSON.
        This means that for example: all tuples within the dictionary will be converted to list, etc.

        :param content_to_assert: dictionary | list to save or assert to the corresponding test file
        :param test_name: the test file name
        :param subfolder: the test file subfolder(s), separated by `/` if there is more than one
        """
        json_path = self._get_test_file_path(f"{test_name}.json", subfolder=subfolder)
        content_to_assert = json.loads(json.dumps(content_to_assert))
        if json_ignore_schema := self._get_json_ignore_schema(subfolder):
            self._apply_json_ignore_schema(content_to_assert, json_ignore_schema)

        if 'SAVE_JSON' in config['test_tags']:
            with file_open(json_path, 'w') as f:
                f.write(json.dumps(content_to_assert, indent=4))
            _logger.info("Saved the generated JSON content to %s", json_path)
        else:
            with file_open(json_path, 'rb') as f:
                expected_content = json.loads(f.read())
            self.assertDictEqual(content_to_assert, expected_content)

    def assert_xml(
            self,
            xml_element: str | bytes | etree._Element,
            test_name: str,
            subfolder='',
    ):
        """
        Helper to save/assert an XML element/string/bytes to an XML file.
        By default, this method will assert the passed XML content to the test XML file.
        To switch to save mode, add a `SAVE_XML` tag when calling the test;
        This mode will instead do the following:

        - Reindent the XML element by `\t`
        - Save the XML element to a temporary folder for potential external testing
        - Patch the XML element with `___ignore___` values, following the corresponding schema on the closest `ignore_schema.xml`
        - Canonicalize the XML element to ensure consistency in their namespaces & attributes order
        - Save the XML element content to the test file

        :param xml_element: the _Element/str/bytes content to be saved or asserted
        :param test_name: the test file name
        :param subfolder: the test file subfolder(s), separated by `/` if there is more than one
        :return:
        """
        file_name = f"{test_name}.xml"
        test_file_path = self._get_test_file_path(file_name, subfolder=subfolder)
        if isinstance(xml_element, str):
            xml_element = xml_element.encode()
        if isinstance(xml_element, bytes):
            xml_element = etree.fromstring(xml_element)

        if 'SAVE_XML' in config['test_tags']:
            # Save the XML to tmp folder before modifying some elements with `___ignore___`
            etree.indent(xml_element, space='\t')
            with patch.object(re, 'fullmatch', lambda _arg1, _arg2: True):
                save_test_file(
                    test_name=test_name,
                    content=etree.tostring(xml_element, pretty_print=True, encoding='UTF-8'),
                    prefix=f"{self.test_module}",
                    extension='xml',
                    document_type='Invoice XML',
                    date_format='',
                )
            # Search for closest `ignore_schema.xml` from the file path and apply the change to xml_element
            xml_ignore_schema = self._get_xml_ignore_schema(subfolder)
            if xml_ignore_schema is not None:
                self._prepare_xml_ignore_schema(xml_ignore_schema)
                self._merge_two_xml(
                    xml_element,
                    xml_ignore_schema,
                    overwrite_on_conflict=True,
                    add_on_absent=False,
                )
                etree.indent(xml_element, space='\t')

            # Canonicalize & re-sort the namespaces
            canonicalized_xml_str = etree.canonicalize(xml_element)
            xml_element = etree.fromstring(canonicalized_xml_str)
            xml_element = self._rebuild_xml_with_sorted_namespaces(xml_element)

            # Save the xml_element content
            with file_open(test_file_path, 'wb') as f:
                f.write(etree.tostring(xml_element, pretty_print=True, encoding='UTF-8'))
                _logger.info("Saved the generated XML content to %s", file_name)
        else:
            with file_open(test_file_path, 'rb') as f:
                expected_xml_str = f.read()

            expected_xml_tree = etree.fromstring(expected_xml_str)
            self.assertXmlTreeEqual(xml_element, expected_xml_tree)

    @classmethod
    def _turn_node_as_dict_hierarchy(cls, node, path=''):
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
                cls._turn_node_as_dict_hierarchy(child_node, path=full_path)
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

    @classmethod
    def with_applied_xpath(cls, xml_tree, xpath):
        ''' Applies the xpath to the xml_tree passed as parameter.
        :param xml_tree:    An instance of etree.
        :param xpath:       The xpath to apply as a string.
        :return:            The resulting etree after applying the xpaths.
        '''
        diff_xml_tree = etree.fromstring('<data>%s</data>' % xpath)
        return cls.env['ir.ui.view'].apply_inheritance_specs(xml_tree, diff_xml_tree)

    @classmethod
    def get_xml_tree_from_attachment(cls, attachment):
        ''' Extract an instance of etree from an ir.attachment.
        :param attachment:  An ir.attachment.
        :return:            An instance of etree.
        '''
        return etree.fromstring(base64.b64decode(attachment.with_context(bin_size=False).datas))

    @classmethod
    def get_xml_tree_from_string(cls, xml_tree_str):
        ''' Convert the string passed as parameter to an instance of etree.
        :param xml_tree_str:    A string representing an xml.
        :return:                An instance of etree.
        '''
        return etree.fromstring(xml_tree_str)


class AccountTestMockOnlineSyncCommon(HttpCase):
    def start_tour(self, url_path, tour_name, **kwargs):
        with self.mock_online_sync_favorite_institutions():
            super().start_tour(url_path, tour_name, **kwargs)

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


@tagged('is_tour')
class TestTaxCommon(AccountTestInvoicingHttpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.number = 0
        cls.maxDiff = None

    def setUp(self):
        super().setUp()
        self.js_tests = []

    def _ensure_rate(self, currency, date, rate):
        currency_rate = currency.rate_ids.filtered(lambda x: x.name == fields.Date.from_string(date))
        if currency_rate:
            currency_rate.rate = rate
        else:
            currency.rate_ids = [
                Command.create({
                    'name': date,
                    'rate': rate,
                    'company_id': self.env.company.id,
                })
            ]

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

    def _jsonify_product_uom(self, uom, taxes):
        if not uom:
            return {}
        return {
            **taxes._eval_taxes_computation_turn_to_product_uom_values(product_uom=uom),
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
            'product_uom_id': self._jsonify_product_uom(line['product_uom_id'], line['tax_ids']),
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
        currency = document['currency']
        self._ensure_rate(currency, invoice_date, document['rate'])
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
        for index, (js_test, expected_values, assert_function), r in zip(count(1), self.js_tests, results):
            js_test.update(r)
            with self.subTest(test=js_test['test'], index=index):
                assert_function(js_test, expected_values)

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

    def populate_document(self, document_params):
        AccountTax = self.env['account.tax']
        base_lines = [
            AccountTax._prepare_base_line_for_taxes_computation(
                None,
                id=i,
                rate=line['rate'] if 'rate' in line else document_params['rate'],
                **{
                    'currency_id': line.get('currency_id') or document_params['currency'],
                    'quantity': 1.0,
                    **line,
                },
            )
            for i, line in enumerate(document_params['lines'])
        ]
        AccountTax._add_tax_details_in_base_lines(base_lines, self.env.company)
        AccountTax._round_base_lines_tax_details(base_lines, self.env.company)
        return {
            **document_params,
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

    def _create_py_sub_test_taxes_computation(self, taxes, price_unit, quantity, product, product_uom, precision_rounding, rounding_method, excluded_tax_ids):
        kwargs = {
            'product': product,
            'product_uom': product_uom,
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

    def _create_js_sub_test_taxes_computation(self, taxes, price_unit, quantity, product, product_uom, precision_rounding, rounding_method, excluded_tax_ids):
        return {
            'test': 'taxes_computation',
            'taxes': [self._jsonify_tax(tax) for tax in taxes],
            'price_unit': price_unit,
            'quantity': quantity,
            'product': self._jsonify_product(product, taxes),
            'product_uom': self._jsonify_product_uom(product_uom, taxes),
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
        product_uom=None,
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
            product_uom,
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

    def _create_py_sub_test_adapt_price_unit_to_another_taxes(self, price_unit, original_taxes, new_taxes, product, product_uom):
        return {'price_unit': self.env['account.tax']._adapt_price_unit_to_another_taxes(price_unit, product, original_taxes, new_taxes, product_uom=product_uom)}

    def _create_js_sub_test_adapt_price_unit_to_another_taxes(self, price_unit, original_taxes, new_taxes, product, product_uom):
        return {
            'test': 'adapt_price_unit_to_another_taxes',
            'price_unit': price_unit,
            'product': self._jsonify_product(product, original_taxes + new_taxes),
            'product_uom': self._jsonify_product_uom(product_uom, original_taxes + new_taxes),
            'original_taxes': [self._jsonify_tax(tax) for tax in original_taxes],
            'new_taxes': [self._jsonify_tax(tax) for tax in new_taxes],
        }

    def assert_adapt_price_unit_to_another_taxes(self, price_unit, original_taxes, new_taxes, expected_price_unit, product=None, product_uom=None):
        self._create_assert_test(
            expected_price_unit,
            self._create_py_sub_test_adapt_price_unit_to_another_taxes,
            self._create_js_sub_test_adapt_price_unit_to_another_taxes,
            self._assert_sub_test_adapt_price_unit_to_another_taxes,
            price_unit,
            original_taxes,
            new_taxes,
            product,
            product_uom,
        )

    # -------------------------------------------------------------------------
    # base_lines_tax_details
    # -------------------------------------------------------------------------

    def _extract_base_lines_details(self, document):
        return [
            {
                'total_excluded_currency': base_line['tax_details']['total_excluded_currency'],
                'total_excluded': base_line['tax_details']['total_excluded'],
                'total_included_currency': base_line['tax_details']['total_included_currency'],
                'total_included': base_line['tax_details']['total_included'],
                'delta_total_excluded_currency': base_line['tax_details']['delta_total_excluded_currency'],
                'delta_total_excluded': base_line['tax_details']['delta_total_excluded'],
                'manual_total_excluded': base_line['manual_total_excluded'],
                'manual_total_excluded_currency': base_line['manual_total_excluded_currency'],
                'manual_tax_amounts': base_line['manual_tax_amounts'],
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
            for base_line in document['lines']
        ]

    def _assert_sub_test_base_lines_tax_details(self, results, expected_values):
        self.assertEqual(len(results['base_lines_tax_details']), len(expected_values['base_lines_tax_details']))
        for result, expected in zip(results['base_lines_tax_details'], expected_values['base_lines_tax_details']):
            self.assertDictEqual(result, expected)

    def _create_py_sub_test_base_lines_tax_details(self, document):
        return {
            'base_lines_tax_details': self._extract_base_lines_details(document),
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

    def assert_py_tax_totals_summary(self, document, expected_values, excluded_tax_group_ids=None, soft_checking=False):
        results = self._create_py_sub_test_tax_totals_summary(document, excluded_tax_group_ids, soft_checking)
        self._assert_sub_test_tax_totals_summary(results, expected_values)

    # -------------------------------------------------------------------------
    # global_discount
    # -------------------------------------------------------------------------

    def _assert_sub_test_global_discount(self, results, expected_results):
        self._assert_tax_totals_summary(
            results['tax_totals'],
            expected_results,
            soft_checking=results['soft_checking'],
        )

    def _create_py_sub_test_global_discount(self, document, amount_type, amount, soft_checking):
        AccountTax = self.env['account.tax']
        base_lines = AccountTax._prepare_global_discount_lines(
            base_lines=document['lines'],
            company=self.env.company,
            amount_type=amount_type,
            amount=amount,
        )
        new_document = copy.deepcopy(document)
        new_document['lines'] += base_lines
        AccountTax._add_tax_details_in_base_lines(new_document['lines'], self.env.company)
        AccountTax._round_base_lines_tax_details(new_document['lines'], self.env.company)
        tax_totals = AccountTax._get_tax_totals_summary(
            base_lines=new_document['lines'],
            currency=new_document['currency'],
            company=self.env.company,
            cash_rounding=new_document['cash_rounding'],
        )
        return {'tax_totals': tax_totals, 'soft_checking': soft_checking}

    def _create_js_sub_test_global_discount(self, document, amount_type, amount, soft_checking):
        return {
            'test': 'global_discount',
            'document': self._jsonify_document(document),
            'amount_type': amount_type,
            'amount': amount,
            'soft_checking': soft_checking,
        }

    def assert_global_discount(self, document, amount_type, amount, expected_values, soft_checking=False):
        self._create_assert_test(
            expected_values,
            self._create_py_sub_test_global_discount,
            self._create_js_sub_test_global_discount,
            self._assert_sub_test_global_discount,
            document,
            amount_type,
            amount,
            soft_checking,
        )

    # -------------------------------------------------------------------------
    # down_payment
    # -------------------------------------------------------------------------

    def _assert_sub_test_down_payment(self, results, expected_results):
        self._assert_tax_totals_summary(
            results['tax_totals'],
            expected_results['tax_totals'],
            soft_checking=results['soft_checking'],
        )
        if 'base_lines_tax_details' in expected_results:
            self._assert_sub_test_base_lines_tax_details(results, expected_results)

    def _create_py_sub_test_down_payment(self, document, amount_type, amount, soft_checking):
        AccountTax = self.env['account.tax']
        base_lines = AccountTax._prepare_down_payment_lines(
            base_lines=document['lines'],
            company=self.env.company,
            amount_type=amount_type,
            amount=amount,
            computation_key='down_payment',
        )
        new_document = copy.deepcopy(document)
        new_document['lines'] = base_lines
        AccountTax._add_tax_details_in_base_lines(new_document['lines'], self.env.company)
        AccountTax._round_base_lines_tax_details(new_document['lines'], self.env.company)
        tax_totals = AccountTax._get_tax_totals_summary(
            base_lines=new_document['lines'],
            currency=new_document['currency'],
            company=self.env.company,
            cash_rounding=new_document['cash_rounding'],
        )
        return {
            'tax_totals': tax_totals,
            'soft_checking': soft_checking,
            'base_lines_tax_details': self._extract_base_lines_details(new_document),
        }

    def _create_js_sub_test_down_payment(self, document, amount_type, amount, soft_checking):
        return {
            'test': 'down_payment',
            'document': self._jsonify_document(document),
            'amount_type': amount_type,
            'amount': amount,
            'soft_checking': soft_checking,
        }

    def assert_down_payment(self, document, amount_type, amount, expected_values, soft_checking=False):
        self._create_assert_test(
            expected_values,
            self._create_py_sub_test_down_payment,
            self._create_js_sub_test_down_payment,
            self._assert_sub_test_down_payment,
            document,
            amount_type,
            amount,
            soft_checking,
        )

    # -------------------------------------------------------------------------
    # invoice tax_totals_summary
    # -------------------------------------------------------------------------

    def assert_invoice_totals(self, invoice, expected_values):
        cash_rounding_base_amount_currency = invoice.tax_totals.get('cash_rounding_base_amount_currency', 0.0)
        expected_amounts = {}
        if 'base_amount_currency' in expected_values:
            expected_amounts['amount_untaxed'] = expected_values['base_amount_currency'] + cash_rounding_base_amount_currency
        if 'tax_amount_currency' in expected_values:
            expected_amounts['amount_tax'] = expected_values['tax_amount_currency']
        if 'total_amount_currency' in expected_values:
            expected_amounts['amount_total'] = expected_values['total_amount_currency']
        self.assertRecordValues(invoice, [expected_amounts])

    def assert_invoice_tax_totals_summary(self, invoice, expected_values, soft_checking=False):
        self._assert_tax_totals_summary(invoice.tax_totals, expected_values, soft_checking=soft_checking)
        self.assert_invoice_totals(invoice, expected_values)


class TestAccountMergeCommon(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # this field is added to account.journal because there are no many2many fields referencing account.account
        # the many2many field is needed in `_create_references_to_account` function below
        cls.env['ir.model.fields'].create({
            'ttype': 'many2many',
            'model_id': cls.env.ref('account.model_account_journal').id,
            'relation': 'account.account',
            'name': 'x_account_control_ids',
        })

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

        # Many2many
        journal = self.env['account.journal'].create({
            'name': f'For account {account.id}',
            'code': f'T{account.id}',
            'type': 'general',
            'company_id': account.company_ids.id,
            'x_account_control_ids': [Command.set(account.ids)],
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
            journal: 'x_account_control_ids',
            partner: 'property_account_receivable_id',
            attachment: 'res_id',
        }


class PatchRequestsMixin(TestCase):
    """ Mock external HTTP requests made through the `requests` library.
    Assert expected requests and provide mocked responses in a record/replay fashion.
    """

    external_mode = False

    @contextmanager
    def assertRequests(self, expected_requests_and_responses: list[tuple[dict, requests.Response]]):
        """ Assert expected requests and provide mocked responses in a record/replay fashion.

        Patches `requests.Session.request`, which is the main method internally used by the
        `requests` library to perform HTTP requests, asserts the request contents and serves
        the provided mocked responses.

        To transform the mocked test into a live test, set the `external_mode` attribute to:
        - True to let the requests through;
        - 'warn' to let the requests through but issue a warning if the requests / responses
          differ from the expected requests / mocked responses.

        :param expected_requests_and_responses: A list of tuples, each containing
                                                an expected request and a mocked response.
                                                The expected request is a dictionary of arguments
                                                passed to `requests.Session.request`,
                                                and the mocked response is an object that supports
                                                the `requests.Response` interface.

        Example usage:
        ```
        mocked_response = requests.Response()
        mocked_response.status_code = 200
        mocked_response._content = json.dumps({'message': 'Success'})

        with self.assertRequestsMade([
            (
                {'method': 'POST', 'url': 'https://example.com/send', 'json': {'message': 'Hello World!'}},
                mocked_response,
            ),
        ]):
            response = requests.post('https://example.com/send', json={'message': 'Hello World!'})
        ```
        """
        if self.external_mode is True:
            yield  # Full external mode: don't patch `requests.Session.request` at all
        elif self.external_mode == 'warn':
            # External mode with warnings
            yield from self.patch_requests_warn(expected_requests_and_responses)
        else:
            # Mocked mode
            yield from self.assertMockRequests(expected_requests_and_responses)

    def assertMockRequests(self, expected_requests_and_responses):
        """ Mock requests, assert that the requests are as expected and serve a mocked response. """
        expected_requests_and_responses_iter = iter(expected_requests_and_responses)

        def mock_request(session, method, url, **kwargs):
            actual_request = {
                'method': method,
                'url': url,
                **kwargs,
            }

            try:
                expected_request, mocked_response = next(expected_requests_and_responses_iter)
            except StopIteration:
                self.fail("Unexpected request: %s" % actual_request)

            self.assertRequestsEqual(actual_request, expected_request)
            return mocked_response

        with patch.object(requests.Session, 'request', new=mock_request):
            yield

        next_expected_request, _ = next(expected_requests_and_responses_iter, (None, None))
        if next_expected_request is not None:
            self.fail("Expected request not made: %s" % next_expected_request)

    def patch_requests_warn(self, expected_requests_and_responses):
        """ Let requests pass through but warn if the request or the response differ from
        what is expected.
        """
        expected_requests_and_responses_iter = iter(expected_requests_and_responses)
        original_request_method = requests.Session.request

        def request_and_warn(session, method, url, **kwargs):
            actual_request = {
                'method': method,
                'url': url,
                **kwargs,
            }

            try:
                expected_request, expected_response = next(expected_requests_and_responses_iter)
            except StopIteration:
                _logger.warning("Unexpected request: %s", actual_request)
                return original_request_method(session, method, url, **kwargs)

            try:
                self.assertRequestsEqual(actual_request, expected_request)
            except AssertionError as e:
                _logger.warning("Request differs from expected request: \n%s", e.args[0])

            actual_response = original_request_method(session, method, url, **kwargs)

            if diff_msg := self.difference_between_responses(actual_response, expected_response):
                _logger.warning('Response differs from expected response:\n%s', diff_msg)

            return actual_response

        with patch.object(requests.Session, 'request', request_and_warn):
            yield

        for expected_request, _ in expected_requests_and_responses_iter:
            _logger.warning("Expected request not made: %s", expected_request)

    def assertRequestsEqual(self, actual_request, expected_request):
        """ Method used to validate that the actual request is identical to the expected one.
            Can be overridden to customize the validation. """
        return self.assertEqual(actual_request, expected_request)

    def difference_between_responses(self, actual_response, expected_response):
        """ Method used by the `patch_requests_warn` method to know whether
            the actual response is identical to the mocked response when live-testing.
            Can be overridden to customize this behaviour. """

        def generate_diff(d1, d2):
            return '\n'.join(difflib.ndiff(
                pprint.pformat(d1).splitlines(),
                pprint.pformat(d2).splitlines())
            )

        if (
            actual_response.status_code == expected_response.status_code
            and actual_response.content == expected_response.content
        ):
            return None

        diff_msg = ""
        if actual_response.status_code != expected_response.status_code:
            diff_msg += 'Status code: %s != %s\n' % (actual_response.status_code, expected_response.status_code)

        if actual_response.content != expected_response.content:
            try:
                diff = generate_diff(actual_response.json(), expected_response.json())
                diff_msg += 'Content: \n%s' % diff
            except (TypeError, requests.exceptions.InvalidJSONError):
                try:
                    diff = generate_diff(actual_response.text, expected_response.text)
                    diff_msg += 'Content: \n%s' % diff
                except (TypeError, requests.exceptions.InvalidJSONError):
                    diff_msg += 'Content: \n%s\n != \n%s' % (actual_response.content, expected_response.content)

        return diff_msg
