from odoo.tests.common import TransactionCase


class TestResConfigSettings(TransactionCase):
    """Tests for web-layer res.config.settings fields and group management."""

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
        Settings = self.env["res.config.settings"].with_user(self.user.id)
        self.config = Settings.create({})

    def test_multi_company_res_config_group(self):
        """Enabling/disabling a group flag propagates to all users and new-user template."""
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

        ResConfig = self.env["res.config.settings"]
        default_values = ResConfig.default_get(list(ResConfig.fields_get()))

        # Case 1: Enable a group
        default_values.update({"group_multi_currency": True})
        ResConfig.create(default_values).execute()
        self.assertIn(
            user, self.env.ref("base.group_multi_currency").sudo().all_user_ids
        )

        new_partner = self.env["res.partner"].create({"name": "New User"})
        new_user = self.env["res.users"].create(
            {
                "login": "My First New User",
                "company_id": company.id,
                "company_ids": [(4, company.id)],
                "partner_id": new_partner.id,
            }
        )
        self.assertIn(
            new_user,
            self.env.ref("base.group_multi_currency").sudo().all_user_ids,
        )

        # Case 2: Disable a group
        default_values.update({"group_multi_currency": False})
        ResConfig.create(default_values).execute()
        self.assertNotIn(
            user, self.env.ref("base.group_multi_currency").sudo().all_user_ids
        )

        new_partner = self.env["res.partner"].create({"name": "New User 2"})
        new_user = self.env["res.users"].create(
            {
                "login": "My Second New User",
                "company_id": company.id,
                "company_ids": [(4, company.id)],
                "partner_id": new_partner.id,
            }
        )
        self.assertNotIn(
            new_user,
            self.env.ref("base.group_multi_currency").sudo().all_user_ids,
        )
