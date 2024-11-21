# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo.addons.mail.tests.test_thread_controller import (
    MessagePostSubTestData,
    TestThreadControllerCommon,
)


@odoo.tests.tagged("-at_install", "post_install")
class TestPortalThreadController(TestThreadControllerCommon):
    def test_message_post_access_portal_no_partner(self):
        """Test access of message post for portal without partner."""
        record = self.env["mail.test.portal.no.partner"].create({"name": "Test"})
        access_token = record._portal_ensure_token()
        partner = self.env["res.partner"].create({"name": "Sign Partner"})
        _hash = record._sign_token(partner.id)
        token = {"token": access_token}
        bad_token = {"token": "incorrect token"}
        sign = {"hash": _hash, "pid": partner.id}
        bad_sign = {"hash": "incorrect hash", "pid": partner.id}

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
                test_access(self.user_demo, True),
                test_access(self.user_demo, True, route_kw=bad_token),
                test_access(self.user_demo, True, route_kw=bad_sign),
                test_access(self.user_demo, True, route_kw=token),
                test_access(self.user_demo, True, route_kw=sign),
                test_access(self.user_admin, True),
                test_access(self.user_admin, True, route_kw=bad_token),
                test_access(self.user_admin, True, route_kw=bad_sign),
                test_access(self.user_admin, True, route_kw=token),
                test_access(self.user_admin, True, route_kw=sign),
            ),
        )

    def test_message_post_access_portal_assigned_partner(self):
        """Test access of message post for portal with partner."""
        rec_partner = self.env["res.partner"].create({"name": "Record Partner"})
        record = self.env["mail.test.portal"].create({"name": "Test", "partner_id": rec_partner.id})
        access_token = record._portal_ensure_token()
        partner = self.env["res.partner"].create({"name": "Sign Partner"})
        _hash = record._sign_token(partner.id)
        token = {"token": access_token}
        bad_token = {"token": "incorrect token"}
        sign = {"hash": _hash, "pid": partner.id}
        bad_sign = {"hash": "incorrect hash", "pid": partner.id}

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
                test_access(self.user_demo, True),
                test_access(self.user_demo, True, route_kw=bad_token),
                test_access(self.user_demo, True, route_kw=bad_sign),
                test_access(self.user_demo, True, route_kw=token),
                test_access(self.user_demo, True, route_kw=sign),
                test_access(self.user_admin, True),
                test_access(self.user_admin, True, route_kw=bad_token),
                test_access(self.user_admin, True, route_kw=bad_sign),
                test_access(self.user_admin, True, route_kw=token),
                test_access(self.user_admin, True, route_kw=sign),
            ),
        )

    def test_message_post_partner_ids_portal(self):
        """Test partner_ids of message_post for portal record without partner.
        Only followers are allowed to be mentioned by non-internal users."""
        record = self.env["mail.test.portal.no.partner"].create({"name": "Test"})
        access_token = record._portal_ensure_token()
        partner = self.env["res.partner"].create({"name": "Sign Partner"})
        _hash = record._sign_token(partner.id)
        token = {"token": access_token}
        bad_token = {"token": "incorrect token"}
        sign = {"hash": _hash, "pid": partner.id}
        bad_sign = {"hash": "incorrect hash", "pid": partner.id}
        all_partners = (
            self.user_portal + self.user_employee + self.user_demo + self.user_admin
        ).partner_id
        record.message_subscribe(partner_ids=self.user_demo.partner_id.ids)
        followers = self.user_demo.partner_id

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
                test_partners(self.user_demo, True, all_partners),
                test_partners(self.user_demo, True, all_partners, route_kw=bad_token),
                test_partners(self.user_demo, True, all_partners, route_kw=bad_sign),
                test_partners(self.user_demo, True, all_partners, route_kw=token),
                test_partners(self.user_demo, True, all_partners, route_kw=sign),
                test_partners(self.user_admin, True, all_partners),
                test_partners(self.user_admin, True, all_partners, route_kw=bad_token),
                test_partners(self.user_admin, True, all_partners, route_kw=bad_sign),
                test_partners(self.user_admin, True, all_partners, route_kw=token),
                test_partners(self.user_admin, True, all_partners, route_kw=sign),
            ),
        )
