from odoo import Command
from odoo.addons.account.models.chart_template import update_taxes_from_templates
from odoo.tests import tagged
from odoo.tests.common import TransactionCase



@tagged('post_install', '-at_install')
class TestChartTemplate(TransactionCase):

    @classmethod
    def create_tax_template(cls, name, template_name, amount):
        return cls.env['account.tax.template']._load_records([{
            'xml_id': template_name,
            'values': {
                'name': name,
                'amount': amount,
                'chart_template_id': cls.chart_template.id,
                'invoice_repartition_line_ids': [
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
            },
        }])

    @classmethod
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

        cls.chart_template = cls.env['account.chart.template']._load_records([{
            'xml_id': 'account.test_chart_template',
            'values': {
                'name': 'Test Chart Template',
                'code_digits': 6,
                'currency_id': cls.env.ref('base.EUR').id,
                'bank_account_code_prefix': 1000,
                'cash_account_code_prefix': 2000,
                'transfer_account_code_prefix': 3000,
            },
        }])

        account_templates = cls.env['account.account.template']._load_records([
            {
                'xml_id': 'account.test_account_income_template',
                'values':
                    {
                        'name': 'property_income_account',
                        'code': '222221',
                        'user_type_id': cls.env.ref('account.data_account_type_revenue').id,
                        'chart_template_id': cls.chart_template.id,
                    }
            },
            {
                'xml_id': 'account.test_account_expense_template',
                'values':
                    {
                        'name': 'property_expense_account',
                        'code': '222222',
                        'user_type_id': cls.env.ref('account.data_account_type_expenses').id,
                        'chart_template_id': cls.chart_template.id,
                    }
            },
        ])

        cls.chart_template.property_account_income_categ_id = account_templates[0].id
        cls.chart_template.property_account_expense_categ_id = account_templates[1].id

        cls.tax_1_template = cls.create_tax_template('Tax 1', 'account.test_tax_1_template', 15)
        cls.tax_2_template = cls.create_tax_template('Tax 2', 'account.test_tax_2_template', 0)

        cls.fiscal_position_template = cls.env['account.fiscal.position.template']._load_records([{
            'xml_id': 'account.test_fiscal_position_template',
            'values': {
                'name': 'Fiscal Position',
                'chart_template_id': cls.chart_template.id,
                'country_id': cls.env.ref('base.be').id,
                'auto_apply': True,
            },
        }])

        cls.env['account.fiscal.position.tax.template']._load_records([{
            'xml_id': 'account.test_fiscal_position_tax_template_1',
            'values': {
                'tax_src_id': cls.tax_1_template.id,
                'tax_dest_id': cls.tax_2_template.id,
                'position_id': cls.fiscal_position_template.id,
            },
        }])

        cls.chart_template.try_loading(company=cls.company_1, install_demo=False)

        cls.partner_1 = cls.env['res.partner'].create({
            'name': 'Partner 1',
            'country_id': cls.env.ref('base.be').id,
        })

    def test_update_taxes_from_templates(self):
        """
            Tests that adding a new tax template and a fiscal position tax template with this new tax template
            creates this new tax and fiscal position line when updating
        """
        fiscal_position = self.env['account.fiscal.position'].get_fiscal_position(self.partner_1.id)
        tax_3_template = self.create_tax_template('Tax 3', 'account.test_tax_3_template', 16)
        tax_4_template = self.create_tax_template('Tax 4', 'account.test_tax_4_template', 17)

        self.env['account.fiscal.position.tax.template']._load_records([
            {
                'xml_id': 'account.test_fiscal_position_new_tax_src_template',
                'values': {
                    'tax_src_id': tax_3_template.id,
                    'tax_dest_id': self.tax_1_template.id,
                    'position_id': self.fiscal_position_template.id,
                },
            },
            {
                'xml_id': 'account.test_fiscal_position_new_tax_dest_template',
                'values': {
                    'tax_src_id': self.tax_2_template.id,
                    'tax_dest_id': tax_4_template.id,
                    'position_id': self.fiscal_position_template.id,
                },
            },
        ])

        taxes = self.env['account.tax'].search([('company_id', '=', self.company_1.id)])

        # Only the template have been created, so it should not be reflected yet on the company's chart template
        self.assertEqual(len(fiscal_position.tax_ids), 1)
        self.assertEqual(len(taxes), 2)

        chart_template_xml_id = self.chart_template.get_external_id()[self.chart_template.id]
        update_taxes_from_templates(self.env.cr, chart_template_xml_id)

        taxes = self.env['account.tax'].search([('company_id', '=', self.company_1.id)])
        self.assertRecordValues(taxes, [
            {'name': 'Tax 1'},
            {'name': 'Tax 2'},
            {'name': 'Tax 3'},
            {'name': 'Tax 4'},
        ])

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
        fiscal_position = self.env['account.fiscal.position'].get_fiscal_position(self.partner_1.id)
        fiscal_position.tax_ids.unlink()
        self.env['account.tax'].search([('company_id', '=', self.company_1.id)]).unlink()

        chart_template_xml_id = self.chart_template.get_external_id()[self.chart_template.id]
        update_taxes_from_templates(self.env.cr, chart_template_xml_id)

        # if taxes have been deleted, they will be recreated, and the fiscal position mapping for it too
        self.assertEqual(len(self.env['account.tax'].search([('company_id', '=', self.company_1.id)])), 2)
        self.assertEqual(len(fiscal_position.tax_ids), 1)

        fiscal_position.tax_ids.unlink()
        update_taxes_from_templates(self.env.cr, chart_template_xml_id)

        # if only the fiscal position mapping has been removed, it won't be recreated
        self.assertEqual(len(fiscal_position.tax_ids), 0)
