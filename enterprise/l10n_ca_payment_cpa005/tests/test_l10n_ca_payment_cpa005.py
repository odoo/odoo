# Part of Odoo. See LICENSE file for full copyright and licensing details.
from dateutil.relativedelta import relativedelta

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged, freeze_time

import datetime


@tagged("post_install_l10n", "post_install", "-at_install")
@freeze_time("2020-11-30 19:45:00")
class TestCPA005(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company_data["company"].write({"l10n_ca_cpa005_short_name": "COMP_NAME", "name": "Long Company Name"})

        cls.journal = cls.company_data["default_journal_bank"]
        cls.journal.outbound_payment_method_line_ids |= cls.env["account.payment.method.line"].create(
            {"payment_method_id": cls.env.ref("l10n_ca_payment_cpa005.account_payment_method_cpa005").id}
        )
        cls.journal.write(
            {
                "l10n_ca_cpa005_originator_id": "1234567890",
                "l10n_ca_cpa005_destination_data_center": "01600",
            }
        )
        cls.journal.bank_account_id = cls.env["res.partner.bank"].create(
            {
                "partner_id": cls.company_data["company"].partner_id.id,
                "acc_number": "9999999",
                "l10n_ca_financial_institution_number": "022233333",
            }
        )
        cls.journal.l10n_ca_cpa005_fcn_number_next = 103

        cls.bank_partner_a = cls.env["res.partner.bank"].create(
            {
                "partner_id": cls.partner_a.id,
                "acc_number": "333333333",
                "l10n_ca_financial_institution_number": "055566666",
            }
        )
        cls.bank_partner_b = cls.env["res.partner.bank"].create(
            {
                "partner_id": cls.partner_b.id,
                "acc_number": "444444444",
                "l10n_ca_financial_institution_number": "077788888",
            }
        )

        def create_payment(partner, amount, memo, days_from_now, transaction_code):
            payment = cls.env["account.payment"].create(
                {
                    "partner_id": partner.id,
                    "currency_id": cls.env.ref("base.CAD").id,
                    "memo": memo,
                    "amount": amount,
                    "payment_type": "outbound",
                    "date": datetime.datetime.today() + relativedelta(days=days_from_now),
                    "l10n_ca_cpa005_transaction_code_id": cls.env["l10n_ca_cpa005.transaction.code"]
                    .search([("code", "=", transaction_code)], limit=1)
                    .id,
                }
            )
            payment.action_post()
            return payment

        cls.batch = cls.env["account.batch.payment"].create(
            {
                "journal_id": cls.journal.id,
                "batch_type": "outbound",
            }
        )

        cls.env.ref("base.CAD").active = True
        payments = (
            create_payment(cls.partner_a, 123.45, "partner_a_1", 0, "430")
            | create_payment(cls.partner_a, 543.21, "partner_a_2", 0, "430")
            | create_payment(cls.partner_b, 456.78, "partner_b_1", 1, "430")
            | create_payment(cls.partner_b, 567.89, "partner_b_2", 0, "200")
        )
        # Sort to ensure payments are in order of creation. Otherwise, the tests won't be consistent. The first
        # test will use payment_ids as set here, the second test will load according to _order.
        cls.batch.payment_ids = payments.sorted("id")

    def test_cpa005(self):
        self.maxDiff = None  # show full diff in case of errors
        self.company_data["company"].write({"name": "Long Compàny Nàme"})
        expected = [
            # A record ("header")
            "A0000000011234567890010302033501600                    CAD                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              ",
            # C records ("outgoing payments")
            "C000000002123456789001034300000012345020335055566666333333333   0000000000000000000000000COMP_NAME      partner_a                     Long Company Name             1234567890                   0222333339999999                                            00000000000                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                ",
            "C000000003123456789001034300000054321020335055566666333333333   0000000000000000000000000COMP_NAME      partner_a                     Long Company Name             1234567890                   0222333339999999                                            00000000000                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                ",
            "C000000004123456789001034300000045678020336077788888444444444   0000000000000000000000000COMP_NAME      partner_b                     Long Company Name             1234567890                   0222333339999999                                            00000000000                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                ",
            "C000000005123456789001032000000056789020335077788888444444444   0000000000000000000000000COMP_NAME      partner_b                     Long Company Name             1234567890                   0222333339999999                                            00000000000                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                ",
            # Z record ("footer")
            "Z000000006123456789001030000000000000000000000000000001691330000000400000000000000000000000000000000000000000000                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        ",
        ]

        for line in expected:
            self.assertEqual(
                len(line), 1464, "Every line in our CPA file should have 1464 characters (excluding \\r\\n)."
            )

        self.assertEqual(
            len(expected),
            len(self.batch.payment_ids) + 2,
            "There should be an A record, one C record per payment and one Z record.",
        )

        generated = self.batch._generate_cpa005_file()
        self.assertEqual(
            generated.count("\r\n"), len(expected) - 1, "The generated CPA 005 file should use DOS line endings."
        )
        self.assertEqual(
            generated.count("à"), 0, "The generated CPA 005 file should not have special characters."
        )

        generated = generated.splitlines()
        self.assertEqual(len(generated), len(expected), "The generated CPA 005 file has an incorrect amount of lines.")

        for line in generated:
            self.assertEqual(
                len(line), 1464, "Every line in the generated CPA file should have 1464 characters (excluding \\r\\n)."
            )

        for generated_line, expected_line in zip(generated, expected):
            self.assertEqual(generated_line, expected_line, "Generated line in CPA 005 file does not match expected.")

    def test_cpa005_rollover_step_1(self):
        self.journal.l10n_ca_cpa005_fcn_number_next = 9999
        self.assertEqual(
            self.journal._l10n_ca_cpa005_next_file_creation_nr(), "9999", "FCN different from what was set."
        )
        self.assertEqual(self.journal._l10n_ca_cpa005_next_file_creation_nr(), "0001", "FCN should have rolled over back to 0001.")

    def test_cpa005_rollover_step_10(self):
        self.journal.l10n_ca_cpa005_fcn_number_next = 9991
        self.journal.l10n_ca_cpa005_fcn_sequence_id.number_increment = 10
        self.assertEqual(
            self.journal._l10n_ca_cpa005_next_file_creation_nr(), "9991", "FCN different from what was set."
        )
        self.assertEqual(self.journal._l10n_ca_cpa005_next_file_creation_nr(), "0002", "FCN should have rolled over back to 0002.")
