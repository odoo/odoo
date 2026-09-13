from urllib.parse import urlparse

from odoo import http
from odoo.exceptions import UserError
from odoo.tests import HttpCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestDocumentAccessRequest(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.owner = new_test_user(
            cls.env,
            login="doc_access_owner",
            groups="base.group_user,document.group_documents_user",
        )
        cls.asker = new_test_user(
            cls.env, login="doc_access_asker", groups="base.group_user"
        )
        cls.portal = new_test_user(
            cls.env, login="doc_access_portal", groups="base.group_portal"
        )
        cls.folder = cls.env["document.document"].create(
            {
                "type": "folder",
                "name": "Private Folder",
                "owner_id": cls.owner.id,
                "access_internal": "none",
                "access_via_link": "none",
            }
        )
        cls.child = cls.env["document.document"].create(
            {
                "type": "folder",
                "name": "Inside",
                "folder_id": cls.folder.id,
                "owner_id": cls.owner.id,
            }
        )

    def _row(self, request):
        return request.approver_ids.filtered(lambda row: row.user_id == self.owner)

    def _ask(self, user, role):
        return self.folder.with_user(user).sudo()._request_access(user.partner_id, role)

    def _permission(self, user, document=None):
        return (document or self.folder).with_user(user).user_permission

    def test_the_owner_approving_shares_the_folder_and_what_it_holds(self):
        request = self._ask(self.asker, "view")

        self.assertEqual(request.state, "pending")
        self.assertEqual(request.request_owner_id, self.asker)
        self.assertIn(self.owner, request.approver_ids.user_id)
        asked = request.approver_ids.filtered(lambda row: row._is_notifiable())
        self.assertEqual(asked.user_id, self.owner)
        request.with_user(self.owner).action_approve(approver=self._row(request))

        self.assertEqual(self._permission(self.asker), "view")
        self.assertEqual(self._permission(self.asker, self.child), "view")

    def test_an_edit_request_grants_edit(self):
        request = self._ask(self.asker, "edit")

        request.with_user(self.owner).action_approve(approver=self._row(request))

        self.assertEqual(self._permission(self.asker), "edit")

    def test_the_access_already_held_is_not_asked_for(self):
        self.folder.action_update_access_rights(
            partners={self.asker.partner_id: ("view", None)}
        )

        with self.assertRaises(UserError):
            self._ask(self.asker, "view")
        self.assertEqual(self._ask(self.asker, "edit").state, "pending")

    def test_only_view_or_edit_is_asked_for(self):
        with self.assertRaises(UserError):
            self._ask(self.asker, "own")

    def test_a_documents_administrator_may_decide_for_the_owner(self):
        administrator = new_test_user(
            self.env,
            login="doc_access_admin",
            groups="base.group_user,document.group_documents_manager",
        )
        request = self._ask(self.asker, "view")

        self.folder.with_user(administrator)._decide_access_request(
            self.asker.partner_id, "view", approve=True
        )

        self.assertEqual(request.state, "approved")
        self.assertEqual(self._permission(self.asker), "view")

    def test_refusing_shares_nothing(self):
        request = self._ask(self.asker, "view")

        request.with_user(self.owner).action_refuse(approver=self._row(request))

        self.assertEqual(request.state, "refused")
        self.assertEqual(self._permission(self.asker), "none")

    def test_an_internal_user_following_the_link_is_offered_a_request(self):
        self.authenticate("doc_access_asker", "doc_access_asker")
        token = self.folder.access_token

        response = self.url_open(f"/odoo/documents/{token}", allow_redirects=False)

        self.assertEqual(
            urlparse(response.headers["Location"]).path,
            f"/documents/request_access/{token}",
        )
        page = self.url_open(f"/documents/request_access/{token}")
        self.assertIn("Request to view", page.text)
        self.assertNotIn("Private Folder", page.text)

        self.url_open(
            f"/documents/request_access/{token}",
            data={"role": "edit", "csrf_token": http.Request.csrf_token(self)},
        )

        request = self.folder.sudo()._get_live_access_request(
            self.asker.partner_id, "edit"
        )
        self.assertEqual(request.request_owner_id, self.asker)
        page = self.url_open(f"/documents/request_access/{token}")
        self.assertIn("Your request to edit it is waiting", page.text)

    def test_a_portal_user_following_the_link_is_offered_a_request(self):
        self.authenticate("doc_access_portal", "doc_access_portal")
        token = self.folder.access_token

        response = self.url_open(f"/documents/{token}", allow_redirects=False)

        self.assertEqual(
            urlparse(response.headers["Location"]).path,
            f"/documents/request_access/{token}",
        )

    def test_someone_who_can_open_it_is_not_offered_a_request(self):
        self.authenticate("doc_access_owner", "doc_access_owner")
        token = self.folder.access_token

        response = self.url_open(
            f"/documents/request_access/{token}", allow_redirects=False
        )

        self.assertEqual(
            urlparse(response.headers["Location"]).path, f"/documents/{token}"
        )

    def test_a_wrong_token_offers_nothing(self):
        self.authenticate("doc_access_asker", "doc_access_asker")
        token = self.folder.access_token

        response = self.url_open(f"/documents/request_access/x{token}")

        self.assertEqual(response.status_code, 404)
        self.assertFalse(self.folder.sudo().approval_request_ids)
