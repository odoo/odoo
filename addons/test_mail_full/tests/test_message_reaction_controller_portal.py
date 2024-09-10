# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo.addons.mail.tests.test_message_reaction_controller import (
    TestMessageReactionControllerCommon,
)


@odoo.tests.tagged("-at_install", "post_install")
class TestPortalMessageReactionController(TestMessageReactionControllerCommon):
    def test_message_reaction_portal_no_partner(self):
        """Test access of message reaction for portal without partner."""
        record = self.env["mail.test.portal.no.partner"].create({"name": "Test"})
        message = record.message_post(body="portal no partner")
        token = record._portal_ensure_token()
        sign_partner = self.env["res.partner"].create({"name": "Sign Partner"})
        _hash = record._sign_token(sign_partner.id)
        token_param = {"token": token}
        incorrect_token_param = {"token": "incorrect token"}
        hash_pid_param = {"hash": _hash, "pid": sign_partner.id}
        incorrect_hash_pid_param = {"hash": "incorrect hash", "pid": sign_partner.id}
        self._execute_subtests(
            message,
            (
                (self.no_user, False),
                (self.no_user, False, incorrect_token_param),
                (self.no_user, False, incorrect_hash_pid_param),
                # False because no portal partner, no guest
                (self.no_user, False, token_param),
                (self.no_user, True, hash_pid_param, {"partner": sign_partner}),
                (self.public_w_guest, False),
                (self.public_w_guest, False, incorrect_token_param),
                (self.public_w_guest, False, incorrect_hash_pid_param),
                (self.public_w_guest, True, token_param),
                (self.public_w_guest, True, hash_pid_param, {"partner": sign_partner}),
                (self.user_portal, False),
                (self.user_portal, False, incorrect_token_param),
                (self.user_portal, False, incorrect_hash_pid_param),
                (self.user_portal, True, token_param),
                (self.user_portal, True, hash_pid_param),
                (self.user_employee, True),
                (self.user_employee, True, incorrect_token_param),
                (self.user_employee, True, incorrect_hash_pid_param),
                (self.user_employee, True, token_param),
                (self.user_employee, True, hash_pid_param),
                (self.user_demo, True),
                (self.user_demo, True, incorrect_token_param),
                (self.user_demo, True, incorrect_hash_pid_param),
                (self.user_demo, True, token_param),
                (self.user_demo, True, hash_pid_param),
                (self.user_admin, True),
                (self.user_admin, True, incorrect_token_param),
                (self.user_admin, True, incorrect_hash_pid_param),
                (self.user_admin, True, token_param),
                (self.user_admin, True, hash_pid_param),
            ),
        )

    def test_message_reaction_portal_assigned_partner(self):
        """Test access of message reaction for portal with partner."""
        rec_partner = self.env["res.partner"].create({"name": "Record Partner"})
        record = self.env["mail.test.portal"].create({"name": "Test", "partner_id": rec_partner.id})
        message = record.message_post(body="portal with partner")
        token = record._portal_ensure_token()
        sign_partner = self.env["res.partner"].create({"name": "Sign Partner"})
        _hash = record._sign_token(sign_partner.id)
        token_param = {"token": token}
        incorrect_token_param = {"token": "incorrect token"}
        hash_pid_param = {"hash": _hash, "pid": sign_partner.id}
        incorrect_hash_pid_param = {"hash": "incorrect hash", "pid": sign_partner.id}
        self._execute_subtests(
            message,
            (
                (self.no_user, False),
                (self.no_user, False, incorrect_token_param),
                (self.no_user, False, incorrect_hash_pid_param),
                (self.no_user, True, token_param, {"partner": rec_partner}),
                (self.no_user, True, hash_pid_param, {"partner": sign_partner}),
                # sign has priority over token when both are provided
                (self.no_user, True, token_param | hash_pid_param, {"partner": sign_partner}),
                (self.public_w_guest, False),
                (self.public_w_guest, False, incorrect_token_param),
                (self.public_w_guest, False, incorrect_hash_pid_param),
                (self.public_w_guest, True, token_param, {"partner": rec_partner}),
                (self.public_w_guest, True, hash_pid_param, {"partner": sign_partner}),
                (self.public_w_guest, True, token_param | hash_pid_param, {"partner": sign_partner}),
                (self.user_portal, False),
                (self.user_portal, False, incorrect_token_param),
                (self.user_portal, False, incorrect_hash_pid_param),
                (self.user_portal, True, token_param),
                (self.user_portal, True, hash_pid_param),
                (self.user_employee, True),
                (self.user_employee, True, incorrect_token_param),
                (self.user_employee, True, incorrect_hash_pid_param),
                (self.user_employee, True, token_param),
                (self.user_employee, True, hash_pid_param),
                (self.user_demo, True),
                (self.user_demo, True, incorrect_token_param),
                (self.user_demo, True, incorrect_hash_pid_param),
                (self.user_demo, True, token_param),
                (self.user_demo, True, hash_pid_param),
                (self.user_admin, True),
                (self.user_admin, True, incorrect_token_param),
                (self.user_admin, True, incorrect_hash_pid_param),
                (self.user_admin, True, token_param),
                (self.user_admin, True, hash_pid_param),
            ),
        )
