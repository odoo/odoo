from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPartyLink(TransactionCase):
    """Linking a login re-points the employee at the user's party; everything
    that is the person's follows, and the shell it leaves is archived."""

    def _badged_employee(self):
        tag = self.env["res.partner.tag"].create({"name": "Forklift"})
        employee = self.env["hr.employee"].create(
            {
                "name": "Link Person",
                "barcode": "LINK0001",
                "identification_id": "LINK-ID",
                "private_street": "Home Street 1",
                "work_email": "link@example.com",
            }
        )
        employee.partner_id.tag_ids = tag
        bank = self.env["res.partner.bank.account"].create(
            {"acc_number": "LINK-ACC-1", "partner_id": employee.partner_id.id}
        )
        employee.bank_account_ids = bank
        return employee, tag, bank

    def test_a_user_link_keeps_everything_that_is_the_persons(self):
        employee, tag, bank = self._badged_employee()
        former = employee.partner_id
        user = self.env["res.users"].create({"name": "Link Login", "login": "link"})
        employee.user_id = user
        self.assertEqual(employee.partner_id, user.partner_id)
        self.assertEqual(employee.barcode, "LINK0001")
        self.assertEqual(employee.identification_id, "LINK-ID")
        self.assertEqual(employee.private_street, "Home Street 1")
        self.assertEqual(employee.private_address_id.parent_id, user.partner_id)
        self.assertEqual(bank.partner_id, user.partner_id)
        self.assertIn(tag, user.partner_id.tag_ids)
        self.assertEqual(
            self.env["hr.employee"].search([("barcode", "=", "LINK0001")]), employee
        )
        self.assertFalse(former.active)
        self.assertTrue(former.exists())

    def test_a_user_link_leaves_the_former_partys_history_on_the_shell(self):
        employee, _tag, _bank = self._badged_employee()
        former = employee.partner_id
        former.message_post(body="Logged before the login existed")
        logged = former.message_ids
        self.assertTrue(logged)
        user = self.env["res.users"].create({"name": "Link Login", "login": "link"})
        employee.user_id = user
        self.assertNotEqual(employee.partner_id, former)
        # The shell is archived rather than deleted precisely so that what was
        # said about the person before they had a login is still readable.
        self.assertTrue(former.exists())
        self.assertFalse(former.active)
        self.assertLessEqual(
            logged,
            former.message_ids,
            "nothing said about the person before the login may be moved off the "
            "shell or deleted with it",
        )

    def test_a_former_party_that_is_a_real_contact_is_not_archived(self):
        employee, _tag, _bank = self._badged_employee()
        former = employee.partner_id
        company = self.env["res.partner"].create(
            {"name": "Customer Co", "is_company": True}
        )
        former.parent_id = company
        user = self.env["res.users"].create({"name": "Link Login", "login": "link2"})
        employee.user_id = user
        self.assertEqual(employee.partner_id, user.partner_id)
        self.assertTrue(former.active)

    def test_unlinking_the_user_leaves_the_party_with_the_user(self):
        employee, _tag, _bank = self._badged_employee()
        user = self.env["res.users"].create({"name": "Link Login", "login": "link3"})
        employee.user_id = user
        employee.user_id = False
        self.assertEqual(employee.partner_id, user.partner_id)
        self.assertTrue(user.partner_id.active)
