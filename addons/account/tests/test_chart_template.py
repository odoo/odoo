import io
from unittest.mock import patch

from odoo import Command
from odoo.addons.account.models.chart_template import code_translations, AccountChartTemplate, TEMPLATE_MODELS
from odoo.addons.account.tests.common import instantiate_accountman
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


def _get_chart_template_mapping(self, get_all=False):
    return {'test': {
        'name': 'test',
        'country_id': self.env.ref('base.be').id,
        'country_code': None,
        'module': 'account',
        'parent': None,
    }}

def test_get_data(self, template_code):
    return {
        'template_data': {
            'code_digits': 6,
            'currency_id': 'base.EUR',
            'property_account_income_categ_id': 'test_account_income_template',
            'property_account_expense_categ_id': 'test_account_expense_template',
            'property_account_receivable_id': 'test_account_receivable_template',
            'property_account_payable_id': 'test_account_payable_template',
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
            f'account.account_tax_tag_{i}': {
                'name': f'tax_tag_name_{i}',
                'applicability': 'taxes',
                'country_id': 'base.be',
            } for i in range(1, 9)
        },
        'account.tax': {
            xmlid: _tax_vals(name, amount, 'account.account_tax_tag_1')
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
            'test_account_receivable_template': {
                'name': 'property_receivable_account',
                'code': '411111',
                'account_type': 'asset_receivable',
            },
            'test_account_payable_template': {
                'name': 'property_payable_account',
                'code': '421111',
                'account_type': 'liability_payable',
            },
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


def _tax_vals(name, amount, tax_tag_id=None, children_tax_xmlids=None, active=True, tax_scope="consu"):
    tag_command = [Command.set([tax_tag_id])] if tax_tag_id else None
    tax_vals = {
        'name': name,
        'amount': amount,
        'amount_type': 'percent' if not children_tax_xmlids else 'group',
        'tax_group_id': 'tax_group_taxes',
        'active': active,
        'tax_scope': tax_scope
    }
    if children_tax_xmlids:
        tax_vals.update({'children_tax_ids': [Command.set(children_tax_xmlids)]})
    else:
        tax_vals.update({'repartition_line_ids': [
            Command.create({'document_type': 'invoice', 'factor_percent': 100, 'repartition_type': 'base', 'tag_ids': tag_command}),
            Command.create({'document_type': 'invoice', 'factor_percent': 100, 'repartition_type': 'tax'}),
            Command.create({'document_type': 'refund', 'factor_percent': 100, 'repartition_type': 'base'}),
            Command.create({'document_type': 'refund', 'factor_percent': 100, 'repartition_type': 'tax'}),
        ]})
    return tax_vals

CSV_DATA = {
    'tax_1': (
        '"id","name","type_tax_use","amount","amount_type","description","invoice_label","tax_group_id","repartition_line_ids/repartition_type",'
        '"repartition_line_ids/factor_percent","repartition_line_ids/document_type","repartition_line_ids/tag_ids","repartition_line_ids/account_id",'
        '"repartition_line_ids/use_in_tax_closing","description@en"\n'
        '"tax_1","5%","sale","5.0","percent","","VAT 5%","tax_group_taxes","base","","invoice","tax_tag_name_1||tax_tag_name_2","","","Test tax"\n'
        '"","","","","","","","","tax","50","invoice","tax_tag_name_3","test_account_income_template","False",""\n'
        '"","","","","","","","","tax","50","invoice","tax_tag_name_4","test_account_income_template","False",""\n'
        '"","","","","","","","","base","","refund","tax_tag_name_5||tax_tag_name_6","","",""\n'
        '"","","","","","","","","tax","50","refund","tax_tag_name_7","test_account_income_template","False",""\n'
        '"","","","","","","","","tax","50","refund","tax_tag_name_8","test_account_income_template","False",""\n'
    ),
    'test_fiscal_position_template': (
        '"id","name","country_id","auto_apply","tax_ids/tax_src_id","tax_ids/tax_dest_id"\n'
        '"test_fiscal_position_template","Fiscal Position","base.be","1","test_tax_3_template","test_tax_4_template"\n'
    ),
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
        cls.ChartTemplate = cls.env['account.chart.template'].with_company(cls.company_1)
        cls.country_be = cls.env.ref('base.be')

    def test_signed_and_unsigned_tags_tax(self):
        tax_report = self.env['account.report'].create({
            'name': "Tax report 1",
            'country_id': self.country_be.id,
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
                    'country_id': self.country_be.id,
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

    def test_inactive_tag_tax(self):
        inactive_tag = self.env['account.account.tag'].create({
            'name': 'Inactive Tax Tag',
            'applicability': 'taxes',
            'active': False,
            'country_id': self.country_be.id,
        })
        tax_to_load = {
            'name': 'Inactive Tags Tax',
            'amount': 30,
            'amount_type': 'percent',
            'tax_group_id': 'tax_group_taxes',
            'active': True,
            'repartition_line_ids': [
                Command.create({
                    'document_type': 'invoice',
                    'factor_percent': 100,
                    'repartition_type': 'base',
                    'tag_ids': inactive_tag.name,
                }),
            ]
        }
        self.env['account.chart.template']._deref_account_tags('test', {'tax1': tax_to_load})
        self.assertEqual(
            tax_to_load['repartition_line_ids'][0],
            Command.create({
                'document_type': 'invoice',
                'factor_percent': 100,
                'repartition_type': 'base',
                'tag_ids': [(Command.set([inactive_tag.id]))],
            }),
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

        def local_get_data2(self, template_code):
            data = test_get_data(self, template_code)
            data['account.tax']['test_tax_1_template']['amount'] = 15
            return data

        tax_1_existing = self.env['account.tax'].search([('company_id', '=', self.company_1.id), ('name', '=', "Tax 1")])
        with patch.object(AccountChartTemplate, '_get_chart_template_data', side_effect=local_get_data, autospec=True):
            self.env['account.chart.template'].try_loading('test', company=self.company_1, install_demo=False)
        tax_1_old = self.env['account.tax'].search([('company_id', '=', self.company_1.id), ('name', '=', "[old] Tax 1")])
        tax_1_new = self.env['account.tax'].search([('company_id', '=', self.company_1.id), ('name', '=', "Tax 1")])
        self.assertEqual(tax_1_old, tax_1_existing, "Old tax still exists but with a different name.")
        self.assertEqual(len(tax_1_new), 1, "New tax have been created with the original name.")

        with patch.object(AccountChartTemplate, '_get_chart_template_data', side_effect=local_get_data2, autospec=True):
            self.env['account.chart.template'].try_loading('test', company=self.company_1, install_demo=False)
        tax_1_old_first = self.env['account.tax'].search([('company_id', '=', self.company_1.id), ('name', '=', "[old] Tax 1")])
        tax_1_old_second = self.env['account.tax'].search([('company_id', '=', self.company_1.id), ('name', '=', "[old1] Tax 1")])
        tax_1_latest = self.env['account.tax'].search([('company_id', '=', self.company_1.id), ('name', '=', "Tax 1")])

        self.assertEqual(tax_1_old, tax_1_old_first, "Old renamed tax is still the same.")
        self.assertEqual(tax_1_old_second, tax_1_new, "Outdated tax is renamed again.")
        self.assertEqual(len(tax_1_latest), 1, "New tax have been created with the original name.")

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

        with patch.object(AccountChartTemplate, '_get_chart_template_data', side_effect=local_get_data, autospec=True):
            # We don't change anything
            self.env['account.chart.template'].try_loading('test', company=self.company_1, install_demo=False)

        self.assertEqual(parent_tax.name, 'Tax with children', "The parent tax created before should not have changed")

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

    def test_unknown_company_fields(self):
        """ Tests that if a key is not known in the company template data when the
        context value 'l10n_check_fields_complete' is set, an error is raised. If a
        key is not known in the company template data but the context value is not
        set, that key is skipped and no error is raised."""

        def local_get_data(self, template_code):
            data = test_get_data(self, template_code)
            data['res.company'][company.id]['unknown_company_key'] = 'unknown_company_value'
            return data

        company = self.company_1

        with patch.object(AccountChartTemplate, '_get_chart_template_data', side_effect=local_get_data, autospec=True):
            # hard fail the loading if the context key is set to ensure `test_all_l10n` works as expected
            with (
                self.assertRaisesRegex(ValueError, 'unknown_company_key'),
                self.env.cr.savepoint(),
            ):
                self.env['account.chart.template'].with_context(l10n_check_fields_complete=True).try_loading('test', company=company, install_demo=False)

            # silently ignore if the field doesn't exist (yet)
            self.env['account.chart.template'].try_loading('test', company=company, install_demo=False)

    def test_change_coa(self):
        def _get_chart_template_mapping(self, get_all=False):
            return {'other_test': {
                'name': 'test',
                'country_id': None,
                'country_code': None,
                'module': 'account',
                'parent': None,
            }}

        with (
            patch.object(AccountChartTemplate, '_get_chart_template_mapping', _get_chart_template_mapping),
            patch.object(AccountChartTemplate, '_get_chart_template_data', side_effect=test_get_data, autospec=True)
        ):
            self.env['account.chart.template'].try_loading('other_test', company=self.company_1, install_demo=True)
        self.assertEqual(self.company_1.chart_template, 'other_test')

        with patch.object(AccountChartTemplate, '_get_chart_template_data', side_effect=test_get_data, autospec=True):
            self.env['account.chart.template'].try_loading('test', company=self.company_1, install_demo=True)
        self.assertEqual(self.company_1.chart_template, 'test')

    def test_update_tax_with_non_existent_tag(self):
        """ Tests that when we update the CoA with a tax that has a tag that does not exist yet we raise an error.
        Typical use case is when the code got updated but the module haven't been updated (-u).
        """
        tax_to_load = {
            'name': 'Mixed Tags Tax',
            'amount': 30,
            'amount_type': 'percent',
            'tax_group_id': 'tax_group_taxes',
            'active': True,
            'repartition_line_ids': [
                Command.create({'document_type': 'invoice', 'factor_percent': 100, 'repartition_type': 'base', 'tag_ids': '+SIGNED_TAG'}),
                Command.create({'document_type': 'invoice', 'factor_percent': 100, 'repartition_type': 'tax'}),
                Command.create({'document_type': 'refund', 'factor_percent': 100, 'repartition_type': 'base'}),
                Command.create({'document_type': 'refund', 'factor_percent': 100, 'repartition_type': 'tax'}),
            ]
        }
        with self.assertRaisesRegex(UserError, 'update your localization'):
            self.env['account.chart.template']._deref_account_tags('test', {'tax1': tax_to_load})

    def test_install_with_translations(self):
        """ Ensure that the translations are loaded correctly when installing chart data; i.e. test '_load_translations' and that the untranslatable fields are translated correctly.
        Note: The '_load_translations' function depends on the '_get_chart_template_data' function for some information.
        The result of '_get_chart_template_data' is mocked (correctly) in this test (and not tested).
        """

        # Local mock for '_get_chart_template_mapping'
        # We will use / install a dedicated new chart 'translation' (not just reload 'test')
        # To have control over the original / en_US values.
        def local_get_mapping(self, get_all=False):
            return {'translation': {
                'name': 'translation',
                'country_id': None,
                'country_code': None,
                'modules': ['account'],
                'parent': None,
            }}

        company = self.company_1

        # Create records that are not part of the chart template
        # They will be translated via code translations.
        # The module used to source the translation is the module from the xml_id or 'account' (as fallback)

        non_chart_data = {
            'account.group': {
                # try module 'no_translation'; fallback to 'account'
                'no_translation.test_chart_template_company_test_free_account_group': {
                    'name': 'Free Account Group',
                    'code_prefix_start': 333330,
                    'code_prefix_end': 333339,
                    'company_id': company.id,
                },
            },
            'account.account': {
                # translate via 'translation' module
                'translation.test_chart_template_company_test_free_account': {
                    'name': 'Free Account',
                    'code': '333331',
                    'account_type': 'asset_current',
                    'company_id': company.id,
                },
            },
            'account.tax': {
                # translate via 'translation' module;
                # 2 translatable fields ('name' and 'description')
                'translation.test_chart_template_company_test_free_tax': {
                    "name": "Free Tax",
                    "description": "Free Tax Description",
                    "amount": "0.00",
                    "company_id": company.id,
                },
            },
        }

        # Local function to "extend" '_post_load_data' to ensure the creation of the records from 'non_chart_data'
        def test_post_load_data(template_code, company, template_data):
            for model, data in non_chart_data.items():
                for xml_id, values in data.items():
                    self.env[model]._load_records([{
                        'xml_id': xml_id,
                        'values': values,
                    }])

        # Create a local mock of '_get_chart_template_data'; "extend" 'test_get_data' with the translation info

        translation_update_for_test_get_data = {
            # Use code translations from module 'translation'
            'account.journal': {
                'cash': {
                    'name': "Cash",
                    'code': "C",  # untranslatable field; shortened due to length restriction (for _translation)
                    '__translation_module__': {
                        'name': 'translation',
                        'code': 'translation',
                    },
                },
            },
            # Different modules for code translations of 'name' and 'description'
            'account.tax': {
                'test_tax_1_template': {
                    'name': "Tax 1",
                    'description': "Tax 1 Description",
                    '__translation_module__': {
                        'name': 'translation',
                        'description': 'translation2',
                    },
                },
            },
            # Use 'name@' and not code translation
            'account.tax.group': {
                'tax_group_taxes': {
                    'name': "Taxes",
                    'name@fr': "Taxes FR",
                    '__translation_module__': {
                        'name': 'translation',
                    },
                },
            },
        }

        def local_get_data(self, template_code):
            data = test_get_data(self, template_code)
            for model, record_info in translation_update_for_test_get_data.items():
                for xmlid, data_update in record_info.items():
                    data[model][xmlid].update(data_update)
            return data

        # Tranlations should fall back to more generic locale 'fr'

        # Target lang for untranslatable fields
        company.partner_id.lang = self.env['res.lang']._activate_lang('fr_BE').code

        # Init empty mock translations to make sure we do not use unintended translation
        mock_python_translations = {}

        for module, lang, value, translation in [
            # wrong translations
            ('translation', 'fr', "Taxes", "WRONG"),  # there is a value in the chart data
            ('translation', 'fr', "Free Account", "Free Account FR"),  # there is a value for fr_BE
            # correct translations
            ('translation', 'fr', "Cash", "Cash FR"),
            ('translation', 'fr', "C", "C FR"),
            ('translation', 'fr', "Tax 1", "Tax 1 FR"),
            ('translation', 'fr_BE', "Free Account", "Free Account FR_BE"),
            ('translation', 'fr', "Free Tax", "Free Tax FR"),
            ('translation', 'fr', "Free Tax Description", "Free Tax Description FR"),
            ('translation2', 'fr', "Tax 1 Description", "Tax 1 Description translation2/FR"),
            ('account', 'fr', "Free Account Group", "Free Account Group account/FR"),
        ]:
            mock_python_translations.setdefault((module, lang), {})[value] = translation

        with patch.object(AccountChartTemplate, '_get_chart_template_mapping', side_effect=local_get_mapping, autospec=True):
            with patch.object(AccountChartTemplate, '_get_chart_template_data', side_effect=local_get_data, autospec=True):
                with patch.object(AccountChartTemplate, '_post_load_data', wraps=test_post_load_data):
                    with patch.object(code_translations, 'python_translations', mock_python_translations):
                        self.env['account.chart.template'].try_loading('translation', company=company, install_demo=False)

        # Check translations
        translatable_model_fields = self.env['account.chart.template']._get_translatable_template_model_fields()
        untranslatable_model_fields = self.env['account.chart.template']._get_untranslatable_fields_to_translate()
        fields_to_translate = {
            model: set(translatable_model_fields.get(model, []) + untranslatable_model_fields.get(model, []))
            for model in TEMPLATE_MODELS
        }

        self.assertEqual({
            f'{xmlid}.{field}@{lang}': self.env['account.chart.template'].ref(xmlid).with_context(lang=lang)[field]
            for chart_like_data in [non_chart_data, translation_update_for_test_get_data]
            for model, data in chart_like_data.items()
            for xmlid, record_data in data.items()
            for field in record_data if field in fields_to_translate.get(model, set())
            for lang in ['en_US', 'fr_BE']
        }, {
            'cash.code@en_US': 'C FR',  # untranslatable field loaded in lang fr_BE
            'cash.code@fr_BE': 'C FR',
            'cash.name@en_US': 'Cash',
            'cash.name@fr_BE': 'Cash FR',
            'no_translation.test_chart_template_company_test_free_account_group.name@en_US': 'Free Account Group',
            'no_translation.test_chart_template_company_test_free_account_group.name@fr_BE': 'Free Account Group account/FR',  # fallback to account
            'tax_group_taxes.name@en_US': 'Taxes',
            'tax_group_taxes.name@fr_BE': 'Taxes FR',
            'test_tax_1_template.description@en_US': 'Tax 1 Description',
            'test_tax_1_template.description@fr_BE': 'Tax 1 Description translation2/FR',
            'test_tax_1_template.name@en_US': 'Tax 1',
            'test_tax_1_template.name@fr_BE': 'Tax 1 FR',
            'translation.test_chart_template_company_test_free_account.name@en_US': 'Free Account',
            'translation.test_chart_template_company_test_free_account.name@fr_BE': 'Free Account FR_BE',  # do not use generic lang
            'translation.test_chart_template_company_test_free_tax.description@en_US': 'Free Tax Description',
            'translation.test_chart_template_company_test_free_tax.description@fr_BE': 'Free Tax Description FR',
            'translation.test_chart_template_company_test_free_tax.name@en_US': 'Free Tax',
            'translation.test_chart_template_company_test_free_tax.name@fr_BE': 'Free Tax FR',
        })

    def test_parsed_csv_submodel_being_loaded(self):
        def get_rep_line_data(x):
            return (x.document_type, x.repartition_type, x.factor_percent, x.use_in_tax_closing)

        with patch('odoo.addons.account.models.chart_template.file_open',
                   side_effect=lambda *args: io.StringIO(CSV_DATA['tax_1'])):
            data = {'account.tax': self.ChartTemplate._get_account_tax('test')}
        self.ChartTemplate._load_data(data)

        tax_1 = self.env.ref(f'account.{self.company_1.id}_tax_1', raise_if_not_found=False)
        tax_rep_lines = tax_1.repartition_line_ids.filtered(lambda x: x.repartition_type == 'tax')
        self.assertEqual([
            ('invoice', 'tax', 50.0, False),
            ('invoice', 'tax', 50.0, False),
            ('refund', 'tax', 50.0, False),
            ('refund', 'tax', 50.0, False),
        ], tax_rep_lines.mapped(get_rep_line_data))

    def test_parsed_csv_submodel_being_updated(self):
        def local_get_data(self, template_code):
            return {
                **test_get_data(self, template_code),
                'account.tax': {
                    xmlid: _tax_vals(name, amount)
                    for name, xmlid, amount in [
                        ('Tax 1', 'test_tax_1_template', 15),
                        ('Tax 2', 'test_tax_2_template', 0),
                        ('Tax 3', 'test_tax_3_template', 16),
                        ('Tax 4', 'test_tax_4_template', 17),
                    ]
                },
            }

        with patch.object(AccountChartTemplate, '_get_chart_template_data', side_effect=local_get_data, autospec=True):
            self.env['account.chart.template'].try_loading('test', company=self.company_1, install_demo=False)

        with patch('odoo.addons.account.models.chart_template.file_open',
                   side_effect=lambda *args: io.StringIO(CSV_DATA['test_fiscal_position_template'])):
            data = {'account.fiscal.position': self.ChartTemplate._get_account_fiscal_position('test')}
        self.ChartTemplate._pre_reload_data(self.company_1, {}, data)
        self.ChartTemplate._load_data(data)

    def test_command_int_values(self):
        """ Command int values should just work in place of their Enum alternatives. """
        def local_get_data(self, template_code):
            data = test_get_data(self, template_code)
            data['account.account'].update({
                "test_account": {
                    'name': "Test account A",
                    'code': '777777',
                    'account_type': 'income_other',
                    'tag_ids': [(6, 0, self.ref('account.account_tag_investing').ids)],
                },
                "test_account_2": {
                    'name': "Test account B",
                    'code': '777778',
                    'account_type': 'income_other',
                    'tag_ids': [
                        (5, 0, 0),
                        (0, 0, {'name': 'Test account tag', 'applicability': 'accounts'}),
                        (0, 0, {'name': 'Test account tag 2', 'applicability': 'accounts'}),
                    ]}
            })
            return data

        with patch.object(AccountChartTemplate, '_get_chart_template_data', side_effect=local_get_data, autospec=True):
            self.env['account.chart.template'].try_loading('test', company=self.company_1, install_demo=False)

        accounts = self.env['account.account'].search([
            ('company_id', '=', self.company_1.id),
            ('code', 'in', ('777777', '777778'))
        ], order='code asc')
        self.assertEqual(2, len(accounts))
        self.assertEqual(self.env.ref('account.account_tag_investing'), accounts[0].tag_ids)
        self.assertEqual({'Test account tag', 'Test account tag 2'}, set(accounts[1].tag_ids.mapped("name")))

    def test_chart_template_company_without_country(self):
        """
            In this test we will try to install a chart template to a company without a country. The expected behavior
            is that the country of the chart template will be set on the company
        """
        company = self.env['res.company'].create({'name': 'Test Company Without country'})
        self.assertFalse(company.country_id)
        with patch.object(AccountChartTemplate, '_get_chart_template_data', side_effect=test_get_data, autospec=True):
            self.env['account.chart.template'].try_loading('test', company=company, install_demo=False)
        self.assertEqual(company.country_id.code, "BE")
