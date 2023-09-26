from unittest.mock import patch

from odoo import Command
from odoo.addons.account.models.chart_template import AccountChartTemplate
from odoo.addons.account.models.chart_template import TEMPLATE_MODELS
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
            'account.account_tax_tag_1': {
                'name': 'tax_tag_name_1',
                'applicability': 'taxes',
                'country_id': 'base.be',
            }
        },
        'account.tax': {
            xmlid: _tax_vals(name, amount)
            for name, xmlid, amount in [
                ('Tax 1', 'test_tax_1_template', 15),
                ('Tax 2', 'test_tax_2_template', 0),
            ]
        },
        'account.group': {
            'test_account_group_1': {
                'name': 'test_account_group_name_1',
                'code_prefix_start': 222220,
                'code_prefix_end': 222229,
            }
        },
        'account.account': {
            'test_account_income_template': {
                'name': 'property_income_account',
                'code': '222221',
                'account_type': 'income',
                'group_id': 'test_account_group_1',
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
        'account.reconcile.model': {
            'test_account_reconcile_model_1': {
                'name': 'test_reconcile_model_with_payment_tolerance',
                'rule_type': 'invoice_matching',
                'allow_payment_tolerance': True,
                'payment_tolerance_type': 'percentage',
                'payment_tolerance_param': 2.0,
                'line_ids': [Command.create({'account_id': 'test_account_income_template'})],
            }
        }
    }

def _tax_vals(name, amount, children_tax_xmlids=None, active=True):
    tax_vals = {
        'name': name,
        'amount': amount,
        'amount_type': 'percent' if not children_tax_xmlids else 'group',
        'tax_group_id': 'tax_group_taxes',
        'active': active,
    }
    if children_tax_xmlids:
        tax_vals.update({'children_tax_ids': [Command.set(children_tax_xmlids)]})
    return tax_vals


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

    def test_signed_and_unsigned_tags_tax(self):
        tax_report = self.env['account.report'].create({
            'name': "Tax report 1",
            'country_id': None,
            'column_ids': [
                Command.create({
                    'name': "Balance",
                    'expression_label': 'balance',
                }),
            ],
        })
        self.env['account.report.line'].create({
            'name': "[SIGNED_TAG] Signed tag line",
            'report_id': tax_report.id,
            'sequence': max(tax_report.mapped('line_ids.sequence') or [0]) + 1,
            'expression_ids': [
                Command.create({
                    'label': 'balance',
                    'engine': 'tax_tags',
                    'formula': 'SIGNED_TAG',
                }),
            ],
        })
        signed_tag = self.env['account.account.tag'].search([
            ('applicability', '=', 'taxes'),
            ('name', '=', '+SIGNED_TAG'),
        ])
        self.env['account.account.tag']._load_records([
            {
                'xml_id': 'account.unsigned_tax_tag',
                'noupdate': True,
                'values': {
                    'name': "unsigned tax tag",
                    'applicability': 'taxes',
                },
            },
        ])
        tax_to_load = {
            'name': 'Mixed Tags Tax',
            'amount': 30,
            'amount_type': 'percent',
            'tax_group_id': 'tax_group_taxes',
            'active': True,
            'repartition_line_ids': [
                Command.create({'document_type': 'invoice', 'factor_percent': 100, 'repartition_type': 'base', 'tag_ids': 'account.unsigned_tax_tag||+SIGNED_TAG'}),
                Command.create({'document_type': 'invoice', 'factor_percent': 100, 'repartition_type': 'tax'}),
                Command.create({'document_type': 'refund', 'factor_percent': 100, 'repartition_type': 'base'}),
                Command.create({'document_type': 'refund', 'factor_percent': 100, 'repartition_type': 'tax'}),
            ]
        }
        self.env['account.chart.template']._deref_account_tags('test', {'tax1': tax_to_load})
        self.assertEqual(
            tax_to_load['repartition_line_ids'][0],
            Command.create({
                'document_type': 'invoice',
                'factor_percent': 100,
                'repartition_type': 'base',
                'tag_ids': [Command.set(['account.unsigned_tax_tag', signed_tag.id])],
            })
        )

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
            data['account.account.tag']['account.account_tax_tag_1']['name'] += ' [DUP]'
            return data

        tax_existing = self.env['account.tax'].search([('company_id', '=', self.company_1.id), ('name', '=', 'Tax 1')])
        tag_existing = self.env['account.account.tag'].search([('name', '=', 'tax_tag_name_1')])
        tax_existing.invoice_repartition_line_ids.tag_ids = tag_existing
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
            ('name', '=like', '%Tax 1'),
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

    def test_update_taxes_children_tax_ids(self):
        """ Ensures children_tax_ids are correctly generated when updating taxes with
        amount_type='group'.
        """
        def local_get_data(self, template_code):
            data = test_get_data(self, template_code)
            normal_tax_xmlids = ['test_tax_3_template', 'test_tax_4_template']
            data['account.tax'].update({
                xmlid: _tax_vals(name, amount, children_tax_xmlids=children_tax_xmlids)
                for name, xmlid, amount, children_tax_xmlids in [
                    ('Tax 3', normal_tax_xmlids[0], 16, None),
                    ('Tax 4', normal_tax_xmlids[1], 17, None),
                    ('Tax with children', 'test_tax_5_group_template', 0, normal_tax_xmlids)
                ]
            })
            return data

        with patch.object(AccountChartTemplate, '_get_chart_template_data', side_effect=local_get_data, autospec=True):
            self.env['account.chart.template'].try_loading('test', company=self.company_1, install_demo=False)

        parent_tax = self.env['account.tax'].search([
            ('company_id', '=', self.company_1.id),
            ('name', '=', 'Tax with children'),
        ])
        children_taxes = self.env['account.tax'].search([
            ('company_id', '=', self.company_1.id),
            ('name', 'in', ['Tax 3', 'Tax 4']),
        ])
        self.assertEqual(len(parent_tax), 1, "The parent tax should have been created.")
        self.assertEqual(len(children_taxes), 2, "Two children should have been created.")
        self.assertEqual(parent_tax.children_tax_ids.ids, children_taxes.ids, "The parent and its children taxes should be linked together.")

    def test_update_taxes_children_tax_ids_inactive(self):
        """ Ensure tax templates are correctly generated when updating taxes with children taxes,
        even if templates are inactive.
        """
        def local_get_data(self, template_code):
            data = test_get_data(self, template_code)
            normal_tax_xmlids = ['test_tax_3_template', 'test_tax_4_template']
            data['account.tax'].update({
                xmlid: _tax_vals(name, amount, children_tax_xmlids=children_tax_xmlids, active=active)
                for name, xmlid, amount, children_tax_xmlids, active in [
                    ('Inactive Tax 3', normal_tax_xmlids[0], 16, None, False),
                    ('Inactive Tax 4', normal_tax_xmlids[1], 17, None, False),
                    ('Inactive Tax with children', 'test_tax_5_group_template', 0, normal_tax_xmlids, False)
                ]
            })
            return data

        with patch.object(AccountChartTemplate, '_get_chart_template_data', side_effect=local_get_data, autospec=True):
            self.env['account.chart.template'].try_loading('test', company=self.company_1, install_demo=False)

        parent_tax = self.env['account.tax'].with_context(active_test=False).search([
            ('company_id', '=', self.company_1.id),
            ('name', '=', 'Inactive Tax with children'),
        ])
        children_taxes = self.env['account.tax'].with_context(active_test=False).search([
            ('company_id', '=', self.company_1.id),
            ('name', 'in', ['Inactive Tax 3', 'Inactive Tax 4']),
        ])
        self.assertEqual(len(parent_tax), 1, "The parent tax should have been created, even if it is inactive.")
        self.assertFalse(parent_tax.active, "The parent tax should be inactive.")
        self.assertEqual(len(children_taxes), 2, "Two children should have been created, even if they are inactive.")
        self.assertEqual(children_taxes.mapped('active'), [False] * 2, "Children taxes should be inactive.")

    def test_update_reload_no_new_data(self):
        """ Tests that the reload does nothing when data are left unchanged.
        Tested models: account.group, account.account, account.tax.group, account.tax, account.journal,
        account.reconcile.model, account.fiscal.position, account.fiscal.position.tax, account.tax.repartition.line,
        account.account.tag.
        """
        def get_domain(model):
            if model == 'account.account.tag':
                return [('country_id', '=', self.company_1.country_id.id)]
            else:
                return [('company_id', '=', self.company_1.id)]

        sub_models = ('account.fiscal.position.tax', 'account.tax.repartition.line', 'account.account.tag')
        data_before = {}
        for model in TEMPLATE_MODELS + sub_models:
            data_before[model] = self.env[model].search(get_domain(model))

        with patch.object(AccountChartTemplate, '_get_chart_template_data', side_effect=test_get_data, autospec=True):
            self.env['account.chart.template'].try_loading('test', company=self.company_1, install_demo=False)

        for model in TEMPLATE_MODELS + sub_models:
            data_after = self.env[model].search(get_domain(model))
            self.assertEqual(data_before[model], data_after)
