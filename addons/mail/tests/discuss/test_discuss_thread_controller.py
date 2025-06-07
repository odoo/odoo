# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo.addons.mail.tests.test_thread_controller import (
    MessagePostSubTestData,
    TestThreadControllerCommon,
)


@odoo.tests.tagged("-at_install", "post_install")
class TestDiscussThreadController(TestThreadControllerCommon):
    def test_internal_channel_message_post_access(self):
        """Test access of message_post on internal channel."""
        channel = self.env["discuss.channel"].create({"name": "Internal Channel"})

        def test_access(user, allowed):
            return MessagePostSubTestData(user, allowed)

        self._execute_message_post_subtests(
            channel,
            (
                test_access(self.user_public, False),
                test_access(self.guest, False),
                test_access(self.user_portal, False),
                test_access(self.user_employee, True),
                test_access(self.user_demo, True),
                test_access(self.user_admin, True),
            ),
        )

    def test_public_channel_message_post_access(self):
        """Test access of message_post on public channel."""
        channel = self.env["discuss.channel"].create(
            {"name": "Public Channel", "group_public_id": None}
        )

        def test_access(user, allowed, exp_author=None):
            return MessagePostSubTestData(user, allowed, exp_author=exp_author)

        self._execute_message_post_subtests(
            channel,
            (
                test_access(self.user_public, True),
                test_access(self.guest, True),
                test_access(self.user_portal, True),
                test_access(self.user_employee, True),
                test_access(self.user_demo, True),
                test_access(self.user_admin, True),
            ),
        )

    def test_public_channel_message_post_partner_ids(self):
        """Test partner_ids of message_post on public channel.
        Only members are allowed to be mentioned by non-internal users."""
        channel = self.env["discuss.channel"].create(
            {"name": "Public Channel", "group_public_id": None}
        )
        channel.add_members(partner_ids=self.user_demo.partner_id.ids)
        partners = (
            self.user_portal + self.user_employee + self.user_demo + self.user_admin
        ).partner_id
        members = self.user_demo.partner_id

        def test_partners(user, allowed, exp_partners, exp_author=None):
            return MessagePostSubTestData(
                user, allowed, partners=partners, exp_author=exp_author, exp_partners=exp_partners
            )

        self._execute_message_post_subtests(
            channel,
            (
                test_partners(self.user_public, True, members),
                test_partners(self.guest, True, members),
                test_partners(self.user_portal, True, members),
                test_partners(self.user_employee, True, partners),
                test_partners(self.user_demo, True, partners),
                test_partners(self.user_admin, True, partners),
            ),
        )

    def test_public_channel_message_post_partner_emails(self):
        """Test partner_emails of message_post on public channel can only be
        used by users of base.group_partner_manager."""
        channel = self.env["discuss.channel"].create(
            {"name": "Public Channel", "group_public_id": None}
        )
        no_emails = []
        partner_emails = [self.user_demo.email, "test@example.com"]

        def test_emails(user, allowed, exp_emails, exp_author=None):
            return MessagePostSubTestData(
                user,
                allowed,
                partner_emails=partner_emails,
                exp_author=exp_author,
                exp_emails=exp_emails,
            )

        self._execute_message_post_subtests(
            channel,
            (
                test_emails(self.user_public, True, no_emails),
                test_emails(self.guest, True, no_emails),
                test_emails(self.user_portal, True, no_emails),
                # restricted because not base.group_partner_manager
                test_emails(self.user_employee, True, no_emails),
                test_emails(self.user_demo, True, partner_emails),
                test_emails(self.user_admin, True, partner_emails),
            ),
        )
