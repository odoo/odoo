from odoo.tests.common import TransactionCase


class TestDefaultGroup(TransactionCase):
    """Tests for the default user group mechanism."""

    def setUp(self):
        super().setUp()
        self.user = self.env.ref("base.user_admin")
        self.company = self.env["res.company"].create({"name": "oobO"})
        self.user.write(
            {
                "company_ids": [(4, self.company.id)],
                "company_id": self.company.id,
            }
        )

    def test_create_user_default_user_groups(self):
        """Groups implied by the default user group are inherited by new users."""
        company = self.env["res.company"].create({"name": "My Last Company"})
        partner = self.env["res.partner"].create({"name": "My User"})
        user = self.env["res.users"].create(
            {
                "login": "My User",
                "company_id": company.id,
                "company_ids": [(4, company.id)],
                "partner_id": partner.id,
            }
        )

        group_system = self.env.ref("base.group_system")
        self.assertTrue(user not in group_system.all_user_ids)

        self.env.ref("base.default_user_group").implied_ids |= group_system

        new_partner = self.env["res.partner"].create({"name": "New User"})
        new_user = self.env["res.users"].create(
            {
                "login": "My First New User",
                "company_id": company.id,
                "company_ids": [(4, company.id)],
                "partner_id": new_partner.id,
            }
        )
        self.assertTrue(new_user in group_system.all_user_ids)
