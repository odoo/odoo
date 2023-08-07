import logging

from odoo import Command
from odoo.addons.account.models.chart_template import update_taxes_from_templates
from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase



@tagged('post_install', '-at_install')
class TestChartTemplate(TransactionCase):

    @classmethod
    def setUpClass(cls):
        """ Set up a company with the generic chart template, containing two taxes and a fiscal position.
        We need to add xml_ids to the templates because they are loaded from their xml_ids
        """
        super().setUpClass()

        us_country_id = cls.env.ref('base.us').id
        cls.company = cls.env['res.company'].create({
            'name': 'TestCompany1',
            'country_id': us_country_id,
            'account_fiscal_country_id': us_country_id,
        })

        cls.chart_template_xmlid = 'l10n_test.test_chart_template_xmlid'
        cls.chart_template = cls.env['account.chart.template']._load_records([{
            'xml_id': cls.chart_template_xmlid,
            'values': {
                'name': 'Test Chart Template US',
                'currency_id': cls.env.ref('base.USD').id,
                'bank_account_code_prefix': 1000,
                'cash_account_code_prefix': 2000,
                'transfer_account_code_prefix': 3000,
                'country_id': us_country_id,
            }
        }])
        account_templates = cls.env['account.account.template']._load_records([{
            'xml_id': 'account.test_account_income_template',
            'values':
                {
                    'name': 'property_income_account',
                    'code': '222221',
                    'user_type_id': cls.env.ref('account.data_account_type_revenue').id,
                    'chart_template_id': cls.chart_template.id,
                }
        }, {
            'xml_id': 'account.test_account_expense_template',
            'values':
                {
                    'name': 'property_expense_account',
                    'code': '222222',
                    'user_type_id': cls.env.ref('account.data_account_type_expenses').id,
                    'chart_template_id': cls.chart_template.id,
                }
        }])
        cls.chart_template.property_account_income_categ_id = account_templates[0].id
        cls.chart_template.property_account_expense_categ_id = account_templates[1].id

        cls.fiscal_position_template = cls._create_fiscal_position_template('account.test_fiscal_position_template',
                                                                            'US fiscal position test', us_country_id)
        cls.tax_template_1 = cls._create_tax_template('account.test_tax_template_1', 'Tax name 1', 1, tag_name='tag_name_1')
        cls.tax_template_2 = cls._create_tax_template('account.test_tax_template_2', 'Tax name 2', 2, tag_name='tag_name_2')
        cls.fiscal_position_tax_template_1 = cls._create_fiscal_position_tax_template(
            cls.fiscal_position_template, 'account.test_fp_tax_template_1', cls.tax_template_1, cls.tax_template_2
        )

        cls.chart_template.try_loading(company=cls.company, install_demo=False)
        cls.fiscal_position = cls.env['account.fiscal.position'].search([
            ('company_id', '=', cls.company.id),
            ('name', '=', cls.fiscal_position_template.name),
        ])

    @classmethod
    def create_tax_template(cls, name, template_name, amount):
        # TODO to remove in master
        logging.warning("Deprecated method, please use _create_tax_template() instead")
        return cls._create_tax_template(template_name, name, amount, tag_name=None)

    @classmethod
    def _create_group_tax_template(cls, tax_template_xmlid, name, chart_template_id=None, active=True):
        children_1 = cls._create_tax_template(f'{tax_template_xmlid}_children1', f'{name}_children_1', 10, active=active)
        children_2 = cls._create_tax_template(f'{tax_template_xmlid}_children2', f'{name}_children_2', 15, active=active)
        return cls.env['account.tax.template']._load_records([{
            'xml_id': tax_template_xmlid,
            'values': {
                'name': name,
                'amount_type': 'group',
                'type_tax_use': 'none',
                'active': active,
                'chart_template_id': chart_template_id if chart_template_id else cls.chart_template.id,
                'children_tax_ids': [Command.set((children_1 + children_2).ids)],
            },
        }])

    @classmethod
    def _create_tax_template(cls, tax_template_xmlid, name, amount, tag_name=None, chart_template_id=None, account_data=None, active=True):
        if tag_name:
            tag = cls.env['account.account.tag'].create({
                'name': tag_name,
                'applicability': 'taxes',
                'country_id': cls.company.account_fiscal_country_id.id,
            })
        if account_data:
            account_vals = {
                'name': account_data['name'],
                'code': account_data['code'],
                'user_type_id': cls.env.ref('account.data_account_type_current_liabilities').id,
            }
            # We have to instantiate both the template and the record since we suppose accounts are already created.
            account_template = cls.env['account.account.template'].create(account_vals)
            account_vals.update({'company_id': cls.company.id})
            cls.env['account.account'].create(account_vals)
        return cls.env['account.tax.template']._load_records([{
            'xml_id': tax_template_xmlid,
            'values': {
                'name': name,
                'amount': amount,
                'type_tax_use': 'none',
                'active': active,
                'chart_template_id': chart_template_id if chart_template_id else cls.chart_template.id,
                'invoice_repartition_line_ids': [
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': [(6, 0, tag.ids)] if tag_name else None,
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'account_id': account_template.id if account_data else None,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    Command.create({
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': [(6, 0, tag.ids)] if tag_name else None,
                    }),
                    Command.create({
                        'factor_percent': 100,
                        'account_id': account_template.id if account_data else None,
                        'repartition_type': 'tax',
                    }),
                ],
            },
        }])

    @classmethod
    def _create_fiscal_position_template(cls, fp_template_xmlid, fp_template_name, country_id):
        return cls.env['account.fiscal.position.template']._load_records([{
            'xml_id': fp_template_xmlid,
            'values': {
                'name': fp_template_name,
                'chart_template_id': cls.chart_template.id,
                'country_id': country_id,
                'auto_apply': True,
            },
        }])

    @classmethod
    def _create_fiscal_position_tax_template(cls, fiscal_position_template, fiscal_position_tax_template_xmlid, tax_template_src, tax_template_dest):
        return cls.env['account.fiscal.position.tax.template']._load_records([{
            'xml_id': fiscal_position_tax_template_xmlid,
            'values': {
                'tax_src_id': tax_template_src.id,
                'tax_dest_id': tax_template_dest.id,
                'position_id': fiscal_position_template.id,
            },
        }])

    def test_update_taxes_new_template(self):
        """ Tests that adding a new tax template and a fiscal position tax template
        creates this new tax and fiscal position line when updating
        """
        tax_template_3 = self._create_tax_template('account.test_tax_3_template', 'Tax name 3', 3, tag_name='tag_name_3')
        tax_template_4 = self._create_tax_template('account.test_tax_4_template', 'Tax name 4', 4, account_data={'name': 'account_name_4', 'code': 'TACT'})
        self._create_fiscal_position_tax_template(self.fiscal_position_template, 'account.test_fiscal_position_tax_template', tax_template_3, tax_template_4)
        update_taxes_from_templates(self.env.cr, self.chart_template_xmlid)

        taxes = self.env['account.tax'].search([
            ('company_id', '=', self.company.id),
            ('name', 'in', [tax_template_3.name, tax_template_4.name]),
        ])
        self.assertRecordValues(taxes, [
            {'name': 'Tax name 3', 'amount': 3},
            {'name': 'Tax name 4', 'amount': 4},
        ])
        self.assertEqual(taxes.invoice_repartition_line_ids.tag_ids.name, 'tag_name_3')
        self.assertEqual(taxes.invoice_repartition_line_ids.account_id.name, 'account_name_4')
        self.assertRecordValues(self.fiscal_position.tax_ids.tax_src_id, [
            {'name': 'Tax name 1'},
            {'name': 'Tax name 3'},
        ])
        self.assertRecordValues(self.fiscal_position.tax_ids.tax_dest_id, [
            {'name': 'Tax name 2'},
            {'name': 'Tax name 4'},
        ])

    def test_update_taxes_existing_template_update(self):
        """ When a template is close enough from the corresponding existing tax we want to update
        that tax with the template values.
        """
        self.tax_template_1.invoice_repartition_line_ids.tag_ids.name += " [DUP]"
        update_taxes_from_templates(self.env.cr, self.chart_template_xmlid)

        tax = self.env['account.tax'].search([
            ('company_id', '=', self.company.id),
            ('name', '=', self.tax_template_1.name),
        ])
        # Check that tax was not recreated
        self.assertEqual(len(tax), 1)
        # Check that tags have been updated
        self.assertEqual(tax.invoice_repartition_line_ids.tag_ids.name, self.tax_template_1.invoice_repartition_line_ids.tag_ids.name)

    def test_update_taxes_existing_template_recreation(self):
        """ When a template is too different from the corresponding existing tax we want to recreate
        a new taxes from template.
        """
        # We increment the amount so the template gets slightly different from the
        # corresponding tax and triggers recreation
        old_tax_name = self.tax_template_1.name
        old_tax_amount = self.tax_template_1.amount
        self.tax_template_1.name = "Tax name 1 modified"
        self.tax_template_1.amount += 1
        update_taxes_from_templates(self.env.cr, self.chart_template_xmlid)

        # Check that old tax has not been changed
        old_tax = self.env['account.tax'].search([
            ('company_id', '=', self.company.id),
            ('name', '=', old_tax_name),
        ], limit=1)
        self.assertEqual(old_tax[0].amount, old_tax_amount)

        # Check that new tax has been recreated
        tax = self.env['account.tax'].search([
            ('company_id', '=', self.company.id),
            ('name', '=', self.tax_template_1.name),
        ], limit=1)
        self.assertEqual(tax[0].amount, self.tax_template_1.amount)

    def test_update_taxes_remove_fiscal_position_from_tax(self):
        """ Tests that when we remove the tax from the fiscal position mapping it is not
        recreated after update of taxes.
        """
        self.fiscal_position.tax_ids.unlink()
        update_taxes_from_templates(self.env.cr, self.chart_template_xmlid)
        self.assertEqual(len(self.fiscal_position.tax_ids), 0)

    def test_update_taxes_conflict_name(self):
        """ When recreating a tax during update a conflict name can occur since
        we need to respect unique constraint on (name, company_id, type_tax_use, tax_scope).
        To do so, the old tax needs to be prefixed with '[old] '.
        """
        # We increment the amount so the template gets slightly different from the
        # corresponding tax and triggers recreation
        old_amount = self.tax_template_1.amount
        self.tax_template_1.amount += 1
        update_taxes_from_templates(self.env.cr, self.chart_template_xmlid)

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
        chart_template_xmlid_test = 'l10n_test2.test_chart_template_xmlid_2'
        chart_template_test = self.env['account.chart.template']._load_records([{
            'xml_id': chart_template_xmlid_test,
            'values': {
                'name': 'Test Chart Template ZZ',
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

    def test_update_taxes_fiscal_country_check(self):
        """ If there is no country set on chart_template, the taxes can only be updated if
        their country matches the fiscal country. """
        self.chart_template.country_id = None
        country_lu = self.env.ref('base.lu')
        self.company.account_fiscal_country_id = country_lu
        self.tax_template_1.amount += 1
        self.tax_template_2.invoice_repartition_line_ids.tag_ids.name = 'tag_name_2_modified'
        with self.assertRaises(ValidationError):
            update_taxes_from_templates(self.env.cr, self.chart_template_xmlid)

    def test_update_taxes_children_tax_ids(self):
        """ Ensures children_tax_ids are correctly generated when updating taxes with
        amount_type='group'.
        """
        # Both parent and its two children should be created.
        group_tax_name = 'Group Tax name 1 TEST'
        self._create_group_tax_template('account.test_group_tax_test_template', group_tax_name, chart_template_id=self.chart_template.id)
        update_taxes_from_templates(self.env.cr, self.chart_template_xmlid)

        parent_tax = self.env['account.tax'].search([
            ('company_id', '=', self.company.id),
            ('name', '=', group_tax_name),
        ])
        children_taxes = self.env['account.tax'].search([
            ('company_id', '=', self.company.id),
            ('name', 'like', f'{group_tax_name}_%'),
        ])
        self.assertEqual(len(parent_tax), 1, "The parent tax should have been created.")
        self.assertEqual(len(children_taxes), 2, "Two children should have been created.")
        self.assertEqual(parent_tax.children_tax_ids.ids, children_taxes.ids, "The parent and its children taxes should be linked together.")

        # Parent exists - only the two children should be created.
        children_taxes.unlink()
        update_taxes_from_templates(self.env.cr, self.chart_template_xmlid)
        children_taxes = self.env['account.tax'].search([
            ('company_id', '=', self.company.id),
            ('name', 'like', f'{group_tax_name}_%'),
        ])
        self.assertEqual(len(children_taxes), 2, "Two children should be re-created.")
        self.assertEqual(parent_tax.children_tax_ids.ids, children_taxes.ids,
                         "The parent and its children taxes should be linked together.")

        # Children exist - only the parent should be created.
        parent_tax.unlink()
        update_taxes_from_templates(self.env.cr, self.chart_template_xmlid)
        parent_tax = self.env['account.tax'].search([
            ('company_id', '=', self.company.id),
            ('name', '=', group_tax_name),
        ])
        self.assertEqual(len(parent_tax), 1, "The parent tax should have been re-created.")
        self.assertEqual(parent_tax.children_tax_ids.ids, children_taxes.ids,
                         "The parent and its children taxes should be linked together.")

    def test_update_taxes_children_tax_ids_inactive(self):
        """ Ensure tax templates are correctly generated when updating taxes with children taxes,
        even if templates are inactive.
        """
        group_tax_name = 'Group Tax name 1 inactive TEST'
        self._create_group_tax_template('account.test_group_tax_test_template_inactive', group_tax_name, chart_template_id=self.chart_template.id, active=False)
        update_taxes_from_templates(self.env.cr, self.chart_template_xmlid)

        parent_tax = self.env['account.tax'].with_context(active_test=False).search([
            ('company_id', '=', self.company.id),
            ('name', '=', group_tax_name),
        ])
        children_taxes = self.env['account.tax'].with_context(active_test=False).search([
            ('company_id', '=', self.company.id),
            ('name', 'like', f'{group_tax_name}_%'),
        ])
        self.assertEqual(len(parent_tax), 1, "The parent tax should have been created, even if it is inactive.")
        self.assertFalse(parent_tax.active, "The parent tax should be inactive.")
        self.assertEqual(len(children_taxes), 2, "Two children should have been created, even if they are inactive.")
        self.assertEqual(children_taxes.mapped('active'), [False] * 2, "Children taxes should be inactive.")
