from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestLanguageDeactivation(TransactionCase):
    def test_a_user_cannot_deactivate_a_language_a_website_serves(self):
        website = self.env.ref("website.default_website")
        lang = website.language_ids[0]
        admin = self.env.ref("base.user_admin")
        with self.assertRaises(UserError):
            lang.with_user(admin).write({"active": False})
        self.assertTrue(lang.active)

    def test_the_superuser_can(self):
        website = self.env.ref("website.default_website")
        lang = self.env["res.lang"]._activate_lang("nl_NL")
        website.language_ids += lang
        lang.write({"active": False})
        self.assertFalse(lang.active)
