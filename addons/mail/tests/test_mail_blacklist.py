# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestMailBlacklist(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.email = "archived@test.example.com"
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Archived Blacklist Test",
                "email": cls.email,
            }
        )
        cls.blacklist_entry = cls.env["mail.blacklist"].create(
            {
                "email": cls.email,
                "active": False,
            }
        )

    def test_is_blacklisted_ignores_archived(self):
        self.assertFalse(
            self.partner.is_blacklisted,
            "Archived blacklist entries should not mark partner as blacklisted",
        )

    def test_is_blacklisted_active_entry(self):
        self.blacklist_entry.action_unarchive()
        self.assertTrue(
            self.partner.is_blacklisted,
            "Active blacklist entries should mark partner as blacklisted",
        )

    def test_active_test_false_context_works(self):
        self.assertFalse(
            self.partner.with_context(active_test=False).is_blacklisted,
            "Always blacklisted, even if context searches for archived records",
        )
