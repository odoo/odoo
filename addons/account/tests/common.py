# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, Command
from odoo.tools import config, file_path, file_open
from odoo.tests import save_test_file, Form, HttpCase, TransactionCase

import base64
import logging
import re

from contextlib import contextmanager
from lxml import etree
from unittest import SkipTest
from unittest.mock import patch

_logger = logging.getLogger(__name__)


def instantiate_accountman(cls):
    cls.user = cls.env['res.users'].create({
        'name': 'Because I am accountman!',
        'login': 'accountman',
        'password': 'accountman',
        'groups_id': [
            Command.set(cls.env.user.groups_id.ids),
            Command.link(cls.env.ref('account.group_account_manager').id),
            Command.link(cls.env.ref('account.group_account_user').id),
        ],
    })
    cls.user.partner_id.email = 'accountman@test.com'

    # Shadow the current environment/cursor with one having the report user.
    # This is mandatory to test access rights.
    cls.env = cls.env(user=cls.user)
    cls.cr = cls.env.cr


class AccountTestInvoicingCommon(TransactionCase):
    extra_tags = ['-standard', 'external'] if 'EXTERNAL_MODE' in (config['test_tags'] or {}) else []

    @classmethod
    def safe_copy(cls, record):
        return record and record.copy()

    @classmethod
    def copy_account(cls, account, default=None):
        suffix_nb = 1
        while True:
            new_code = '%s.%s' % (account.code, suffix_nb)
            if account.search_count([('company_id', '=', account.company_id.id), ('code', '=', new_code)]):
                suffix_nb += 1
            else:
                return account.copy(default={**(default or {}), 'code': new_code})

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass()
        cls.env.ref('base.main_company').currency_id = cls.env.ref('base.USD')
        instantiate_accountman(cls)

        assert 'post_install' in cls.test_tags, 'This test requires a CoA to be installed, it should be tagged "post_install"'

        if chart_template_ref:
            template_vals = cls.env['account.chart.template']._get_chart_template_mapping()[chart_template_ref]
            template_module = cls.env.ref(f"base.module_{template_vals['module']}")
            if template_module.state != 'installed':
                raise SkipTest(f"Module required for the test is not installed ({template_module.name})")

        cls.company_data_2 = cls.setup_company_data('company_2_data', chart_template=chart_template_ref)
        cls.company_data = cls.setup_company_data('company_1_data', chart_template=chart_template_ref)
        cls.tax_number = 0

        cls.user.write({
            'company_ids': [Command.set((cls.company_data['company'] + cls.company_data_2['company']).ids)],
            'company_id': cls.company_data['company'].id,
        })

        cls.simple_accountman = cls.env['res.users'].create({
            'name': 'simple accountman',
            'login': 'simple_accountman',
            'password': 'simple_accountman',
            'groups_id': [
                # from instantiate_accountman() without "default" superuser groups
                Command.link(cls.env.ref('account.group_account_manager').id),
                Command.link(cls.env.ref('account.group_account_user').id),
            ],
        })

        cls.currency_data = cls.setup_multi_currency_data()

        # ==== Product category ====
        cls.product_category = cls.env['product.category'].create({
            'name': 'Test Category',
        })

        # ==== UOM ====
        cls.uom_unit = cls.env.ref('uom.product_uom_unit')

        # ==== Taxes ====
        cls.tax_sale_a = cls.company_data['default_tax_sale']
        cls.tax_sale_b = cls.safe_copy(cls.company_data['default_tax_sale'])
        cls.tax_purchase_a = cls.company_data['default_tax_purchase']
        cls.tax_purchase_b = cls.safe_copy(cls.company_data['default_tax_purchase'])
        cls.tax_armageddon = cls.setup_armageddon_tax('complex_tax', cls.company_data)

        # ==== Products ====
        cls.product_a = cls.env['product.product'].create({
            'name': 'product_a',
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
            'uom_po_id': cls.env.ref('uom.product_uom_unit').id,
            'lst_price': 1000.0,
            'standard_price': 800.0,
            'property_account_income_id': cls.company_data['default_account_revenue'].id,
            'property_account_expense_id': cls.company_data['default_account_expense'].id,
            'taxes_id': [Command.set(cls.tax_sale_a.ids)],
            'supplier_taxes_id': [Command.set(cls.tax_purchase_a.ids)],
        })
        cls.product_b = cls.env['product.product'].create({
            'name': 'product_b',
            'uom_id': cls.env.ref('uom.product_uom_dozen').id,
            'uom_po_id': cls.env.ref('uom.product_uom_dozen').id,
            'lst_price': 200.0,
            'standard_price': 160.0,
            'property_account_income_id': cls.copy_account(cls.company_data['default_account_revenue']).id,
            'property_account_expense_id': cls.copy_account(cls.company_data['default_account_expense']).id,
            'taxes_id': [Command.set((cls.tax_sale_a + cls.tax_sale_b).ids)],
            'supplier_taxes_id': [Command.set((cls.tax_purchase_a + cls.tax_purchase_b).ids)],
        })

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
            'property_payment_term_id': cls.pay_terms_a.id,
            'property_supplier_payment_term_id': cls.pay_terms_a.id,
            'property_account_receivable_id': cls.company_data['default_account_receivable'].id,
            'property_account_payable_id': cls.company_data['default_account_payable'].id,
            'company_id': False,
        })
        cls.partner_b = cls.env['res.partner'].create({
            'name': 'partner_b',
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
        cls.inbound_payment_method_line = bank_journal.inbound_payment_method_line_ids[0]
        cls.outbound_payment_method_line = bank_journal.outbound_payment_method_line_ids[0]

    @classmethod
    def _create_product(cls, **create_values):
        # OVERRIDE
        create_values.setdefault('property_account_income_id', cls.company_data['default_account_revenue'].id)
        create_values.setdefault('property_account_expense_id', cls.company_data['default_account_expense'].id)
        create_values.setdefault('taxes_id', [Command.set(cls.tax_sale_a.ids)])
        return cls.env['product.product'].create({
            'name': "Test Product",
            'type': 'consu',
            'list_price': 100.0,
            'standard_price': 50.0,
            'uom_id': cls.uom_unit.id,
            'categ_id': cls.product_category.id,
             **create_values,
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
    def setup_company_data(cls, company_name, chart_template=None, **kwargs):
        ''' Create a new company having the name passed as parameter.
        A chart of accounts will be installed to this company: the same as the current company one.
        The current user will get access to this company.

        :param chart_template: The chart template to be used on this new company.
        :param company_name: The name of the company.
        :return: A dictionary will be returned containing all relevant accounting data for testing.
        '''

        company = cls.env['res.company'].create({
            'name': company_name,
            **kwargs,
        })
        cls.env.user.company_ids |= company

        # Install the chart template
        chart_template = chart_template or cls.env['account.chart.template']._guess_chart_template(company.country_id)
        cls.env['account.chart.template'].try_loading(chart_template, company=company, install_demo=False)
        if not company.account_fiscal_country_id:
            company.account_fiscal_country_id = cls.env.ref('base.us')

        # The currency could be different after the installation of the chart template.
        if kwargs.get('currency_id'):
            company.write({'currency_id': kwargs['currency_id']})

        return {
            'company': company,
            'currency': company.currency_id,
            'default_account_revenue': cls.env['account.account'].search([
                    ('company_id', '=', company.id),
                    ('account_type', '=', 'income'),
                    ('deprecated', '=', False),
                    ('id', '!=', company.account_journal_early_pay_discount_gain_account_id.id)
                ], limit=1),
            'default_account_expense': cls.env['account.account'].search([
                    ('company_id', '=', company.id),
                    ('account_type', '=', 'expense'),
                    ('deprecated', '=', False),
                    ('id', '!=', company.account_journal_early_pay_discount_loss_account_id.id)
                ], limit=1),
            'default_account_receivable': cls.env['ir.property'].with_company(company)._get(
                'property_account_receivable_id', 'res.partner'
            ),
            'default_account_payable': cls.env['account.account'].search([
                    ('company_id', '=', company.id),
                    ('account_type', '=', 'liability_payable'),
                    ('deprecated', '=', False),
                ], limit=1),
            'default_account_assets': cls.env['account.account'].search([
                    ('company_id', '=', company.id),
                    ('account_type', '=', 'asset_fixed'),
                ], limit=1),
            'default_account_deferred_expense': cls.env['account.account'].search([
                    ('company_id', '=', company.id),
                    ('account_type', '=', 'asset_current'),
                    ('deprecated', '=', False),
                ], limit=1),
            'default_account_deferred_revenue': cls.env['account.account'].search([
                    ('company_id', '=', company.id),
                    ('account_type', '=', 'liability_current'),
                    ('deprecated', '=', False),
                ], limit=1),
            'default_account_tax_sale': company.account_sale_tax_id.mapped('invoice_repartition_line_ids.account_id'),
            'default_account_tax_purchase': company.account_purchase_tax_id.mapped('invoice_repartition_line_ids.account_id'),
            'default_journal_misc': cls.env['account.journal'].search([
                    ('company_id', '=', company.id),
                    ('type', '=', 'general')
                ], limit=1),
            'default_journal_sale': cls.env['account.journal'].search([
                    ('company_id', '=', company.id),
                    ('type', '=', 'sale')
                ], limit=1),
            'default_journal_purchase': cls.env['account.journal'].search([
                    ('company_id', '=', company.id),
                    ('type', '=', 'purchase')
                ], limit=1),
            'default_journal_bank': cls.env['account.journal'].search([
                    ('company_id', '=', company.id),
                    ('type', '=', 'bank')
                ], limit=1),
            'default_journal_cash': cls.env['account.journal'].search([
                    ('company_id', '=', company.id),
                    ('type', '=', 'cash')
                ], limit=1),
            'default_tax_sale': company.account_sale_tax_id,
            'default_tax_purchase': company.account_purchase_tax_id,
        }

    @classmethod
    def setup_multi_currency_data(cls, default_values=None, rate2016=3.0, rate2017=2.0):
        default_values = default_values or {}
        foreign_currency = cls.env['res.currency'].create({
            'name': 'Gold Coin',
            'symbol': '☺',
            'rounding': 0.001,
            'position': 'after',
            'currency_unit_label': 'Gold',
            'currency_subunit_label': 'Silver',
            **default_values,
        })
        rates = cls.env['res.currency.rate'].create([{
            'name': '1900-01-01',
            'rate': 1,
            'currency_id': foreign_currency.id,
            'company_id': cls.env.company.id,
        }, {
            'name': '2016-01-01',
            'rate': rate2016,
            'currency_id': foreign_currency.id,
            'company_id': cls.env.company.id,
        }, {
            'name': '2017-01-01',
            'rate': rate2017,
            'currency_id': foreign_currency.id,
            'company_id': cls.env.company.id,
        }])
        return {
            'currency': foreign_currency,
            'rates': rates,
        }

    @classmethod
    def setup_other_currency(cls, code, **kwargs):
        kwargs.setdefault('rates', [
            ('1900-01-01', 1.0),
            ('2016-01-01', 3.0),
            ('2017-01-01', 2.0),
        ])
        rates = kwargs.pop('rates', [])
        currency = cls.env['res.currency'].with_context(active_test=False).search([('name', '=', code.upper())])
        currency.action_unarchive()
        currency.rate_ids.unlink()
        currency.write({
            'active': True,
            'rate_ids': [Command.create(
                {
                    'name': rate_date,
                    'rate': rate,
                    'company_id': cls.env.company.id,
                }
            ) for rate_date, rate in rates],
            **kwargs,
        })
        return currency

    @classmethod
    def _instantiate_basic_test_tax_group(cls, company=None, country=None):
        company = company or cls.env.company
        vals = {
            'name': 'Test tax group',
            'company_id': company.id,
            'tax_receivable_account_id': cls.company_data['default_account_receivable'].sudo().copy({'company_id': company.id}).id,
            'tax_payable_account_id': cls.company_data['default_account_payable'].sudo().copy({'company_id': company.id}).id,
        }
        if country:
            vals['country_id'] = country.id
        return cls.env['account.tax.group'].sudo().create(vals)

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
            'python_compute': formula,
        })

    @classmethod
    def setup_armageddon_tax(cls, tax_name, company_data):
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
                    'country_id': company_data['company'].account_fiscal_country_id.id,
                    'price_include': True,
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
                    'country_id': company_data['company'].account_fiscal_country_id.id,
                    'tax_exigibility': 'on_payment',
                    'cash_basis_transition_account_id': cls.safe_copy(company_data['default_account_tax_sale']).id,
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
        })

    @classmethod
    def ensure_installed(cls, module_name: str):
        if cls.env['ir.module.module']._get(module_name).state != 'installed':
            raise SkipTest(f"Module required for the test is not installed ({module_name})")

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

    @classmethod
    def _prepare_record_kwargs(cls, model_name: str, kwargs: dict):
        for key, value in kwargs.items():
            if isinstance(value, models.BaseModel):
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

    def assertInvoiceValues(self, move, expected_lines_values, expected_move_values):
        def sort_lines(lines):
            return lines.sorted(lambda line: (line.sequence, not bool(line.tax_line_id), line.name or '', line.balance))
        self.assertRecordValues(sort_lines(move.line_ids.sorted()), expected_lines_values)
        self.assertRecordValues(move, [expected_move_values])

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

    ####################################################
    # Xml Comparison
    ####################################################

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
        subfolders = subfolder.split('/')
        ignore_schema_paths = []
        while subfolders:
            ignore_schema_paths.append(f"{cls.test_module}/tests/test_files/{'/'.join(subfolders)}/ignore_schema.xml")
            subfolders.pop()
        ignore_schema_paths.append(f"{cls.test_module}/tests/test_files/ignore_schema.xml")

        for ignore_schema_path in ignore_schema_paths:
            try:
                with file_open(ignore_schema_path, 'rb') as f:
                    return etree.fromstring(f.read())
            except FileNotFoundError:
                pass

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
            if ((new_attrib_key not in primary_xml.attrib and add_on_absent) or
                    (new_attrib_key in primary_xml.attrib and overwrite_on_conflict)):
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

    def assert_xml(
            self,
            xml_element: str | bytes | etree._Element,
            test_name: str,
            subfolder='',
            xpath_to_apply='',
            force_save=False,
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
        :param xpath_to_apply: optional `xpath` string to be applied on the expected file
        :param force_save: force the assert method to save the XML to the test file instead of asserting it
        :return:
        """
        file_name = f"{test_name}.xml"
        test_file_path = self._get_test_file_path(file_name, subfolder=subfolder)
        if isinstance(xml_element, str):
            xml_element = xml_element.encode()
        if isinstance(xml_element, bytes):
            xml_element = etree.fromstring(xml_element)

        if 'SAVE_XML' in config['test_tags'] or force_save:
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
                _logger.info("Saved the generated xml content to %s", file_name)
        else:
            with file_open(test_file_path, 'rb') as f:
                expected_xml_str = f.read()

            expected_xml_tree = etree.fromstring(expected_xml_str)
            if xpath_to_apply:
                expected_xml_tree = self.with_applied_xpath(expected_xml_tree, xpath_to_apply)
            try:
                self.assertXmlTreeEqual(xml_element, expected_xml_tree)
            except AssertionError:
                if not force_save and 'SAVE_XML_ON_FAIL' in config['test_tags']:
                    self.assert_xml(
                        xml_element=xml_element,
                        test_name=test_name,
                        subfolder=subfolder,
                        xpath_to_apply=xpath_to_apply,
                        force_save=True,
                    )
                else:
                    raise

    def _turn_node_as_dict_hierarchy(self, node, path=''):
        ''' Turn the node as a python dictionary to be compared later with another one.
        Allow to ignore the management of namespaces.
        :param node:    A node inside an xml tree.
        :param path:    The optional path of tags for recursive call.
        :return:        A python dictionary.
        '''
        tag_split = node.tag.split('}')
        tag_wo_ns = tag_split[-1]
        attrib_wo_ns = {k: v for k, v in node.attrib.items() if '}' not in k}
        full_path = f'{path}/{tag_wo_ns}'
        return {
            'tag': tag_wo_ns,
            'full_path': full_path,
            'namespace': None if len(tag_split) < 2 else tag_split[0],
            'text': (node.text or '').strip(),
            'attrib': attrib_wo_ns,
            'children': [
                self._turn_node_as_dict_hierarchy(child_node, path=path)
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
            # Check tag.
            self.assertEqual(node_dict['tag'], expected_node_dict['tag'])

            # Check attributes.
            node_dict_attrib = {k: '___ignore___' if expected_node_dict['attrib'].get(k) == '___ignore___' else v
                                for k, v in node_dict['attrib'].items()}
            expected_node_dict_attrib = {k: v for k, v in expected_node_dict['attrib'].items() if v != '___remove___'}
            self.assertDictEqual(
                node_dict_attrib,
                expected_node_dict_attrib,
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
            self.assertEqual(
                [child['tag'] for child in node_dict['children']],
                [child['tag'] for child in expected_node_dict['children']],
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


class AccountTestInvoicingHttpCommon(AccountTestInvoicingCommon, HttpCase):
    pass
