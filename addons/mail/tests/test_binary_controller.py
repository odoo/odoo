# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo.addons.mail.tests.test_controller_common import TestControllerCommon


@odoo.tests.tagged("-at_install", "post_install")
class TestBinaryControllerCommon(TestControllerCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_user = cls.env["res.users"].create(
            {
                "email": "testuser@testuser.com",
                "name": "Test User",
                "login": "test_user",
                "password": "test_user",
            }
        )
        cls.guest_2 = cls.env["mail.guest"].create({"name": "Guest 2"})

    def _execute_subtests(self, record, subtests, options=None):
        for data_user, allowed in subtests:
            if options:
                self._execute_options(options, data_user, record)
            user = data_user if data_user._name == "res.users" else self.user_public
            guest = data_user if data_user._name == "mail.guest" else self.env["mail.guest"]
            self._authenticate_user(user=user, guest=guest)
            with self.subTest(user=user.name, guest=guest.name, options=options):
                guest_or_partner = record if record._name == "mail.guest" else record.partner_id
                if allowed:
                    self.assertEqual(
                        self._get_avatar_url(guest_or_partner).headers["Content-Disposition"],
                        f'inline; filename="{guest_or_partner.name}.svg"',
                    )
                else:
                    self.assertEqual(
                        self._get_avatar_url(guest_or_partner).headers["Content-Disposition"],
                        "inline; filename=placeholder.png",
                    )

    def _execute_options(self, options, data_user, record):
        pass

    def _get_avatar_url(self, record):
        url = f"/web/image?field=avatar_128&id={record.id}&model={record._name}&unique={odoo.fields.Datetime.to_string(record.write_date)}"
        return self.url_open(url)


@odoo.tests.tagged("-at_install", "post_install")
class TestBinaryController(TestBinaryControllerCommon):

    def test_open_partner_avatar(self):
        """Test access to open the partner avatar."""
        self._execute_subtests(
            self.test_user,
            (
                (self.user_public, False),
                (self.guest, False),
                (self.user_portal, False),
                (self.user_employee, True),
                (self.user_demo, True),
                (self.user_admin, True),
            ),
        )

    def test_open_guest_avatar(self):
        """Test access to open a guest avatar."""
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
