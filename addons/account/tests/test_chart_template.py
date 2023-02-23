from unittest.mock import patch

from odoo import Command
from odoo.addons.account.models.chart_template import AccountChartTemplate
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


def _get_chart_template_mapping(self):
    return {'test': {
        'name': 'test',
        'country_id': None,
        'country_code': None,
        'modules': ['account'],
        'parent': None,
    }}

def test_get_data(self, template_code):
    return {
        'template_data': {
            'code_digits': 6,
            'currency_id': 'base.EUR',
            'property_account_income_categ_id': 'test_account_income_template',
            'property_account_expense_categ_id': 'test_account_expense_template',
        },
        'account.tax.group': {
            'tax_group_taxes': {
                'name': "Taxes",
                'sequence': 0,
            },
        },
        'account.journal': self._get_account_journal(template_code),
        'res.company': {
            self.env.company.id: {
                'bank_account_code_prefix': '1000',
                'cash_account_code_prefix': '2000',
                'transfer_account_code_prefix': '3000',
            },
        },
        'account.tax': {
            xmlid: _tax_vals(name, amount)
            for name, xmlid, amount in [
                ('Tax 1', 'test_tax_1_template', 15),
                ('Tax 2', 'test_tax_2_template', 0),
            ]
        },
        'account.account': {
            'test_account_income_template': {
                'name': 'property_income_account',
                'code': '222221',
                'account_type': 'income',
            },
            'test_account_expense_template': {
                'name': 'property_expense_account',
                'code': '222222',
                'account_type': 'expense',
            },
        },
        'account.fiscal.position': {
            'test_fiscal_position_template': {
                'name': 'Fiscal Position',
                'country_id': 'base.be',
                'auto_apply': True,
                'tax_ids': [
                    Command.create({
                        'tax_src_id': 'test_tax_1_template',
                        'tax_dest_id': 'test_tax_2_template',
                    })
                ]
            }
        },
    }

def _tax_vals(name, amount):
    return {
        'name': name,
        'amount': amount,
        'tax_group_id': 'tax_group_taxes',
        'invoice_repartition_line_ids': [
            Command.create({'factor_percent': 100, 'repartition_type': 'base'}),
            Command.create({'factor_percent': 100, 'repartition_type': 'tax'}),
        ],
        'refund_repartition_line_ids': [
            Command.create({'factor_percent': 100, 'repartition_type': 'base'}),
            Command.create({'factor_percent': 100, 'repartition_type': 'tax'}),
        ],
    }

