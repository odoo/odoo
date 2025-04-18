from itertools import product

import odoo
from odoo.addons.mail.tests.common_controllers import MailControllerAttachmentCommon


@odoo.tests.tagged("-at_install", "post_install", "mail_controller")
class TestPortalAttachmentController(MailControllerAttachmentCommon):

    def test_attachment_upload_portal(self):
        """Test access to upload an attachment on portal"""
        record = self.env["mail.test.portal.no.partner"].create({"name": "Test"})
        token, bad_token, sign, bad_sign, _ = self._get_sign_token_params(record)
        self._execute_subtests_upload(
            record,
            (
                (self.user_public, False),
                (self.user_public, True, token),
                (self.user_public, True, sign),
                (self.guest, False),
                (self.guest, True, token),
                (self.guest, True, sign),
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
                (self.user_admin, True),
                (self.user_admin, True, bad_token),
                (self.user_admin, True, bad_sign),
                (self.user_admin, True, token),
                (self.user_admin, True, sign),
            ),
        )

    def test_independent_attachment_delete_portal(self):
        """Test access to delete an attachment on portal"""
        # Subtest format: (user, token, {"route_kw": security params})
        record = self.env["mail.test.portal"].create({"name": "Test"})
        token, bad_token, sign, bad_sign, _ = self._get_sign_token_params(record)
        route_kws = (
            {"route_kw": token},
            {"route_kw": sign},
            {"route_kw": bad_token},
            {"route_kw": bad_sign},
        )
        self._execute_subtests_delete(
            product(
                (self.guest, self.user_employee, self.user_portal, self.user_public),
                (self.WITH_TOKEN, self.NO_TOKEN),
                route_kws,
            ),
            allowed=False,
        )
        self._execute_subtests_delete(
            product(self.user_admin, (self.WITH_TOKEN, self.NO_TOKEN), route_kws),
            allowed=True,
        )

    def test_attachment_delete_portal_linked_to_thread(self):
        """Test access to delete an attachment on portal associated with a thread"""
        record = self.env["mail.test.portal"].create({"name": "Test"})
        token, bad_token, sign, bad_sign, _ = self._get_sign_token_params(record)
        # Subtest format: (user, token, {"route_kw": security params})
        route_kws = (
            {},
            {"route_kw": token},
            {"route_kw": sign},
            {"route_kw": bad_token},
            {"route_kw": bad_sign},
        )
        self._execute_subtests_delete(
            product(
                (self.guest, self.user_portal, self.user_public),
                (self.WITH_TOKEN, self.NO_TOKEN),
                route_kws,
            ),
            allowed=False,
            thread=record,
        )
        self._execute_subtests_delete(
            product(
                (self.user_admin, self.user_employee),
                (self.WITH_TOKEN, self.NO_TOKEN),
                route_kws,
            ),
            allowed=True,
            thread=record,
        )

    def test_attachment_delete_portal_no_partner(self):
        """Test access to delete an attachment on a portal document without partner which is
        associated with a message"""
        record = self.env["mail.test.portal.no.partner"].create({"name": "Test"})
        message = self.env["mail.message"].create({"model": record._name, "res_id": record.id})
        sign_token_params = self._get_sign_token_params(record)
        allowed_subtests, forbidden_subtests = self._get_delete_attachment_subtests(
            sign_token_params, False
        )
        self._execute_subtests_delete(
            allowed_subtests,
            allowed=True,
            message=message,
        )
        self._execute_subtests_delete(
            forbidden_subtests,
            allowed=False,
            message=message,
        )

    def test_attachment_delete_portal_assigned_partner(self):
        """Test access to delete an attachment on a portal document with a partner which is
        associated with a message"""
        record = self.env["mail.test.portal"].create({"name": "Test"})
        sign_token_params = self._get_sign_token_params(record)
        record.partner_id = sign_token_params[-1]
        message = self.env["mail.message"].create({"model": record._name, "res_id": record.id})
        allowed_subtests, forbidden_subtests = self._get_delete_attachment_subtests(
            sign_token_params, True
        )
        self._execute_subtests_delete(
            allowed_subtests,
            allowed=True,
            message=message,
        )
        self._execute_subtests_delete(
            forbidden_subtests,
            allowed=False,
            message=message,
        )

    def _get_delete_attachment_subtests(self, sign_token_params, specific_partner_result):
        token, bad_token, sign, bad_sign, doc_partner = sign_token_params
        # Subtest format: (user, token, {"author": message author, "route_kw": security params})
        portal_partner = self.user_portal.partner_id
        allowed_subtests = [
            (self.user_portal, self.NO_TOKEN, {"author": portal_partner, "route_kw": token}),
            (self.user_portal, self.WITH_TOKEN, {"author": portal_partner, "route_kw": token}),
            (self.user_portal, self.NO_TOKEN, {"author": portal_partner, "route_kw": sign}),
            (self.user_portal, self.WITH_TOKEN, {"author": portal_partner, "route_kw": sign}),
            (self.user_public, self.NO_TOKEN, {"author": doc_partner, "route_kw": sign}),
            (self.user_public, self.WITH_TOKEN, {"author": doc_partner, "route_kw": sign}),
        ]
        if specific_partner_result:
            allowed_subtests.extend(
                [
                    (self.user_public, self.NO_TOKEN, {"author": doc_partner, "route_kw": token}),
                    (self.user_public, self.WITH_TOKEN, {"author": doc_partner, "route_kw": token}),
                ]
            )
        forbidden_subtests = filter(
            lambda subtest: subtest not in allowed_subtests,
            product(
                (self.user_portal, self.user_public),
                (self.WITH_TOKEN, self.NO_TOKEN),
                [
                    {"author": author, "route_kw": route_kw}
                    for author in (None, portal_partner, doc_partner)
                    for route_kw in ({}, token, sign, bad_token, bad_sign)
                ],
            ),
        )
        return allowed_subtests, forbidden_subtests
