# Part of Odoo. See LICENSE file for full copyright and licensing details.
from freezegun import freeze_time

from odoo import Command
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestWT003Generation(TestAccountReportsCommon):

    @classmethod
    @TestAccountReportsCommon.setup_country('kh')
    def setUpClass(cls):
        super().setUpClass()
        # Prepare a sample of taxes for the tests.
        cls.ChartTemplate = cls.env['account.chart.template'].with_company(cls.company_data['company'])
        wth_tax_xml_ids = [
            'l10n_kh_tax_purchase_15_wht_s',
            'l10n_kh_tax_purchase_15_wht_i',
            'l10n_kh_tax_purchase_6_wht_fd',
            'l10n_kh_tax_purchase_4_wht_sd',
            'l10n_kh_tax_purchase_10_wht_rental_legal',
            'l10n_kh_tax_purchase_10_wht_rental_physical',
            'l10n_kh_tax_purchase_14_wht_nr_i',
            'l10n_kh_tax_purchase_14_wht_nr_r',
            'l10n_kh_tax_purchase_14_wht_nr_t',
            'l10n_kh_tax_purchase_14_wht_nr_div',
            'l10n_kh_tax_purchase_14_wht_nr_s',
            'l10n_kh_tax_purchase_10_m',
        ]
        cls.wth_tax_set = cls.env['account.tax'].union(*[cls.ChartTemplate.ref(tax_xml_id) for tax_xml_id in wth_tax_xml_ids])

        cls.withholding_sequence = cls.env['ir.sequence'].create({
            'implementation': 'no_gap',
            'name': 'Withholding Sequence',
            'padding': 4,
            'number_increment': 1,
        })
        cls.wth_tax_set.withholding_sequence_id = cls.withholding_sequence
        # VAT
        cls.l10n_kh_tax_purchase_10_m = cls.ChartTemplate.ref('l10n_kh_tax_purchase_10_m')

        cls.company_data['company'].withholding_tax_base_account_id = cls.env['account.account'].create({
            'code': 'WITHB',
            'name': 'Withholding Tax Base Account',
            'reconcile': True,
            'account_type': 'asset_current',
        })

    @freeze_time('2025-01-15')
    def test_wth_on_payment_export(self):
        """ Generate an amount of bills using wth tax on payment, pay them, then test the export. """
        invoice_data = [
            ("in_invoice", self.partner_a, "2025-01-15", [(100 * i, tax)])
            for i, tax in enumerate(self.wth_tax_set, start=1)
        ]

        invoice_vals = []
        for move_type, partner, invoice_date, lines_data in invoice_data:
            invoice_vals.append({
                'move_type': move_type,
                'invoice_date': invoice_date,
                'partner_id': partner.id,
                'invoice_line_ids': [
                    Command.create({
                        'name': 'Test line',
                        'quantity': 1.0,
                        'price_unit': amount,
                        'tax_ids': tax,
                    }) for amount, tax in lines_data
                ],
            })
        invoices = self.env['account.move'].create(invoice_vals)
        invoices.action_post()
        for invoice in invoices:
            wizard = self.env['account.payment.register']\
                .with_context(active_model='account.move', active_ids=invoice.ids)\
                .create({})
            wizard._create_payments()

        self.env['account.move.line'].flush_model(['tax_tag_invert'])  # Required for the tax_tag_invert computation which is used in the sql query for the export.
        report = self.env.ref('l10n_kh.l10n_kh_wt003')
        options = self._generate_options(report, '2025-01-01', '2025-01-31')

        sls = self.env[report.custom_handler_model_name].export_wt_003(options)['file_content']

        expected_row_values = {
            # Headers
            **self._get_header_row_vals(),
            # Sales data
            2: (1,     '01/15/2025', 'BILL/2025/01/0011', 1, '', 'partner_a', '1100.00', '0.00', '0.00',  '0.00',  '0.00',  '0.00',  '0.00',  '0.00',  '0.00',   '0.00',   '0.00',   '154.00'),
            3: (2,     '01/15/2025', 'BILL/2025/01/0010', 1, '', 'partner_a', '1000.00', '0.00', '0.00',  '0.00',  '0.00',  '0.00',  '0.00',  '0.00',  '0.00',   '0.00',   '140.00', '0.00'),
            4: (3,     '01/15/2025', 'BILL/2025/01/0009', 1, '', 'partner_a', '900.00',  '0.00', '0.00',  '0.00',  '0.00',  '0.00',  '0.00',  '0.00',  '0.00',   '126.00', '0.00',   '0.00'),
            5: (4,     '01/15/2025', 'BILL/2025/01/0008', 1, '', 'partner_a', '800.00',  '0.00', '0.00',  '0.00',  '0.00',  '0.00',  '0.00',  '0.00',  '112.00', '0.00',   '0.00',   '0.00'),
            6: (5,     '01/15/2025', 'BILL/2025/01/0007', 1, '', 'partner_a', '700.00',  '0.00', '0.00',  '0.00',  '0.00',  '0.00',  '0.00',  '98.00', '0.00',   '0.00',   '0.00',   '0.00'),
            7: (6,     '01/15/2025', 'BILL/2025/01/0006', 1, '', 'partner_a', '600.00',  '0.00', '0.00',  '0.00',  '0.00',  '0.00',  '60.00', '0.00',  '0.00',   '0.00',   '0.00',   '0.00'),
            8: (7,     '01/15/2025', 'BILL/2025/01/0005', 1, '', 'partner_a', '500.00',  '0.00', '0.00',  '0.00',  '0.00',  '50.00', '0.00',  '0.00',  '0.00',   '0.00',   '0.00',   '0.00'),
            9: (8,     '01/15/2025', 'BILL/2025/01/0004', 1, '', 'partner_a', '400.00',  '0.00', '0.00',  '0.00',  '16.00', '0.00',  '0.00',  '0.00',  '0.00',   '0.00',   '0.00',   '0.00'),
            10: (9,    '01/15/2025', 'BILL/2025/01/0003', 1, '', 'partner_a', '300.00',  '0.00', '0.00',  '18.00', '0.00',  '0.00',  '0.00',  '0.00',  '0.00',   '0.00',   '0.00',   '0.00'),
            11: (10,   '01/15/2025', 'BILL/2025/01/0002', 1, '', 'partner_a', '200.00',  '0.00', '30.00', '0.00',  '0.00',  '0.00',  '0.00',  '0.00',  '0.00',   '0.00',   '0.00',   '0.00'),
            12: (11,   '01/15/2025', 'BILL/2025/01/0001', 1, '', 'partner_a', '100.00',  '15.00', '0.00', '0.00',  '0.00',  '0.00',  '0.00',  '0.00',  '0.00',   '0.00',   '0.00',   '0.00'),
        }
        self._test_xlsx_file(sls, expected_row_values)

    @freeze_time('2025-01-15')
    def test_wth_on_invoice_export(self):
        """ Repeat the previous test, but set the withholding tax to be applied on invoice. """
        invoice_data = [
            ("in_invoice", self.partner_a, "2025-01-15", [(100 * i, tax)])
            for i, tax in enumerate(self.wth_tax_set, start=1)
        ]
        self.wth_tax_set.is_withholding_tax_on_payment = False

        invoice_vals = []
        for move_type, partner, invoice_date, lines_data in invoice_data:
            invoice_vals.append({
                'move_type': move_type,
                'invoice_date': invoice_date,
                'partner_id': partner.id,
                'invoice_line_ids': [
                    Command.create({
                        'name': 'Test line',
                        'quantity': 1.0,
                        'price_unit': amount,
                        'tax_ids': tax,
                    }) for amount, tax in lines_data
                ],
            })
        invoices = self.env['account.move'].create(invoice_vals)
        invoices.action_post()

        self.env['account.move.line'].flush_model()  # Required for the tax_tag_invert computation which is used in the sql query for the export.
        report = self.env.ref('l10n_kh.l10n_kh_wt003')
        options = self._generate_options(report, '2025-01-01', '2025-01-31')

        sls = self.env[report.custom_handler_model_name].export_wt_003(options)['file_content']

        expected_row_values = {
            # Headers
            **self._get_header_row_vals(),
            # Sales data
            2: (1,     '01/15/2025', 'BILL/2025/01/0011', 1, '', 'partner_a', '1100.00', '0.00',  '0.00',  '0.00',  '0.00',  '0.00', '0.00',  '0.00',  '0.00',   '0.00',   '0.00',   '154.00'),
            3: (2,     '01/15/2025', 'BILL/2025/01/0010', 1, '', 'partner_a', '1000.00', '0.00',  '0.00',  '0.00',  '0.00',  '0.00', '0.00',  '0.00',  '0.00',   '0.00',   '140.00', '0.00'),
            4: (3,     '01/15/2025', 'BILL/2025/01/0009', 1, '', 'partner_a', '900.00',  '0.00',  '0.00',  '0.00',  '0.00',  '0.00', '0.00',  '0.00',  '0.00',   '126.00', '0.00',   '0.00'),
            5: (4,     '01/15/2025', 'BILL/2025/01/0008', 1, '', 'partner_a', '800.00',  '0.00',  '0.00',  '0.00',  '0.00',  '0.00', '0.00',  '0.00',  '112.00', '0.00',   '0.00',   '0.00'),
            6: (5,     '01/15/2025', 'BILL/2025/01/0007', 1, '', 'partner_a', '700.00',  '0.00',  '0.00',  '0.00',  '0.00',  '0.00', '0.00',  '98.00', '0.00',   '0.00',   '0.00',   '0.00'),
            7: (6,     '01/15/2025', 'BILL/2025/01/0006', 1, '', 'partner_a', '600.00',  '0.00',  '0.00',  '0.00',  '0.00',  '0.00', '60.00', '0.00',  '0.00',   '0.00',   '0.00',   '0.00'),
            8: (7,     '01/15/2025', 'BILL/2025/01/0005', 1, '', 'partner_a', '500.00',  '0.00',  '0.00',  '0.00',  '0.00',  '50.00', '0.00', '0.00',  '0.00',   '0.00',   '0.00',   '0.00'),
            9: (8,     '01/15/2025', 'BILL/2025/01/0004', 1, '', 'partner_a', '400.00',  '0.00',  '0.00',  '0.00',  '16.00', '0.00', '0.00',  '0.00',  '0.00',   '0.00',   '0.00',   '0.00'),
            10: (9,    '01/15/2025', 'BILL/2025/01/0003', 1, '', 'partner_a', '300.00',  '0.00',  '0.00',  '18.00', '0.00',  '0.00', '0.00',  '0.00',  '0.00',   '0.00',   '0.00',   '0.00'),
            11: (10,   '01/15/2025', 'BILL/2025/01/0002', 1, '', 'partner_a', '200.00',  '0.00',  '30.00', '0.00',  '0.00',  '0.00', '0.00',  '0.00',  '0.00',   '0.00',   '0.00',   '0.00'),
            12: (11,   '01/15/2025', 'BILL/2025/01/0001', 1, '', 'partner_a', '100.00',  '15.00', '0.00',  '0.00',  '0.00',  '0.00', '0.00',  '0.00',  '0.00',   '0.00',   '0.00',   '0.00'),
        }
        self._test_xlsx_file(sls, expected_row_values)

    @freeze_time('2025-01-15')
    def test_partner_type_export(self):
        """ Generate an amount of bills having partners of different fpos, pay them, then test the export. """
        fpos_ntax = self.ChartTemplate.ref('l10n_kh_fiscal_position_non_taxable_person')
        fpos_oc = self.ChartTemplate.ref('l10n_kh_fiscal_position_overseas_company')

        partner_ntax = self.partner_a.copy()
        partner_ntax.write({
            'name': 'Partner NTAX',
            'property_account_position_id': fpos_ntax.id,
        })
        partner_oc = self.partner_a.copy()
        partner_oc.write({
            'name': 'Partner OC',
            'property_account_position_id': fpos_oc.id,
        })

        self.partner_a.vat = '987654312'
        invoice_data = [
            ("in_invoice", self.partner_a, '2025-01-15', [(500, self.wth_tax_set[0])]),
            ("in_invoice", partner_ntax, '2025-01-15', [(500, self.wth_tax_set[0])]),
            ("in_invoice", partner_oc, '2025-01-15', [(500, self.wth_tax_set[0])]),
        ]

        invoice_vals = []
        for move_type, partner, invoice_date, lines_data in invoice_data:
            invoice_vals.append({
                'move_type': move_type,
                'invoice_date': invoice_date,
                'partner_id': partner.id,
                'invoice_line_ids': [
                    Command.create({
                        'name': 'Test line',
                        'quantity': 1.0,
                        'price_unit': amount,
                        'tax_ids': tax,
                    }) for amount, tax in lines_data
                ],
            })
        invoices = self.env['account.move'].create(invoice_vals)
        invoices.action_post()
        for invoice in invoices:
            wizard = self.env['account.payment.register']\
                .with_context(active_model='account.move', active_ids=invoice.ids)\
                .create({})
            wizard._create_payments()

        self.env['account.move.line'].flush_model(['tax_tag_invert'])  # Required for the tax_tag_invert computation which is used in the sql query for the export.
        report = self.env.ref('l10n_kh.l10n_kh_wt003')
        options = self._generate_options(report, '2025-01-01', '2025-01-31')

        sls = self.env[report.custom_handler_model_name].export_wt_003(options)['file_content']

        expected_row_values = {
            # Headers
            **self._get_header_row_vals(),
            # Sales data
            2: (1,    '01/15/2025', 'BILL/2025/01/0003', 3, '',          'Partner OC',   '500.00', '75.00', '0.00', '0.00', '0.00', '0.00', '0.00', '0.00', '0.00', '0.00', '0.00', '0.00'),
            3: (2,    '01/15/2025', 'BILL/2025/01/0002', 2, '',          'Partner NTAX', '500.00', '75.00', '0.00', '0.00', '0.00', '0.00', '0.00', '0.00', '0.00', '0.00', '0.00', '0.00'),
            4: (3,    '01/15/2025', 'BILL/2025/01/0001', 1, '987654312', 'partner_a',    '500.00', '75.00', '0.00', '0.00', '0.00', '0.00', '0.00', '0.00', '0.00', '0.00', '0.00', '0.00'),
        }
        self._test_xlsx_file(sls, expected_row_values)

    @freeze_time('2025-01-15')
    def test_number_gap(self):
        """ Generate an amount of bills with wth and vat, and validate the numbers. """
        invoice_data = [
            ("in_invoice", self.partner_a, '2025-01-15', [(500, self.wth_tax_set[0])]),
            ("in_invoice", self.partner_a, '2025-01-15', [(400, self.wth_tax_set[0]), (250, self.l10n_kh_tax_purchase_10_m)]),
            ("in_invoice", self.partner_a, '2025-01-15', [(300, self.l10n_kh_tax_purchase_10_m)]),  # Will be skipped
            ("in_invoice", self.partner_a, '2025-01-15', [(650, False), (800, self.l10n_kh_tax_purchase_10_m)]),  # Will be skipped
            ("in_invoice", self.partner_a, '2025-01-15', [(700, self.wth_tax_set[0])]),
        ]

        invoice_vals = []
        for move_type, partner, invoice_date, lines_data in invoice_data:
            invoice_vals.append({
                'move_type': move_type,
                'invoice_date': invoice_date,
                'partner_id': partner.id,
                'invoice_line_ids': [
                    Command.create({
                        'name': 'Test line',
                        'quantity': 1.0,
                        'price_unit': amount,
                        'tax_ids': tax,
                    }) for amount, tax in lines_data
                ],
            })
        invoices = self.env['account.move'].create(invoice_vals)
        invoices.action_post()
        for invoice in invoices:
            wizard = self.env['account.payment.register']\
                .with_context(active_model='account.move', active_ids=invoice.ids)\
                .create({})
            wizard._create_payments()

        self.env['account.move.line'].flush_model(['tax_tag_invert'])  # Required for the tax_tag_invert computation which is used in the sql query for the export.
        report = self.env.ref('l10n_kh.l10n_kh_wt003')
        options = self._generate_options(report, '2025-01-01', '2025-01-31')

        sls = self.env[report.custom_handler_model_name].export_wt_003(options)['file_content']

        expected_row_values = {
            # Headers
            **self._get_header_row_vals(),
            # Sales data
            2: (1,    '01/15/2025', 'BILL/2025/01/0005', 1, '', 'partner_a', '700.00', '105.00', '0.00', '0.00', '0.00', '0.00', '0.00', '0.00', '0.00', '0.00', '0.00', '0.00'),
            3: (2,    '01/15/2025', 'BILL/2025/01/0002', 1, '', 'partner_a', '400.00', '60.00',  '0.00', '0.00', '0.00', '0.00', '0.00', '0.00', '0.00', '0.00', '0.00', '0.00'),
            4: (3,    '01/15/2025', 'BILL/2025/01/0001', 1, '', 'partner_a', '500.00', '75.00',  '0.00', '0.00', '0.00', '0.00', '0.00', '0.00', '0.00', '0.00', '0.00', '0.00'),
        }
        self._test_xlsx_file(sls, expected_row_values)

    def _get_header_row_vals(self):
        """ return the header vals to be used in the tests. They are quite long, so this avoids repetition."""
        first_header = (
            "ល.រ\nNo.",
            "កាលបរិច្ឆេទ\nDate",
            "លេខវិក្កយបត្រ\nInvoice Number",
            "អ្នកទទួលប្រាក់\nRecipient",
            "",
            "",
            "ទឹកប្រាក់ត្រូវបើកមុនកាត់ទុក\nAmount",
            "ពន្ធកាត់ទុកលើនិវាសជន\nWithholding Tax on Residents",
            "",
            "",
            "",
            "",
            "",
            "ពន្ធកាត់ទុកលើនិវាសជន\nWithholding Tax on Non-residents",
            "",
            "",
            "",
            "",
        )
        second_header = (
            "",
            "",
            "",
            "ប្រភេទ\nType",
            "លេខសម្គាល់ការចុះបញ្ចីពន្ធដារ\nTIN/BIN/TID",
            "ឈ្មោះ\nName",
            "",
            "ការបំពេញសេវានានា សួយសារចំពោះទ្រព្យ អរូបីភាគកម្មក្នុងធនធានរ៉ែ\nPerformance of Service and \nRoyalty for intangibles, \ninterests in minerals(15%)",
            "ការបង់ការប្រាក់ឱ្យអ្នកជាប់ពន្ធ មិនមែនជាធនាគារ\nPayment of interest to \nnon-bank or saving \ninstitution taxpayers(15%)",
            "ការបង់ការប្រាក់ឱ្យអ្នកជាប់ពន្ធ ដែលមានគណនីសន្សំមានកាលកំណត់\nPayment of interest to \ntaxpayers who have fixed \nterm deposit accounts(6%)",
            "ការបង់ការប្រាក់ឱ្យអ្នកជាប់ពន្ធ ដែលមានគណនីសន្សំគ្មានកាលកំណត់\nPayment of interest to \ntaxpayers who have \nnon-fixed term saving(4%)",
            "ការបង់ថ្លៃឈ្នួលចលនទ្រព្យ និង អចលនទ្រព្យ (នីតិបុគ្គល)\nPayment of rental/lease of \nmovable and immovable \nproperty - Legal Person(10%)",
            "ការបង់ថ្លៃឈ្នួលចលនទ្រព្យ និង អចលនទ្រព្យ (រូបវន្តបុគ្គល)\nPayment of rental/lease of \nmovable and immovable \nproperty - Physical Person(10%)",
            "ការបង់ការប្រាក់\nPayment of Interest(14%)",
            "ការបង់សួយសារ ថ្លៃឈ្នួល ចំនូលផ្សេងៗទាក់ទិន និងការប្រើប្រាស់ទ្រព្យសម្បត្តិ\nPayment of royalty, \nrental/leasing, and \nincome related to \nthe use of property(14%)",
            "ការទូទាត់ថ្លៃសេវាគ្រប់គ្រង និងសេវាបច្ចេកទេសនានា\nPayment of management \nfee and technical \nservices(14%)",
            "ការបង់ភាគលាភ\nPayment of Dividend(14%)",
            "សេវា\nService(14%)",
        )
        return {
            0: first_header,
            1: second_header,
        }
