# Part of Odoo. See LICENSE file for full copyright and licensing details.

from itertools import product

from odoo.addons.mail.tests.common_controllers import MailControllerThreadCommon, MessagePostSubTestData
from odoo.tests import tagged


@tagged("-at_install", "post_install", "mail_controller")
class TestPortalThreadController(MailControllerThreadCommon):
    def _check_fetched_messages(self, record, messages, allowed, route_kw):
        """Check which messages should be displayed in portal."""
        super()._check_fetched_messages(record, messages, allowed, route_kw)
        if allowed == "only_comments":
            if not self.env.user._is_internal():
                self._fetch_and_assert_is_not_note(record, messages, route_kw)
            route_kw["only_portal"] = True
            self._fetch_and_assert_is_not_note(record, messages, route_kw)

    def _fetch_and_assert_is_not_note(self, record, messages, route_kw):
        fetched_data = self._message_fetch(record, route_kw)
        fetched_messages = fetched_data["data"]["mail.message"]
        self.assertNotEqual(len(fetched_messages), len(messages))
        self.assertEqual(len(fetched_messages), 1)
        self.assertMessageFields(
            fetched_messages[0], {"subtype_id": self.env.ref("mail.mt_comment").id}
        )

    def test_message_post_portal_no_partner(self):
        """Test access of message post for portal without partner."""
        record = self.env["mail.test.portal.no.partner"].create({"name": "Test"})
        token, bad_token, sign, bad_sign, partner = self._get_sign_token_params(record)

        def test_access(user, allowed, route_kw=None, exp_author=None):
            return MessagePostSubTestData(user, allowed, route_kw=route_kw, exp_author=exp_author)

        self._execute_message_post_subtests(
            record,
            (
                test_access(self.user_public, False),
                test_access(self.user_public, False, route_kw=bad_token),
                test_access(self.user_public, False, route_kw=bad_sign),
                test_access(self.user_public, True, route_kw=token),
                test_access(self.user_public, True, route_kw=sign, exp_author=partner),
                test_access(self.guest, False),
                test_access(self.guest, False, route_kw=bad_token),
                test_access(self.guest, False, route_kw=bad_sign),
                test_access(self.guest, True, route_kw=token),
                test_access(self.guest, True, route_kw=sign, exp_author=partner),
                test_access(self.user_portal, False),
                test_access(self.user_portal, False, route_kw=bad_token),
                test_access(self.user_portal, False, route_kw=bad_sign),
                test_access(self.user_portal, True, route_kw=token),
                test_access(self.user_portal, True, route_kw=sign),
                test_access(self.user_employee, True),
                test_access(self.user_employee, True, route_kw=bad_token),
                test_access(self.user_employee, True, route_kw=bad_sign),
                test_access(self.user_employee, True, route_kw=token),
                test_access(self.user_employee, True, route_kw=sign),
            ),
        )

    def test_message_post_portal_with_partner(self):
        """Test access of message post for portal with partner."""
        rec_partner = self.env["res.partner"].create({"name": "Record Partner"})
        record = self.env["mail.test.portal"].create({"name": "Test", "partner_id": rec_partner.id})
        token, bad_token, sign, bad_sign, partner = self._get_sign_token_params(record)

        def test_access(user, allowed, route_kw=None, exp_author=None):
            return MessagePostSubTestData(user, allowed, route_kw=route_kw, exp_author=exp_author)

        self._execute_message_post_subtests(
            record,
            (
                test_access(self.user_public, False),
                test_access(self.user_public, False, route_kw=bad_token),
                test_access(self.user_public, False, route_kw=bad_sign),
                test_access(self.user_public, True, route_kw=token, exp_author=rec_partner),
                test_access(self.user_public, True, route_kw=sign, exp_author=partner),
                # sign has priority over token when both are provided
                test_access(self.user_public, True, route_kw=token | sign, exp_author=partner),
                test_access(self.guest, False),
                test_access(self.guest, False, route_kw=bad_token),
                test_access(self.guest, False, route_kw=bad_sign),
                test_access(self.guest, True, route_kw=token, exp_author=rec_partner),
                test_access(self.guest, True, route_kw=sign, exp_author=partner),
                test_access(self.guest, True, route_kw=token | sign, exp_author=partner),
                test_access(self.user_portal, False),
                test_access(self.user_portal, False, route_kw=bad_token),
                test_access(self.user_portal, False, route_kw=bad_sign),
                test_access(self.user_portal, True, route_kw=token),
                test_access(self.user_portal, True, route_kw=sign),
                test_access(self.user_employee, True),
                test_access(self.user_employee, True, route_kw=bad_token),
                test_access(self.user_employee, True, route_kw=bad_sign),
                test_access(self.user_employee, True, route_kw=token),
                test_access(self.user_employee, True, route_kw=sign),
            ),
        )

    def test_message_post_partner_ids_mention_token(self):
        """Test partner_ids of message_post for portal record without partner.
        All users are allowed to mention with specific message_mention token."""
        record = self.env["mail.test.portal.no.partner"].create({"name": "Test"})
        token, bad_token, sign, bad_sign, partner = self._get_sign_token_params(record)
        all_partners = (
            self.user_portal + self.user_employee + self.user_admin
        ).partner_id
        record.message_subscribe(partner_ids=self.user_employee.partner_id.ids)

        def test_partners(user, allowed, exp_partners, route_kw=None, exp_author=None):
            return MessagePostSubTestData(
                user,
                allowed,
                partners=all_partners,
                route_kw=route_kw,
                exp_author=exp_author,
                exp_partners=exp_partners,
                add_mention_token=True,
            )

        self._execute_message_post_subtests(
            record,
            (
                test_partners(self.user_public, False, all_partners),
                test_partners(self.user_public, False, all_partners, route_kw=bad_token),
                test_partners(self.user_public, False, all_partners, route_kw=bad_sign),
                test_partners(self.user_public, True, all_partners, route_kw=token),
                test_partners(self.user_public, True, all_partners, route_kw=sign, exp_author=partner),
                test_partners(self.guest, False, all_partners),
                test_partners(self.guest, False, all_partners, route_kw=bad_token),
                test_partners(self.guest, False, all_partners, route_kw=bad_sign),
                test_partners(self.guest, True, all_partners, route_kw=token),
                test_partners(self.guest, True, all_partners, route_kw=sign, exp_author=partner),
                test_partners(self.user_portal, False, all_partners),
                test_partners(self.user_portal, False, all_partners, route_kw=bad_token),
                test_partners(self.user_portal, False, all_partners, route_kw=bad_sign),
                test_partners(self.user_portal, True, all_partners, route_kw=token),
                test_partners(self.user_portal, True, all_partners, route_kw=sign),
                test_partners(self.user_employee, True, all_partners),
                test_partners(self.user_employee, True, all_partners, route_kw=bad_token),
                test_partners(self.user_employee, True, all_partners, route_kw=bad_sign),
                test_partners(self.user_employee, True, all_partners, route_kw=token),
                test_partners(self.user_employee, True, all_partners, route_kw=sign),
            ),
        )

    def test_message_post_partner_ids_portal(self):
        """Test partner_ids of message_post for portal record without partner.
        Only internal users are allowed to mention without specific message_mention token."""
        record = self.env["mail.test.portal.no.partner"].create({"name": "Test"})
        token, bad_token, sign, bad_sign, partner = self._get_sign_token_params(record)
        all_partners = (
            self.user_portal + self.user_employee + self.user_admin
        ).partner_id
        record.message_subscribe(partner_ids=self.user_employee.partner_id.ids)

        def test_partners(user, allowed, exp_partners, route_kw=None, exp_author=None):
            return MessagePostSubTestData(
                user,
                allowed,
                partners=all_partners,
                route_kw=route_kw,
                exp_author=exp_author,
                exp_partners=exp_partners,
            )

        self._execute_message_post_subtests(
            record,
            (
                test_partners(self.user_public, False, self.env["res.partner"]),
                test_partners(self.user_public, False, self.env["res.partner"], route_kw=bad_token),
                test_partners(self.user_public, False, self.env["res.partner"], route_kw=bad_sign),
                test_partners(self.user_public, True, self.env["res.partner"], route_kw=token),
                test_partners(self.user_public, True, self.env["res.partner"], route_kw=sign, exp_author=partner),
                test_partners(self.guest, False, self.env["res.partner"]),
                test_partners(self.guest, False, self.env["res.partner"], route_kw=bad_token),
                test_partners(self.guest, False, self.env["res.partner"], route_kw=bad_sign),
                test_partners(self.guest, True, self.env["res.partner"], route_kw=token),
                test_partners(self.guest, True, self.env["res.partner"], route_kw=sign, exp_author=partner),
                test_partners(self.user_portal, False, self.env["res.partner"]),
                test_partners(self.user_portal, False, self.env["res.partner"], route_kw=bad_token),
                test_partners(self.user_portal, False, self.env["res.partner"], route_kw=bad_sign),
                test_partners(self.user_portal, True, self.env["res.partner"], route_kw=token),
                test_partners(self.user_portal, True, self.env["res.partner"], route_kw=sign),
                test_partners(self.user_employee, True, all_partners),
                test_partners(self.user_employee, True, all_partners, route_kw=bad_token),
                test_partners(self.user_employee, True, all_partners, route_kw=bad_sign),
                test_partners(self.user_employee, True, all_partners, route_kw=token),
                test_partners(self.user_employee, True, all_partners, route_kw=sign),
            ),
        )

    def test_message_fetch_access_portal(self):
        """Test access to fetch the messages on a portal record."""
        record = self.env["mail.test.portal.no.partner"].create({"name": "Test"})
        token, bad_token, sign, bad_sign, _ = self._get_sign_token_params(record)
        route_kws = ({}, token, bad_token, sign, bad_sign)
        # Subtest format: (user, security params)
        self._execute_message_fetch_subtests(
            product((self.guest, self.user_public), ({}, bad_token, bad_sign)),
            record,
            allowed=False,
        )
        self._execute_message_fetch_subtests(
            product((self.guest, self.user_public), (token, sign)), record, allowed="only_comments"
        )
        self._execute_message_fetch_subtests(
            product((self.user_admin, self.user_employee, self.user_portal), route_kws),
            record,
            allowed="only_comments",
        )
