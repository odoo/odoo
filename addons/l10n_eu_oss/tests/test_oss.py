# -*- coding: utf-8 -*-

from odoo.addons.l10n_eu_oss.models.eu_tag_map import EU_TAG_MAP
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', 'post_install_l10n', '-at_install')
class OssTemplateTestCase(AccountTestInvoicingCommon):

    @classmethod
    def load_specific_chart_template(cls, chart_template_ref):
        try:
            super().setUpClass(chart_template_ref=chart_template_ref)
        except ValueError as e:
            if e.args[0] == f"External ID not found in the system: {chart_template_ref}":
                cls.skipTest(cls, reason=f"The {chart_template_ref} CoA is required for this testSuite but the corresponding localization module isn't installed")
            else:
                raise e

@tagged('post_install', 'post_install_l10n', '-at_install')
class TestOSSBelgium(OssTemplateTestCase):

    @classmethod
    def setUpClass(cls, chart_template_ref='l10n_be.l10nbe_chart_template'):
        cls.load_specific_chart_template(chart_template_ref)
        cls.company_data['company'].country_id = cls.env.ref('base.be')
        cls.company_data['company']._map_eu_taxes()

    def test_country_tag_from_belgium(self):
        """
        This test ensure that xml_id from `account.tax.report.line` in the EU_TAG_MAP are processed correctly by the oss
        tax creation mechanism.
        """
        # get an eu country which isn't the current one:
        another_eu_country_code = (self.env.ref('base.europe').country_ids - self.company_data['company'].country_id)[0].code
        tax_oss = self.env['account.tax'].search([('name', 'ilike', f'%{another_eu_country_code}%')], limit=1)

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
class TestOSSSpain(OssTemplateTestCase):

    @classmethod
    def setUpClass(cls, chart_template_ref='l10n_es.account_chart_template_common'):
        cls.load_specific_chart_template(chart_template_ref)
        cls.company_data['company'].country_id = cls.env.ref('base.es')
        cls.company_data['company']._map_eu_taxes()

    def test_country_tag_from_spain(self):
        """
        This test ensure that xml_id from `account.account.tag` in the EU_TAG_MAP are processed correctly by the oss
        tax creation mechanism.
        """
        # get an eu country which isn't the current one:
        another_eu_country_code = (self.env.ref('base.europe').country_ids - self.company_data['company'].country_id)[0].code
        tax_oss = self.env['account.tax'].search([('name', 'ilike', f'%{another_eu_country_code}%')], limit=1)

        for doc_type, tag_xml_id in (
                ("invoice", "l10n_es.mod_303_124"),
        ):
            with self.subTest(doc_type=doc_type, report_line_xml_id=tag_xml_id):
                oss_tag_id = tax_oss[f"{doc_type}_repartition_line_ids"]\
                    .filtered(lambda x: x.repartition_type == 'base')\
                    .tag_ids

                expected_tag_id = self.env.ref(tag_xml_id)

                self.assertIn(expected_tag_id, oss_tag_id, f"{doc_type} tag from Spanish CoA not correctly linked")


@tagged('post_install', 'post_install_l10n', '-at_install')
class TestOSSUSA(OssTemplateTestCase):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        cls.load_specific_chart_template(chart_template_ref)
        cls.company_data['company'].country_id = cls.env.ref('base.us')
        cls.company_data['company']._map_eu_taxes()

    def test_no_oss_tax(self):
        # get an eu country which isn't the current one:
        another_eu_country_code = (self.env.ref('base.europe').country_ids - self.company_data['company'].country_id)[0].code
        tax_oss = self.env['account.tax'].search([('name', 'ilike', f'%{another_eu_country_code}%')], limit=1)

        self.assertFalse(len(tax_oss), "OSS tax shouldn't be instanced on a US company")


@tagged('post_install', 'post_install_l10n', '-at_install')
class TestOSSMap(OssTemplateTestCase):

    def test_oss_eu_tag_map(self):
        """ Checks that the xml_id referenced in the map are correct.
        In case of failure display the couple (chart_template_xml_id, tax_report_line_xml_id).
        The test doesn't fail for unreferenced char_template or unreferenced tax_report_line.
        """
        chart_templates = self.env['account.chart.template'].search([])
        for chart_template in chart_templates:
            [chart_template_xml_id] = chart_template.get_external_id().values()
            oss_tags = EU_TAG_MAP.get(chart_template_xml_id, {})
            for tax_report_line_xml_id in filter(lambda d: d, oss_tags.values()):
                with self.subTest(chart_template_xml_id=chart_template_xml_id, tax_report_line_xml_id=tax_report_line_xml_id):
                    tag = self.env.ref(tax_report_line_xml_id, raise_if_not_found=False)
                    self.assertIsNotNone(tag, f"The following xml_id is incorrect in EU_TAG_MAP.py:{tax_report_line_xml_id}")
