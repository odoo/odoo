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

<<<<<<< HEAD
        with patch.object(AccountChartTemplate, '_get_chart_template_data', side_effect=test_get_data, autospec=True):
            cls.env['account.chart.template'].try_loading('test', company=cls.company_1, install_demo=False)
||||||| parent of e5ccaffa4d8 (temp)
        cls.chart_template.try_loading(company=cls.company)
        cls.chart_template_xmlid = cls.chart_template.get_external_id()[cls.chart_template.id]
        cls.fiscal_position = cls.env['account.fiscal.position'].search([
            ('company_id', '=', cls.company.id),
            ('name', '=', cls.fiscal_position_template.name),
        ])
=======
        cls.chart_template.try_loading(company=cls.company, install_demo=False)
        cls.chart_template_xmlid = cls.chart_template.get_external_id()[cls.chart_template.id]
        cls.fiscal_position = cls.env['account.fiscal.position'].search([
            ('company_id', '=', cls.company.id),
            ('name', '=', cls.fiscal_position_template.name),
        ])
>>>>>>> e5ccaffa4d8 (temp)

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

<<<<<<< HEAD
        tax_1_existing = self.env['account.tax'].search([('company_id', '=', self.company_1.id), ('name', '=', "Tax 1")])
        with patch.object(AccountChartTemplate, '_get_chart_template_data', side_effect=local_get_data, autospec=True):
            self.env['account.chart.template'].try_loading('test', company=self.company_1, install_demo=False)
        tax_1_old = self.env['account.tax'].search([('company_id', '=', self.company_1.id), ('name', '=', "[old] Tax 1")])
        tax_1_new = self.env['account.tax'].search([('company_id', '=', self.company_1.id), ('name', '=', "Tax 1")])
        self.assertEqual(tax_1_old, tax_1_existing, "Old tax still exists but with a different name.")
        self.assertEqual(len(tax_1_new), 1, "New tax have been created with the original name.")
