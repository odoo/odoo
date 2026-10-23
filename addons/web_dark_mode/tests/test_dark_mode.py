# © 2022 Florian Kantelberg - initOS GmbH
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from unittest.mock import MagicMock

import odoo.http
from odoo.tests import common


class TestDarkMode(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.request = MagicMock(env=cls.env)
        odoo.http._request_stack.push(cls.request)

    def test_dark_mode_cookie(self):
        response = MagicMock()

        # Cookie is set because the color_scheme changed
        self.request.httprequest.cookies = {"color_scheme": "dark"}
        self.env["ir.http"]._post_dispatch(response)
        response.set_cookie.assert_called_with("color_scheme", "light")

        # Cookie isn't set because the color_scheme is the same
        response.reset_mock()
        self.request.httprequest.cookies = {"color_scheme": "light"}
        self.env["ir.http"]._post_dispatch(response)
        response.set_cookie.assert_not_called()

        # Cookie isn't set because it's device dependent
        self.env.user.dark_mode_device_dependent = True
        self.request.httprequest.cookies = {"color_scheme": "dark"}
        self.env["ir.http"]._post_dispatch(response)
        response.set_cookie.assert_not_called()
