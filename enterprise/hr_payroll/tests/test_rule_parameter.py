# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch
from datetime import date

from odoo import tests
from odoo.fields import Date
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, new_test_user

@tests.tagged('post_install', '-at_install')
class TestRuleParameter(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.rule_parameter = cls.env['hr.rule.parameter'].create({
            'name': 'Test Parameter',
            'code': 'test_param',
        })

        values = []
        for year in [2016, 2017, 2018, 2020]:
            values.append({
                'rule_parameter_id': cls.rule_parameter.id,
                'parameter_value': str(year),
                'date_from': date(year, 1, 1)
            })
        cls.env['hr.rule.parameter.value'].create(values)

    @patch.object(Date, 'today', lambda: date(2019, 10, 10))
    def test_get_last_version(self):
        value = self.env['hr.rule.parameter']._get_parameter_from_code('test_param')
        self.assertEqual(value, 2018, "It should get last valid value")

    def test_get_middle_version(self):
        value = self.env['hr.rule.parameter']._get_parameter_from_code('test_param', date=date(2017, 5, 5))
        self.assertEqual(value, 2017, "It should get the 2017 version")

    def test_get_unexisting_version(self):
        with self.assertRaises(UserError):
            value = self.env['hr.rule.parameter']._get_parameter_from_code('test_param', date=date(2014, 5, 5))

    def test_wrong_code(self):
        with self.assertRaises(UserError):
            value = self.env['hr.rule.parameter']._get_parameter_from_code('wrong_code')

    def test_multicompany(self):
        """ Test value is not reused from cache when allowed_company_ids changes """

        be = self.env.ref('base.be')
        fr = self.env.ref('base.fr')
        company_1 = self.env['res.company'].create({'name': 'Table', 'country_id': be.id})
        company_2 = self.env['res.company'].create({'name': 'Tableau', 'country_id': fr.id})
        user = new_test_user(self.env, login='bub', groups='hr.group_hr_user',
                             company_id=company_2.id,
                             company_ids=[(6, 0, (company_1 + company_2).ids)])

        rule_parameter = self.env['hr.rule.parameter'].create({
            'name': 'Test Parameter',
            'code': 'test_parameter',
            'country_id': be.id,
        })
        self.env['hr.rule.parameter.value'].create({
            'rule_parameter_id': rule_parameter.id,
            'date_from': date(2015, 10, 10),
            'parameter_value': 100,
        })

        with self.assertRaises(UserError):
            # Read a BE parameter from FR company
            self.env['hr.rule.parameter'].with_user(user).with_company(company_2)._get_parameter_from_code('test_parameter')

        # Read a BE parameter from BE company, value is set in cache
        be_value = self.env['hr.rule.parameter'].with_user(user).with_company(company_1)._get_parameter_from_code('test_parameter')
        self.assertEqual(be_value, 100)

        with self.assertRaises(UserError):
            # Read a BE parameter from FR company
            # Value should not come from cache, access rights should be checked
            self.env['hr.rule.parameter'].with_user(user).with_company(company_2)._get_parameter_from_code('test_parameter')
