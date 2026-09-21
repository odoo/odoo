from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestResPartnerBankTrust(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.RPB = cls.env["res.partner.bank.account"]
        cls.be = cls.env.ref("base.be")
        cls.fr = cls.env.ref("base.fr")
        cls.partner_be = cls.env["res.partner"].create(
            {"name": "BE Vendor", "country_id": cls.be.id, "is_company": True}
        )
        cls.partner_fr = cls.env["res.partner"].create(
            {"name": "FR Vendor", "country_id": cls.fr.id, "is_company": True}
        )
        cls.clerk = cls.env["res.users"].create(
            {
                "name": "Billing Clerk",
                "login": "clerk_trust_test",
                "group_ids": [
                    (
                        6,
                        0,
                        [
                            cls.env.ref("base.group_user").id,
                            cls.env.ref("account.group_account_invoice").id,
                        ],
                    )
                ],
            }
        )

    def test_money_transfer_belgian_account_detected(self):
        acc = self.RPB.create(
            {"acc_number": "BE40967000000063", "partner_id": self.partner_be.id}
        )
        self.assertEqual(acc.money_transfer_service, "Wise")
        self.assertEqual(acc._get_money_transfer_service(), "Wise")
        if acc.acc_type == "iban":
            self.assertTrue(acc.has_money_transfer_warning)

    def test_money_transfer_foreign_account_not_false_positive(self):
        acc = self.RPB.create(
            {
                "acc_number": "FR7296700000000000000000000",
                "partner_id": self.partner_fr.id,
            }
        )
        self.assertEqual(acc.sanitized_acc_number[4:7], "967")
        self.assertFalse(acc.money_transfer_service)
        self.assertIsNone(acc._get_money_transfer_service())
        if acc.acc_type == "iban":
            self.assertFalse(acc.has_money_transfer_warning)

    def test_money_transfer_service_independent_of_trust(self):
        acc = self.RPB.create(
            {"acc_number": "BE40967000000063", "partner_id": self.partner_be.id}
        )
        before = acc.money_transfer_service
        acc.allow_out_payment = True
        acc.invalidate_recordset()
        self.assertEqual(acc.money_transfer_service, before)

    def test_display_name_transient_record_has_no_literal_false(self):
        new_rec = self.RPB.with_context(display_account_trust=True).new(
            {"partner_id": self.partner_fr.id}
        )
        self.assertNotIn("False", new_rec.display_name or "")

    def test_lock_trust_fields(self):
        new_rec = self.RPB.new({"partner_id": self.partner_be.id})
        self.assertFalse(new_rec.lock_trust_fields, "new record is never locked")

        acc = self.RPB.create(
            {"acc_number": "BE71096123456769", "partner_id": self.partner_be.id}
        )
        self.assertFalse(acc.lock_trust_fields, "untrusted persisted account unlocked")
        acc.allow_out_payment = True
        self.assertTrue(acc.lock_trust_fields, "trusted persisted account locked")

    def test_clerk_cannot_trust(self):
        acc = self.RPB.create(
            {"acc_number": "BE71096123456769", "partner_id": self.partner_be.id}
        )
        with self.assertRaises(UserError):
            acc.with_user(self.clerk).write({"allow_out_payment": True})

    def test_clerk_cannot_untrust(self):
        acc = self.RPB.create(
            {"acc_number": "BE71096123456769", "partner_id": self.partner_be.id}
        )
        acc.allow_out_payment = True
        with self.assertRaises(UserError):
            acc.with_user(self.clerk).write({"allow_out_payment": False})

    def test_create_rejects_archived_duplicate(self):
        acc = self.RPB.create(
            {"acc_number": "BE68539007547034", "partner_id": self.partner_be.id}
        )
        acc.action_archive()
        with self.assertRaises(UserError):
            self.RPB.create(
                {"acc_number": "BE68539007547034", "partner_id": self.partner_be.id}
            )

    def test_create_rejects_archived_duplicate_ignoring_formatting(self):
        acc = self.RPB.create(
            {"acc_number": "BE68539007547034", "partner_id": self.partner_be.id}
        )
        acc.action_archive()
        with self.assertRaises(UserError):
            self.RPB.create(
                {
                    "acc_number": "be68 5390 0754 7034",
                    "partner_id": self.partner_be.id,
                }
            )

    def test_create_multi_detects_archived_duplicate(self):
        acc = self.RPB.create(
            {"acc_number": "BE62510007547061", "partner_id": self.partner_be.id}
        )
        acc.action_archive()
        with self.assertRaises(UserError):
            self.RPB.create(
                [
                    {
                        "acc_number": "BE71096123456769",
                        "partner_id": self.partner_fr.id,
                    },
                    {
                        "acc_number": "BE62510007547061",
                        "partner_id": self.partner_be.id,
                    },
                ]
            )
