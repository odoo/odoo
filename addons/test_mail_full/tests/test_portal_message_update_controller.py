# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo.addons.mail.tests.test_message_update_controller import TestMessageUpdateControllerCommon


@odoo.tests.tagged("-at_install", "post_install")
class TestPortalMessageUpdateController(TestMessageUpdateControllerCommon):
    def test_message_update_portal(self):
        """Test Only Admin and Portal User can update a portal user message on a record with no assigned partner."""
        record = self.env["mail.test.portal.no.partner"].create({"name": "Test"})
        token, bad_token, sign, bad_sign, _ = record._get_sign_token_params()
        message = record.message_post(
            body=self.message_body,
            author_id=self.user_portal.partner_id.id,
            message_type="comment",
        )
        self._execute_subtests(
            message,
            (
                (self.user_public, False),
                (self.user_public, False, token),
                (self.user_public, False, sign),
                (self.guest, False),
                (self.guest, False, token),
                (self.guest, False, sign),
                (self.user_portal, False),
                (self.user_portal, False, bad_token),
                (self.user_portal, False, bad_sign),
                (self.user_portal, True, token),
                (self.user_portal, True, sign),
                (self.user_employee, False),
                (self.user_employee, False, token),
                (self.user_employee, False, sign),
                (self.user_demo, False),
                (self.user_demo, False, token),
                (self.user_demo, False, sign),
                (self.user_admin, True),
                (self.user_admin, True, bad_token),
                (self.user_admin, True, bad_sign),
                (self.user_admin, True, token),
                (self.user_admin, True, sign),
            ),
        )
