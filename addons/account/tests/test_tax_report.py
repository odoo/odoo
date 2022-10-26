# -*- coding: utf-8 -*-
from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TaxReportTest(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.test_country_1 = cls.env['res.country'].create({
            'name': "The Old World",
            'code': 'YY',
        })

        cls.test_country_2 = cls.env['res.country'].create({
            'name': "The Principality of Zeon",
            'code': 'ZZ',
        })

        cls.tax_report_1 = cls.env['account.report'].create({
            'name': "Tax report 1",
            'country_id': cls.test_country_1.id,
            'column_ids': [
                Command.create({
                    'name': "Balance",
                    'expression_label': 'balance',
                }),
            ],
        })
        cls.tax_report_line_1_1 = cls._create_basic_tax_report_line(cls.tax_report_1, "Line 01", '01')
        cls.tax_report_line_1_2 = cls._create_basic_tax_report_line(cls.tax_report_1, "Line 02", '02')
        cls.tax_report_line_1_3 = cls._create_basic_tax_report_line(cls.tax_report_1, "Line 03", '03')
        cls.tax_report_line_1_4 = cls._create_basic_tax_report_line(cls.tax_report_1, "Line 04", '04')
        cls.tax_report_line_1_5 = cls._create_basic_tax_report_line(cls.tax_report_1, "Line 05", '05')
        cls.tax_report_line_1_55 = cls._create_basic_tax_report_line(cls.tax_report_1, "Line 55", '55')
        cls.tax_report_line_1_6 = cls._create_basic_tax_report_line(cls.tax_report_1, "Line 100", '100')

        cls.tax_report_2 = cls.env['account.report'].create({
            'name': "Tax report 2",
            'country_id': cls.test_country_1.id,
            'column_ids': [
                Command.create({
                    'name': "Balance",
                    'expression_label': 'balance',
                }),
            ],
        })
        cls.tax_report_line_2_1 = cls._create_basic_tax_report_line(cls.tax_report_2, "Line 01, but in report 2", '01')
        cls.tax_report_line_2_2 = cls._create_basic_tax_report_line(cls.tax_report_2, "Line 02, but in report 2", '02')
        cls.tax_report_line_2_42 = cls._create_basic_tax_report_line(cls.tax_report_2, "Line 42", '42')
        cls.tax_report_line_2_6 = cls._create_basic_tax_report_line(cls.tax_report_2, "Line 100, but in report 2", '100')

    @classmethod
    def _create_basic_tax_report_line(cls, report, line_name, tag_name):
        return cls.env['account.report.line'].create({
            'name': f"[{tag_name}] {line_name}",
            'report_id': report.id,
            'sequence': max(report.mapped('line_ids.sequence') or [0]) + 1,
            'expression_ids': [
                Command.create({
                    'label': 'balance',
                    'engine': 'tax_tags',
                    'formula': tag_name,
                }),
            ],
        })

    def _get_tax_tags(self, country, tag_name=None):
        domain = [('country_id', '=', country.id), ('applicability', '=', 'taxes')]
        if tag_name:
            domain.append(('name', 'like', '_' + tag_name ))
        return self.env['account.account.tag'].search(domain)

    def test_create_shared_tags(self):
        self.assertEqual(len(self._get_tax_tags(self.test_country_1, tag_name='01')), 2, "tax_tags expressions created for reports within the same countries using the same formula should create a single pair of tags.")

    def test_add_expression(self):
        """ Adding a tax_tags expression creates new tags.
        """
        tags_before = self._get_tax_tags(self.test_country_1)
        self._create_basic_tax_report_line(self.tax_report_1, "new tax_tags line", 'tournicoti')
        tags_after = self._get_tax_tags(self.test_country_1)

        self.assertEqual(len(tags_after), len(tags_before) + 2, "Two tags should have been created, +tournicoti and -tournicoti.")

    def test_write_single_line_tagname_not_shared(self):
        """ Writing on the formula of a tax_tags expression should overwrite the name of the existing tags if they are not used in other formulas.
        """
        start_tags = self._get_tax_tags(self.test_country_1)
        original_tag_name = self.tax_report_line_1_55.expression_ids.formula
        original_tags = self.tax_report_line_1_55.expression_ids._get_matching_tags()
        self.tax_report_line_1_55.expression_ids.formula = 'Mille sabords !'
        new_tags = self.tax_report_line_1_55.expression_ids._get_matching_tags()

        self.assertEqual(len(self._get_tax_tags(self.test_country_1, tag_name=original_tag_name)), 0, "The original formula of the expression should not correspond to any tag anymore.")
        self.assertEqual(original_tags, new_tags, "The expression should still be linked to the same tags.")
        self.assertEqual(len(self._get_tax_tags(self.test_country_1)), len(start_tags), "No new tag should have been created.")

    def test_write_single_line_tagname_shared(self):
        """ Writing on the formula of a tax_tags expression should create new tags if the formula was shared.
        """
        start_tags = self._get_tax_tags(self.test_country_1)
        original_tag_name = self.tax_report_line_1_1.expression_ids.formula
        original_tags = self.tax_report_line_1_1.expression_ids._get_matching_tags()
        self.tax_report_line_1_1.expression_ids.formula = 'Bulldozers à réaction !'
        new_tags = self.tax_report_line_1_1.expression_ids._get_matching_tags()

        self.assertEqual(self._get_tax_tags(self.test_country_1, tag_name=original_tag_name), original_tags, "The original tags should be unchanged")
        self.assertEqual(len(self._get_tax_tags(self.test_country_1)), len(start_tags) + 2, "A + and - tag should have been created")
        self.assertNotEqual(original_tags, new_tags, "New tags should have been assigned to the expression")

    def test_write_multi_no_change(self):
        """ Rewriting the formula of a tax_tags expression to the same value shouldn't do anything
        """
        tags_before = self._get_tax_tags(self.test_country_1)
        (self.tax_report_line_1_1 + self.tax_report_line_2_1).expression_ids.write({'formula': '01'})
        tags_after = self._get_tax_tags(self.test_country_1)
        self.assertEqual(tags_before, tags_after, "Re-assigning the same formula to a tax_tags expression should keep the same tags.")

    def test_edit_multi_line_tagname_all_different_new(self):
        """ Writing a new, common formula on expressions with distinct formulas should create a single pair of new + and - tag, and not
        delete any of the previously-set tags (those can be archived by the user if he wants to hide them, but this way we don't loose previous
        history in case we need to revert the change).
        """
        lines = self.tax_report_line_1_1 + self.tax_report_line_2_2 + self.tax_report_line_2_42
        tags_before = self._get_tax_tags(self.test_country_1)
        lines.expression_ids.write({'formula': 'crabe'})
        tags_after = self._get_tax_tags(self.test_country_1)

        self.assertEqual(len(tags_before) + 2, len(tags_after), "Only two distinct tags should have been created.")

        line_1_1_tags = self.tax_report_line_1_1.expression_ids._get_matching_tags()
        line_2_2_tags = self.tax_report_line_2_2.expression_ids._get_matching_tags()
        line_2_42_tags = self.tax_report_line_2_42.expression_ids._get_matching_tags()
        self.assertTrue(line_1_1_tags == line_2_2_tags == line_2_42_tags, "The impacted expressions should now all share the same tags.")

    def test_tax_report_change_country(self):
        """ Tests that duplicating and modifying the country of a tax report works as intended
        (countries wanting to use the tax report of another country need that).
        """
        # Copy our first report
        country_1_tags_before_copy = self._get_tax_tags(self.test_country_1)
        copied_report_1 = self.tax_report_1.copy()
        country_1_tags_after_copy = self._get_tax_tags(self.test_country_1)

        self.assertEqual(country_1_tags_before_copy, country_1_tags_after_copy, "Report duplication should not create or remove any tag")

        # Assign another country to one of the copies
        country_2_tags_before_change = self._get_tax_tags(self.test_country_2)
        copied_report_1.country_id = self.test_country_2
        country_2_tags_after_change = self._get_tax_tags(self.test_country_2)
        country_1_tags_after_change = self._get_tax_tags(self.test_country_1)

        self.assertEqual(country_1_tags_after_change, country_1_tags_after_copy, "Modifying the country should not have changed the tags in the original country.")
        self.assertEqual(len(country_2_tags_after_change), len(country_2_tags_before_change) + 2 * len(copied_report_1.line_ids), "Modifying the country should have created a new + and - tag in the new country for each tax_tags expression of the report.")

        for original, copy in zip(self.tax_report_1.line_ids, copied_report_1.line_ids):
            original_tags = original.expression_ids._get_matching_tags()
            copy_tags = copy.expression_ids._get_matching_tags()

            self.assertNotEqual(original_tags, copy_tags, "Tags matched by original and copied expressions should now be different.")
            self.assertEqual(set(original_tags.mapped('name')), set(copy_tags.mapped('name')), "Tags matched by original and copied expression should have the same names.")
            self.assertNotEqual(original_tags.country_id, copy_tags.country_id, "Tags matched by original and copied expression should have different countries.")

        # Directly change the country of a report without copying it first (some of its tags are shared, but not all)
        original_report_2_tags = {line: line.expression_ids._get_matching_tags() for line in self.tax_report_2.line_ids}
        self.tax_report_2.country_id = self.test_country_2
        for line in self.tax_report_2.line_ids:
            line_tags = line.expression_ids._get_matching_tags()

            if line == self.tax_report_line_2_42:
                # This line is the only one of the report not sharing its tags
                self.assertEqual(line_tags, original_report_2_tags[line], "The tax_tags expressions not sharing their tags with any other report should keep the same tags when the country of their report is changed.")
            else:
                # Tags already exist since 'copied_report_1' belongs to 'test_country_2'
                for tag in line_tags:
                    self.assertIn(tag, country_2_tags_after_change, "The tax_tags expressions sharing their tags with other report should not receive new tags since they already exist.")