@tagged('post_install', '-at_install')
@patch.object(AccountChartTemplate, '_get_chart_template_mapping', _get_chart_template_mapping)
class TestChartTemplate(TransactionCase):

    @classmethod
    @patch.object(AccountChartTemplate, '_get_chart_template_mapping', _get_chart_template_mapping)
    def setUpClass(cls):
        """
            Setups a company with a custom chart template, containing a tax and a fiscal position.
            We need to add xml_ids to the templates because they are loaded from their xml_ids
        """
        super().setUpClass()

        # Create user.
        user = cls.env['res.users'].create({
            'name': 'Because I am accountman!',
            'login': 'accountman',
            'password': 'accountman',
            'groups_id': [Command.set(cls.env.user.groups_id.ids), Command.link(cls.env.ref('account.group_account_user').id)],
        })
        user.partner_id.email = 'accountman@test.com'

        cls.company_1 = cls.env['res.company'].create({
            'name': 'TestCompany1',
            'country_id': cls.env.ref('base.be').id,
        })

        cls.env = cls.env(user=user)
        cls.cr = cls.env.cr

        user.write({
            'company_ids': [Command.set(cls.company_1.ids)],
            'company_id': cls.company_1.id,
        })

        with patch.object(AccountChartTemplate, '_get_chart_template_data', side_effect=test_get_data, autospec=True):
            cls.env['account.chart.template'].try_loading('test', company=cls.company_1, install_demo=False)

    def test_update_taxes_from_templates(self):
        """
            Tests that adding a new tax template and a fiscal position tax template with this new tax template
            creates this new tax and fiscal position line when updating
        """
        def local_get_data(self, template_code):
            data = test_get_data(self, template_code)
            data['account.tax'].update({
                xmlid: _tax_vals(name, amount)
                for name, xmlid, amount in [
                    ('Tax 3', 'test_tax_3_template', 16),
                    ('Tax 4', 'test_tax_4_template', 17),
                ]
            })
            data['account.fiscal.position']['test_fiscal_position_template']['tax_ids'].extend([
                Command.create({
                    'tax_src_id': 'test_tax_3_template',
                    'tax_dest_id': 'test_tax_1_template',
                }),
                Command.create({
                    'tax_src_id': 'test_tax_2_template',
                    'tax_dest_id': 'test_tax_4_template',
                }),
            ])
            return data

        with patch.object(AccountChartTemplate, '_get_chart_template_data', side_effect=local_get_data, autospec=True):
            self.env['account.chart.template'].try_loading('test', company=self.company_1, install_demo=False)

        taxes = self.env['account.tax'].search([('company_id', '=', self.company_1.id)])
        self.assertRecordValues(taxes, [
            {'name': 'Tax 1'},
            {'name': 'Tax 2'},
            {'name': 'Tax 3'},
            {'name': 'Tax 4'},
        ])

        fiscal_position = self.env['account.fiscal.position'].search([])
        self.assertRecordValues(fiscal_position.tax_ids.tax_src_id, [
            {'name': 'Tax 1'},
            {'name': 'Tax 3'},
            {'name': 'Tax 2'},
        ])
        self.assertRecordValues(fiscal_position.tax_ids.tax_dest_id, [
            {'name': 'Tax 2'},
            {'name': 'Tax 1'},
            {'name': 'Tax 4'},
        ])

    def test_update_taxes_removed_from_templates(self):
        """
            Tests updating after the removal of taxes and fiscal position mapping from the company

        """
        fiscal_position = self.env['account.fiscal.position'].search([])
        fiscal_position.tax_ids.unlink()
        self.env['account.tax'].search([('company_id', '=', self.company_1.id)]).unlink()

        with patch.object(AccountChartTemplate, '_get_chart_template_data', side_effect=test_get_data, autospec=True):
            self.env['account.chart.template'].try_loading('test', company=self.company_1, install_demo=False)

        # if taxes have been deleted, they will be recreated, and the fiscal position mapping for it too
        self.assertEqual(len(self.env['account.tax'].search([('company_id', '=', self.company_1.id)])), 2)
        self.assertEqual(len(fiscal_position.tax_ids), 1)

        fiscal_position.tax_ids.unlink()
        with patch.object(AccountChartTemplate, '_get_chart_template_data', side_effect=test_get_data, autospec=True):
            self.env['account.chart.template'].try_loading('test', company=self.company_1, install_demo=False)

        # if only the fiscal position mapping has been removed, it won't be recreated
        self.assertEqual(len(fiscal_position.tax_ids), 0)

    def test_update_taxes_conflict_name(self):
        def local_get_data(self, template_code):
            data = test_get_data(self, template_code)
            data['account.tax']['test_tax_1_template']['amount'] = 40
            return data

        tax_1_existing = self.env['account.tax'].search([('company_id', '=', self.company_1.id), ('name', '=', "Tax 1")])
        with patch.object(AccountChartTemplate, '_get_chart_template_data', side_effect=local_get_data, autospec=True):
            self.env['account.chart.template'].try_loading('test', company=self.company_1, install_demo=False)
        tax_1_old = self.env['account.tax'].search([('company_id', '=', self.company_1.id), ('name', '=', "[old] Tax 1")])
        tax_1_new = self.env['account.tax'].search([('company_id', '=', self.company_1.id), ('name', '=', "Tax 1")])
        self.assertEqual(tax_1_old, tax_1_existing, "Old tax still exists but with a different name.")
        self.assertEqual(len(tax_1_new), 1, "New tax have been created with the original name.")
