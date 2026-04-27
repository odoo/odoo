import os

from freezegun import freeze_time

from odoo.addons.account_reports.tests.common import TestAccountReportsCommon

from odoo import Command, fields
from odoo.tests import tagged
from odoo.tools import misc


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestL10nBgLedgerReports(TestAccountReportsCommon):
    @classmethod
    @TestAccountReportsCommon.setup_country('bg')
    def setUpClass(cls):
        super().setUpClass()

        cls.company.update({
            'vat': 'BG9999999999',
            'l10n_bg_branch_code': '1',
        })

        cls.branch_a = cls.env['res.company'].create({
            'name': 'Bulgarian Branch A',
            'parent_id': cls.company.id,
            'l10n_bg_branch_code': '2',
        })

        cls.env.cr.precommit.run()  # Load COA

        cls.tax_unit = cls.env['account.tax.unit'].create({
            'name': "Tax unit",
            'country_id': cls.company.country_id.id,
            'vat': cls.company.vat,
            'company_ids': [Command.set((cls.company + cls.branch_a).ids)],
            'main_company_id': cls.company.id,
        })

        cls.sales_tags = cls.env['account.account.tag'].search([
            ('name', 'in', ('+11', '+21')),
            ('country_id.code', '=', 'BG'),
        ])

        cls.sale_tax_a = cls.env['account.tax'].create({
            'name': '20% sale',
            'type_tax_use': 'sale',
            'amount_type': 'percent',
            'amount': 20,
            'invoice_repartition_line_ids': [
                Command.create({'tag_ids': [tag.id for tag in cls.sales_tags if tag.display_name == '+11'], 'repartition_type': 'base'}),
                Command.create({'tag_ids': [tag.id for tag in cls.sales_tags if tag.display_name == '+21'], 'repartition_type': 'tax'}),
            ],
        })

        cls.purchase_tags = cls.env['account.account.tag'].search([
            ('name', 'in', ('+31', '+41')),
            ('country_id.code', '=', 'BG'),
        ])

        cls.purchase_tax_a = cls.env['account.tax'].create({
            'name': '20% purchase',
            'type_tax_use': 'purchase',
            'amount_type': 'percent',
            'amount': 20,
            'invoice_repartition_line_ids': [
                Command.create({'tag_ids': [tag.id for tag in cls.purchase_tags if tag.display_name == '+31'], 'repartition_type': 'base'}),
                Command.create({'tag_ids': [tag.id for tag in cls.purchase_tags if tag.display_name == '+41'], 'repartition_type': 'tax'}),
            ],
        })

        cls.moves = cls.env['account.move'].create([
            {
                'move_type': 'out_invoice',
                'partner_id': cls.partner_a.id,
                'invoice_date': fields.Date.from_string('2024-01-01'),
                'journal_id': cls.company_data['default_journal_sale'].id,
                'line_ids': [
                    Command.create({
                        'product_id': cls.product_a.id,
                        'quantity': 2.0,
                        'price_unit': 100.0,
                        'tax_ids': [cls.sale_tax_a.id],
                    })
                ]
            },
            {
                'move_type': 'out_invoice',
                'partner_id': cls.partner_a.id,
                'invoice_date': fields.Date.from_string('2024-01-05'),
                'journal_id': cls.company_data['default_journal_sale'].id,
                'line_ids': [
                    Command.create({
                        'product_id': cls.product_a.id,
                        'quantity': 4.0,
                        'price_unit': 100.0,
                        'tax_ids': [cls.sale_tax_a.id],
                    })
                ]
            },
            {
                'move_type': 'in_invoice',
                'partner_id': cls.partner_a.id,
                'invoice_date': fields.Date.from_string('2024-01-01'),
                'date': fields.Date.from_string('2024-01-01'),
                'journal_id': cls.company_data['default_journal_purchase'].id,
                'l10n_bg_exemption_reason': '01',
                'line_ids': [
                    Command.create({
                        'product_id': cls.product_a.id,
                        'quantity': 2.0,
                        'price_unit': 100.0,
                        'tax_ids': [cls.purchase_tax_a.id],
                    })
                ]
            },
            {
                'move_type': 'in_invoice',
                'partner_id': cls.partner_a.id,
                'invoice_date': fields.Date.from_string('2024-01-05'),
                'date': fields.Date.from_string('2024-01-05'),
                'journal_id': cls.company_data['default_journal_purchase'].id,
                'line_ids': [
                    Command.create({
                        'product_id': cls.product_a.id,
                        'quantity': 4.0,
                        'price_unit': 100.0,
                        'tax_ids': [cls.purchase_tax_a.id],
                    })
                ]
            },
        ])
        cls.moves.action_post()

        cls.tax_report = cls.env.ref('l10n_bg.l10n_bg_tax_report')

    @freeze_time('2024-01-01')
    def test_export_sale_report(self):
        options = self._generate_options(self.tax_report, '2024-01-01', '2024-01-31')
        file_content = self.env[self.tax_report.custom_handler_model_name].export_sale_report_to_txt(options)['file_content']
        expected_content = misc.file_open('l10n_bg_reports_ledger/tests/expected_files/test_sale.txt').read()
        # As the prodagbi.txt contains a lot of white space, we remove them to avoid missing spaces due to IDE auto format
        self.assertEqual(file_content.decode().replace(' ', ''), expected_content.replace(' ', ''))

    @freeze_time('2024-01-01')
    def test_export_purchase_report(self):
        options = self._generate_options(self.tax_report, '2024-01-01', '2024-01-31')
        file_content = self.env[self.tax_report.custom_handler_model_name].export_purchase_report_to_txt(options)['file_content']
        expected_content = misc.file_open('l10n_bg_reports_ledger/tests/expected_files/test_purchase.txt').read()
        # As the pokupki.txt contains a lot of white space, we remove them to avoid missing spaces due to IDE auto format
        self.assertEqual(file_content.decode().replace(' ', ''), expected_content.replace(' ', ''))

    @freeze_time('2024-01-01')
    def test_export_report_with_untracked_tax(self):
        untracked_tag = self.env['account.account.tag'].create({
            'name': 'Untracked Tax Tag',
            'applicability': 'taxes',
            'active': True,
            'country_id': self.company.country_id.id,
        })
        untracked_tax = self.env['account.tax'].create({
            'name': 'Untracked Tax',
            'type_tax_use': 'sale',
            'amount_type': 'percent',
            'amount': 20,
            'invoice_repartition_line_ids': [
                Command.create({'tag_ids': untracked_tag, 'repartition_type': 'base'}),
                Command.create({'tag_ids': untracked_tag, 'repartition_type': 'tax'}),
            ],
        })

        self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': fields.Date.from_string('2024-01-01'),
            'journal_id': self.company_data['default_journal_sale'].id,
            'line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'quantity': 2.0,
                    'price_unit': 100.0,
                    'tax_ids': [untracked_tax.id],
                })
            ]
        })

        options = self._generate_options(self.tax_report, '2024-01-01', '2024-01-31')
        file_content = self.env[self.tax_report.custom_handler_model_name].export_sale_report_to_txt(options)['file_content']
        expected_content = misc.file_open('l10n_bg_reports_ledger/tests/expected_files/test_sale.txt').read()
        self.assertEqual(file_content.decode().replace(' ', ''), expected_content.replace(' ', ''))

    @freeze_time('2024-01-01')
    def test_export_report_with_branches(self):
        self.env['account.move'].with_company(self.branch_a).create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': fields.Date.from_string('2024-01-01'),
            'journal_id': self.company_data['default_journal_sale'].id,
            'line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'quantity': 2.0,
                    'price_unit': 100.0,
                    'tax_ids': [self.sale_tax_a.id],
                })
            ]
        }).action_post()

        options = self._generate_options(
            self.tax_report.with_context(allowed_company_ids=(self.company + self.branch_a).ids),
            '2024-01-01',
            '2024-01-31',
            default_options={'tax_unit': self.tax_unit.id}
        )
        file_content = self.env[self.tax_report.custom_handler_model_name].export_sale_report_to_txt(options)['file_content']
        expected_content = misc.file_open('l10n_bg_reports_ledger/tests/expected_files/test_sale_with_branch.txt').read()
        self.assertEqual(file_content.decode().replace(' ', ''), expected_content.replace(' ', ''))
