# -*- coding: utf-8 -*-
from odoo import fields
from odoo.tests.common import Form, SavepointCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class AccountingSavepointCase(SavepointCase):

    # -------------------------------------------------------------------------
    # DATA GENERATION
    # -------------------------------------------------------------------------

    @classmethod
    def setUpClass(cls):
        super(AccountingSavepointCase, cls).setUpClass()

        chart_template = cls.env.user.company_id.chart_template_id
        if not chart_template:
            chart_template = cls.env.ref('l10n_generic_coa.configurable_chart_template', raise_if_not_found=False)
        if not chart_template:
            cls.skipTest("Accounting Tests skipped because the user's company has no chart of accounts.")

        # Create user.
        user = cls.env['res.users'].create({
            'name': 'Because I am accountman!',
            'login': 'accountman',
            'groups_id': [(6, 0, cls.env.user.groups_id.ids), (4, cls.env.ref('account.group_account_user').id)],
        })
        user.partner_id.email = 'accountman@test.com'

        # Shadow the current environment/cursor with one having the report user.
        # This is mandatory to test access rights.
        cls.env = cls.env(user=user)
        cls.cr = cls.env.cr

        cls.company_data = cls.setup_company_data('company_1_data')
        cls.currency_data = cls.setup_multi_currency_data()

    @classmethod
    def setup_company_data(cls, company_name, **kwargs):
        ''' Create a new company having the name passed as parameter.
        A chart of accounts will be installed to this company: the same as the current company one.
        The current user will get access to this company.

        :param company_name: The name of the company.
        :return: A dictionary will be returned containing all relevant accounting data for testing.
        '''
        chart_template = cls.env.user.company_id.chart_template_id
        company = cls.env['res.company'].create({
            'name': company_name,
            'currency_id': cls.env.user.company_id.currency_id.id,
            **kwargs,
        })
        cls.env.user.company_ids |= company
        cls.env.user.company_id = company

        chart_template = cls.env['account.chart.template'].browse(chart_template.id)
        chart_template.try_loading()

        # The currency could be different after the installation of the chart template.
        company.write({'currency_id': kwargs.get('currency_id', cls.env.user.company_id.currency_id.id)})

        return {
            'company': company,
            'currency': company.currency_id,
            'default_account_revenue': cls.env['account.account'].search([
                    ('company_id', '=', company.id),
                    ('user_type_id', '=', cls.env.ref('account.data_account_type_revenue').id)
                ], limit=1),
            'default_account_expense': cls.env['account.account'].search([
                    ('company_id', '=', company.id),
                    ('user_type_id', '=', cls.env.ref('account.data_account_type_expenses').id)
                ], limit=1),
            'default_account_receivable': cls.env['account.account'].search([
                    ('company_id', '=', company.id),
                    ('user_type_id.type', '=', 'receivable')
                ], limit=1),
            'default_account_payable': cls.env['account.account'].search([
                    ('company_id', '=', company.id),
                    ('user_type_id.type', '=', 'payable')
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
    def setup_multi_currency_data(cls):
        gold_currency = cls.env['res.currency'].create({
            'name': 'Gold Coin',
            'symbol': '☺',
            'rounding': 0.001,
            'position': 'after',
            'currency_unit_label': 'Gold',
            'currency_subunit_label': 'Silver',
        })
        rate1 = cls.env['res.currency.rate'].create({
            'name': '2016-01-01',
            'rate': 3.0,
            'currency_id': gold_currency.id,
            'company_id': cls.env.company.id,
        })
        rate2 = cls.env['res.currency.rate'].create({
            'name': '2017-01-01',
            'rate': 2.0,
            'currency_id': gold_currency.id,
            'company_id': cls.env.company.id,
        })
        return {
            'currency': gold_currency,
            'rates': rate1 + rate2,
        }

    @classmethod
    def setup_armageddon_tax(cls, tax_name, company_data):
        return cls.env['account.tax'].create({
            'name': '%s (group)' % tax_name,
            'amount_type': 'group',
            'amount': 0.0,
            'children_tax_ids': [
                (0, 0, {
                    'name': '%s (child 1)' % tax_name,
                    'amount_type': 'percent',
                    'amount': 20.0,
                    'price_include': True,
                    'include_base_amount': True,
                    'tax_exigibility': 'on_invoice',
                    'invoice_repartition_line_ids': [
                        (0, 0, {
                            'factor_percent': 100,
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
                            'factor_percent': 100,
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
                    'tax_exigibility': 'on_payment',
                    'cash_basis_transition_account_id': company_data['default_account_tax_sale'].copy().id,
                    'invoice_repartition_line_ids': [
                        (0, 0, {
                            'factor_percent': 100,
                            'repartition_type': 'base',
                        }),
                        (0, 0, {
                            'factor_percent': 100,
                            'repartition_type': 'tax',
                            'account_id': company_data['default_account_tax_sale'].id,
                        }),
                    ],
                    'refund_repartition_line_ids': [
                        (0, 0, {
                            'factor_percent': 100,
                            'repartition_type': 'base',
                        }),

                        (0, 0, {
                            'factor_percent': 100,
                            'repartition_type': 'tax',
                            'account_id': company_data['default_account_tax_sale'].id,
                        }),
                    ],
                }),
            ],
        })
