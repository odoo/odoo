# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
from freezegun import freeze_time
from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestZenginBatchPayment(AccountTestInvoicingCommon):

    def create_payment(self, partner, amount, memo, days_from_now):
        payment = self.env['account.payment'].create({
            "partner_id": partner.id,
            'payment_method_line_id': self.batch_payment.id,
            "memo": memo,
            "amount": amount,
            "payment_type": "outbound",
            "date": fields.Date.context_today(self.env.user) + relativedelta(days=days_from_now),
        })
        payment.action_post()
        return payment

    @classmethod
    @AccountTestInvoicingCommon.setup_country('jp')
    def setUpClass(cls):
        super().setUpClass()

        cls.journal = cls.company_data['default_journal_bank']
        cls.batch_payment = cls.journal.outbound_payment_method_line_ids.filtered(lambda line: line.code == 'zengin')

        cls.env.user.groups_id |= cls.env.ref('account.group_validate_bank_account')

        cls.bank_a = cls.env["res.bank"].create({
            "name": "Mitsuisumitomo",
            "bic": "0009",
            "l10n_jp_zengin_name_kana": "ﾐﾂｲｽﾐﾄﾓ",
            "l10n_jp_zengin_branch_name": "Sannomiya",
            "l10n_jp_zengin_branch_name_kana": "ｻﾝﾉﾐﾔ",
            "l10n_jp_zengin_branch_code": "410",
            "country": cls.env.ref("base.jp").id,
        })

        cls.bank_b = cls.env["res.bank"].create({
            "name": "Mitsuisumitomo",
            "bic": "0009",
            "l10n_jp_zengin_name_kana": "ﾐﾂｲｽﾐﾄﾓ",
            "l10n_jp_zengin_branch_name": "Hibiya",
            "l10n_jp_zengin_branch_name_kana": "ﾋﾋﾞﾔ",
            "l10n_jp_zengin_branch_code": "632",
            "country": cls.env.ref("base.jp").id,
        })

        cls.bank_c = cls.env["res.bank"].create({
            "name": "Mitsuisumitomo",
            "bic": "0009",
            "l10n_jp_zengin_name_kana": "ﾐﾂｲｽﾐﾄﾓ",
            "l10n_jp_zengin_branch_name": "Osaka Honten",
            "l10n_jp_zengin_branch_name_kana": "ｵｵｻｶﾎﾝﾃﾝ",
            "l10n_jp_zengin_branch_code": "101",
            "country": cls.env.ref("base.jp").id,
        })

        cls.journal.bank_account_id = cls.env["res.partner.bank"].create({
            "partner_id": cls.company_data["company"].partner_id.id,
            "bank_id": cls.bank_a.id,
            "acc_number": "0185018",
            "l10n_jp_zengin_acc_holder_name_kana": "ﾜｶｸｻﾀﾛｳ",
            "l10n_jp_zengin_account_type": "regular",
            "l10n_jp_zengin_client_code": "8818002600",
        })

        cls.bank_partner_a = cls.env["res.partner.bank"].create({
            "partner_id": cls.partner_a.id,
            "bank_id": cls.bank_b.id,
            "allow_out_payment": True,
            "acc_number": "1234567",
            "l10n_jp_zengin_acc_holder_name_kana": "ﾜｶｸｻｼﾖｳｼﾞ",
            "l10n_jp_zengin_account_type": "regular",
        })

        cls.bank_partner_b = cls.env["res.partner.bank"].create({
            "partner_id": cls.partner_b.id,
            "bank_id": cls.bank_c.id,
            "allow_out_payment": True,
            "acc_number": "7654321",
            "l10n_jp_zengin_acc_holder_name_kana": "ﾜｶｸｻｼﾖｳｼﾞｵｵｻｶｼｼﾔ",
            "l10n_jp_zengin_account_type": "regular",
        })

        with freeze_time('2023-12-15'):
            cls.batch = cls.env["account.batch.payment"].create({
                "journal_id": cls.company_data["default_journal_bank"].id,
                "batch_type": "outbound",
            })
            payments = cls.create_payment(cls, cls.partner_b, 150000, 'partner_b', 0) | cls.create_payment(cls, cls.partner_a, 1000000, 'partner_a', 0)

        cls.batch.payment_ids = payments.sorted()

    def test_generate_zengin_batch_payment_file(self):
        generated = self.batch._generate_export_file()
        data: bytes = base64.decodebytes(generated['file'])
        record_data = data.decode('SHIFT_JIS')  # Zengin files are encoded in SHIFT_JIS
        expected = [
            # header
            "12108818002600ﾜｶｸｻﾀﾛｳ                                 12150009ﾐﾂｲｽﾐﾄﾓ        410ｻﾝﾉﾐﾔ          10185018                 ",
            # entry detail for payment "partner_a"
            "20009ﾐﾂｲｽﾐﾄﾓ        632ﾋﾋﾞﾔ           000011234567ﾜｶｸｻｼﾖｳｼﾞ                     00010000000000000000000000000007        ",
            # entry detail for payment "partner_b"
            "20009ﾐﾂｲｽﾐﾄﾓ        101ｵｵｻｶﾎﾝﾃﾝ       000017654321ﾜｶｸｻｼﾖｳｼﾞｵｵｻｶｼｼﾔ              00001500000000000000000000000007        ",
            # file control record
            "8000002000001150000                                                                                                     ",
            # footer
            "9                                                                                                                       ",
        ]
        for generated_line, expected_line in zip(record_data.splitlines(), expected):
            self.assertEqual(generated_line, expected_line, "Generated line in Zengin file does not match expected.")

    def test_generate_zengin_batch_payment_file_group_payment(self):
        self.batch.l10n_jp_zengin_merge_transactions = True
        with freeze_time('2023-12-15'):
            new_payment = self.create_payment(self.partner_a, 1000000, 'partner_a', 1)
            self.batch.payment_ids |= new_payment
            sorted(self.batch.payment_ids)

        generated = self.batch._generate_export_file()
        data: bytes = base64.decodebytes(generated['file'])
        record_data = data.decode('SHIFT_JIS')  # Zengin files are encoded in SHIFT_JIS
        expected = [
            # header
            "12108818002600ﾜｶｸｻﾀﾛｳ                                 12150009ﾐﾂｲｽﾐﾄﾓ        410ｻﾝﾉﾐﾔ          10185018                 ",
            # entry detail for payment "partner_a"
            "20009ﾐﾂｲｽﾐﾄﾓ        632ﾋﾋﾞﾔ           000011234567ﾜｶｸｻｼﾖｳｼﾞ                     00020000000000000000000000000007        ",
            # entry detail for payment "partner_b"
            "20009ﾐﾂｲｽﾐﾄﾓ        101ｵｵｻｶﾎﾝﾃﾝ       000017654321ﾜｶｸｻｼﾖｳｼﾞｵｵｻｶｼｼﾔ              00001500000000000000000000000007        ",
            # file control record
            "8000002000002150000                                                                                                     ",
            # footer
            "9                                                                                                                       ",
        ]
        for generated_line, expected_line in zip(record_data.splitlines(), expected):
            self.assertEqual(generated_line, expected_line, "Generated line in Zengin file does not match expected.")
