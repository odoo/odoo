# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo.addons.mail.tests.test_message_update_controller import TestMessageUpdateControllerCommon


@odoo.tests.tagged("-at_install", "post_install")
class TestPortalMessageUpdateController(TestMessageUpdateControllerCommon):
    def test_message_update_portal(self):
        """Test Only Admin and Portal User can update a portal user message on a record with no assigned partner."""
        record = self.env["mail.test.portal.no.partner"].create({"name": "Test"})
        token = record._portal_ensure_token()
        partner = self.env["res.partner"].create({"name": "Sign Partner"})
        _hash = record._sign_token(partner.id)
        token_param = {"token": token}
        incorrect_token_param = {"token": "incorrect token"}
        hash_pid_param = {"hash": _hash, "pid": partner.id}
        incorrect_hash_pid_param = {"hash": "incorrect hash", "pid": partner.id}
        message = record.message_post(
            body=self.message_body,
            author_id=self.user_portal.partner_id.id,
            message_type="comment",
        )
        self._execute_subtests(
            message,
            (
                (self.user_public, False),
                (self.user_public, False, token_param),
                (self.user_public, False, hash_pid_param),
                (self.guest, False),
                (self.guest, False, token_param),
                (self.guest, False, hash_pid_param),
                (self.user_portal, False),
                (self.user_portal, False, incorrect_token_param),
                (self.user_portal, False, incorrect_hash_pid_param),
                (self.user_portal, True, token_param),
                (self.user_portal, True, hash_pid_param),
                (self.user_employee, False),
                (self.user_employee, False, token_param),
                (self.user_employee, False, hash_pid_param),
                (self.user_demo, False),
                (self.user_demo, False, token_param),
                (self.user_demo, False, hash_pid_param),
                (self.user_admin, True),
                (self.user_admin, True, incorrect_token_param),
                (self.user_admin, True, incorrect_hash_pid_param),
                (self.user_admin, True, token_param),
                (self.user_admin, True, hash_pid_param),
            ),
        )
