# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo.addons.mail.tests.test_controller_common import TestControllerCommon


@odoo.tests.tagged("-at_install", "post_install")
class TestPortalControllerCommon(TestControllerCommon):
    def _get_sign_token_params(self, record):
        access_token = record._portal_ensure_token()
        partner = record.env["res.partner"].create({"name": "Sign Partner"})
        _hash = record._sign_token(partner.id)
        token = {"token": access_token}
        bad_token = {"token": "incorrect token"}
        sign = {"hash": _hash, "pid": partner.id}
        bad_sign = {"hash": "incorrect hash", "pid": partner.id}
        return token, bad_token, sign, bad_sign, partner
