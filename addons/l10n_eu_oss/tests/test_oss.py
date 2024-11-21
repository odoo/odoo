# -*- coding: utf-8 -*-

from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.l10n_eu_oss.models.eu_tag_map import EU_TAG_MAP
from odoo.tests import tagged


@tagged('post_install', 'post_install_l10n', '-at_install')
class TestOSSBelgium(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('be')
    def setUpClass(cls):
        super().setUpClass()
        cls.root_company = cls.company_data['company']
        cls.root_company.child_ids = [Command.create({'name': 'Branch A'})]
        cls.cr.precommit.run()  # load the CoA
        cls.child_company = cls.root_company.child_ids
        cls.child_company.child_ids = [Command.create({'name': 'sub Branch B'})]
        cls.sub_child_company = cls.root_company.child_ids.child_ids
        cls.cr.precommit.run()  # load the CoA

    def test_oss_tax_should_be_instantiated_on_root_company_if_no_tax_id_on_sub_branch(self):
        self.sub_child_company._map_eu_taxes()
        # simulate sub child selection in the switcher
        self.env.user.company_id, self.env.user.company_ids = self.sub_child_company, self.sub_child_company

        another_eu_country_code = (self.env.ref('base.europe').country_ids - self.sub_child_company.country_id)[0].code
        tax_oss = self.env['account.tax'].search([('name', 'ilike', f'%"{another_eu_country_code}"%')], limit=1)
        self.assertTrue(tax_oss)
        self.assertEqual(tax_oss.company_id, self.root_company)

    def test_oss_tax_should_be_instantiated_on_first_branch_having_a_tax_id(self):
        # simulate sub child selection in the switcher
        self.env.user.company_id, self.env.user.company_ids = self.sub_child_company, self.sub_child_company
        self.sub_child_company.vat = "BE0477472701"
        self.sub_child_company._map_eu_taxes()
        another_eu_country_code = (self.env.ref('base.europe').country_ids - self.sub_child_company.country_id)[0].code
        tax_oss = self.env['account.tax'].search([('name', 'ilike', f'%{another_eu_country_code}%')], limit=1)
        self.assertTrue(tax_oss)
        self.assertEqual(tax_oss.company_id, self.sub_child_company)

    def test_country_tag_from_belgium(self):
        """
        This test ensure that xml_id from `account.tax.report.line` in the EU_TAG_MAP are processed correctly by the oss
        tax creation mechanism.
        """
        self.sub_child_company._map_eu_taxes()
        # get an eu country which isn't the current one:
        another_eu_country_code = (self.env.ref('base.europe').country_ids - self.company_data['company'].country_id)[0].code
        tax_oss = self.env['account.tax'].search([('name', 'ilike', f'%"{another_eu_country_code}"%')], limit=1)

        for doc_type, report_expression_xml_id in (
                ("invoice", "l10n_be.tax_report_line_47_tag"),
                ("refund", "l10n_be.tax_report_line_49_tag"),
        ):
            with self.subTest(doc_type=doc_type, report_expression_xml_id=report_expression_xml_id):
                oss_tag_id = tax_oss[f"{doc_type}_repartition_line_ids"]\
                    .filtered(lambda x: x.repartition_type == 'base')\
                    .tag_ids

                expected_tag_id = self.env.ref(report_expression_xml_id)\
                    ._get_matching_tags()\
                    .filtered(lambda t: not t.tax_negate)

                self.assertIn(expected_tag_id, oss_tag_id, f"{doc_type} tag from Belgian CoA not correctly linked")


@tagged('post_install', 'post_install_l10n', '-at_install')
class TestOSSSpain(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('es')
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data['company']._map_eu_taxes()

    def test_country_tag_from_spain(self):
        """
        This test ensure that xml_id from `account.account.tag` in the EU_TAG_MAP are processed correctly by the oss
        tax creation mechanism.
        """
        # get an eu country which isn't the current one:
        another_eu_country_code = (self.env.ref('base.europe').country_ids - self.company_data['company'].country_id)[0].code
        tax_oss = self.env['account.tax'].search([('name', 'ilike', f'%"{another_eu_country_code}"%')], limit=1)

        for doc_type, tag_xml_id in (
                ("invoice", "l10n_es.mod_303_casilla_124_balance"),
        ):
            with self.subTest(doc_type=doc_type, report_line_xml_id=tag_xml_id):
                oss_tag_id = tax_oss[f"{doc_type}_repartition_line_ids"]\
                    .filtered(lambda x: x.repartition_type == 'base')\
                    .tag_ids

                expected_tag_id = self.env.ref(tag_xml_id)\
                    ._get_matching_tags()\
                    .filtered(lambda t: not t.tax_negate)

                self.assertIn(expected_tag_id, oss_tag_id, f"{doc_type} tag from Spanish CoA not correctly linked")


@tagged('post_install', 'post_install_l10n', '-at_install')
class TestOSSUSA(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data['company']._map_eu_taxes()

    def test_no_oss_tax(self):
        # get an eu country which isn't the current one:
        another_eu_country_code = (self.env.ref('base.europe').country_ids - self.company_data['company'].country_id)[0].code
        tax_oss = self.env['account.tax'].search([('name', 'ilike', f'%"{another_eu_country_code}"%')], limit=1)

        self.assertFalse(len(tax_oss), "OSS tax shouldn't be instanced on a US company")

    def test_oss_tax_on_eu_branch(self):
        """Ensure a company outside EU can have an EU branch with an EU VAT and that the OSS feature could be used on those"""
        # This test can only be run if l10n_be is installed
        if not self.env['ir.module.module'].search_count([('name', '=', 'l10n_be'), ('state', '=', 'installed')], limit=1):
            self.skipTest(reason="The belgian CoA is required for this test to be performed but the corresponding localization module isn't installed")

        self.root_company = self.company_data['company']
        self.root_company.child_ids = [Command.create({'name': 'Branch A'})]
        self.cr.precommit.run()  # load the CoA
        self.child_company = self.root_company.child_ids
        self.child_company.child_ids = [Command.create({'name': 'sub Branch B'})]
        self.sub_child_company = self.root_company.child_ids.child_ids
        self.cr.precommit.run()  # load the CoA
        # simulate sub child selection in the switcher
        self.env.user.company_id, self.env.user.company_ids = self.sub_child_company, self.sub_child_company

        foreign_country = self.env.ref('base.be')
        self.sub_child_company.country_id = foreign_country
        self.sub_child_company.account_fiscal_country_id = self.sub_child_company.country_id
        self.sub_child_company.vat = "BE0477472701"

        self.foreign_vat_fpos = self.env["account.fiscal.position"].create({
            "name": "sub branch BE foreign VAT",
            "auto_apply": True,
            "country_id": foreign_country.id,
            "foreign_vat": "BE0477472701",
            "company_id": self.sub_child_company.id,
        })
        self.foreign_vat_fpos.action_create_foreign_taxes()

        self.sub_child_company._map_eu_taxes()

        another_eu_country_code = (self.env.ref('base.europe').country_ids - self.sub_child_company.country_id)[0].code
        tax_oss = self.env['account.tax'].search([('name', 'ilike', f'%{another_eu_country_code}%')], limit=1)

        self.assertTrue(tax_oss)
        self.assertEqual(tax_oss.company_id, self.sub_child_company)
        self.assertEqual(tax_oss.country_id, self.foreign_vat_fpos.country_id)


@tagged('post_install', 'post_install_l10n', '-at_install')
class TestOSSMap(AccountTestInvoicingCommon):

    def test_oss_eu_tag_map(self):
        """ Checks that the xml_id referenced in the map are correct.
        In case of failure display the couple (chart_template_xml_id, tax_report_line_xml_id).
        The test doesn't fail for unreferenced char_template or unreferenced tax_report_line.
        """
        chart_templates = self.env['account.chart.template']._get_chart_template_mapping()
        for chart_template, template_vals in chart_templates.items():
            if self.env.ref(f"base.module_{template_vals['module']}").state != 'installed':
                continue
            oss_tags = EU_TAG_MAP.get(chart_template, {})
            for tax_report_line_xml_id in filter(lambda d: d, oss_tags.values()):
                with self.subTest(chart_template=chart_template, tax_report_line_xml_id=tax_report_line_xml_id):
                    tag = self.env.ref(tax_report_line_xml_id, raise_if_not_found=False)
                    self.assertIsNotNone(tag, f"The following xml_id is incorrect in EU_TAG_MAP.py: {tax_report_line_xml_id}")
