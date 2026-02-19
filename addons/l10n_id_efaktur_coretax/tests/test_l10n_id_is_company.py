from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class L10nIDPartnerCompanyTest(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        indonesia = cls.env.ref('base.id')

        # Parent Contact - Company (rule: starts with 10)
        cls.partner_company = cls.partner_a
        cls.partner_company.write({
            'name': 'ID Parent Company',
            'country_id': indonesia.id,
            'vat': '1000000000014256',
            'l10n_id_tku': '000000',
        })

        # Parent Contact - Company (rule: starts with 0X)
        cls.partner_company_zero = cls.env['res.partner'].create({
            'name': 'ID Parent Company 0X',
            'country_id': indonesia.id,
            'vat': '0864099064063000',
            'l10n_id_tku': '000000',
        })

        # Parent Contact - Individual
        cls.partner_individual = cls.partner_b
        cls.partner_individual.write({
            'name': 'ID Parent Individual',
            'country_id': indonesia.id,
            'vat': '3273061809970002',
            'l10n_id_tku': '000000',
            'parent_id': False,
        })

        # Child Contact - Branch
        cls.partner_branch = cls.env['res.partner'].create({
            'name': 'ID Branch',
            'country_id': indonesia.id,
            'parent_id': cls.partner_company.id,
            'l10n_id_tku': '123456',
        })

        # Child Contact - Individual
        cls.partner_child_individual = cls.env['res.partner'].create({
            'name': 'ID Child Individual',
            'country_id': indonesia.id,
            'parent_id': cls.partner_company.id,
        })

    def test_id_partner_company_classification(self):
        """
        Ensure Indonesian partners are categorized correctly:

        Parent Contact - Company
            parent_id: False
            TKU: 000000
            VAT rule:
                - first digit = 0
                OR
                - first digit = 1 and second digit = 0
            is_company: True

        Parent Contact - Individual
            parent_id: False
            TKU: 000000
            VAT prefix: not matching company rule
            is_company: False

        Child Contact - Branch
            parent_id: True
            TKU != 000000
            is_company: True

        Child Contact - Individual
            parent_id: True
            TKU empty
            is_company: False
        """

        self.assertTrue(
            self.partner_company.is_company,
            "VAT starting with '10' should be treated as a company."
        )

        self.assertTrue(
            self.partner_company_zero.is_company,
            "VAT starting with '0X' should be treated as a company."
        )

        self.assertFalse(
            self.partner_individual.is_company,
            "with VAT not matching the company rule should be treated as an individual."
        )

        self.assertTrue(
            self.partner_branch.is_company,
            "Child partner with TKU different from 000000 should be treated as a branch company."
        )

        self.assertFalse(
            self.partner_child_individual.is_company,
            "Child partner with empty TKU should be treated as an individual contact."
        )
