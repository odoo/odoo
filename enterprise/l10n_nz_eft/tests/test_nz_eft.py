# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64

from odoo import Command, fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.tests import tagged
from odoo.tools import format_date


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestNZEFT(AccountTestInvoicingCommon):

    @classmethod
    @TestAccountReportsCommon.setup_country('nz')
    def setUpClass(cls):
        super().setUpClass()

        cls.env.user.groups_id |= cls.env.ref('account.group_validate_bank_account')

        # -- Setup Common -- #

        cls.partner_a.bank_ids = [Command.create({
            'acc_number': '01-12645-1349786-054',
            'acc_type': 'bank',
            'allow_out_payment': True,
        })]

        cls.partner_b.bank_ids = [Command.create({
            'acc_number': '05-98756-6794815-038',
            'acc_type': 'bank',
            'allow_out_payment': True,
        })]

        cls.company_data['company'].partner_id.bank_ids = [Command.create({
            'acc_number': '01-123654-4532687-012',
            'acc_type': 'bank',
            'allow_out_payment': True,
        })]

        cls.company_data['default_journal_bank'].set_bank_account('02-13469-1345768-042')
        cls.company_data['default_journal_bank'].bank_account_id.allow_out_payment = True

        # -- Setup Inbound Batch -- #

        inbound_payment_method_line = cls.company_data['default_journal_bank'].inbound_payment_method_line_ids.filtered(
            lambda line: line.code == 'l10n_nz_eft_in'
        )[0]

        inbound_base_data = {
            'payment_type': 'inbound',
            'journal_id': cls.company_data['default_journal_bank'].id,
            'currency_id': cls.company_data['currency'].id,
            'company_id': cls.company_data['company'].id,
            'payment_method_line_id': inbound_payment_method_line.id,
        }

        cls.inbound_payments = cls.env['account.payment'].create([{
            'amount': 250,
            'partner_id': cls.partner_a.id,
            'memo': 'Payment for noodles,',
            'date': '2024-05-23',
            'l10n_nz_dd_account_id': cls.partner_a.bank_ids[0].id,
            'l10n_nz_payer_particulars': '#123#',
            'l10n_nz_payer_code': '#234#',
            'l10n_nz_payee_particulars': '#345#',
            'l10n_nz_payee_code': '#456#',
            **inbound_base_data,
        }, {
            'amount': 150,
            'partner_id': cls.partner_b.id,
            'memo': 'Payment for boat,',
            'date': '2024-05-24',
            'l10n_nz_dd_account_id': cls.partner_a.bank_ids[0].id,
            'l10n_nz_payer_particulars': '#123#',
            'l10n_nz_payer_code': '#234#',
            'l10n_nz_payee_particulars': '#345#',
            'l10n_nz_payee_code': '#456#',
            **inbound_base_data,
        }])
        cls.inbound_payments.action_post()
        inbound_batch_payment_action = cls.inbound_payments.create_batch_payment()
        cls.inbound_batch = cls.env['account.batch.payment'].browse(inbound_batch_payment_action.get('res_id'))
        cls.inbound_batch.write({
            'l10n_nz_batch_reference': 'Payments',
            'l10n_nz_batch_particulars': '111/222',
            'l10n_nz_dd_info': '9965423',
            'date': '2024-05-25',
        })

        # -- Setup Outbound Batch -- #

        outbound_payment_method_line = cls.company_data['default_journal_bank'].outbound_payment_method_line_ids.filtered(
            lambda line: line.code == 'l10n_nz_eft_out'
        )[0]

        outbound_base_data = {
            'payment_type': 'outbound',
            'journal_id': cls.company_data['default_journal_bank'].id,
            'currency_id': cls.company_data['currency'].id,
            'company_id': cls.company_data['company'].id,
            'payment_method_line_id': outbound_payment_method_line.id,
        }

        cls.outbound_payments = cls.env['account.payment'].create([{
            'amount': 250,
            'partner_id': cls.partner_a.id,
            'memo': 'Purchase of cups,',
            'date': '2024-05-23',
            'l10n_nz_payer_particulars': '#123#',
            'l10n_nz_payer_code': '#234#',
            'l10n_nz_payee_particulars': '#345#',
            'l10n_nz_payee_code': '#456#',
            **outbound_base_data,
        }, {
            'amount': 150,
            'partner_id': cls.partner_b.id,
            'memo': 'Purchase of water bottles,',
            'date': '2024-05-24',
            'l10n_nz_payer_particulars': '#123#',
            'l10n_nz_payer_code': '#234#',
            'l10n_nz_payee_particulars': '#345#',
            'l10n_nz_payee_code': '#456#',
            **outbound_base_data,
        }])
        cls.outbound_payments.action_post()
        outbound_batch_payment_action = cls.outbound_payments.create_batch_payment()
        cls.outbound_batch = cls.env['account.batch.payment'].browse(outbound_batch_payment_action.get('res_id'))
        cls.outbound_batch.write({
            'l10n_nz_batch_reference': 'Purchases',
            'l10n_nz_batch_particulars': '333/666',
            'date': '2024-05-25',
        })

    def test_export_anz(self):
        """ Test exporting the file for ANZ """
        # 1 - Inbound batch
        self.inbound_batch.write({
            'l10n_nz_file_format': 'anz',
            'l10n_nz_dishonour_account_id': self.company_data['company'].partner_id.bank_ids[0],  # here because only ANZ requires that.
        })
        # To be exact it's the date at which the file is generated, so today.
        batch_creation_date = format_date(self.env, fields.Date.context_today(self.inbound_batch), date_format='YYYYMMdd')
        self._test_file('inbound', [
            f'1,D,20240525,,{batch_creation_date},02134691345768042,9965423,S,011236544532687012,BATCH/IN/202,111/222,,Payments,,,',
            '2,01126451349786054,00,25000,partner_a,#123#,#234#,for noodles,#345#,#456#,for noodles,,,',
            '2,01126451349786054,00,15000,partner_a,#123#,#234#,ent for boat,#345#,#456#,ent for boat,,,',
            '3,40000,,2,25282699572,,,',
        ])

        # 2 - Outbound batch
        self.outbound_batch.write({
            'l10n_nz_file_format': 'anz',
            'l10n_nz_dishonour_account_id': self.company_data['company'].partner_id.bank_ids[0],  # here because only ANZ requires that.
        })
        self._test_file('outbound', [
            f'1,C,20240525,,{batch_creation_date},02134691345768042,,S,011236544532687012,BATCH/OUT/20,333/666,,Purchases,,,',
            '2,01126451349786054,50,25000,partner_a,#345#,#456#,hase of cups,#123#,#234#,hase of cups,,,',
            '2,05987566794815038,50,15000,partner_b,#345#,#456#,ater bottles,#123#,#234#,ater bottles,,,',
            '3,,40000,2,11398144601,,,',
        ])

    def test_export_bnz(self):
        """ Test exporting the file for BNZ """
        # 1 - Inbound batch
        self.inbound_batch.l10n_nz_file_format = 'bnz'
        batch_creation_date = format_date(self.env, fields.Date.context_today(self.inbound_batch), date_format='YYMMdd')
        self._test_file('inbound', [
            f'1,9965423,,,02134691345768042,6,240525,{batch_creation_date},',
            '2,01126451349786054,00,25000,partner_a,for noodles,#234#,,#123#,company_1_data,#456#,for noodles,#345#',
            '2,01126451349786054,00,15000,partner_a,ent for boat,#234#,,#123#,company_1_data,#456#,ent for boat,#345#',
            '3,40000,2,25282699572',
        ])
        # 2 - Outbound batch
        self.outbound_batch.l10n_nz_file_format = 'bnz'
        self._test_file('outbound', [
            f'1,,,,02134691345768042,7,240525,{batch_creation_date},',
            '2,01126451349786054,50,25000,partner_a,hase of cups,#456#,,#345#,company_1_data,#234#,hase of cups,#123#',
            '2,05987566794815038,50,15000,partner_b,ater bottles,#456#,,#345#,company_1_data,#234#,ater bottles,#123#',
            '3,40000,2,11398144601',
        ])

    def test_export_asb(self):
        """ Test exporting the file for ASB """
        # 1 - Inbound batch
        self.inbound_batch.l10n_nz_file_format = 'asb'
        self._test_file('inbound', [
            '20,9965423,20240525,,25282699572,400.00,2',
            '01126451349786054,000,250.00,partner_a,,#234#,for noodles,#123#,,#456#,for noodles,#345#',
            '01126451349786054,000,150.00,partner_a,,#234#,ent for boat,#123#,,#456#,ent for boat,#345#',
        ])
        # 2 - Outbound batch
        self.outbound_batch.l10n_nz_file_format = 'asb'
        self._test_file('outbound', [
            f'{self.outbound_batch.name},2024/05/25,02134691345768042,250.00,#345#,#456#,hase of cups,01126451349786054,#123#,#234#,hase of cups,partner_a',
            f'{self.outbound_batch.name},2024/05/25,02134691345768042,150.00,#345#,#456#,ater bottles,05987566794815038,#123#,#234#,ater bottles,partner_b',
        ])

    def test_export_westpac(self):
        """ Test exporting the file for WESTPAC """
        # 1 - Inbound batch
        self.inbound_batch.l10n_nz_file_format = 'westpac'
        self._test_file('inbound', [
            'A,1,02,1346,company_1_data,,Payments,250524,',
            'D,2,01,1264,51349786,054,00,DD,25000,partner_a,#123#,#234#,for noodles,02,1346,91345768,042,company_1_data,',
            'D,3,01,1264,51349786,054,00,DD,15000,partner_a,#123#,#234#,ent for boat,02,1346,91345768,042,company_1_data,',
        ])
        # 2 - Outbound batch
        self.outbound_batch.l10n_nz_file_format = 'westpac'
        self._test_file('outbound', [
            'A,1,02,1346,company_1_data,,Purchases,250524,',
            'D,2,01,1264,51349786,054,50,DC,25000,partner_a,#345#,#456#,hase of cups,02,1346,91345768,042,company_1_data,',
            'D,3,05,9875,66794815,038,50,DC,15000,partner_b,#345#,#456#,ater bottles,02,1346,91345768,042,company_1_data,',
        ])

    def _test_file(self, payment_type, expected_lines):
        """ Simple helper that compares the lines in the inbound/outbound file by the ones provided. """
        if payment_type == 'outbound':
            file = self.outbound_batch._generate_export_file()['file']
        else:
            file = self.inbound_batch._generate_export_file()['file']

        batch_file = base64.decodebytes(file).decode()
        lines = batch_file.split('\r\n')
        for line_number, (file_line, expected_line) in enumerate(zip(lines, expected_lines), start=1):
            self.assertEqual(file_line, expected_line, f'Line {line_number} did not match with the expected values.')
