# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo.addons.mail.tests.test_binary_controller import TestBinaryControllerCommon


@odoo.tests.tagged("-at_install", "post_install")
class TestPublicBinaryController(TestBinaryControllerCommon):
    def test_01_guest_avatar_public_record(self):
        """Test access to open a guest avatar who hasn't sent a message on a public record."""
        self.env["mail.test.public"].create({"name": "Test"})
        self._execute_subtests(
            self.guest_2,
            (
                (self.user_public, False),
                (self.guest, False),
                (self.user_portal, False),
                (self.user_employee, True),
                (self.user_demo, True),
                (self.user_admin, True),
            ),
        )

    def test_02_guest_avatar_public_record(self):
        """Test access to open a guest avatar who has sent a message on a public record."""
        thread = self.env["mail.test.public"].create({"name": "Test"})
        self._send_message(self.guest_2, "mail.test.public", thread.id)
        self._execute_subtests(
            self.guest_2,
            (
                (self.user_public, False),
                (self.guest, False),
                (self.user_portal, False),
                (self.user_employee, True),
                (self.user_demo, True),
                (self.user_admin, True),
            ),
        )

    def test_01_partner_avatar_public_record(self):
        """Test access to open a partner avatar who hasn't sent a message on a public record."""
        self.env["mail.test.public"].create({"name": "Test"})
        self._execute_subtests(
            self.user_test,
            (
                (self.user_public, False),
                (self.guest, False),
                (self.user_portal, False),
                (self.user_employee, True),
                (self.user_demo, True),
                (self.user_admin, True),
            ),
        )

    def test_02_partner_avatar_public_record(self):
        """Test access to open a partner avatar who has sent a message on a public record."""
        thread = self.env["mail.test.public"].create({"name": "Test"})
        self._send_message(self.user_test, "mail.test.public", thread.id)
        self._execute_subtests(
            self.user_test,
            (
                (self.user_public, False),
                (self.guest, False),
                (self.user_portal, False),
                (self.user_employee, True),
                (self.user_demo, True),
                (self.user_admin, True),
            ),
        )
