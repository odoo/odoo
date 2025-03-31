# -*- coding: utf-8 -*-
from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TaxReportTest(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
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

    def _get_tax_tags(self, country, tag_name=None, active_test=True):
        domain = [('country_id', '=', country.id), ('applicability', '=', 'taxes')]
        if tag_name:
            domain.append(('name', '=like', '_' + tag_name))
        return self.env['account.account.tag'].with_context(active_test=active_test).search(domain)

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

    def test_unlink_report_line_tags_used_by_amls(self):
        """
        Deletion of a report line whose tags are still referenced by an aml should archive tags and not delete them.
        """
        tag_name = "55b"
        tax_report_line = self._create_basic_tax_report_line(self.tax_report_1, "Line 55 bis", tag_name)
        test_tag = tax_report_line.expression_ids._get_matching_tags("+")
        self.env['account.tax.group'].create({
            'name': 'Tax group',
            'country_id': self.tax_report_1.country_id.id,
        })
        test_tax = self.env['account.tax'].create({
            'name': "Test tax",
            'amount_type': 'percent',
            'amount': 25,
            'country_id': self.tax_report_1.country_id.id,
            'type_tax_use': 'sale',
            'invoice_repartition_line_ids': [
                (0, 0, {'factor_percent': 100, 'repartition_type': 'base'}),
                (0, 0, {
                    'factor_percent': 100,
                    'repartition_type': 'tax',
                    'tag_ids': [Command.link(test_tag.id)],
                }),
            ],
            'refund_repartition_line_ids': [
                (0, 0, {'factor_percent': 100, 'repartition_type': 'base'}),
                (0, 0, {'factor_percent': 100, 'repartition_type': 'tax'}),
            ],
        })

        # Make sure the fiscal country allows using this tax directly
        self.env.company.account_fiscal_country_id = self.test_country_1

        test_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'date': '1992-12-22',
            'invoice_line_ids': [
                (0, 0, {'quantity': 1, 'price_unit': 42, 'tax_ids': [Command.set([test_tax.id])]}),
            ],
        })
        test_invoice.action_post()

        tax_report_line.unlink()
        tags_after = self._get_tax_tags(self.test_country_1, tag_name=tag_name, active_test=False)
        # only the +tag_name should be kept (and archived), -tag_name should be unlinked
        self.assertEqual(tags_after.mapped('tax_negate'), [False], "Unlinking a tax_tags expression should keep the tag if it was used on move lines, and unlink it otherwise.")
        self.assertEqual(tags_after.mapped('active'), [False], "Unlinking a tax_tags expression should archive the tag if it was used on move lines, and unlink it otherwise.")
        self.assertEqual(len(test_tax.invoice_repartition_line_ids.tag_ids), 0, "After a tag is archived it shouldn't be on tax repartition lines.")

    def test_unlink_report_line_tags_used_by_other_expression(self):
        """
        Deletion of a report line whose tags are still referenced in other expression should not delete nor archive tags.
        """
        tag_name = self.tax_report_line_1_1.expression_ids.formula  # tag "O1" is used in both line 1.1 and line 2.1
        tags_before = self._get_tax_tags(self.test_country_1, tag_name=tag_name, active_test=False)
        tags_archived_before = tags_before.filtered(lambda tag: not tag.active)
        self.tax_report_line_1_1.unlink()
        tags_after = self._get_tax_tags(self.test_country_1, tag_name=tag_name, active_test=False)
        tags_archived_after = tags_after.filtered(lambda tag: not tag.active)
        self.assertEqual(len(tags_after), len(tags_before), "Unlinking a report expression whose tags are used by another expression should not delete them.")
        self.assertEqual(len(tags_archived_after), len(tags_archived_before), "Unlinking a report expression whose tags are used by another expression should not archive them.")

    def test_tag_recreation_archived(self):
        """
        In a situation where we have only one of the two (+ and -) sign that exist
        we want only the missing sign to be re-created if we try to reuse the same tag name.
        (We can get into this state when only one of the signs were used by aml: then we archived it and deleted the complement.)
        """
        tag_name = self.tax_report_line_1_55.expression_ids.formula
        tags_before = self._get_tax_tags(self.test_country_1, tag_name=tag_name, active_test=False)
        tags_before[0].unlink()  # we unlink one and archive the other, doesn't matter which one
        tags_before[1].active = False
        self._create_basic_tax_report_line(self.tax_report_1, "Line 55 bis", tag_name)
        tags_after = self._get_tax_tags(self.test_country_1, tag_name=tag_name, active_test=False)
        self.assertEqual(len(tags_after), 2, "When creating a tax report line with an archived tag and it's complement doesn't exist, it should be re-created.")
        self.assertEqual(tags_after.mapped('name'), ['+' + tag_name, '-' + tag_name], "After creating a tax report line with an archived tag and when its complement doesn't exist, both a negative and a positive tag should be created.")
