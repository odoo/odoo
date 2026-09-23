from odoo.tests import BaseCase, tagged

from ..controllers.home import _is_private_address


@tagged("-at_install", "post_install")
class TestAdminPasswordWarnAddress(BaseCase):
    def test_private_addresses_are_recognised(self):
        for address in (
            "127.0.0.1",
            "10.1.2.3",
            "192.168.0.7",
            "::1",
            "fd00::1",
            "100.64.1.1",
        ):
            with self.subTest(address=address):
                self.assertTrue(_is_private_address(address))

    def test_public_addresses_are_recognised(self):
        for address in (
            "8.8.8.8",
            "1.1.1.1",
            "2001:4860:4860::8888",
            "2002:a00:1::",
            "192.0.2.1",
        ):
            with self.subTest(address=address):
                self.assertFalse(_is_private_address(address))

    def test_unparsable_addresses_do_not_raise(self):
        for address in (None, "", "unknown", "127.0.0.1, 10.0.0.1", "_hidden", "abc"):
            with self.subTest(address=address):
                self.assertFalse(_is_private_address(address))
