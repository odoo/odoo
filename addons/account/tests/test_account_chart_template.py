# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re
import collections
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class AccountChartTemplateTest(TransactionCase):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super(AccountChartTemplateTest, cls).setUpClass()

        # Create user.
        user = cls.env['res.users'].create({
            'name': 'Because I am accountman!',
            'login': 'accountman',
            'password': 'accountman',
            'groups_id': [(6, 0, cls.env.user.groups_id.ids), (4, cls.env.ref('account.group_account_manager').id)],
        })
        user.partner_id.email = 'accountman@test.com'

        # Shadow the current environment/cursor with one having the report user.
        # This is mandatory to test access rights.
        cls.env = cls.env(user=user)
        cls.cr = cls.env.cr
        cls.company = cls.env['res.company'].create({'name': "company_1"})
        cls.env['ir.model.data']._update_xmlids([{
            'xml_id': f"base.company_{cls.company.id}",
            'record': cls.company,
        }])
        cls.env.user.company_ids |= cls.company
        cls.env.user.company_id = cls.company
        cls.env.user.company_id.currency_id = cls.env.ref('base.EUR')

        cls.ChartTemplate = cls.env['account.chart.template']
        cls._prepare_subclasses()

    @classmethod
    def _prepare_subclasses(cls):
        chart_template_mapping = cls.ChartTemplate.get_chart_template_mapping()
        template_codes = '|'.join(chart_template_mapping)
        pattern = re.compile(f"^_get_(?P<template_code>{template_codes})_(?P<model>.*)$")
        matcher = lambda x: re.match(pattern, x)
        attrs = [x for x in dir(cls.ChartTemplate)]
        attrs = filter(matcher, attrs)
        attrs = [getattr(cls.ChartTemplate, x) for x in attrs]
        get_methods = [x for x in filter(callable, attrs)]
        cls.chart_templates = collections.defaultdict(dict)
        for get_method in get_methods:
            template_code, model = matcher(get_method.__name__).groups()
            cls.chart_templates[template_code][model] = get_method

    def _test_chart_function(self, model, must_be_present):

        def check(template_code, data, _id=None):
            self.assertTrue(isinstance(data, dict))
            for attr in must_be_present:
                self.assertTrue(attr in data, (
                    f"AccountChartTemplate({template_code}): Function '_get_{template_code}_{model}'"
                    f"does not output '{attr}'{' id=' + _id if _id else ''}"
                ))

        for template_code, methods in self.chart_templates.items():
            method = methods.get(model, getattr(self.ChartTemplate, f"_get_{model}"))
            datas = method(self.ChartTemplate, self.company)
            if model == 'template_data':
                return check(template_code, datas)
            self.assertTrue(isinstance(datas, dict))
            for _id, data in datas.items():
                self.assertTrue(bool(_id) and bool(data))
                check(template_code, data, _id)

    def test_default_chart_code(self):
        default_chart_template = self.ChartTemplate.get_default_chart_template_code()
        guessed_chart_template = self.ChartTemplate._guess_chart_template(self.company)
        self.assertEqual(default_chart_template, guessed_chart_template)

    def test_country_chart_code(self):
        self.company.country_id = self.env.ref('base.be')
        guessed_chart_template = self.ChartTemplate._guess_chart_template(self.company)
        self.assertEqual('be', guessed_chart_template)

    def test_res_company(self):
        self._test_chart_function("res_company", [
            "account_fiscal_country_id",
            "account_default_pos_receivable_account_id",
            "income_currency_exchange_account_id",
            "expense_currency_exchange_account_id"
        ])

    def test_account_journal(self):
        self._test_chart_function("template_data", [
            'cash_account_code_prefix',
            'bank_account_code_prefix',
            'transfer_account_code_prefix',
            'property_account_receivable_id',
            'property_account_payable_id',
            'property_account_expense_categ_id',
            'property_account_income_categ_id',
            # 'property_tax_payable_account_id',
            # 'property_tax_receivable_account_id',
        ])

    def test_parent_prefixes(self):
        for code, parents in [
            ('be', ['be', '']),
            ('se_k3', ['se_k3', 'se_k2', 'se', '']),
        ]:
            self.assertEqual(self.ChartTemplate._get_parent_prefixes(code), parents)


class DefaultChartTemplateTest(AccountChartTemplateTest):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super(DefaultChartTemplateTest, cls).setUpClass(chart_template_ref)
        cls.ChartTemplate.try_loading(template_code=None, company=cls.company, install_demo=False)

    def test_default_chart(self):
        self.assertEqual(self.company.currency_id.name, 'USD')
        self.assertTrue(self.env.ref('base.EUR').active)
        self.assertTrue(self.env.ref('base.USD').active)

# import json
# from pprint import pprint
# from odoo import fields
# def serialize(obj, level=0):
#     def serialize_val(obj, k):
#         v = getattr(obj, k)
#         if isinstance(v, str):
#             return v
#         if isinstance(v, (int, float)):
#             return str(v)
#         if isinstance(obj._fields[k], (fields.One2many, fields.Many2many)) and level == 0:
#             return [serialize(x, level=level+1) for x in v]
#         return v
#     as_dict = lambda x: {k: serialize_val(obj, k) for k in x._fields}
#     return [as_dict(x) for x in obj]
#
# pprint([serialize(x) for x in self.env['res.currency'].with_context({'active_test': False}).search([('name', 'in', ['EUR', 'USD'])])])
