# -*- coding: utf-8 -*-
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

        cls.tax_report_1 = cls.env['account.tax.report'].create({
            'name': "Tax report 1",
            'country_id': cls.test_country_1.id,
        })

        cls.tax_report_line_1_1 = cls.env['account.tax.report.line'].create({
            'name': "[01] Line 01",
            'tag_name': '01',
            'report_id': cls.tax_report_1.id,
            'sequence': 2,
        })

        cls.tax_report_line_1_2 = cls.env['account.tax.report.line'].create({
            'name': "[01] Line 02",
            'tag_name': '02',
            'report_id': cls.tax_report_1.id,
            'sequence': 3,
        })

        cls.tax_report_line_1_3 = cls.env['account.tax.report.line'].create({
            'name': "[03] Line 03",
            'tag_name': '03',
            'report_id': cls.tax_report_1.id,
            'sequence': 4,
        })

        cls.tax_report_line_1_4 = cls.env['account.tax.report.line'].create({
            'name': "[04] Line 04",
            'report_id': cls.tax_report_1.id,
            'sequence': 5,
        })

        cls.tax_report_line_1_5 = cls.env['account.tax.report.line'].create({
            'name': "[05] Line 05",
            'report_id': cls.tax_report_1.id,
            'sequence': 6,
        })

        cls.tax_report_line_1_55 = cls.env['account.tax.report.line'].create({
            'name': "[55] Line 55",
            'tag_name': '55',
            'report_id': cls.tax_report_1.id,
            'sequence': 7,
        })

        cls.tax_report_line_1_6 = cls.env['account.tax.report.line'].create({
            'name': "[100] Line 100",
            'tag_name': '100',
            'report_id': cls.tax_report_1.id,
            'sequence': 8,
        })

        cls.tax_report_2 = cls.env['account.tax.report'].create({
            'name': "Tax report 2",
            'country_id': cls.test_country_1.id,
        })

        cls.tax_report_line_2_1 = cls.env['account.tax.report.line'].create({
            'name': "[01] Line 01, but in report 2",
            'tag_name': '01',
            'report_id': cls.tax_report_2.id,
            'sequence': 1,
        })

        cls.tax_report_line_2_2 = cls.env['account.tax.report.line'].create({
            'name': "[02] Line 02, but in report 2",
            'report_id': cls.tax_report_2.id,
            'sequence': 2,
        })

        cls.tax_report_line_2_42 = cls.env['account.tax.report.line'].create({
            'name': "[42] Line 42",
            'tag_name': '42',
            'report_id': cls.tax_report_2.id,
            'sequence': 3,
        })

        cls.tax_report_line_2_6 = cls.env['account.tax.report.line'].create({
            'name': "[100] Line 100",
            'tag_name': '100',
            'report_id': cls.tax_report_2.id,
            'sequence': 4,
        })

    def _get_tax_tags(self, tag_name=None, active_test=True):
        domain = [('country_id', '=', self.test_country_1.id), ('applicability', '=', 'taxes')]
        if tag_name:
            domain.append(('name', 'like', '_' + tag_name))
        return self.env['account.account.tag'].with_context(active_test=active_test).search(domain)

    def test_write_add_tagname(self):
        """ Adding a tag_name to a line without any should create new tags.
        """
        tags_before = self._get_tax_tags()
        self.tax_report_line_2_2.tag_name = 'tournicoti'
        tags_after = self._get_tax_tags()

        self.assertEqual(len(tags_after), len(tags_before) + 2, "Two tags should have been created, +tournicoti and -tournicoti.")

    def test_write_single_line_tagname(self):
        """ Writing on the tag_name of a line with a non-null tag_name used in
        no other line should overwrite the name of the existing tags.
        """
        start_tags = self._get_tax_tags()
        original_tag_name = self.tax_report_line_1_55.tag_name
        original_tags = self.tax_report_line_1_55.tag_ids
        self.tax_report_line_1_55.tag_name = 'Mille sabords !'

        self.assertEqual(len(self._get_tax_tags(tag_name=original_tag_name)), 0, "The original tag name of the line should not correspond to any tag anymore.")
        self.assertEqual(original_tags, self.tax_report_line_1_55.tag_ids, "The tax report line should still be linked to the same tags.")
        self.assertEqual(len(self._get_tax_tags()), len(start_tags), "No new tag should have been created.")

    def test_write_single_line_remove_tagname(self):
        """ Setting None as the tag_name of a line with a non-null tag_name used
        in a unique line should delete the tags, also removing all the references to it
        from tax repartition lines and account move lines
        """

        test_tax = self.env['account.tax'].create({
            'name': "Test tax",
            'amount_type': 'percent',
            'amount': 25,
            'type_tax_use': 'sale',
            'country_id': self.tax_report_1.country_id.id,
            'invoice_repartition_line_ids': [
                (0,0, {
                    'factor_percent': 100,
                    'repartition_type': 'base',
                }),

                (0,0, {
                    'factor_percent': 100,
                    'repartition_type': 'tax',
                    'tag_ids': [(6, 0, self.tax_report_line_1_55.tag_ids[0].ids)],
                }),
            ],
            'refund_repartition_line_ids': [
                (0,0, {
                    'factor_percent': 100,
                    'repartition_type': 'base',
                }),

                (0,0, {
                    'factor_percent': 100,
                    'repartition_type': 'tax',
                }),
            ],
        })

        # Make sure the fiscal country allows using this tax directly
        self.env.company.account_fiscal_country_id = self.tax_report_1.country_id.id

        test_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'date': '1992-12-22',
            'invoice_line_ids': [
                (0, 0, {'quantity': 1, 'price_unit': 42, 'tax_ids': [(6, 0, test_tax.ids)]}),
            ],
        })
        test_invoice.action_post()

        self.assertTrue(any(line.tax_tag_ids == self.tax_report_line_1_55.tag_ids[0] for line in test_invoice.line_ids), "The test invoice should contain a tax line with tag 55")
        tag_name_before = self.tax_report_line_1_55.tag_name
        tag_nber_before = len(self._get_tax_tags())
        self.tax_report_line_1_55.tag_name = None
        self.assertFalse(self.tax_report_line_1_55.tag_name, "The tag name for line 55 should now be None")
        self.assertEqual(len(self._get_tax_tags(tag_name=tag_name_before)), 0, "None of the original tags for this line should be left after setting tag_name to None if no other line was using this tag_name.")
        self.assertEqual(len(self._get_tax_tags()), tag_nber_before - 2, "No new tag should have been created, and the two that were assigned to the report line should have been removed.")
        self.assertFalse(test_tax.mapped('invoice_repartition_line_ids.tag_ids'), "There should be no tag left on test tax's repartition lines after the removal of tag 55.")
        self.assertFalse(test_invoice.mapped('line_ids.tax_tag_ids'), "The link between test invoice and tag 55 should have been broken. There should be no tag left on the invoice's lines.")

    def test_write_multi_no_change(self):
        """ Writing the same tag_name as they already use on a set of tax report
        lines with the same tag_name should not do anything.
        """
        tags_before = self._get_tax_tags().ids
        (self.tax_report_line_1_1 + self.tax_report_line_2_1).write({'tag_name': '01'})
        tags_after = self._get_tax_tags().ids
        self.assertEqual(tags_before, tags_after, "Re-assigning the same tag_name should keep the same tags.")

    def test_edit_line_shared_tags(self):
        """ Setting the tag_name of a tax report line sharing its tags with another line
        should edit the tags' name and the tag_name of this other report line, to
        keep consistency.
        """
        original_tag_name = self.tax_report_line_1_1.tag_name
        self.tax_report_line_1_1.tag_name = 'Groucha'
        self.assertEqual(self.tax_report_line_2_1.tag_name, self.tax_report_line_1_1.tag_name, "Modifying the tag name of a tax report line sharing it with another one should also modify the other's.")

    def test_edit_multi_line_tagname_all_different_new(self):
        """ Writing a tag_name on multiple lines with distinct tag_names should
        delete all the former tags and replace them by new ones (also on lines
        sharing tags with them).
        """
        lines = self.tax_report_line_1_1 + self.tax_report_line_2_2 + self.tax_report_line_2_42
        previous_tag_ids = lines.mapped('tag_ids.id')
        lines.write({'tag_name': 'crabe'})
        new_tags = lines.mapped('tag_ids')

        self.assertNotEqual(new_tags.ids, previous_tag_ids, "All the tags should have changed")
        self.assertEqual(len(new_tags), 2, "Only two distinct tags should be assigned to all the lines after writing tag_name on them all")
        surviving_tags = self.env['account.account.tag'].search([('id', 'in', previous_tag_ids)])
        self.assertEqual(len(surviving_tags), 0, "All former tags should have been deleted")
        self.assertEqual(self.tax_report_line_1_1.tag_ids, self.tax_report_line_2_1.tag_ids, "The report lines initially sharing their tag_name with the written-on lines should also have been impacted")

    def test_remove_line_dependency(self):
        """ Setting to None the tag_name of a report line sharing its tags with
        other lines should only impact this line ; the other ones should keep their
        link to the initial tags (their tag_name will hence differ in the end).
        """
        tags_before = self.tax_report_line_1_1.tag_ids
        self.tax_report_line_1_1.tag_name = None
        self.assertEqual(len(self.tax_report_line_1_1.tag_ids), 0, "Setting the tag_name to None should have removed the tags.")
        self.assertEqual(self.tax_report_line_2_1.tag_ids, tags_before, "Setting tag_name to None on a line linked to another one via tag_name should break this link.")

    def test_tax_report_change_country(self):
        """ Tests that duplicating and modifying the country of a tax report works
        as intended (countries wanting to use the tax report of another
        country need that).
        """
        # Copy our first report
        tags_before = self._get_tax_tags().ids
        copied_report_1 = self.tax_report_1.copy()
        copied_report_2 = self.tax_report_1.copy()
        tags_after = self._get_tax_tags().ids
        self.assertEqual(tags_before, tags_after, "Report duplication should not create or remove any tag")

        for original, copy in zip(self.tax_report_1.get_lines_in_hierarchy(), copied_report_1.get_lines_in_hierarchy()):
            self.assertEqual(original.tag_ids, copy.tag_ids, "Copying the lines of a tax report should keep the same tags on lines")

        # Assign another country to one of the copies
        copied_report_1.country_id = self.test_country_2
        for original, copy in zip(self.tax_report_1.get_lines_in_hierarchy(), copied_report_1.get_lines_in_hierarchy()):
            if original.tag_ids or copy.tag_ids:
                self.assertNotEqual(original.tag_ids, copy.tag_ids, "Changing the country of a copied report should create brand new tags for all of its lines")

        for original, copy in zip(self.tax_report_1.get_lines_in_hierarchy(), copied_report_2.get_lines_in_hierarchy()):
            self.assertEqual(original.tag_ids, copy.tag_ids, "Changing the country of a copied report should not impact the other copies or the original report")


        # Direclty change the country of a report without copying it first (some of its tags are shared, but not all)
        original_report_2_tags = {line.id: line.tag_ids.ids for line in self.tax_report_2.get_lines_in_hierarchy()}
        self.tax_report_2.country_id = self.test_country_2
        for line in self.tax_report_2.get_lines_in_hierarchy():
            if line == self.tax_report_line_2_42:
                # This line is the only one of the report not sharing its tags
                self.assertEqual(line.tag_ids.ids, original_report_2_tags[line.id], "The tax report lines not sharing their tags with any other report should keep the same tags when the country of their report is changed")
            elif line.tag_ids or original_report_2_tags[line.id]:
                self.assertNotEqual(line.tag_ids.ids, original_report_2_tags[line.id], "The tax report lines sharing their tags with other report should receive new tags when the country of their report is changed")

    def test_unlink_report_line_tags(self):
        """ Under certain circumstances, unlinking a tax report line should also unlink
        the tags that are linked to it. We test those cases here.
        """
        def check_tags_unlink(tag_name, report_lines, unlinked, error_message):
            report_lines.unlink()
            surviving_tags = self._get_tax_tags(tag_name=tag_name)
            required_len = 0 if unlinked else 2 # 2 for + and - tag
            self.assertEqual(len(surviving_tags), required_len, error_message)

        check_tags_unlink('42', self.tax_report_line_2_42, True, "Unlinking one line not sharing its tags should also unlink them")
        check_tags_unlink('01', self.tax_report_line_1_1, False, "Unlinking one line sharing its tags with others should keep the tags")
        check_tags_unlink('100', self.tax_report_line_1_6 + self.tax_report_line_2_6, True, "Unlinkink all the lines sharing the same tags should also unlink them")

    def test_unlink_report_line_tags_archive(self):
        test_tax = self.env['account.tax'].create({
            'name': "Test tax",
            'amount_type': 'percent',
            'amount': 25,
            'country_id': self.tax_report_1.country_id.id,
            'type_tax_use': 'sale',
            'invoice_repartition_line_ids': [
                (0, 0, {
                    'factor_percent': 100,
                    'repartition_type': 'base',
                }),

                (0, 0, {
                    'factor_percent': 100,
                    'repartition_type': 'tax',
                    'tag_ids': [(6, 0, self.tax_report_line_1_55.tag_ids[0].ids)],
                }),
            ],
            'refund_repartition_line_ids': [
                (0, 0, {
                    'factor_percent': 100,
                    'repartition_type': 'base',
                }),

                (0, 0, {
                    'factor_percent': 100,
                    'repartition_type': 'tax',
                }),
            ],
        })

        # Make sure the fiscal country allows using this tax directly
        self.env.company.account_fiscal_country_id = self.tax_report_1.country_id.id

        test_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'date': '1992-12-22',
            'invoice_line_ids': [
                (0, 0, {'quantity': 1, 'price_unit': 42, 'tax_ids': [(6, 0, test_tax.ids)]}),
            ],
        })
        test_invoice.action_post()

        self.assertTrue(any(line.tax_tag_ids == self.tax_report_line_1_55.tag_ids[0] for line in test_invoice.line_ids),
                        "The test invoice should contain a tax line with tag 55")
        tag_name = self.tax_report_line_1_55.tag_name
        tags_before = self._get_tax_tags(tag_name=tag_name, active_test=False)
        tags_archived_before = tags_before.filtered(lambda tag: not tag.active)
        self.tax_report_line_1_55.unlink()
        tags_after = self._get_tax_tags(tag_name=tag_name, active_test=False)
        tags_archived_after = tags_after.filtered(lambda tag: not tag.active)
        # only the + tag will survive, - will be deleted as it's not on a move.line
        self.assertEqual(len(tags_after), len(tags_before) - 1, "Unlinking a report line whose tags are used on move lines should not delete them.")
        self.assertEqual(len(tags_archived_after), len(tags_archived_before) + 1, "Unlinking a report line whose tags are used on move lines should archive them.")
