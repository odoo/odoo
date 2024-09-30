from odoo.addons.mail.tests.common_controllers import MailControllerThreadCommon, MessagePostSubTestData
from odoo.tests import tagged


@tagged("-at_install", "post_install", "mail_controller")
class TestPortalThreadController(MailControllerThreadCommon):
    def _check_fetched_messages(self, record, messages, allowed, route_kw):
        """Check which messages should be displayed in portal."""
        super()._check_fetched_messages(record, messages, allowed, route_kw)
        if allowed == "only_comments":
            if not self.env.user._is_internal():
                self._assert_fetched_messages(record, messages, route_kw)
            route_kw["in_portal"] = True
            self._assert_fetched_messages(record, messages, route_kw)

    def _assert_fetched_messages(self, record, messages, route_kw):
        fetched_data = self._message_fetch(record, route_kw)
        self.assertNotEqual(len(fetched_data["messages"]), len(messages))
        self.assertEqual(len(fetched_data["messages"]), 1)
        self.assertEqual(fetched_data["data"]["mail.message"][0].get("is_note"), False)

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

    def test_message_post_partner_ids_portal(self):
        """Test partner_ids of message_post for portal record without partner.
        Only followers are allowed to be mentioned by non-internal users."""
        record = self.env["mail.test.portal.no.partner"].create({"name": "Test"})
        token, bad_token, sign, bad_sign, partner = self._get_sign_token_params(record)
        all_partners = (
            self.user_portal + self.user_employee + self.user_admin
        ).partner_id
        record.message_subscribe(partner_ids=self.user_employee.partner_id.ids)
        followers = self.user_employee.partner_id

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
                test_partners(self.user_public, False, followers),
                test_partners(self.user_public, False, followers, route_kw=bad_token),
                test_partners(self.user_public, False, followers, route_kw=bad_sign),
                test_partners(self.user_public, True, followers, route_kw=token),
                test_partners(self.user_public, True, followers, route_kw=sign, exp_author=partner),
                test_partners(self.guest, False, followers),
                test_partners(self.guest, False, followers, route_kw=bad_token),
                test_partners(self.guest, False, followers, route_kw=bad_sign),
                test_partners(self.guest, True, followers, route_kw=token),
                test_partners(self.guest, True, followers, route_kw=sign, exp_author=partner),
                test_partners(self.user_portal, False, followers),
                test_partners(self.user_portal, False, followers, route_kw=bad_token),
                test_partners(self.user_portal, False, followers, route_kw=bad_sign),
                test_partners(self.user_portal, True, followers, route_kw=token),
                test_partners(self.user_portal, True, followers, route_kw=sign),
                test_partners(self.user_employee, True, all_partners),
                test_partners(self.user_employee, True, all_partners, route_kw=bad_token),
                test_partners(self.user_employee, True, all_partners, route_kw=bad_sign),
                test_partners(self.user_employee, True, all_partners, route_kw=token),
                test_partners(self.user_employee, True, all_partners, route_kw=sign),
            ),
        )

    def test_message_fetch_access_portal(self):
        record = self.env["mail.test.portal.no.partner"].create({"name": "Test"})
        token, bad_token, sign, bad_sign, _ = self._get_sign_token_params(record)
        self._execute_message_fetch_subtests(
            record,
            (
                (self.user_public, False),
                (self.user_public, False, bad_token),
                (self.user_public, False, bad_sign),
                (self.user_public, "only_comments", token),
                (self.user_public, "only_comments", sign),
                (self.guest, False),
                (self.guest, False, bad_token),
                (self.guest, False, bad_sign),
                (self.guest, "only_comments", token),
                (self.guest, "only_comments", sign),
                (self.user_portal, "only_comments"),
                (self.user_portal, "only_comments", bad_token),
                (self.user_portal, "only_comments", bad_sign),
                (self.user_portal, "only_comments", token),
                (self.user_portal, "only_comments", sign),
                (self.user_employee, "only_comments"),
                (self.user_employee, "only_comments", bad_token),
                (self.user_employee, "only_comments", bad_sign),
                (self.user_employee, "only_comments", token),
                (self.user_employee, "only_comments", sign),
                (self.user_admin, "only_comments"),
                (self.user_admin, "only_comments", bad_token),
                (self.user_admin, "only_comments", bad_sign),
                (self.user_admin, "only_comments", token),
                (self.user_admin, "only_comments", sign),
            ),
        )
