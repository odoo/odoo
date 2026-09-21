from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestResBank(TransactionCase):
    def test_a_bank_is_a_party(self):
        bank = self.env["res.bank"].create(
            {
                "name": "Party Bank",
                "bic": "prtybank",
                "street": "1 Bank St",
                "city": "Bankton",
                "country_id": self.env.ref("base.be").id,
                "email": "bank@example.com",
            }
        )
        self.assertEqual(bank.bic, "PRTYBANK")
        self.assertTrue(bank.partner_id.is_company)
        self.assertFalse(bank.partner_id.parent_id)
        self.assertEqual(bank.partner_id.name, "Party Bank")
        self.assertEqual(bank.partner_id.street, "1 Bank St")
        self.assertEqual(bank.partner_id.country_id.code, "BE")
        self.assertEqual(bank.country_code, "BE")
        self.assertTrue(bank.partner_id.is_bank)
        self.assertIn(
            bank.partner_id, self.env["res.partner"].search([("is_bank", "=", True)])
        )
        self.assertNotIn(
            bank.partner_id, self.env["res.partner"].search([("is_bank", "=", False)])
        )
        self.assertEqual(bank.display_name, "Party Bank - PRTYBANK")
        self.assertEqual(
            self.env["res.bank"].search([("name", "ilike", "party bank")]), bank
        )
        self.assertEqual(self.env["res.bank"].name_search("PRTY")[0][0], bank.id)

    def test_identity_is_written_through_the_bank_and_read_in_one_query(self):
        bank = self.env["res.bank"].create({"name": "Rename Bank"})
        bank.name = "Renamed Bank"
        bank.write({"email": "new@example.com", "active": False})
        self.assertEqual(bank.partner_id.name, "Renamed Bank")
        self.assertEqual(bank.partner_id.email, "new@example.com")
        self.assertFalse(bank.partner_id.active)
        self.assertFalse(bank.active)
        self.assertNotIn(bank, self.env["res.bank"].search([]))
        self.assertIn(
            bank, self.env["res.bank"].with_context(active_test=False).search([])
        )
        bank.partner_id.name = "Renamed by the party"
        self.assertEqual(bank.name, "Renamed by the party")
        self.env.flush_all()
        self.env.invalidate_all()
        with self.assertQueryCount(1):
            self.assertEqual(bank.name, "Renamed by the party")
            self.assertEqual(bank.email, "new@example.com")

    def test_identity_is_readable_and_writable_by_whoever_may_read_and_write_the_bank(
        self,
    ):
        bank = self.env["res.bank"].create({"name": "Access Bank", "bic": "ACCSBANK"})
        bank.partner_id.comment = "private note"
        employee = new_test_user(
            self.env, login="rb_employee", groups="base.group_user"
        )
        as_employee = bank.with_user(employee)
        self.assertEqual(as_employee.name, "Access Bank")
        self.assertEqual(as_employee.display_name, "Access Bank - ACCSBANK")
        with self.assertRaises(AccessError):
            as_employee.write({"name": "not allowed"})
        manager = new_test_user(
            self.env, login="rb_manager", groups="base.group_partner_manager"
        )
        bank.with_user(manager).write({"name": "Managed Bank", "bic": "mngdbank"})
        self.assertEqual(bank.partner_id.name, "Managed Bank")
        self.assertEqual(bank.bic, "MNGDBANK")

    def test_a_bank_account_still_names_its_bank(self):
        bank = self.env["res.bank"].create({"name": "Holder Bank", "bic": "HLDRBANK"})
        partner = self.env["res.partner"].create({"name": "Holder"})
        account = self.env["res.partner.bank"].create(
            {"acc_number": "HB-0001", "partner_id": partner.id, "bank_id": bank.id}
        )
        self.assertEqual(account.bank_name, "Holder Bank")
        self.assertEqual(account.bank_bic, "HLDRBANK")
        self.assertEqual(account.display_name, "HB-0001 - Holder Bank")
        self.assertEqual(
            self.env["res.partner.bank"].search([("bank_id.name", "=", "Holder Bank")]),
            account,
        )
        self.assertEqual(partner.bank_ids, account)
        self.assertNotEqual(partner, bank.partner_id)

    def test_a_party_outlives_its_bank(self):
        bank = self.env["res.bank"].create({"name": "Excluded Bank"})
        Partner = self.env["res.partner"].with_context(active_test=False)
        self.assertNotIn(bank.partner_id, Partner.search([("is_bank", "=", False)]))
        self.assertEqual(
            set(Partner.search([("is_bank", "=", True)]).ids),
            set(
                self.env["res.bank"]
                .with_context(active_test=False)
                .search([])
                .partner_id.ids
            ),
        )
        party = bank.partner_id
        bank.unlink()
        self.assertFalse(bank.exists())
        self.assertNotIn(party.id, self.env["res.bank"]._get_bank_partner_ids())
        self.assertTrue(party.exists(), "the party outlives the bank")
        self.assertFalse(party.is_bank)
