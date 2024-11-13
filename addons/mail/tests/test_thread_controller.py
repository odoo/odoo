# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.addons.mail.tests.common_controllers import MailControllerThreadCommon, MessagePostSubTestData


@tagged("-at_install", "post_install", "mail_controller")
class TestThreadController(MailControllerThreadCommon):

    def test_partner_message_post_access(self):
        """Test access of message_post on partner record."""
        record = self.env["res.partner"].create({"name": "Test Partner"})

        def test_access(user, allowed):
            return MessagePostSubTestData(user, allowed)

        self._execute_message_post_subtests(
            record,
            (
                test_access(self.user_public, False),
                test_access(self.guest, False),
                test_access(self.user_portal, False),
                # False because not base.group_partner_manager
                test_access(self.user_employee, False),
                test_access(self.user_demo, True),
                test_access(self.user_admin, True),
            ),
        )

    def test_partner_message_post_partner_ids(self):
        """Test partner_ids of message_post on partner record."""
        record = self.env["res.partner"].create({"name": "Test Partner"})
        partners = (
            self.user_portal + self.user_employee + self.user_demo + self.user_admin
        ).partner_id
        no_partner = self.env["res.partner"]

        def test_partners(user, allowed, exp_partners):
            return MessagePostSubTestData(
                user, allowed, partners=partners, exp_partners=exp_partners
            )

        self._execute_message_post_subtests(
            record,
            (
                test_partners(self.user_public, False, no_partner),
                test_partners(self.guest, False, no_partner),
                test_partners(self.user_portal, False, no_partner),
                # False because not base.group_partner_manager
                test_partners(self.user_employee, False, no_partner),
                test_partners(self.user_demo, True, partners),
                test_partners(self.user_admin, True, partners),
            ),
        )
