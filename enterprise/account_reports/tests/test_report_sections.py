# -*- coding: utf-8 -*-
# pylint: disable=C0326

from freezegun import freeze_time
from unittest.mock import patch

from odoo.addons.account.tests.common import AccountTestInvoicingHttpCommon

from odoo import Command
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestReportSections(AccountTestInvoicingHttpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.section_1 = cls.env['account.report'].create({
            'name': "Section 1",
            'filter_journals': True,
            'column_ids': [
                Command.create({
                    'name': "Column 1",
                    'expression_label': 'col1',
                }),
            ],
            'line_ids': [
                Command.create({
                    'name': 'Section 1 line',
                    'expression_ids': [
                        Command.create({
                            'label': 'col1',
                            'engine': 'tax_tags',
                            'formula': 'tag1_1',
                        }),
                    ],
                }),
            ],
        })

        cls.section_2 = cls.env['account.report'].create({
            'name': "Section 2",
            'filter_period_comparison': True,
            'column_ids': [
                Command.create({
                    'name': "Column 1",
                    'expression_label': 'col1',
                }),

                Command.create({
                    'name': "Column 2",
                    'expression_label': 'col2',
                }),
            ],
            'line_ids': [
                Command.create({
                    'name': 'Section 2 line',
                    'expression_ids': [
                        Command.create({
                            'label': 'col1',
                            'engine': 'tax_tags',
                            'formula': 'tag2_1',
                        }),

                        Command.create({
                            'label': 'col2',
                            'engine': 'tax_tags',
                            'formula': 'tag2_2',
                        })
                    ],
                }),
            ],
        })

        cls.composite_report = cls.env['account.report'].create({
            'name': "Test Sections",
            'section_report_ids': [Command.set((cls.section_1 + cls.section_2).ids)],
        })

    def test_sections_options_report_selection_variant(self):
        generic_tax_report = self.env.ref('account.generic_tax_report')
        self.composite_report.root_report_id = generic_tax_report

        # Open root report
        options = generic_tax_report.get_options({})
        self.assertEqual(options['variants_source_id'], generic_tax_report.id, "The root report should be the variants source.")
        self.assertEqual(options['sections_source_id'], generic_tax_report.id, "No variant is selected; the root report should be chosen.")
        self.assertEqual(options['selected_variant_id'], generic_tax_report.id, "No variant is selected; the root report should be chosen.")
        self.assertEqual(options['report_id'], generic_tax_report.id, "No variant is selected; the root report should be chosen.")

        # Select the variant
        options = generic_tax_report.get_options({**options, 'selected_variant_id': self.composite_report.id})
        self.assertEqual(options['variants_source_id'], generic_tax_report.id, "The root report should be the variants source.")
        self.assertEqual(options['sections_source_id'], self.composite_report.id, "The selected variant should be the sections source.")
        self.assertEqual(options['selected_section_id'], self.section_1.id, "Selecting the composite variant should select its first section.")
        self.assertEqual(options['report_id'], self.section_1.id, "Selecting the composite variant should open its first section.")

        # Select the section
        options = generic_tax_report.get_options({**options, 'selected_section_id': self.section_2.id})
        self.assertEqual(options['variants_source_id'], generic_tax_report.id, "The root report should be the variants source.")
        self.assertEqual(options['sections_source_id'], self.composite_report.id, "The selected variant should be the sections source.")
        self.assertEqual(options['selected_section_id'], self.section_2.id, "Section 2 should be selected.")
        self.assertEqual(options['report_id'], self.section_2.id, "Selecting the second section from the first one should open it.")

    def test_sections_options_report_selection_root(self):
        # Open the report
        options = self.composite_report.get_options({})
        self.assertEqual(options['variants_source_id'], self.composite_report.id, "The root report should be the variants source.")
        self.assertEqual(options['sections_source_id'], self.composite_report.id, "The root report should be the sections source.")
        self.assertEqual(options['selected_section_id'], self.section_1.id, "Opening the composite report should select its first section.")
        self.assertEqual(options['report_id'], self.section_1.id, "Opening the composite report should open its first section.")

        # Select the section
        options = self.composite_report.get_options({**options, 'selected_section_id': self.section_2.id})
        self.assertEqual(options['variants_source_id'], self.composite_report.id, "The root report should be the variants source.")
        self.assertEqual(options['sections_source_id'], self.composite_report.id, "The root report should be the sections source.")
        self.assertEqual(options['selected_section_id'], self.section_2.id, "Section 2 should be selected.")
        self.assertEqual(options['report_id'], self.section_2.id, "Selecting the second section from the first one should open it.")

    def test_sections_tour(self):
        def patched_init_options_custom(report, options, previous_options):
            # Emulates a custom handler modifying the export buttons
            if report == self.composite_report:
                options['buttons'][0]['name'] = 'composite_report_custom_button'

        # Setup the reports
        generic_tax_report = self.env.ref('account.generic_tax_report')
        self.composite_report.root_report_id = generic_tax_report
        self.section_1.root_report_id = generic_tax_report # First section is a variant of the root report, to increase test coverage
        # Rewriting the root report recomputes filter_journal ; re-enable it
        self.section_1.filter_journals = True

        with patch.object(type(self.env['account.report']), '_init_options_custom', patched_init_options_custom):
            self.start_tour("/odoo", 'account_reports_sections', login=self.env.user.login)

    def test_exported_xlsx_unique_names(self):
        composite_report = self.env['account.report'].create({
            'name': "Composite",
        })
        for i in range(1, 13):
            self.env['account.report'].create({
                'name': "Comprehensive Monthly Analysis Report Q%d" % i,
                'section_main_report_ids': [Command.set([composite_report.id])],
            })

        composite_report.export_to_xlsx(composite_report.get_options({}))

    def test_composite_report_with_journal_report_pdf_export(self):
        """
        Test that exporting a composite report containing a journal report to PDF
        works correctly.
        """
        journal_report = self.env.ref('account_reports.journal_report')
        composite_with_journal = self.env['account.report'].create({
            'name': 'Test Composite with Journal Report',
            'section_report_ids': [Command.set([journal_report.id])],
        })
        options = composite_with_journal.get_options({})
        result = composite_with_journal.export_to_pdf(options)
        self.assertTrue(result.get('file_content'), 'PDF should be generated successfully')
        self.assertEqual(result.get('file_type'), 'pdf', 'File type should be PDF')
