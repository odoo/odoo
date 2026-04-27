from odoo import Command, fields
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.exceptions import UserError
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestLibroDiarioXLSX(TestAccountReportsCommon):
    @classmethod
    @TestAccountReportsCommon.setup_country('es')
    def setUpClass(cls):
        super().setUpClass()

        cls.report = cls.env.ref('account_reports.general_ledger_report')

        tax_repartition_line = cls.company_data['default_tax_sale'].refund_repartition_line_ids\
            .filtered(lambda line: line.repartition_type == 'tax')
        cls.move_1 = cls.env['account.move'].create({
            'company_id': cls.company_data['company'].id,
            'move_type': 'entry',
            'date': fields.Date.from_string('2020-12-10'),
            'line_ids': [
                Command.create({
                    'name': 'revenue line 1a',
                    'account_id': cls.company_data['default_account_revenue'].id,
                    'debit': 500.0,
                }),
                Command.create({
                    'name': 'revenue line 1b',
                    'account_id': cls.company_data['default_account_revenue'].id,
                    'debit': 1000.0,
                    'tax_ids': [Command.set(cls.company_data['default_tax_sale'].ids)],
                }),
                Command.create({
                    'name': 'tax line 1',
                    'account_id': cls.company_data['default_account_tax_sale'].id,
                    'debit': 150.0,
                    'tax_repartition_line_id': tax_repartition_line.id,
                }),
                Command.create({
                    'name': 'counterpart line 1',
                    'account_id': cls.company_data['default_account_expense'].id,
                    'credit': 1650.0,
                }),
            ]
        })
        cls.move_2 = cls.env['account.move'].create({
            'company_id': cls.company_data['company'].id,
            'move_type': 'entry',
            'date': fields.Date.from_string('2020-12-01'),
            'line_ids': [
                Command.create({
                    'name': 'revenue line 2',
                    'account_id': cls.company_data['default_account_revenue'].id,
                    'debit': 500.0,
                }),
                Command.create({
                    'name': 'tax line 2',
                    'account_id': cls.company_data['default_account_tax_sale'].id,
                    'debit': 150.0,
                    'tax_repartition_line_id': tax_repartition_line.id,
                }),
                Command.create({
                    'name': 'counterpart line 2',
                    'account_id': cls.company_data['default_account_expense'].id,
                    'credit': 650.0,
                }),
            ]
        })
        (cls.move_1 + cls.move_2).action_post()

    def test_libro_diario_non_es_error(self):
        non_es_company = self.env['res.company'].search([('partner_id.country_code', '!=', 'ES')], limit=1)
        self.env.company = self.env.companies = non_es_company

        options = self._generate_options(self.report, '2020-12-01', '2020-12-31')

        with self.assertRaisesRegex(
            UserError,
            'This report export is only available for ES companies.'
        ):
            self.env[self.report.custom_handler_model_name].es_libro_diario_export_to_xlsx(options)

    def test_libro_diario_export(self):
        """ Test that the export of the Libro Diario completes without failure and that the button to export it is present. """

        options = self._generate_options(self.report, '2020-12-01', '2020-12-31')
        libro_button = [button for button in options['buttons'] if button.get('action_param') == 'es_libro_diario_export_to_xlsx']
        self.assertEqual(len(libro_button), 1)
        results = self.env[self.report.custom_handler_model_name].es_libro_diario_export_to_xlsx(options)
        self.assertEqual(results['file_name'], 'libro_diario.xlsx')

    def test_libro_diario_line_data(self):
        # Activate single company mode
        self.env.company = self.env.companies = self.company_data['company']

        self.company.vat = 'ESA12345674'

        options = self._generate_options(self.report, '2020-12-01', '2020-12-31')
        header, data = self.env[self.report.custom_handler_model_name]._es_libro_diario_xlsx_get_data(options)

        self.assertListEqual(header, [
            ['company_1_data', 'ESA12345674'],
            ['General Ledger - 2020-12-01_2020-12-31']
        ])

        self.assertListEqual(data, [
            ['Entry', 'Line',       'Date',        'Description',          'Document', 'Account Code',                     'Account Name', 'Debit', 'Credit'],
            [      1,      1, '01/12/2020',     'revenue line 2', 'MISC/2020/12/0001',       '700000',           'Merchandise sold Spain',   500.0,      0.0],
            [      1,      2, '01/12/2020',         'tax line 2', 'MISC/2020/12/0001',       '477000', 'Taxation authorities, output VAT',   150.0,      0.0],
            [      1,      3, '01/12/2020', 'counterpart line 2', 'MISC/2020/12/0001',       '600000',            'Merchandise purchased',     0.0,    650.0],
            [      2,      1, '10/12/2020',    'revenue line 1a', 'MISC/2020/12/0002',       '700000',           'Merchandise sold Spain',   500.0,      0.0],
            [      2,      2, '10/12/2020',    'revenue line 1b', 'MISC/2020/12/0002',       '700000',           'Merchandise sold Spain',  1000.0,      0.0],
            [      2,      3, '10/12/2020',         'tax line 1', 'MISC/2020/12/0002',       '477000', 'Taxation authorities, output VAT',   150.0,      0.0],
            [      2,      4, '10/12/2020', 'counterpart line 1', 'MISC/2020/12/0002',       '600000',            'Merchandise purchased',     0.0,   1650.0],
        ])