||||||| parent of e5ccaffa4d8 (temp)
        taxes_from_template_1 = self.env['account.tax'].search([
            ('company_id', '=', self.company.id),
            ('name', 'like', f"%{self.tax_template_1.name}"),
        ])
        self.assertRecordValues(taxes_from_template_1, [
            {'name': f"[old] {self.tax_template_1.name}", 'amount': old_amount},
            {'name': f"{self.tax_template_1.name}", 'amount': self.tax_template_1.amount},
        ])

    def test_update_taxes_multi_company(self):
        """ In a multi-company environment all companies should be correctly updated."""
        company_2 = self.env['res.company'].create({
            'name': 'TestCompany2',
            'country_id': self.env.ref('base.us').id,
            'account_fiscal_country_id': self.env.ref('base.us').id,
        })
        self.chart_template.try_loading(company=company_2)

        # triggers recreation of taxes related to template 1
        self.tax_template_1.amount += 1
        update_taxes_from_templates(self.env.cr, self.chart_template_xmlid)

        taxes_from_template_1 = self.env['account.tax'].search([
            ('name', 'like', f"%{self.tax_template_1.name}"),
            ('company_id', 'in', [self.company.id, company_2.id]),
        ])
        # we should have 4 records: 2 companies * (1 original tax + 1 recreated tax)
        self.assertEqual(len(taxes_from_template_1), 4)

    def test_message_to_accountants(self):
        """ When we duplicate a tax because it was too different from the existing one we send
        a message to accountant advisors. This message should only be sent to advisors
        and not to regular users.
        """
        # create 1 normal user, 2 accountants managers
        accountant_manager_group = self.env.ref('account.group_account_manager')
        advisor_users = self.env['res.users'].create([{
            'name': 'AccountAdvisorTest1',
            'login': 'aat1',
            'password': 'aat1aat1',
            'groups_id': [(4, accountant_manager_group.id)],
        }, {
            'name': 'AccountAdvisorTest2',
            'login': 'aat2',
            'password': 'aat2aat2',
            'groups_id': [(4, accountant_manager_group.id)],
        }])
        normal_user = self.env['res.users'].create([{
            'name': 'AccountUserTest1',
            'login': 'aut1',
            'password': 'aut1aut1',
            'groups_id': [(4, self.env.ref('account.group_account_user').id)],
        }])
        # create situation where we need to recreate the tax during update to get notification(s) sent
        self.tax_template_1.amount += 1
        update_taxes_from_templates(self.env.cr, self.chart_template_xmlid)

        # accountants received the message
        self.assertEqual(self.env['mail.message'].search_count([
            ('partner_ids', 'in', advisor_users.partner_id.ids),
            ('body', 'like', f"%{self.tax_template_1.name}%"),  # we look for taxes' name that have been sent in the message's body
        ]), 1)
        # normal user didn't
        self.assertEqual(self.env['mail.message'].search_count([
            ('partner_ids', 'in', normal_user.partner_id.ids),
            ('body', 'like', f"%{self.tax_template_1.name}%"),  # we look for taxes' name that have been sent in the message's body
        ]), 0)

    def test_update_taxes_foreign_taxes(self):
        """ When taxes are instantiated through the fiscal position system (in multivat),
        its taxes should also be updated.
        """
        country_test = self.env['res.country'].create({
            'name': 'Country Test',
            'code': 'ZZ',
        })
        chart_template_xmlid_test = 'l10n_test.test_chart_template_xmlid'
        chart_template_test = self.env['account.chart.template']._load_records([{
            'xml_id': chart_template_xmlid_test,
            'values': {
                'name': 'Test Chart Template',
                'currency_id': self.env.ref('base.EUR').id,
                'bank_account_code_prefix': 1000,
                'cash_account_code_prefix': 2000,
                'transfer_account_code_prefix': 3000,
                'country_id': country_test.id,
            }
        }])
        self._create_tax_template('account.test_tax_test_template', 'Tax name 1 TEST', 10, chart_template_id=chart_template_test.id)
        self.env['account.tax.template']._try_instantiating_foreign_taxes(country_test, self.company)
        self._create_tax_template('account.test_tax_test_template2', 'Tax name 2 TEST', 15, chart_template_id=chart_template_test.id)
        update_taxes_from_templates(self.env.cr, chart_template_xmlid_test)

        tax_test_model_data = self.env['ir.model.data'].search([
            ('name', '=', f'{self.company.id}_test_tax_test_template2'),
            ('model', '=', 'account.tax'),
        ])
        self.assertEqual(len(tax_test_model_data), 1, "Taxes should have been created even if the chart_template is installed through fiscal position system.")

    def test_update_taxes_chart_template_country_check(self):
        """ We can't update taxes that don't match the chart_template's country. """
        self.company.chart_template_id.country_id = self.env.ref('base.lu')
        # We provoke one recreation and one update
        self.tax_template_1.amount += 1
        self.tax_template_2.invoice_repartition_line_ids.tag_ids.name = 'tag_name_2_modified'
        with self.assertRaises(ValidationError):
            update_taxes_from_templates(self.env.cr, self.chart_template_xmlid)

    def test_update_taxes_fiscal_country_check(self):
        """ If there is no country set on chart_template (which is the case for the generic one), the taxes can only be updated if
        their country matches the fiscal country. """
        country_lu = self.env.ref('base.lu')
        self.company.account_fiscal_country_id = country_lu
        self.tax_template_1.amount += 1
        self.tax_template_2.invoice_repartition_line_ids.tag_ids.name = 'tag_name_2_modified'
        with self.assertRaises(ValidationError):
            update_taxes_from_templates(self.env.cr, self.chart_template_xmlid)
