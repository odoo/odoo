# Part of Odoo. See LICENSE file for full copyright and licensing details.
from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged, freeze_time


@tagged('post_install_l10n', 'post_install', '-at_install')
@freeze_time("2020-12-01 03:45:00")
class TestNacha(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company_data["default_journal_bank"].write({
            "nacha_immediate_destination": "111111118",
            "nacha_immediate_origin": "IMM_ORIG",
            "nacha_destination": "DESTINATION",
            "nacha_company_identification": "COMPANY",
            "nacha_origination_dfi_identification": "ORIGINATION_DFI",
        })

        cls.company_data["default_journal_bank"].bank_account_id = cls.env["res.partner.bank"].create({
            "partner_id": cls.company_data["company"].partner_id.id,
            "acc_number": "223344556",
            "aba_routing": "123456780",
        })

        cls.bank_partner_a = cls.env["res.partner.bank"].create({
            "partner_id": cls.partner_a.id,
            "acc_number": "987654321",
            "aba_routing": "123456780",
        })

        cls.bank_partner_b = cls.env["res.partner.bank"].create({
            "partner_id": cls.partner_b.id,
            "acc_number": "987654321",
            "aba_routing": "123456780",
        })

        # Test that we always put times/dates as seen in the user's timezone.
        # 2020-12-01 03:45:00 UTC is 2020-11-31 19:45:00 US/Pacific
        cls.env.user.tz = "America/Los_Angeles"

        def create_payment(partner, amount, memo, days_from_now):
            payment = cls.env['account.payment'].create({
                "partner_id": partner.id,
                "memo": memo,
                "amount": amount,
                "payment_type": "outbound",
                "date": fields.Date.context_today(cls.env.user) + relativedelta(days=days_from_now),
            })
            payment.action_post()
            return payment

        cls.batch = cls.env["account.batch.payment"].create({
            "journal_id": cls.company_data["default_journal_bank"].id,
            "batch_type": "outbound",
        })

        payments = create_payment(cls.partner_b, 567.89, 'partner_b_2', 0) |\
                   create_payment(cls.partner_b, 456.78, 'partner_b_1', 1) |\
                   create_payment(cls.partner_a, 543.21, 'partner_a_2', 1) |\
                   create_payment(cls.partner_a, 123.45, 'partner_a_1', 0)
        # Sort to ensure we set the payments according to the _order. Otherwise, the tests won't be consistent. The first
        # test will use payment_ids as set here, the second test will load according to _order.
        cls.batch.payment_ids = payments.sorted()

    def assertFile(self, expected, nr_of_payments):
        self.assertEqual(
            len(expected) % 10,
            0,
            "NACHA files should always be padded to contain a multiple of 10 lines."
        )

        expected_nr_of_records = len([line for line in expected if not line.startswith("9999")])
        self.assertEqual(
            self.batch._get_nr_of_records(2, nr_of_payments),
            expected_nr_of_records,
            "A incorrect number of records was calculated, it should equal the number of lines in the file (excluding padding)."
        )

        generated = self.batch._generate_nacha_file().splitlines()
        self.assertEqual(len(generated), len(expected), "The generated NACHA file has an incorrect amount of records.")

        for generated_line, expected_line in zip(generated, expected):
            self.assertEqual(generated_line, expected_line, "Generated line in NACHA file does not match expected.")

    def testGenerateNachaFileUnbalanced(self):
        expected = [
            # header
            f"101 111111118  IMM_ORIG2011301945A094101DESTINATION            company_1_data         {self.batch.id:8d}",
            # batch header for payments today "BATCH 0"
            "5220company_1_data  BATCH/OUT/2020/0001 COMPANY   CCDBATCH 0   201130201130   1ORIGINAT0000000",
            # entry detail for payment "partner_a_1"
            "622123456780987654321        0000012345               partner_a               0ORIGINAT0000000",
            # entry detail for payment "partner_b_2"
            "622123456780987654321        0000056789               partner_b               0ORIGINAT0000001",
            # batch control record for "BATCH 0"
            "82200000020024691356000000000000000000069134COMPANY                            ORIGINAT0000000",
            # batch header for payments tomorrow "BATCH 1"
            "5220company_1_data  BATCH/OUT/2020/0001 COMPANY   CCDBATCH 1   201201201201   1ORIGINAT0000001",
            # entry detail for payment "partner_a_2"
            "622123456780987654321        0000054321               partner_a               0ORIGINAT0000000",
            # entry detail for payment "partner_b_1"
            "622123456780987654321        0000045678               partner_b               0ORIGINAT0000001",
            # batch control record for "BATCH 1"
            "82200000020024691356000000000000000000099999COMPANY                            ORIGINAT0000001",
            # file control record
            "9000002000001000000040049382712000000000000000000169133                                       ",
        ]
        self.assertFile(expected, len(self.batch.payment_ids))

    def testGenerateNachaFileBalanced(self):
        journal = self.company_data["default_journal_bank"]
        journal.nacha_is_balanced = True
        journal.nacha_discretionary_data = "00000000000123456789"
        expected = [
            # header
            f"101 111111118  IMM_ORIG2011301945A094101DESTINATION            company_1_data         {self.batch.id:8d}",
            # batch header for payments today "BATCH 0"
            "5200company_1_data  00000000000123456789COMPANY   CCDBATCH 0   201130201130   1ORIGINAT0000000",
            # entry detail for payment "partner_a_1"
            "622123456780987654321        0000012345               partner_a               0ORIGINAT0000000",
            # entry detail for payment "partner_b_2"
            "622123456780987654321        0000056789               partner_b               0ORIGINAT0000001",
            # offset entry for "BATCH 0"
            "627123456780223344556        0000069134               OFFSET                  0ORIGINAT0000002",
            # batch control record for "BATCH 0"
            "82000000030037037034000000069134000000069134COMPANY                            ORIGINAT0000000",
            # batch header for payments tomorrow "BATCH 1"
            "5200company_1_data  00000000000123456789COMPANY   CCDBATCH 1   201201201201   1ORIGINAT0000001",
            # entry detail for payment "partner_a_2"
            "622123456780987654321        0000054321               partner_a               0ORIGINAT0000000",
            # entry detail for payment "partner_b_1"
            "622123456780987654321        0000045678               partner_b               0ORIGINAT0000001",
            # offset entry for "BATCH 1"
            "627123456780223344556        0000099999               OFFSET                  0ORIGINAT0000002",
            # batch control record for "BATCH 1"
            "82000000030037037034000000099999000000099999COMPANY                            ORIGINAT0000001",
            # file control record
            "9000002000002000000060074074068000000169133000000169133                                       ",
            # padding
            "9999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999",
            "9999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999",
            "9999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999",
            "9999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999",
            "9999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999",
            "9999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999",
            "9999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999",
            "9999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999",
        ]

        nr_of_offset_records = len([line for line in expected if line.startswith("627")])
        self.assertFile(expected, len(self.batch.payment_ids) + nr_of_offset_records)
