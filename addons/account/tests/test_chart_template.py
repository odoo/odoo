import logging

from odoo.addons.account.models.chart_template import update_taxes_from_templates
from odoo.tests import tagged
from odoo.tests.common import SavepointCase


@tagged('post_install', '-at_install')
class TestChartTemplate(SavepointCase):

    @classmethod
    def setUpClass(cls):
        """ Set up a company with the generic chart template, containing two taxes and a fiscal position.
        We need to add xml_ids to the templates because they are loaded from their xml_ids
        """
        super().setUpClass()

        be_country_id = cls.env.ref('base.be').id
        cls.company = cls.env['res.company'].create({
            'name': 'TestCompany1',
            'country_id': be_country_id,
            'account_tax_fiscal_country_id': be_country_id,
        })

        cls.chart_template = cls.env.ref('l10n_generic_coa.configurable_chart_template', raise_if_not_found=False)
        if not cls.chart_template:
            cls.skipTest(cls, "Accounting Tests skipped because the generic chart of accounts was not found")

        cls.fiscal_position_template = cls._create_fiscal_position_template('account.test_fiscal_position_template',
                                                                            'BE fiscal position test', be_country_id)
        cls.tax_template_1 = cls._create_tax_template('account.test_tax_template_1', 'Tax name 1', 1, 'tag_name_1')
        cls.tax_template_2 = cls._create_tax_template('account.test_tax_template_2', 'Tax name 2', 2, 'tag_name_2')
        cls.fiscal_position_tax_template_1 = cls._create_fiscal_position_tax_template(
            cls.fiscal_position_template, 'account.test_fp_tax_template_1', cls.tax_template_1, cls.tax_template_2
        )

        cls.chart_template.try_loading(company=cls.company)
        cls.chart_template_xmlid = cls.chart_template.get_external_id()[cls.chart_template.id]
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
    def _create_tax_template(cls, tax_template_xmlid, name, amount, tag_name=None):
        if tag_name:
            tag = cls.env['account.account.tag'].create({
                'name': tag_name,
                'applicability': 'taxes',
                'country_id': cls.company.account_tax_fiscal_country_id.id,
            })
        return cls.env['account.tax.template']._load_records([{
            'xml_id': tax_template_xmlid,
            'values': {
                'name': name,
                'amount': amount,
                'type_tax_use': 'none',
                'chart_template_id': cls.chart_template.id,
                'invoice_repartition_line_ids': [
                    (0, 0, {
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': [(6, 0, tag.ids)] if tag_name else None,
                    }),
                    (0, 0, {
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                    }),
                ],
                'refund_repartition_line_ids': [
                    (0, 0, {
                        'factor_percent': 100,
                        'repartition_type': 'base',
                        'tag_ids': [(6, 0, tag.ids)] if tag_name else None,
                    }),
                    (0, 0, {
                        'factor_percent': 100,
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
        tax_template_3 = self._create_tax_template('account.test_tax_3_template', 'Tax name 3', 3, 'tag_name_3')
        tax_template_4 = self._create_tax_template('account.test_tax_4_template', 'Tax name 4', 4)
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
            'country_id': self.env.ref('base.be').id,
            'account_tax_fiscal_country_id': self.env.ref('base.be').id,
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