=======
        taxes_from_template_1 = self.env['account.tax'].search([
            ('company_id', '=', self.company.id),
            ('name', 'like', f"%{self.tax_template_1.name}"),
        ])
        self.assertRecordValues(taxes_from_template_1, [
            {'name': f"[old] {self.tax_template_1.name}", 'amount': old_amount},
            {'name': f"{self.tax_template_1.name}", 'amount': self.tax_template_1.amount},
        ])

    def test_update_taxes_multi_company(self):
        """ In a multi-company environment all companies should be correctly updated."""
        company_2 = self.env['res.company'].create({
            'name': 'TestCompany2',
            'country_id': self.env.ref('base.us').id,
            'account_fiscal_country_id': self.env.ref('base.us').id,
        })
        self.chart_template.try_loading(company=company_2, install_demo=False)

        # triggers recreation of taxes related to template 1
        self.tax_template_1.amount += 1
        update_taxes_from_templates(self.env.cr, self.chart_template_xmlid)

        taxes_from_template_1 = self.env['account.tax'].search([
            ('name', 'like', f"%{self.tax_template_1.name}"),
            ('company_id', 'in', [self.company.id, company_2.id]),
        ])
        # we should have 4 records: 2 companies * (1 original tax + 1 recreated tax)
        self.assertEqual(len(taxes_from_template_1), 4)

    def test_message_to_accountants(self):
        """ When we duplicate a tax because it was too different from the existing one we send
        a message to accountant advisors. This message should only be sent to advisors
        and not to regular users.
        """
        # create 1 normal user, 2 accountants managers
        accountant_manager_group = self.env.ref('account.group_account_manager')
        advisor_users = self.env['res.users'].create([{
            'name': 'AccountAdvisorTest1',
            'login': 'aat1',
            'password': 'aat1aat1',
            'groups_id': [(4, accountant_manager_group.id)],
        }, {
            'name': 'AccountAdvisorTest2',
            'login': 'aat2',
            'password': 'aat2aat2',
            'groups_id': [(4, accountant_manager_group.id)],
        }])
        normal_user = self.env['res.users'].create([{
            'name': 'AccountUserTest1',
            'login': 'aut1',
            'password': 'aut1aut1',
            'groups_id': [(4, self.env.ref('account.group_account_user').id)],
        }])
        # create situation where we need to recreate the tax during update to get notification(s) sent
        self.tax_template_1.amount += 1
        update_taxes_from_templates(self.env.cr, self.chart_template_xmlid)

        # accountants received the message
        self.assertEqual(self.env['mail.message'].search_count([
            ('partner_ids', 'in', advisor_users.partner_id.ids),
            ('body', 'like', f"%{self.tax_template_1.name}%"),  # we look for taxes' name that have been sent in the message's body
        ]), 1)
        # normal user didn't
        self.assertEqual(self.env['mail.message'].search_count([
            ('partner_ids', 'in', normal_user.partner_id.ids),
            ('body', 'like', f"%{self.tax_template_1.name}%"),  # we look for taxes' name that have been sent in the message's body
        ]), 0)

    def test_update_taxes_foreign_taxes(self):
        """ When taxes are instantiated through the fiscal position system (in multivat),
        its taxes should also be updated.
        """
        country_test = self.env['res.country'].create({
            'name': 'Country Test',
            'code': 'ZZ',
        })
        chart_template_xmlid_test = 'l10n_test.test_chart_template_xmlid'
        chart_template_test = self.env['account.chart.template']._load_records([{
            'xml_id': chart_template_xmlid_test,
            'values': {
                'name': 'Test Chart Template',
                'currency_id': self.env.ref('base.EUR').id,
                'bank_account_code_prefix': 1000,
                'cash_account_code_prefix': 2000,
                'transfer_account_code_prefix': 3000,
                'country_id': country_test.id,
            }
        }])
        self._create_tax_template('account.test_tax_test_template', 'Tax name 1 TEST', 10, chart_template_id=chart_template_test.id)
        self.env['account.tax.template']._try_instantiating_foreign_taxes(country_test, self.company)
        self._create_tax_template('account.test_tax_test_template2', 'Tax name 2 TEST', 15, chart_template_id=chart_template_test.id)
        update_taxes_from_templates(self.env.cr, chart_template_xmlid_test)

        tax_test_model_data = self.env['ir.model.data'].search([
            ('name', '=', f'{self.company.id}_test_tax_test_template2'),
            ('model', '=', 'account.tax'),
        ])
        self.assertEqual(len(tax_test_model_data), 1, "Taxes should have been created even if the chart_template is installed through fiscal position system.")

    def test_update_taxes_chart_template_country_check(self):
        """ We can't update taxes that don't match the chart_template's country. """
        self.company.chart_template_id.country_id = self.env.ref('base.lu')
        # We provoke one recreation and one update
        self.tax_template_1.amount += 1
        self.tax_template_2.invoice_repartition_line_ids.tag_ids.name = 'tag_name_2_modified'
        with self.assertRaises(ValidationError):
            update_taxes_from_templates(self.env.cr, self.chart_template_xmlid)

    def test_update_taxes_fiscal_country_check(self):
        """ If there is no country set on chart_template (which is the case for the generic one), the taxes can only be updated if
        their country matches the fiscal country. """
        country_lu = self.env.ref('base.lu')
        self.company.account_fiscal_country_id = country_lu
        self.tax_template_1.amount += 1
        self.tax_template_2.invoice_repartition_line_ids.tag_ids.name = 'tag_name_2_modified'
        with self.assertRaises(ValidationError):
            update_taxes_from_templates(self.env.cr, self.chart_template_xmlid)
>>>>>>> e5ccaffa4d8 (temp)
