from psycopg import IntegrityError

from odoo.tools import mute_logger

from odoo.addons.base.tests.common import SavepointCaseWithUserDemo


class TestResPartnerBank(SavepointCaseWithUserDemo):
    def test_sanitized_acc_number(self):
        partner_bank_model = self.env["res.partner.bank.account"]
        acc_number = " BE-001 2518823 03 "
        vals = partner_bank_model.search([("acc_number", "=", acc_number)])
        self.assertEqual(0, len(vals))
        partner_bank = partner_bank_model.create(
            {
                "acc_number": acc_number,
                "partner_id": self.env["res.partner"]
                .create({"name": "Pepper Test"})
                .id,
                "acc_type": "bank",
            }
        )
        vals = partner_bank_model.search([("acc_number", "=", acc_number)])
        self.assertEqual(1, len(vals))
        self.assertEqual(partner_bank, vals[0])
        vals = partner_bank_model.search([("acc_number", "in", [acc_number])])
        self.assertEqual(1, len(vals))
        self.assertEqual(partner_bank, vals[0])

        self.assertEqual(partner_bank.acc_number, acc_number)

        sanitized_acc_number = "BE001251882303"
        self.assertEqual(partner_bank.sanitized_acc_number, sanitized_acc_number)
        vals = partner_bank_model.search([("acc_number", "=", sanitized_acc_number)])
        self.assertEqual(1, len(vals))
        self.assertEqual(partner_bank, vals[0])
        vals = partner_bank_model.search([("acc_number", "in", [sanitized_acc_number])])
        self.assertEqual(1, len(vals))
        self.assertEqual(partner_bank, vals[0])
        self.assertEqual(partner_bank.sanitized_acc_number, sanitized_acc_number)

        vals = partner_bank_model.search(
            [("acc_number", "=", sanitized_acc_number.lower())]
        )
        self.assertEqual(1, len(vals))
        vals = partner_bank_model.search([("acc_number", "=", acc_number.lower())])
        self.assertEqual(1, len(vals))

        partner_bank.write({"sanitized_acc_number": "BE001251882303WRONG"})
        self.assertEqual(partner_bank.acc_number, partner_bank.sanitized_acc_number)

    def test_acc_holder_name_follows_partner_rename_when_not_customized(self):
        partner = self.env["res.partner"].create({"name": "Old Name"})
        bank = self.env["res.partner.bank.account"].create(
            {"acc_number": "BE001 2518823 03", "partner_id": partner.id}
        )
        self.assertEqual(bank.acc_holder_name, "Old Name")
        partner.write({"name": "New Name"})
        self.assertEqual(bank.acc_holder_name, "New Name")

    def test_acc_holder_name_customization_survives_partner_rename(self):
        partner = self.env["res.partner"].create({"name": "Old Name"})
        bank = self.env["res.partner.bank.account"].create(
            {"acc_number": "BE001 2518823 03", "partner_id": partner.id}
        )
        bank.acc_holder_name = "Custom Holder"
        partner.write({"name": "New Name"})
        self.assertEqual(bank.acc_holder_name, "Custom Holder")

    def test_acc_holder_name_recomputed_on_partner_change(self):
        partner_a = self.env["res.partner"].create({"name": "Holder A"})
        partner_b = self.env["res.partner"].create({"name": "Holder B"})
        bank = self.env["res.partner.bank.account"].create(
            {"acc_number": "BE001 2518823 03", "partner_id": partner_a.id}
        )
        bank.partner_id = partner_b
        self.assertEqual(bank.acc_holder_name, "Holder B")

    def test_bank_bic_uppercased_on_create_and_write(self):
        bank = self.env["res.bank"].create({"name": "Bic Bank", "bic": "gebabebb"})
        self.assertEqual(bank.bic, "GEBABEBB")
        bank.write({"bic": "bbrubebb"})
        self.assertEqual(bank.bic, "BBRUBEBB")

    def test_acc_type_selection_uses_private_hook(self):
        selection = (
            self.env["res.partner.bank.account"]
            ._fields["acc_type"]
            .get_values(self.env)
        )
        self.assertIn("bank", selection)

    def test_unlink_archives_instead_of_deleting(self):
        partner = self.env["res.partner"].create({"name": "Pepper Test"})
        partner_bank = self.env["res.partner.bank.account"].create(
            {"acc_number": "BE001 2518823 03", "partner_id": partner.id}
        )
        partner_bank.unlink()
        self.assertTrue(partner_bank.exists())
        self.assertFalse(partner_bank.active)

    @mute_logger("odoo.db")
    def test_unique_constraint_counts_archived_rows(self):
        # The number is unique per company, and SQL compares two null
        # companies as unknown rather than equal, so the holder needs one for
        # the constraint this pins to be the one under test.
        partner = self.env["res.partner"].create(
            {"name": "Pepper Test", "company_id": self.env.company.id}
        )
        partner_bank = self.env["res.partner.bank.account"].create(
            {"acc_number": "BE001 2518823 03", "partner_id": partner.id}
        )
        partner_bank.unlink()
        self.assertFalse(partner_bank.active)
        with self.assertRaises(IntegrityError), self.cr.savepoint():
            self.cr.execute(
                "INSERT INTO res_partner_bank_account"
                " (partner_id, acc_number, sanitized_acc_number, company_id, active)"
                " VALUES (%s, %s, %s, %s, TRUE)",
                [
                    partner.id,
                    "BE0012518823 03",
                    partner_bank.sanitized_acc_number,
                    partner.company_id.id,
                ],
            )

    def test_acc_holder_name_follows_partner_rename_on_archived_accounts(self):
        partner = self.env["res.partner"].create({"name": "Old Name"})
        bank = self.env["res.partner.bank.account"].create(
            {"acc_number": "BE001 2518823 03", "partner_id": partner.id}
        )
        bank.unlink()
        self.assertFalse(bank.active)
        partner.invalidate_recordset(["bank_ids"])
        partner.write({"name": "New Name"})
        self.assertEqual(
            bank.acc_holder_name,
            "New Name",
            "an archived account must not come back with a stale holder name",
        )

    def test_get_or_create_revives_an_archived_exact_match(self):
        partner = self.env["res.partner"].create({"name": "Pepper Test"})
        bank = self.env["res.partner.bank.account"].create(
            {"acc_number": "BE001 2518823 03", "partner_id": partner.id}
        )
        bank.unlink()
        self.assertFalse(bank.active)

        found = self.env["res.partner.bank.account"]._get_or_create_bank_account(
            "BE0012518823 03", partner, self.env.company
        )

        self.assertEqual(found, bank)
        self.assertTrue(bank.active)

    def test_get_or_create_leaves_an_archived_match_archived_when_asked(self):
        partner = self.env["res.partner"].create({"name": "Pepper Test"})
        bank = self.env["res.partner.bank.account"].create(
            {"acc_number": "BE001 2518823 03", "partner_id": partner.id}
        )
        bank.unlink()

        found = self.env["res.partner.bank.account"]._get_or_create_bank_account(
            "BE0012518823 03",
            partner,
            self.env.company,
            revive_archived_match=False,
        )

        self.assertFalse(found)
        self.assertFalse(bank.active)

    def test_get_or_create_leaves_a_child_partners_archived_account_alone(self):
        company = self.env["res.partner"].create(
            {"name": "Holder Co", "is_company": True}
        )
        child = self.env["res.partner"].create(
            {"name": "Holder Child", "parent_id": company.id}
        )
        bank = self.env["res.partner.bank.account"].create(
            {"acc_number": "BE001 2518823 03", "partner_id": child.id}
        )
        bank.unlink()

        found = self.env["res.partner.bank.account"]._get_or_create_bank_account(
            "BE001 2518823 03", company, self.env.company
        )

        self.assertFalse(found)
        self.assertFalse(bank.active)
