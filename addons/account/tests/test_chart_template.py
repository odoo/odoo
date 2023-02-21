from unittest.mock import patch

from odoo import Command
from odoo.addons.account.models.chart_template import AccountChartTemplate
from odoo.addons.account.tests.common import instantiate_accountman
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


def _get_chart_template_mapping(self, get_all=False):
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
        'account.account.tag': {
            'account_tax_tag_1': {
                'name': 'tax_tag_name_1',
                'applicability': 'taxes',
                'country_id': 'base.be',
            }
        },
        'account.tax': {
            xmlid: _tax_vals(name, amount, 'account_tax_tag_1')
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

def _tax_vals(name, amount, tax_tag_id=None):
    tag_command = [Command.set([tax_tag_id])] if tax_tag_id else None
    return {
        'name': name,
        'amount': amount,
        'tax_group_id': 'tax_group_taxes',
        'repartition_line_ids': [
            Command.create({'document_type': 'invoice', 'factor_percent': 100, 'repartition_type': 'base', 'tag_ids': tag_command}),
            Command.create({'document_type': 'invoice', 'factor_percent': 100, 'repartition_type': 'tax'}),
            Command.create({'document_type': 'refund', 'factor_percent': 100, 'repartition_type': 'base'}),
            Command.create({'document_type': 'refund', 'factor_percent': 100, 'repartition_type': 'tax'}),
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
        instantiate_accountman(cls)

        cls.company_1 = cls.env['res.company'].create({
            'name': 'TestCompany1',
            'country_id': cls.env.ref('base.be').id,
        })

        cls.user.write({
            'company_ids': [Command.set(cls.company_1.ids)],
            'company_id': cls.company_1.id,
        })

        with patch.object(AccountChartTemplate, '_get_chart_template_data', side_effect=test_get_data, autospec=True):
            cls.env['account.chart.template'].try_loading('test', company=cls.company_1, install_demo=False)

    def test_update_taxes_creation(self):
        """ Tests that adding a new tax and a fiscal position tax creates new records when updating. """
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

    def test_update_taxes_update(self):
        """ When a tax is close enough from an existing tax we want to update that tax with the new values. """
        def local_get_data(self, template_code):
            data = test_get_data(self, template_code)
            data['account.account.tag']['account_tax_tag_1']['name'] += ' [DUP]'
            return data

        with patch.object(AccountChartTemplate, '_get_chart_template_data', side_effect=local_get_data, autospec=True):
            self.env['account.chart.template'].try_loading('test', company=self.company_1, install_demo=False)

        updated_tax = self.env['account.tax'].search([('company_id', '=', self.company_1.id), ('name', '=', 'Tax 1')])
        # Check that tax was not recreated
        self.assertEqual(len(updated_tax), 1)
        # Check that tags have been updated
        self.assertEqual(updated_tax.invoice_repartition_line_ids.tag_ids.name, 'tax_tag_name_1 [DUP]')

    def test_update_taxes_recreation(self):
        """ When a tax is too different from an existing tax we want to recreate a new tax with new values. """
        def local_get_data(self, template_code):
            # We increment the amount so the template gets slightly different from the
            # corresponding tax and triggers recreation
            data = test_get_data(self, template_code)
            data['account.tax']['test_tax_1_template']['name'] = 'Tax 1 modified'
            data['account.tax']['test_tax_1_template']['amount'] += 1
            return data

        tax_existing = self.env['account.tax'].search([('company_id', '=', self.company_1.id), ('name', '=', 'Tax 1')])
        with patch.object(AccountChartTemplate, '_get_chart_template_data', side_effect=local_get_data, autospec=True):
            self.env['account.chart.template'].try_loading('test', company=self.company_1, install_demo=False)

        # Check that old tax has not been changed beside of the name prefixed by [old]
        self.assertRecordValues(tax_existing, [{'name': '[old] Tax 1', 'amount': 15}])

        # Check that new tax has been recreated
        new_tax = self.env['account.tax'].search([('company_id', '=', self.company_1.id), ('name', '=', 'Tax 1 modified')])
        self.assertEqual(new_tax.amount, tax_existing.amount + 1)

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

    def test_update_taxes_multi_company(self):
        """ In a multi-company environment all companies should be correctly updated."""
        def local_get_data(self, template_code):
            # triggers recreation of tax 1
            data = test_get_data(self, template_code)
            data['account.tax']['test_tax_1_template']['amount'] += 1
            return data

        company_2 = self.env['res.company'].create({
            'name': 'TestCompany2',
            'country_id': self.env.ref('base.be').id,
        })
        with patch.object(AccountChartTemplate, '_get_chart_template_data', side_effect=test_get_data, autospec=True):
            self.env['account.chart.template'].try_loading('test', company=company_2, install_demo=False)

        with patch.object(AccountChartTemplate, '_get_chart_template_data', side_effect=local_get_data, autospec=True):
            self.env['account.chart.template'].try_loading('test', company=self.company_1, install_demo=False)
            self.env['account.chart.template'].try_loading('test', company=company_2, install_demo=False)

        taxes_1_companies = self.env['account.tax'].search([
            ('name', 'like', '%Tax 1'),
            ('company_id', 'in', [self.company_1.id, company_2.id]),
        ])
        # we should have 4 records: 2 companies * (1 original tax + 1 recreated tax)
        self.assertEqual(len(taxes_1_companies), 4)

    def test_update_account_codes_conflict(self):
        # Change code of an existing account to something else
        standard_account = self.env['account.chart.template'].ref('test_account_income_template')
        standard_account.code = '111111'

        # create a new account with the same code as an existing one
        problematic_account = self.env['account.account'].create({
            'code': '222221',
            'name': 'problematic_account',
            'company_id': self.company_1.id,
        })

        # remove an xmlid to see if it gets relinked and not duplicated
        self.env['ir.model.data'].search([
            ('name', '=', f'{self.company_1.id}_test_account_expense_template'),
            ('module', '=', 'account'),
        ]).unlink()

        # reload chart template
        with patch.object(AccountChartTemplate, '_get_chart_template_data', side_effect=test_get_data, autospec=True):
            self.env['account.chart.template'].try_loading('test', company=self.company_1, install_demo=False)

        # check that xmlid is now pointing to problematic_account
        xmlid_account = self.env.ref(f'account.{self.company_1.id}_test_account_income_template')
        self.assertEqual(problematic_account, xmlid_account, "xmlid is not pointing to the right account")
