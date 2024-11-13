from odoo.addons.mail.tests.common_controllers import MailControllerReactionCommon
from odoo.addons.portal.tests.test_portal_controller_common import TestPortalControllerCommon
from odoo.tests import tagged


@tagged("-at_install", "post_install", "mail_controller")
class TestPortalMessageReactionController(MailControllerReactionCommon, TestPortalControllerCommon):

    def test_message_reaction_portal_no_partner(self):
        """Test access of message reaction for portal without partner."""
        record = self.env["mail.test.portal.no.partner"].create({"name": "Test"})
        token, bad_token, sign, bad_sign, partner = self._get_sign_token_params(record)
        message = record.message_post(body="portal no partner")
        self._execute_subtests(
            message,
            (
                (self.user_public, False),
                (self.user_public, False, bad_token),
                (self.user_public, False, bad_sign),
                # False because no portal partner, no guest
                (self.user_public, False, token),
                (self.user_public, True, sign, {"partner": partner}),
                (self.guest, False),
                (self.guest, False, bad_token),
                (self.guest, False, bad_sign),
                (self.guest, True, token),
                (self.guest, True, sign, {"partner": partner}),
                (self.user_portal, False),
                (self.user_portal, False, bad_token),
                (self.user_portal, False, bad_sign),
                (self.user_portal, True, token),
                (self.user_portal, True, sign),
                (self.user_employee, True),
                (self.user_employee, True, bad_token),
                (self.user_employee, True, bad_sign),
                (self.user_employee, True, token),
                (self.user_employee, True, sign),
                (self.user_demo, True),
                (self.user_demo, True, bad_token),
                (self.user_demo, True, bad_sign),
                (self.user_demo, True, token),
                (self.user_demo, True, sign),
                (self.user_admin, True),
                (self.user_admin, True, bad_token),
                (self.user_admin, True, bad_sign),
                (self.user_admin, True, token),
                (self.user_admin, True, sign),
            ),
        )

    def test_message_reaction_portal_assigned_partner(self):
        """Test access of message reaction for portal with partner."""
        rec_partner = self.env["res.partner"].create({"name": "Record Partner"})
        record = self.env["mail.test.portal"].create({"name": "Test", "partner_id": rec_partner.id})
        message = record.message_post(body="portal with partner")
        token = record._portal_ensure_token()
        partner = self.env["res.partner"].create({"name": "Sign Partner"})
        _hash = record._sign_token(partner.id)
        token_param = {"token": token}
        incorrect_token_param = {"token": "incorrect token"}
        hash_pid_param = {"hash": _hash, "pid": partner.id}
        incorrect_hash_pid_param = {"hash": "incorrect hash", "pid": partner.id}
        self._execute_subtests(
            message,
            (
                (self.user_public, False),
                (self.user_public, False, incorrect_token_param),
                (self.user_public, False, incorrect_hash_pid_param),
                (self.user_public, True, token_param, {"partner": rec_partner}),
                (self.user_public, True, hash_pid_param, {"partner": partner}),
                # sign has priority over token when both are provided
                (self.user_public, True, token_param | hash_pid_param, {"partner": partner}),
                (self.guest, False),
                (self.guest, False, incorrect_token_param),
                (self.guest, False, incorrect_hash_pid_param),
                (self.guest, True, token_param, {"partner": rec_partner}),
                (self.guest, True, hash_pid_param, {"partner": partner}),
                (self.guest, True, token_param | hash_pid_param, {"partner": partner}),
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
