# -*- coding: utf-8 -*-
from odoo import Command, fields
from odoo.tests import tagged
from odoo.tools import pycompat
import zipfile
from freezegun import freeze_time
from io import BytesIO
from odoo.addons.account.tests.common import AccountTestInvoicingCommon



@tagged('post_install_l10n', 'post_install', '-at_install')
class TestDatevCSV(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref='de_skr03')

        cls.account_3400 = cls.env['account.account'].search([
            ('code', '=', 3400),
            ('company_id', '=', cls.company_data['company'].id),
        ], limit=1)
        cls.account_4980 = cls.env['account.account'].search([
            ('code', '=', 4980),
            ('company_id', '=', cls.company_data['company'].id),
        ], limit=1)
        cls.account_1500 = cls.env['account.account'].search([
            ('code', '=', 1500),
            ('company_id', '=', cls.company_data['company'].id),
        ], limit=1)
        cls.tax_19 = cls.env['account.tax'].search([
            ('name', '=', '19% I'),
            ('company_id', '=', cls.company_data['company'].id),
        ], limit=1)
        cls.tax_7 = cls.env['account.tax'].search([
            ('name', '=', '7% I'),
            ('company_id', '=', cls.company_data['company'].id),
        ], limit=1)

    def test_datev_in_invoice(self):
        report = self.env.ref('account_reports.general_ledger_report')
        options = report.get_options()
        options['date'].update({
            'date_from': '2020-01-01',
            'date_to': '2020-12-31',
        })

        move = self.env['account.move'].create([{
            'move_type': 'in_invoice',
            'partner_id': self.env['res.partner'].create({'name': 'Res Partner 12'}).id,
            'invoice_date': fields.Date.to_date('2020-12-01'),
            'date': fields.Date.to_date('2020-12-01'),
            'ref': 'Brocken123',
            'invoice_line_ids': [
                (0, None, {
                    'name': 'Line Number 1',
                    'price_unit': 100,
                    'account_id': self.account_3400.id,
                    'tax_ids': [(6, 0, self.tax_19.ids)],
                }),
                (0, None, {
                    'name': 'Line Number 2',
                    'price_unit': 100,
                    'account_id': self.account_3400.id,
                    'tax_ids': [(6, 0, self.tax_19.ids)],
                }),
                (0, None, {
                    'name': 'Line Number 3',
                    'price_unit': 100,
                    'account_id': self.account_4980.id,
                    'tax_ids': [(6, 0, self.tax_19.ids)],
                }),
            ]
        }])
        move.action_post()
        move.line_ids.flush_recordset()

        zf = zipfile.ZipFile(BytesIO(self.env[report.custom_handler_model_name].l10n_de_datev_export_to_zip(options)['file_content']), 'r')
        csv = zf.open('EXTF_accounting_entries.csv')
        reader = pycompat.csv_reader(csv, delimiter=';', quotechar='"', quoting=2)
        data = [[x[0], x[1], x[2], x[6], x[7], x[8], x[9], x[10], x[13]] for x in reader][2:]
        self.addCleanup(zf.close)
        self.assertEqual(3, len(data), "csv should have 3 lines")
        self.assertIn(['119,00', 's', 'EUR', '34000000', str(move.partner_id.id + 700000000),
                       self.tax_19.l10n_de_datev_code, '112', move.name, move.invoice_line_ids[0].name], data)
        self.assertIn(['119,00', 's', 'EUR', '34000000', str(move.partner_id.id + 700000000),
                       self.tax_19.l10n_de_datev_code, '112', move.name, move.invoice_line_ids[1].name], data)
        self.assertIn(['119,00', 's', 'EUR', '49800000', str(move.partner_id.id + 700000000),
                       self.tax_19.l10n_de_datev_code, '112', move.name, move.invoice_line_ids[2].name], data)

    def test_datev_out_invoice(self):
        report = self.env.ref('account_reports.general_ledger_report')
        options = report.get_options()
        options['date'].update({
            'date_from': '2020-01-01',
            'date_to': '2020-12-31',
        })

        move = self.env['account.move'].create([{
            'move_type': 'out_invoice',
            'partner_id': self.env['res.partner'].create({'name': 'Res Partner 12'}).id,
            'invoice_date': fields.Date.to_date('2020-12-01'),
            'invoice_line_ids': [
                (0, None, {
                    'price_unit': 100,
                    'account_id': self.account_4980.id,
                    'tax_ids': [(6, 0, self.tax_19.ids)],
                }),
            ]
        }])
        move.action_post()
        move.line_ids.flush_recordset()

        zf = zipfile.ZipFile(BytesIO(self.env[report.custom_handler_model_name].l10n_de_datev_export_to_zip(options)['file_content']), 'r')
        csv = zf.open('EXTF_accounting_entries.csv')
        reader = pycompat.csv_reader(csv, delimiter=';', quotechar='"', quoting=2)
        data = [[x[0], x[1], x[2], x[6], x[7], x[8], x[9], x[10], x[13]] for x in reader][2:]
        self.addCleanup(zf.close)
        self.assertEqual(1, len(data), "csv should have 1 line")
        self.assertIn(['119,00', 'h', 'EUR', '49800000', str(move.partner_id.id + 100000000),
                      self.tax_19.l10n_de_datev_code, '112', move.name, move.name], data)

    def test_datev_miscellaneous(self):
        report = self.env.ref('account_reports.general_ledger_report')
        options = report.get_options()
        options['date'].update({
            'date_from': '2020-01-01',
            'date_to': '2020-12-31',
        })

        move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2020-12-01',
            'journal_id': self.company_data['default_journal_misc'].id,
            'line_ids': [
                (0, 0, {
                    'debit': 100,
                    'credit': 0,
                    'partner_id': self.partner_a.id,
                    'account_id': self.account_4980.id,
                }),
                (0, 0, {
                    'debit': 0,
                    'credit': 100,
                    'partner_id': self.partner_a.id,
                    'account_id': self.account_3400.id,
                    'tax_ids': [],
                }),
            ]
        })
        move.action_post()
        move.line_ids.flush_recordset()

        zf = zipfile.ZipFile(BytesIO(self.env[report.custom_handler_model_name].l10n_de_datev_export_to_zip(options)['file_content']), 'r')
        csv = zf.open('EXTF_accounting_entries.csv')
        reader = pycompat.csv_reader(csv, delimiter=';', quotechar='"', quoting=2)
        data = [[x[0], x[1], x[2], x[6], x[7], x[9], x[10], x[13]] for x in reader][2:]
        self.addCleanup(zf.close)
        self.assertEqual(1, len(data), "csv should have 1 lines")
        self.assertIn(['100,00', 'h', 'EUR', '34000000', '49800000', '112', move.name, move.name], data)

    def test_datev_out_invoice_payment(self):
        report = self.env.ref('account_reports.general_ledger_report')
        options = report.get_options()
        options['date'].update({
            'date_from': '2020-01-01',
            'date_to': '2020-12-31',
        })

        move = self.env['account.move'].create([{
            'move_type': 'out_invoice',
            'partner_id': self.env['res.partner'].create({'name': 'Res Partner 12'}).id,
            'invoice_date': fields.Date.to_date('2020-12-01'),
            'invoice_line_ids': [
                (0, None, {
                    'price_unit': 100,
                    'account_id': self.account_4980.id,
                    'tax_ids': [(6, 0, self.tax_19.ids)],
                }),
            ]
        }])
        move.action_post()

        pay = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=move.ids).create({
            'payment_date': fields.Date.to_date('2020-12-03'),
        })._create_payments()

        self.env.flush_all()

        debit_account_code = str(self.env.company.account_journal_payment_debit_account_id.code).ljust(8, '0')

        zf = zipfile.ZipFile(BytesIO(self.env[report.custom_handler_model_name].l10n_de_datev_export_to_zip(options)['file_content']), 'r')
        csv = zf.open('EXTF_accounting_entries.csv')
        reader = pycompat.csv_reader(csv, delimiter=';', quotechar='"', quoting=2)
        data = [[x[0], x[1], x[2], x[6], x[7], x[8], x[9], x[10], x[13]] for x in reader][2:]
        self.addCleanup(zf.close)
        self.assertEqual(2, len(data), "csv should have 2 lines")
        self.assertIn(['119,00', 'h', 'EUR', '49800000', str(move.partner_id.id + 100000000),
                       self.tax_19.l10n_de_datev_code, '112', move.name, move.name], data)
        self.assertIn(['119,00', 'h', 'EUR', str(move.partner_id.id + 100000000), debit_account_code, '', '312',
                       pay.name, pay.line_ids[0].name], data)

    def test_datev_out_invoice_payment_same_account_counteraccount(self):
        report = self.env.ref('account_reports.general_ledger_report')
        options = report.get_options()
        options['date'].update({
            'date_from': '2020-01-01',
            'date_to': '2020-12-31',
        })

        move = self.env['account.move'].create([{
            'move_type': 'out_invoice',
            'partner_id': self.env['res.partner'].create({'name': 'Res Partner 12'}).id,
            'invoice_date': fields.Date.to_date('2020-12-01'),
            'invoice_line_ids': [
                (0, None, {
                    'price_unit': 100,
                    'account_id': self.account_4980.id,
                    'tax_ids': [(6, 0, self.tax_19.ids)],
                }),
            ]
        }])
        move.action_post()

        # set counter account = account
        bank_journal = self.company_data['default_journal_bank']
        bank_journal.inbound_payment_method_line_ids.payment_account_id = bank_journal.default_account_id

        pay = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=move.ids).create({
            'payment_date': fields.Date.to_date('2020-12-03'),
        })._create_payments()

        debit_account_code = str(bank_journal.default_account_id.code).ljust(8, '0')

        zf = zipfile.ZipFile(BytesIO(self.env[report.custom_handler_model_name].l10n_de_datev_export_to_zip(options)['file_content']), 'r')
        self.addCleanup(zf.close)
        csv = zf.open('EXTF_accounting_entries.csv')
        reader = pycompat.csv_reader(csv, delimiter=';', quotechar='"', quoting=2)
        data = [[x[0], x[1], x[2], x[6], x[7], x[8], x[9], x[10], x[13]] for x in reader][2:]
        self.assertEqual(2, len(data), "csv should have 2 lines")
        self.assertIn(['119,00', 'h', 'EUR', '49800000', str(move.partner_id.id + 100000000),
                       self.tax_19.l10n_de_datev_code, '112', move.name, move.name], data)
        self.assertIn(['119,00', 'h', 'EUR', str(move.partner_id.id + 100000000), debit_account_code, '', '312',
                       pay.name, pay.line_ids[0].name], data)

    def test_datev_in_invoice_payment(self):
        report = self.env.ref('account_reports.general_ledger_report')
        options = report.get_options()
        options['date'].update({
            'date_from': '2020-01-01',
            'date_to': '2020-12-31',
        })

        move = self.env['account.move'].create([{
            'move_type': 'in_invoice',
            'partner_id': self.env['res.partner'].create({'name': 'Res Partner 12'}).id,
            'invoice_date': fields.Date.to_date('2020-12-01'),
            'date': fields.Date.to_date('2020-12-01'),
            'invoice_line_ids': [
                (0, None, {
                    'price_unit': 100,
                    'account_id': self.account_4980.id,
                    'tax_ids': [(6, 0, self.tax_19.ids)],
                }),
            ]
        }])
        move.action_post()

        pay = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=move.ids).create({
            'payment_date': fields.Date.to_date('2020-12-03'),
        })._create_payments()

        self.env.flush_all()

        credit_account_code = str(self.env.company.account_journal_payment_credit_account_id.code).ljust(8, '0')
        zf = zipfile.ZipFile(BytesIO(self.env[report.custom_handler_model_name].l10n_de_datev_export_to_zip(options)['file_content']), 'r')
        csv = zf.open('EXTF_accounting_entries.csv')
        reader = pycompat.csv_reader(csv, delimiter=';', quotechar='"', quoting=2)
        data = [[x[0], x[1], x[2], x[6], x[7], x[8], x[9], x[10], x[13]] for x in reader][2:]
        self.addCleanup(zf.close)
        self.assertEqual(2, len(data), "csv should have 2 lines")
        self.assertIn(['119,00', 's', 'EUR', '49800000', str(move.partner_id.id + 700000000),
                       self.tax_19.l10n_de_datev_code, '112', move.name, move.name], data)
        self.assertIn(['119,00', 's', 'EUR', str(move.partner_id.id + 700000000), credit_account_code, '', '312',
                       pay.name, pay.line_ids[0].name], data)

    def test_datev_bank_statement(self):
        report = self.env.ref('account_reports.general_ledger_report')
        options = report.get_options()
        options['date'].update({
            'date_from': '2020-01-01',
            'date_to': '2020-12-31',
        })

        statement = self.env['account.bank.statement'].create({
            'balance_end_real': 100.0,
            'line_ids': [
                (0, 0, {
                    'journal_id': self.company_data['default_journal_bank'].id,
                    'payment_ref': 'line1',
                    'amount': 100.0,
                    'date': '2020-01-01',
                }),
            ],
        })
        statement.line_ids.move_id.flush_recordset()

        suspense_account_code = str(self.env.company.account_journal_suspense_account_id.code).ljust(8, '0')
        bank_account_code = str(self.env.company.bank_journal_ids.default_account_id.code).ljust(8, '0')

        zf = zipfile.ZipFile(BytesIO(self.env[report.custom_handler_model_name].l10n_de_datev_export_to_zip(options)['file_content']), 'r')
        csv = zf.open('EXTF_accounting_entries.csv')
        reader = pycompat.csv_reader(csv, delimiter=';', quotechar='"', quoting=2)
        data = [[x[0], x[1], x[2], x[6], x[7], x[9], x[10], x[13]] for x in reader][2:]
        self.addCleanup(zf.close)
        self.assertIn(['100,00', 'h', 'EUR', suspense_account_code, bank_account_code, '101',
                       statement.line_ids[0].name, statement.line_ids[0].payment_ref], data)

    def test_datev_out_invoice_paid(self):
        report = self.env.ref('account_reports.general_ledger_report')
        options = report.get_options()
        options['date'].update({
            'date_from': '2020-01-01',
            'date_to': '2020-12-31',
        })

        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': fields.Date.to_date('2020-12-01'),
            'invoice_line_ids': [(0, 0, {
                'price_unit': 100.0,
                'quantity': 1,
                'account_id': self.company_data['default_account_revenue'].id,
                'tax_ids': [],
            })],
        })
        move.action_post()

        statement = self.env['account.bank.statement'].create({
            'balance_end_real': 100.0,
            'line_ids': [
                (0, 0, {
                    'journal_id': self.company_data['default_journal_bank'].id,
                    'payment_ref': 'line_1',
                    'amount': 100.0,
                    'partner_id': self.partner_a.id,
                    'date': '2020-01-01',
                }),
            ],
        })

        receivable_line = move.line_ids.filtered(lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable'))
        wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=statement.line_ids.id).new({})
        wizard._action_add_new_amls(receivable_line, allow_partial=False)
        wizard._action_validate()

        bank_account_code = str(self.env.company.bank_journal_ids.default_account_id.code).ljust(8, '0')

        self.env.flush_all()
        file_dict = self.env[report.custom_handler_model_name].l10n_de_datev_export_to_zip(options)
        zf = zipfile.ZipFile(BytesIO(file_dict['file_content']), 'r')
        csv = zf.open('EXTF_accounting_entries.csv')
        reader = pycompat.csv_reader(csv, delimiter=';', quotechar='"', quoting=2)
        data = [[x[0], x[1], x[2], x[6], x[7], x[9], x[10], x[13]] for x in reader][2:]
        self.addCleanup(zf.close)
        self.assertEqual(2, len(data), "csv should have 2 lines")
        self.assertIn(['100,00', 'h', 'EUR', str(self.company_data['default_account_revenue'].code).ljust(8, '0'),
                       str(100000000 + move.partner_id.id), '112', move.name, move.name], data)
        self.assertIn(['100,00', 'h', 'EUR', str(100000000 + move.partner_id.id), bank_account_code, '101',
                       statement.line_ids[0].name, statement.line_ids[0].line_ids[1].name], data)
        # 2nd line of the statement because it's the line without the bank account

    def test_datev_out_invoice_with_negative_amounts(self):
        report = self.env.ref('account_reports.general_ledger_report')
        options = report.get_options()
        options['date'].update({
            'date_from': '2020-01-01',
            'date_to': '2020-12-31',
        })

        move = self.env['account.move'].create([{
            'move_type': 'out_invoice',
            'partner_id': self.env['res.partner'].create({'name': 'Res Partner 12'}).id,
            'invoice_date': fields.Date.to_date('2020-12-01'),
            'invoice_line_ids': [
                (0, None, {
                    'name': 'Line Number 1',
                    'price_unit': 1000,
                    'account_id': self.account_4980.id,
                    'tax_ids': [(6, 0, self.tax_19.ids)],
                }),
                (0, None, {
                    'name': 'Line Number 2',
                    'price_unit': -1000,
                    'account_id': self.account_4980.id,
                    'tax_ids': [(6, 0, self.tax_19.ids)],
                }),
                (0, None, {
                    'name': 'Line Number 3',
                    'price_unit': 1000,
                    'quantity': -1,
                    'account_id': self.account_4980.id,
                    'tax_ids': [(6, 0, self.tax_19.ids)],
                }),
                (0, None, {
                    'price_unit': 2000,
                    'account_id': self.account_1500.id,
                    'tax_ids': [(6, 0, self.tax_7.ids)],
                }),
                (0, None, {
                    'price_unit': 3000,
                    'account_id': self.account_3400.id,
                    'tax_ids': [(6, 0, self.tax_19.ids)],
                }),
            ]
        }])
        move.action_post()
        move.line_ids.flush_recordset()

        zf = zipfile.ZipFile(BytesIO(self.env[report.custom_handler_model_name].l10n_de_datev_export_to_zip(options)['file_content']), 'r')
        csv = zf.open('EXTF_accounting_entries.csv')
        reader = pycompat.csv_reader(csv, delimiter=';', quotechar='"', quoting=2)
        data = [[x[0], x[1], x[2], x[6], x[7], x[8], x[9], x[10], x[13]] for x in reader][2:]
        self.addCleanup(zf.close)
        self.assertEqual(5, len(data), "csv should have 5 line")
        self.assertIn(['1190,00', 'h', 'EUR', '49800000', str(move.partner_id.id + 100000000),
                       self.tax_19.l10n_de_datev_code, '112', move.name, move.invoice_line_ids[0].name], data)
        self.assertIn(['1190,00', 's', 'EUR', '49800000', str(move.partner_id.id + 100000000),
                       self.tax_19.l10n_de_datev_code, '112', move.name, move.invoice_line_ids[1].name], data)
        self.assertIn(['1190,00', 's', 'EUR', '49800000', str(move.partner_id.id + 100000000),
                       self.tax_19.l10n_de_datev_code, '112', move.name, move.invoice_line_ids[2].name], data)
        self.assertIn(['2140,00', 'h', 'EUR', '15000000', str(move.partner_id.id + 100000000),
                       self.tax_7.l10n_de_datev_code, '112', move.name, move.name], data)
        self.assertIn(['3570,00', 'h', 'EUR', '34000000', str(move.partner_id.id + 100000000),
                       self.tax_19.l10n_de_datev_code, '112', move.name, move.name], data)

    def test_datev_miscellaneous_several_line_same_account(self):
        """
            Tests that if we have only a single account to the debit, we have a contra-account that is this account, and
            we can put all the credit lines against this account
        """
        report = self.env.ref('account_reports.general_ledger_report')
        options = report.get_options()
        options['date'].update({
            'date_from': '2020-01-01',
            'date_to': '2020-12-31',
        })

        account_1600 = self.env['account.account'].search(
            [('code', '=', 1600), ('company_id', '=', self.company_data['company'].id), ], limit=1)

        move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2020-12-01',
            'journal_id': self.company_data['default_journal_misc'].id,
            'line_ids': [
                (0, 0, {
                    'debit': 100,
                    'credit': 0,
                    'partner_id': self.partner_a.id,
                    'account_id': self.account_4980.id,
                }),
                (0, 0, {
                    'debit': 100,
                    'credit': 0,
                    'partner_id': self.partner_a.id,
                    'account_id': self.account_4980.id,
                }),
                (0, 0, {
                    'debit': 0,
                    'credit': 100,
                    'partner_id': self.partner_a.id,
                    'account_id': account_1600.id,
                }),
                (0, 0, {
                    'debit': 0,
                    'credit': 100,
                    'partner_id': self.partner_a.id,
                    'account_id': self.account_1500.id,
                }),
            ]
        })
        move.action_post()

        zf = zipfile.ZipFile(BytesIO(self.env[report.custom_handler_model_name].l10n_de_datev_export_to_zip(options)['file_content']), 'r')
        csv = zf.open('EXTF_accounting_entries.csv')
        reader = pycompat.csv_reader(csv, delimiter=';', quotechar='"', quoting=2)
        data = [[x[0], x[1], x[2], x[6], x[7], x[9], x[10], x[13]] for x in reader][2:]
        self.addCleanup(zf.close)
        self.assertEqual(2, len(data), "csv should have 2 lines")
        self.assertIn(['100,00', 'h', 'EUR', '16000000', '49800000', '112', move.name, move.name], data)
        self.assertIn(['100,00', 'h', 'EUR', '15000000', '49800000', '112', move.name, move.name], data)

    def test_datev_all_aml_present(self):
        report = self.env.ref('account_reports.general_ledger_report')
        report.load_more_limit = 3
        options = report.get_options()
        options['date'].update({
            'date_from': '2020-01-01',
            'date_to': '2020-12-31',
        })

        for _dummy in range(5):
            move = self.env['account.move'].create([{
                'move_type': 'out_invoice',
                'partner_id': self.env['res.partner'].create({'name': 'Res Partner 12'}).id,
                'invoice_date': fields.Date.to_date('2020-12-01'),
                'invoice_line_ids': [
                    (0, None, {
                        'price_unit': 100,
                        'account_id': self.account_4980.id,
                        'tax_ids': [(6, 0, self.tax_19.ids)],
                    }),
                ]
            }])
            move.action_post()

        self.env.flush_all()
        zf = zipfile.ZipFile(BytesIO(self.env[report.custom_handler_model_name].l10n_de_datev_export_to_zip(options)['file_content']), 'r')
        self.addCleanup(zf.close)
        csv = zf.open('EXTF_accounting_entries.csv')
        reader = pycompat.csv_reader(csv, delimiter=';', quotechar='"', quoting=2)
        data = [line for line in reader]
        self.assertEqual(7, len(data), "csv should have 5 (+2 header) lines")

    def test_datev_vat_export(self):
        report = self.env.ref('account_reports.general_ledger_report')
        options = report.get_options()
        options['date'].update({
            'date_from': '2020-01-01',
            'date_to': '2020-12-31',
        })

        partners_list = [
            {'name': 'partner1', 'vat': 'BE0897223670'},
            {'name': 'partner2'},
            {'name': 'partner3', 'vat': 'US12345671'},
            {'name': 'partner4', 'vat': ''},
        ]
        partners = self.env['res.partner'].create(partners_list)

        move = self.env['account.move'].create([{
                'move_type': 'out_invoice',
                'invoice_date': fields.Date.to_date('2020-12-01'),
                'date': fields.Date.to_date('2020-12-01'),
                'partner_id': partner.id,
                'invoice_line_ids': [
                    Command.create({
                        'name': 'Invoice Line',
                        'price_unit': 100,
                        'account_id': self.account_3400.id,
                        'tax_ids': [Command.set(self.tax_19.ids)],
                    }),
                ]
        } for partner in partners])
        move.action_post()

        with zipfile.ZipFile(BytesIO(self.env[report.custom_handler_model_name].l10n_de_datev_export_to_zip(options)['file_content']), 'r') as zf, \
                zf.open('EXTF_customer_accounts.csv') as csv_file:
            reader = pycompat.csv_reader(csv_file, delimiter=';', quotechar='"', quoting=2)
            # first 2 rows are just headers and needn't be validated
            # first 2 columns are 'account' and 'name' and they are irrelevant to this test
            data = [row[2:10] for row in list(reader)[2:]]
            self.assertEqual(
                data,
                [
                    ["partner1", "", "", "", "1", "", "", "BE0897223670"],
                    ["partner2", "", "", "", "1", "", "", ""],
                    ["partner3", "", "", "", "1", "", "", "US12345671"],
                    ["partner4", "", "", "", "1", "", "", ""],
                ],
            )

    def test_datev_out_invoice_payment_epd_rounding(self):
        ''' Test epd rounding error correction is applied also when exporting
        in datev, in order to avoid a mismatch between stored and exported data
        '''
        report = self.env.ref('account_reports.general_ledger_report')
        options = report.get_options()
        options['date'].update({
            'date_from': '2020-01-01',
            'date_to': '2020-12-31',
        })

        self.early_pay_2_percents_10_days = self.env['account.payment.term'].create({
            'name': '2% discount if paid within 10 days',
            'company_id': self.company_data['company'].id,
            'early_discount': True,
            'discount_percentage': 2,
            'discount_days': 10,
            'line_ids': [Command.create({
                'value': 'percent',
                'value_amount': 100,
                'nb_days': 30,
            })]
        })

        move = self.env['account.move'].create([{
            'move_type': 'out_invoice',
            'partner_id': self.env['res.partner'].create({'name': 'Res Partner 12'}).id,
            'invoice_date': fields.Date.to_date('2020-12-01'),
            'invoice_payment_term_id': self.early_pay_2_percents_10_days.id,
            'invoice_line_ids': [
                Command.create({
                    'quantity': 1.0,
                    'price_unit': 761.76,
                    'tax_ids': [Command.set(self.tax_19.ids)],
                }),
                Command.create({
                    'quantity': 1.0,
                    'price_unit': 100,
                    'tax_ids': [Command.set(self.tax_7.ids)],
                }),
                Command.create({
                    'quantity': 1.0,
                    'price_unit': 200,
                    'tax_ids': [],
                }),
            ]}])

        move.action_post()

        pay = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=move.ids).create({
            'payment_date': fields.Date.to_date('2020-12-03'),
        })._create_payments()

        debit_account_code = str(self.env.company.account_journal_payment_debit_account_id.code).ljust(8, '0')

        moves = move + pay.move_id
        csv = self.env[report.custom_handler_model_name]._l10n_de_datev_get_csv(options, moves)
        reader = pycompat.csv_reader(BytesIO(csv), delimiter=';', quotechar='"', quoting=2)
        data = [[x[0], x[1], x[2], x[6], x[7], x[8], x[9], x[10], x[13]] for x in reader][2:]
        self.assertIn(['18,14', 's', 'EUR', '21300000', debit_account_code, self.tax_19.l10n_de_datev_code, '312', pay.name, pay.line_ids[2].name], data)
        self.assertIn(['2,13', 's', 'EUR', '21300000', debit_account_code, self.tax_7.l10n_de_datev_code, '312', pay.name, pay.line_ids[2].name], data)

    def test_datev_out_bank_payment_epd_rounding(self):
        report = self.env.ref('account_reports.general_ledger_report')
        self.company_data['default_account_tax_purchase'].reconcile = True
        options = report.get_options()
        options['date'].update({
            'date_from': '2020-01-01',
            'date_to': '2020-12-31',
        })

        self.early_pay_2_percents_10_days = self.env['account.payment.term'].create({
            'name': '2% discount if paid within 10 days',
            'company_id': self.company_data['company'].id,
            'early_discount': True,
            'discount_percentage': 2,
            'discount_days': 10,
            'line_ids': [Command.create({
                'value': 'percent',
                'value_amount': 100,
                'nb_days': 30,
            })]
        })

        move_1 = self.env['account.move'].create([{
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': fields.Date.to_date('2020-12-01'),
            'invoice_payment_term_id': self.early_pay_2_percents_10_days.id,
            'invoice_line_ids': [
                Command.create({
                    'quantity': 1.0,
                    'price_unit': 161.10,
                    'tax_ids': [Command.set(self.tax_19.ids)],
                }),
        ]}])
        move_2 = self.env['account.move'].create([{
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': fields.Date.to_date('2020-12-01'),
            'invoice_payment_term_id': self.early_pay_2_percents_10_days.id,
            'invoice_line_ids': [
                Command.create({
                    'quantity': 1.0,
                    'price_unit': 77.50,
                    'tax_ids': [Command.set(self.tax_19.ids)],
                }),
            ]}])

        moves = (move_1 | move_2)
        moves.action_post()

        # Create the payment statement
        statement = self.env['account.bank.statement'].create({
            'name': 'test_statement',
            'line_ids': [
                (0, 0, {
                    'journal_id': self.company_data['default_journal_bank'].id,
                    'date': '2020-12-02',
                    'payment_ref': 'test',
                    'amount': -278.27,
                    'partner_id': self.partner_a.id,
            })]
        })

        wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=statement.line_ids.id).new({})
        wizard._action_add_new_amls(move_1.line_ids.filtered(lambda x: x.account_id.account_type == 'liability_payable'))
        wizard._action_add_new_amls(move_2.line_ids.filtered(lambda x: x.account_id.account_type == 'liability_payable'))
        wizard._action_validate()

        payment_move = statement.line_ids.move_id
        csv = self.env[report.custom_handler_model_name]._l10n_de_datev_get_csv(options, payment_move)
        reader = pycompat.csv_reader(BytesIO(csv), delimiter=';', quotechar='"', quoting=2)
        data = [[x[0], x[1], x[2], x[6], x[7], x[8], x[9], x[10], x[13]] for x in reader][2:]
        self.assertIn(['5,67', 'h', 'EUR', '26700000', '12010000', self.tax_19.l10n_de_datev_code, '212', payment_move.name, "Early Payment Discount"], data)

    @freeze_time('2021-01-02 18:00')
    def test_datev_out_invoice_with_attch(self):
        report = self.env.ref('account_reports.general_ledger_report')
        options = report.get_options()
        options['date'].update({
            'date_from': '2020-01-01',
            'date_to': '2020-12-31',
        })

        move = self.env['account.move'].create([{
            'move_type': 'out_invoice',
            'partner_id': self.env['res.partner'].create({'name': 'Res Partner 12'}).id,
            'invoice_date': fields.Date.to_date('2020-12-01'),
            'invoice_line_ids': [
                Command.create({
                    'price_unit': 100,
                    'account_id': self.account_4980.id,
                    'tax_ids': [Command.set(self.tax_19.ids)],
                }),
            ]
        }])
        move.action_post()
        self.env['account.move.send'] \
            .with_context(active_model='account.move', active_ids=move.ids) \
            .create({}).action_send_and_print()
        move.line_ids.flush_recordset()

        move_guid = move._l10n_de_datev_get_guid()

        with zipfile.ZipFile(BytesIO(self.env[report.custom_handler_model_name].l10_de_datev_export_to_zip_and_attach(options)['file_content']), 'r') as zf:
            xml = zf.open('document.xml').read()
            csv = zf.open('EXTF_accounting_entries.csv')
            reader = pycompat.csv_reader(csv, delimiter=';', quotechar='"', quoting=2)
            csv_data = list(reader)[2]

        self.assertEqual(f'BEDI"{move_guid}"', csv_data[19])

        # xml document is generated during tests because of an override in _hook_invoice_document_after_pdf_report_render
        expected_tree = f"""
        <archive xmlns="http://xml.datev.de/bedi/tps/document/v06.0"
                     xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                     xsi:schemaLocation="http://xml.datev.de/bedi/tps/document/v06.0 Document_v060.xsd"
                     version="6.0"
                     generatingSystem="Odoo">
            <header>
                <date>2021-01-02T18:00:00</date>
            </header>
            <content>
                <document guid="{move_guid}" processID="1" type="2">
                    <extension xsi:type="File" name="INV-2020-00001-1.xml"></extension>
                </document>
                <document guid="{move_guid}" processID="1" type="2">
                    <extension xsi:type="File" name="INV-2020-00001-2.pdf"></extension>
                </document>
            </content>
        </archive>
        """

        self.assertXmlTreeEqual(self.get_xml_tree_from_string(xml), self.get_xml_tree_from_string(expected_tree))
