from odoo import fields, Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.tools import SQL

from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.addons.stock_account.tests.test_stockvaluationlayer import TestStockValuationCommon

from collections import OrderedDict


@tagged("post_install", "post_install_l10n", "-at_install", "l10n_pe_lib")
class TestPeReportsLib(TestAccountReportsCommon, TestStockValuationCommon):
    @classmethod
    @AccountTestInvoicingCommon.setup_country('pe')
    def setUpClass(cls):
        super().setUpClass()

        # To avoid breaking the constraint _check_l10n_latam_documents because we don't have document number on the moves
        # we set the field l10n_latam_use_document to false
        journals_to_update = cls.env['account.journal'].search([('l10n_latam_use_documents', '=', True)])
        journals_to_update.write({'l10n_latam_use_documents': False})

        cls.company_data['company'].update({
            'country_id': cls.env.ref("base.pe"),
            'vat': "20512528458",
            'l10n_pe_financial_statement_type': '01',
        })
        cls.env.company.partner_id.l10n_latam_identification_type_id = cls.env.ref("l10n_pe.it_RUC")
        cls.partner_a.write({
            "country_id": cls.env.ref("base.pe").id,
            "vat": "20557912879",
            "l10n_latam_identification_type_id": cls.env.ref("l10n_pe.it_RUC").id,
            "ref": "Partner A ref that is longer than 11 characters."
        })
        cls.partner_b.write({
            "country_id": cls.env.ref("base.us").id,
            "vat": "12-3456789",
        })
        cls.product_a = cls.env['product.product'].create({
            'name': 'Product A',
            'default_code': 'AAA',
            'l10n_pe_type_of_existence': '1',
            'unspsc_code_id': cls.env['product.unspsc.code'].search([], limit=1).id,
            'uom_id': cls.env.ref('uom.product_uom_unit').id
        })
        cls.account_base = cls.env['account.account'].search([("code_store", "=", "7012100"), ("company_ids", "=", cls.company_data['company'].id)], limit=1)

        # Generate report options and query elements passed to report element functions, same as what the report button calls
        cls.report = cls.env.ref('account_reports.general_ledger_report')
        cls.handler = cls.env['account.general.ledger.report.handler']
        cls.default_options = cls._generate_options(cls.report, '2024-01-01', '2024-12-31')
        cls.default_options['date']['period_type'] = 'year'

        base_query = cls.report._get_report_query(cls.default_options, 'from_beginning')
        cls.env['account.move.line']._apply_ir_rules(base_query)
        cls.report._init_currency_table(cls.default_options)
        currency_table_query = {
            'join': cls.report._currency_table_aml_join(cls.default_options),
            'balance': cls.report._currency_table_apply_rate(SQL("account_move_line.balance")),
            'debit': cls.report._currency_table_apply_rate(SQL("account_move_line.debit")),
            'credit': cls.report._currency_table_apply_rate(SQL("account_move_line.credit")),
            'residual': cls.report._currency_table_apply_rate(SQL("account_move.amount_residual")),
        }
        cls.report_args = [cls.default_options, currency_table_query]

        cls.move = cls.create_move_on_account_product(cls, cls.account_base)

    def create_move_on_account_product(self, account, move_type='out_invoice', partner=None, amount=100):
        date_invoice = "2024-07-01"
        date_invoice = "2024-07-01"
        move = self.env['account.move'].create({
            'move_type': move_type,
            'partner_id': self.partner_a.id if not partner else partner.id,
            'invoice_date': date_invoice,
            'date': date_invoice,
            'currency_id': self.company_data['currency'].id,
            'ref': '000',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': amount,
                    'account_id': account.id,
                })
            ],
        })
        move.action_post()
        self.env['account.move.line'].flush_model()
        self.env['account.move'].flush_model()
        return move

    def create_move_on_account_payment_term(self, account, move_type='out_invoice', partner=None, amount=100):
        date_invoice = "2024-07-01"
        move = self.env['account.move'].create({
            'move_type': move_type,
            'partner_id': self.partner_a.id if not partner else partner.id,
            'invoice_date': date_invoice,
            'date': date_invoice,
            'currency_id': self.company_data['currency'].id,
            'ref': '000',
            'line_ids': [],
        })
        self.env['account.move.line'].create([
            {
                'move_id': move.id,
                'date': date_invoice,
                'currency_id': self.company_data['currency'].id,
                'account_id': self.company_data['default_account_revenue'].id
                    if move_type == 'out_invoice' else self.company_data['default_account_expense'].id,
                'balance': -amount,
                'company_id': self.company_data['company'].id,
            },
            {
                'move_id': move.id,
                'date': date_invoice,
                'currency_id': self.company_data['currency'].id,
                'account_id': account.id,
                'display_type': 'payment_term',
                'balance': amount,
                'company_id': self.company_data['company'].id,
            }
        ])
        move.action_post()
        self.env['account.move.line'].flush_model()
        self.env['account.move'].flush_model()
        return move

    def test_lib_3_1(self):
        self.account_base.l10n_pe_fs_rubric_ids = self.env.ref('l10n_pe_reports_lib.l10n_pe_fs_rubric_1D0109')
        self.account_base.flush_model()
        report_data = self.handler._l10n_pe_get_lib_3_1_data(*self.report_args)
        self.assertEqual([OrderedDict(data) for data in report_data], [OrderedDict({
            'report_date': '20241231',
            'fs_catalog': '01',
            'fs_rubric': '1D0109',
            'balance': '-100.00',
            'op_status': '1'
        })])

    def test_lib_3_2_cash(self):
        account = self.env['account.account'].search([("code", "=like", "1010000")], limit=1)
        move = self.create_move_on_account_product(account)
        account.flush_model()
        move.flush_model()
        report_data = self.handler._l10n_pe_get_lib_3_2_data(*self.report_args)
        self.assertEqual([OrderedDict(data) for data in report_data], [OrderedDict({
            'report_date': '20241231',
            'account_code': '1010000',
            'bank_code': '99',
            'bank_account': '-',
            'account_currency': 'PEN',
            'sum_debit': '0.00',
            'sum_credit': '100.00',
            'op_status': '1'
        })])

    def test_lib_3_2_bank(self):
        bank = self.env['res.bank'].create({
            'name': "PE Bank A",
            'l10n_pe_edi_code': '00'
        })
        partner_bank = self.env['res.partner.bank'].create({
            'acc_number': '12345678',
            'partner_id': self.env.company.partner_id.id,
            'bank_id': bank.id,
            'currency_id': self.env.ref('base.PEN').id,
            'allow_out_payment': True,
        })
        account = self.env['account.account'].search([("code", "=like", "1051000")], limit=1)
        move = self.create_move_on_account_product(account)
        journal = move.journal_id
        journal.bank_account_id = partner_bank
        journal.default_account_id = account
        bank.flush_model()
        partner_bank.flush_model()
        account.flush_model()
        move.flush_model()
        journal.flush_model()
        report_data = self.handler._l10n_pe_get_lib_3_2_data(*self.report_args)
        self.assertEqual([OrderedDict(data) for data in report_data], [OrderedDict({
            'report_date': '20241231',
            'account_code': '1051000',
            'bank_code': '00',
            'bank_account': '12345678',
            'account_currency': 'PEN',
            'sum_debit': '0.00',
            'sum_credit': '100.00',
            'op_status': '1'
        })])

    def test_lib_3_3(self):
        account = self.env['account.account'].search([("code_store", "=like", "12%")], limit=1)
        move_1 = self.create_move_on_account_payment_term(account)
        account = self.env['account.account'].search([("code_store", "=like", "13%")], limit=1)
        move_2 = self.create_move_on_account_payment_term(account)
        report_data = self.handler._l10n_pe_get_lib_3_3_data(*self.report_args)
        self.assertEqual([OrderedDict(data) for data in report_data], [
            OrderedDict({
                'report_date': '20241231',
                'move_name': 'INV202400001',
                'move_number': ("M%9d" % int(self.move.id)).replace(' ', '0'),
                'id_type_code': '6',
                'partner_vat': '20557912879',
                'partner_name': 'partner_a',
                'move_date': '01/07/2024',
                'move_amount_residual': '118.00',
                'op_status': '1'
            }),
            OrderedDict({
                'report_date': '20241231',
                'move_name': 'INV202400002',
                'move_number': ("M%9d" % int(move_1.id)).replace(' ', '0'),
                'id_type_code': '6',
                'partner_vat': '20557912879',
                'partner_name': 'partner_a',
                'move_date': '01/07/2024',
                'move_amount_residual': '100.00',
                'op_status': '1'
            }),
            OrderedDict({
                'report_date': '20241231',
                'move_name': 'INV202400003',
                'move_number': ("M%9d" % int(move_2.id)).replace(' ', '0'),
                'id_type_code': '6',
                'partner_vat': '20557912879',
                'partner_name': 'partner_a',
                'move_date': '01/07/2024',
                'move_amount_residual': '100.00',
                'op_status': '1'
            })
        ])

    def test_lib_3_4_pe_partner(self):
        account = self.env['account.account'].search([("code_store", "=like", "14%")], limit=1)
        move = self.create_move_on_account_payment_term(account)
        report_data = self.handler._l10n_pe_get_lib_3_4_data(*self.report_args)
        self.assertEqual([OrderedDict(data) for data in report_data], [OrderedDict({
            'report_date': '20241231',
            'move_name': 'INV/2024/00002',
            'move_number': ("M%9d" % int(move.id)).replace(' ', '0'),
            'id_type_code': '6',
            'partner_vat': '20557912879',
            'partner_name': 'partner_a',
            'move_date': '01/07/2024',
            'move_amount_residual': '100.00',
            'op_status': '1'
        })])

    def test_lib_3_4_non_pe_partner(self):
        account = self.env['account.account'].search([("code_store", "=like", "14%")], limit=1)
        move = self.create_move_on_account_payment_term(account, partner=self.partner_b)
        report_data = self.handler._l10n_pe_get_lib_3_4_data(*self.report_args)
        self.assertEqual([OrderedDict(data) for data in report_data], [OrderedDict({
            'report_date': '20241231',
            'move_name': 'INV/2024/00002',
            'move_number': ("M%9d" % int(move.id)).replace(' ', '0'),
            'id_type_code': '0',
            'partner_vat': '12-3456789',
            'partner_name': 'partner_b',
            'move_date': '01/07/2024',
            'move_amount_residual': '100.00',
            'op_status': '1'
        })])

    def test_lib_3_5(self):
        account = self.env['account.account'].search([("code_store", "=like", "16%")], limit=1)
        move_1 = self.create_move_on_account_payment_term(account)
        account = self.env['account.account'].search([("code_store", "=like", "17%")], limit=1)
        move_2 = self.create_move_on_account_payment_term(account)
        report_data = self.handler._l10n_pe_get_lib_3_5_data(*self.report_args)
        self.assertEqual([OrderedDict(data) for data in report_data], [
            OrderedDict({
                'report_date': '20241231',
                'move_name': 'INV202400002',
                'move_number': ("M%9d" % int(move_1.id)).replace(' ', '0'),
                'id_type_code': '6',
                'partner_vat': '20557912879',
                'partner_name': 'partner_a',
                'move_date': '01/07/2024',
                'move_amount_residual': '100.00',
                'op_status': '1'
            }),
            OrderedDict({
                'report_date': '20241231',
                'move_name': 'INV202400003',
                'move_number': ("M%9d" % int(move_2.id)).replace(' ', '0'),
                'id_type_code': '6',
                'partner_vat': '20557912879',
                'partner_name': 'partner_a',
                'move_date': '01/07/2024',
                'move_amount_residual': '100.00',
                'op_status': '1'
            })
        ])

    def test_lib_3_6(self):
        account = self.env['account.account'].search([("code_store", "=like", "19%")], limit=1)
        move = self.create_move_on_account_payment_term(account)
        move.l10n_latam_document_type_id = self.env['l10n_latam.document.type'].search([
            ("code", "=", "01"), ("country_id", "=", self.env.ref('base.pe').id)
        ], limit=1)
        self.env['account.move'].flush_model()
        report_data = self.handler._l10n_pe_get_lib_3_6_data(*self.report_args)
        self.assertEqual([OrderedDict(data) for data in report_data], [OrderedDict({
            'report_date': '20241231',
            'move_name': 'INV/2024/00002',
            'move_number': ("M%9d" % int(move.id)).replace(' ', '0'),
            'id_type_code': '6',
            'partner_vat': '20557912879',
            'partner_name': 'partner_a',
            'move_type_code': '01',
            'serie': 'INV2024',
            'folio': '00002',
            'move_date': '01/07/2024',
            'move_amount_residual': '-100.00',
            'op_status': '1'
        })])

    def test_lib_3_11(self):
        account = self.env['account.account'].search([("code_store", "=like", "41%")], limit=1)
        move = self.create_move_on_account_payment_term(account, move_type='in_invoice', amount=-100)
        report_data = self.handler._l10n_pe_get_lib_3_11_data(*self.report_args)
        self.assertEqual([OrderedDict(data) for data in report_data], [OrderedDict({
            'report_date': '20241231',
            'move_name': 'BILL2024070001',
            'move_number': ("M%9d" % int(move.id)).replace(' ', '0'),
            'account_code': '4111000',
            'id_type_code': '6',
            'partner_vat': '20557912879',
            'partner_ref': 'Partner A r',
            'partner_name': 'partner_a',
            'move_amount_residual': '-100.00',
            'op_status': '1'
        })])

    def test_lib_3_12(self):
        account = self.env['account.account'].search([("code_store", "=like", "42%")], limit=1)
        move_1 = self.create_move_on_account_payment_term(account, move_type='in_invoice', amount=-100.0)
        account = self.env['account.account'].search([("code_store", "=like", "43%")], limit=1)
        move_2 = self.create_move_on_account_payment_term(account, move_type='in_invoice', amount=-100.0)
        report_data = self.handler._l10n_pe_get_lib_3_12_data(*self.report_args)
        self.assertEqual([OrderedDict(data) for data in report_data], [
            OrderedDict({
                'report_date': '20241231',
                'move_name': 'BILL2024070001',
                'move_number': ("M%9d" % int(move_1.id)).replace(' ', '0'),
                'id_type_code': '6',
                'partner_vat': '20557912879',
                'move_date': '01/07/2024',
                'partner_name': 'partner_a',
                'move_amount_residual': '-100.00',
                'op_status': '1'
            }),
            OrderedDict({
                'report_date': '20241231',
                'move_name': 'BILL2024070002',
                'move_number': ("M%9d" % int(move_2.id)).replace(' ', '0'),
                'id_type_code': '6',
                'partner_vat': '20557912879',
                'move_date': '01/07/2024',
                'partner_name': 'partner_a',
                'move_amount_residual': '-100.00',
                'op_status': '1'
            })
        ])

    def test_lib_3_13(self):
        account = self.env['account.account'].search([("code_store", "=like", "46%")], limit=1)
        move = self.create_move_on_account_payment_term(account, move_type='in_invoice', amount=-100.0)
        report_data = self.handler._l10n_pe_get_lib_3_13_data(*self.report_args)
        self.assertEqual([OrderedDict(data) for data in report_data], [OrderedDict({
            'report_date': '20241231',
            'move_name': 'BILL2024070001',
            'move_number': ("M%9d" % int(move.id)).replace(' ', '0'),
            'id_type_code': '6',
            'partner_vat': '20557912879',
            'move_date': '01/07/2024',
            'partner_name': 'partner_a',
            'account_code': '4610000',
            'move_amount_residual': '-100.00',
            'op_status': '1'
        })])

    def test_lib_3_14(self):
        account = self.env['account.account'].search([("code_store", "=like", "47%")], limit=1)
        move = self.create_move_on_account_payment_term(account, move_type='in_invoice', amount=-100.0)
        report_data = self.handler._l10n_pe_get_lib_3_14_data(*self.report_args)
        self.assertEqual([OrderedDict(data) for data in report_data], [OrderedDict({
            'report_date': '20241231',
            'move_name': 'BILL2024070001',
            'move_number': ("M%9d" % int(move.id)).replace(' ', '0'),
            'id_type_code': '6',
            'partner_vat': '20557912879',
            'partner_name': 'partner_a',
            'move_amount_residual': '-100.00',
            'op_status': '1'
        })])

    def test_lib_3_15(self):
        account = self.env['account.account'].search([("code_store", "=like", "37%")], limit=1)
        move = self.create_move_on_account_product(account)
        report_data = self.handler._l10n_pe_get_lib_3_15_data(*self.report_args)
        self.assertEqual([OrderedDict(data) for data in report_data], [OrderedDict({
            'report_date': '20241231',
            'move_name': 'INV/2024/00002',
            'move_number': ("M%9d" % int(move.id)).replace(' ', '0'),
            'move_type_code': '00',
            'serie': 'INV2024',
            'folio': '00002',
            'account_code': '3711000',
            'move_ref': '000',
            'move_amount_residual': '-100.00',
            'additions': '0.00',
            'deductions': '0.00',
            'op_status': '1'
        })])

    def test_lib_3_16_1(self):
        account = self.env['account.account'].search([("code_store", "=like", "50%")], limit=1)
        self.create_move_on_account_product(account)
        report_data = self.handler._l10n_pe_get_lib_3_16_1_data(*self.report_args)
        self.assertEqual([OrderedDict(data) for data in report_data], [OrderedDict({
            'report_date': '20241231',
            'balance_amount': '100.00',
            'nominal_value': '1',
            'balance_number': '100.00',
            'balance_interest': '100.00',
            'op_status': '1'
        })])

    def test_lib_3_16_2(self):
        shareholder = self.env['l10n_pe_reports_lib.shareholder'].create({
            'company_id': self.company_data['company'].id,
            'partner_id': self.partner_a.id,
            'participation_type_code': '01',
            'shares_qty': 1,
            'shares_percentage': 10.0,
            'shares_date': fields.Datetime.from_string("2024-06-01")
        })
        shareholder.flush_model()
        report_data = self.handler._l10n_pe_get_lib_3_16_2_data(*self.report_args)
        self.assertEqual([OrderedDict(data) for data in report_data], [OrderedDict({
            'report_date': '20241231',
            'id_type_code': '6',
            'partner_vat': '20557912879',
            'participation_type_code': '01',
            'partner_name': 'partner_a',
            'shares_qty': 1,
            'shares_percentage': 10.0,
            'op_status': '1'
        })])

    def test_lib_3_17(self):
        report_data = self.handler._l10n_pe_get_lib_3_17_data(*self.report_args)
        self.assertEqual([OrderedDict(data) for data in report_data], [
            OrderedDict({
                'report_date': '20241231',
                'account_code': '1213000',
                'sum_debit_start': '0.00',
                'sum_credit_start': '0.00',
                'sum_debit_during': '118.00',
                'sum_credit_during': '0.00',
                'sum_debit_end': '118.00',
                'sum_credit_end': '0.00',
                'balance_debit_end': '118.00',
                'balance_credit_end': '0.00',
                'transfers_and_cancellations_debit': '0.00',
                'transfers_and_cancellations_credit': '0.00',
                'balance_sheet_accounts_assets': '0.00',
                'balance_sheet_accounts_liabilities': '0.00',
                'result_by_nature_losses': '0.00',
                'result_by_nature_earnings': '0.00',
                'additions': '0.00',
                'deductions': '0.00',
                'op_status': '1'
            }),
            OrderedDict({
                'report_date': '20241231',
                'account_code': '4011100',
                'sum_debit_start': '0.00',
                'sum_credit_start': '0.00',
                'sum_debit_during': '0.00',
                'sum_credit_during': '18.00',
                'sum_debit_end': '0.00',
                'sum_credit_end': '18.00',
                'balance_debit_end': '0.00',
                'balance_credit_end': '18.00',
                'transfers_and_cancellations_debit': '0.00',
                'transfers_and_cancellations_credit': '0.00',
                'balance_sheet_accounts_assets': '0.00',
                'balance_sheet_accounts_liabilities': '0.00',
                'result_by_nature_losses': '0.00',
                'result_by_nature_earnings': '0.00',
                'additions': '0.00',
                'deductions': '0.00',
                'op_status': '1'
            }),
            OrderedDict({
                'report_date': '20241231',
                'account_code': '7012100',
                'sum_debit_start': '0.00',
                'sum_credit_start': '0.00',
                'sum_debit_during': '0.00',
                'sum_credit_during': '100.00',
                'sum_debit_end': '0.00',
                'sum_credit_end': '100.00',
                'balance_debit_end': '0.00',
                'balance_credit_end': '100.00',
                'transfers_and_cancellations_debit': '0.00',
                'transfers_and_cancellations_credit': '0.00',
                'balance_sheet_accounts_assets': '0.00',
                'balance_sheet_accounts_liabilities': '0.00',
                'result_by_nature_losses': '0.00',
                'result_by_nature_earnings': '0.00',
                'additions': '0.00',
                'deductions': '0.00',
                'op_status': '1'
            })
        ])

    def test_lib_3_18(self):
        self.account_base.l10n_pe_fs_rubric_ids = self.env.ref('l10n_pe_reports_lib.l10n_pe_fs_rubric_3D0101')
        self.account_base.flush_model()
        report_data = self.handler._l10n_pe_get_lib_3_18_data(*self.report_args)
        self.assertEqual([OrderedDict(data) for data in report_data], [OrderedDict({
            'report_date': '20241231',
            'fs_catalog': '01',
            'fs_rubric': '3D0101',
            'balance': '-100.00',
            'op_status': '1'
        })])

    def test_lib_3_20(self):
        self.account_base.l10n_pe_fs_rubric_ids = self.env.ref('l10n_pe_reports_lib.l10n_pe_fs_rubric_2D01ST')
        self.account_base.flush_model()
        report_data = self.handler._l10n_pe_get_lib_3_20_data(*self.report_args)
        self.assertEqual([OrderedDict(data) for data in report_data], [OrderedDict({
            'report_date': '20241231',
            'fs_catalog': '01',
            'fs_rubric': '2D01ST',
            'balance': '-100.00',
            'op_status': '1'
        })])

    def test_lib_3_24(self):
        self.account_base.l10n_pe_fs_rubric_ids = self.env.ref('l10n_pe_reports_lib.l10n_pe_fs_rubric_5D0101')
        self.account_base.flush_model()
        report_data = self.handler._l10n_pe_get_lib_3_24_data(*self.report_args)
        self.assertEqual([OrderedDict(data) for data in report_data], [OrderedDict({
            'report_date': '20241231',
            'fs_catalog': '01',
            'fs_rubric': '5D0101',
            'balance': '-100.00',
            'op_status': '1'
        })])

    def test_lib_3_25(self):
        self.account_base.l10n_pe_fs_rubric_ids = self.env.ref('l10n_pe_reports_lib.l10n_pe_fs_rubric_3D0611')
        self.account_base.flush_model()
        report_data = self.handler._l10n_pe_get_lib_3_25_data(*self.report_args)
        self.assertEqual([OrderedDict(data) for data in report_data], [OrderedDict({
            'report_date': '20241231',
            'fs_catalog': '01',
            'fs_rubric': '3D0611',
            'balance': '-100.00',
            'op_status': '1'
        })])

    def test_lib_multiple_fs_codes(self):
        """Testing that linking multiple Financial Statement Rubric objects makes the same account show up on all appropriate reports."""
        self.account_base.l10n_pe_fs_rubric_ids = (
            self.env.ref('l10n_pe_reports_lib.l10n_pe_fs_rubric_1D0109').id,
            self.env.ref('l10n_pe_reports_lib.l10n_pe_fs_rubric_5D0101').id,
            self.env.ref('l10n_pe_reports_lib.l10n_pe_fs_rubric_3D0611').id,
        )
        self.account_base.flush_model()
        report_data = self.handler._l10n_pe_get_lib_3_1_data(*self.report_args) + \
            self.handler._l10n_pe_get_lib_3_20_data(*self.report_args) + \
            self.handler._l10n_pe_get_lib_3_24_data(*self.report_args) + \
            self.handler._l10n_pe_get_lib_3_25_data(*self.report_args)
        self.assertEqual([OrderedDict(data) for data in report_data], [
            OrderedDict({
                'report_date': '20241231',
                'fs_catalog': '01',
                'fs_rubric': '1D0109',
                'balance': '-100.00',
                'op_status': '1'
            }),
            OrderedDict({
                'report_date': '20241231',
                'fs_catalog': '01',
                'fs_rubric': '5D0101',
                'balance': '-100.00',
                'op_status': '1'
            }),
            OrderedDict({
                'report_date': '20241231',
                'fs_catalog': '01',
                'fs_rubric': '3D0611',
                'balance': '-100.00',
                'op_status': '1'
            })
        ])

    def test_lib_multiple_receivable_lines(self):
        """Test that a move containing multiple 'payment_term' lines on different accounts is reported correctly"""
        account_1 = self.env['account.account'].search([("code_store", "=like", "14%")], limit=1)
        account_2 = self.env['account.account'].search([("code_store", "=like", "16%")], limit=1)
        date_invoice = "2024-07-01"
        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': date_invoice,
            'date': date_invoice,
            'currency_id': self.company_data['currency'].id,
            'ref': '000',
            'line_ids': [],
        })
        self.env['account.move.line'].create([
            {
                'move_id': move.id,
                'date': date_invoice,
                'currency_id': self.company_data['currency'].id,
                'account_id': self.company_data['default_account_revenue'].id,
                'balance': -300,
                'company_id': self.company_data['company'].id,
            },
            {
                'move_id': move.id,
                'date': date_invoice,
                'currency_id': self.company_data['currency'].id,
                'account_id': account_1.id,
                'display_type': 'payment_term',
                'balance': 100,
                'company_id': self.company_data['company'].id,
            },
            {
                'move_id': move.id,
                'date': date_invoice,
                'currency_id': self.company_data['currency'].id,
                'account_id': account_1.id,
                'display_type': 'payment_term',
                'balance': 100,
                'company_id': self.company_data['company'].id,
            },
            {
                'move_id': move.id,
                'date': date_invoice,
                'currency_id': self.company_data['currency'].id,
                'account_id': account_2.id,
                'display_type': 'payment_term',
                'balance': 100,
                'company_id': self.company_data['company'].id,
            }
        ])
        move.action_post()
        self.env['account.move.line'].flush_model()
        self.env['account.move'].flush_model()
        report_data = self.handler._l10n_pe_get_lib_3_4_data(*self.report_args) + \
            self.handler._l10n_pe_get_lib_3_5_data(*self.report_args)
        self.assertEqual([OrderedDict(data) for data in report_data], [
            OrderedDict({
                'report_date': '20241231',
                'move_name': 'INV/2024/00002',
                'move_number': ("M%9d" % int(move.id)).replace(' ', '0'),
                'id_type_code': '6',
                'partner_vat': '20557912879',
                'partner_name': 'partner_a',
                'move_date': '01/07/2024',
                'move_amount_residual': '200.00',
                'op_status': '1'
            }),
            OrderedDict({
                'report_date': '20241231',
                'move_name': 'INV202400002',
                'move_number': ("M%9d" % int(move.id)).replace(' ', '0'),
                'id_type_code': '6',
                'partner_vat': '20557912879',
                'partner_name': 'partner_a',
                'move_date': '01/07/2024',
                'move_amount_residual': '100.00',
                'op_status': '1'
            })
        ])
