# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.addons.mail.tests import common


class TestMailServerConfigurator(common.MailCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # company 2 and 3 uses the same alias
        cls.company_3.alias_domain_id.unlink()
        cls.company_3.alias_domain_id = cls.company_2.alias_domain_id

    def test_shared_configuration_new_alias(self):
        """Test the behavior when no alias exists for the company."""
        self.company_2.alias_domain_id.unlink()
        self.assertEqual(self.env["mail.alias.domain"].search_count([]), 1)
        configurator = self._create_configurator()
        with (patch.object(type(self.env["ir.mail_server"]), "test_smtp_connection", lambda *args: True),
              patch.object(type(self.env["fetchmail.server"]), "button_confirm_login", lambda *args: True)):
            configurator.action_setup()

        alias_domain = self.company_2.alias_domain_id

        self.assertNotEqual(alias_domain, self.company_3.alias_domain_id, "Should have created a new alias")
        self.assertEqual(self.env["mail.alias.domain"].search_count([]), 2)

        self.assertEqual(alias_domain.default_from, "personal.email@gmx.com")
        self.assertEqual(alias_domain.name, "gmx.com")

        ir_mail_server = self.env["ir.mail_server"].search([("from_filter", "=", "personal.email@gmx.com")])
        self.assertEqual(len(ir_mail_server), 1)

    def test_shared_configuration_update_alias(self):
        """Test the behavior when 2 companies share the same mail.alias.domain, and we update both."""
        configurator = self._create_configurator()
        self.assertEqual(
            configurator.is_default_warning,
            "The current default email is notifications.c2@test.mycompany2.com and it will be overwritten with personal.email@gmx.com."
            "\nThis configuration is also used by Company 3.",
            "Should warn the user that the company 3 configuration will be affected")

        configurator.catchall_domain = "new.catchall.domain"

        with (patch.object(type(self.env["ir.mail_server"]), "test_smtp_connection", lambda *args: True),
              patch.object(type(self.env["fetchmail.server"]), "button_confirm_login", lambda *args: True)):
            configurator.action_setup()

        alias_domain = self.company_2.alias_domain_id
        self.assertEqual(alias_domain, self.company_3.alias_domain_id, "Should have updated the existing alias")
        self.assertEqual(self.env["mail.alias.domain"].search_count([]), 2)

        self.assertEqual(alias_domain.name, "new.catchall.domain")
        self.assertEqual(alias_domain.default_from, "personal.email@gmx.com")

        ir_mail_server = self.env["ir.mail_server"].search([("from_filter", "=", "personal.email@gmx.com")])
        self.assertEqual(len(ir_mail_server), 1)

    def _create_configurator(self):
        return self.env["mail.server.configurator"].with_company(self.company_2).create({
            "server_type": "gmx",
            "email": "personal.email@gmx.com",
            "password": "password",
            "is_default": True,
        })
