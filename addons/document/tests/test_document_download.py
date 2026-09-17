import zipfile
from io import BytesIO

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests.common import HttpCase, TransactionCase, tagged
from odoo.tools import mute_logger

from .test_document_common import GIF, TEXT, TransactionCaseDocuments
from odoo.addons.base.tests.common import HttpCaseWithUserDemo


class TestDocumentsDownloadBlocked(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.viewer = cls.env["res.users"].create(
            {
                "name": "Blocked Viewer",
                "login": "round4_blocked_viewer",
                "group_ids": [
                    Command.link(cls.env.ref("document.group_documents_user").id)
                ],
            }
        )
        cls.editor = cls.env["res.users"].create(
            {
                "name": "Blocked Editor",
                "login": "round4_blocked_editor",
                "group_ids": [
                    Command.link(cls.env.ref("document.group_documents_user").id)
                ],
            }
        )
        cls.document = cls.env["document.document"].create(
            {
                "name": "confidential.txt",
                "type": "binary",
                "raw": b"secret",
                "is_download_blocked": True,
            }
        )
        cls.document.action_update_access_rights(
            partners={
                cls.viewer.partner_id: ("view", False),
                cls.editor.partner_id: ("edit", False),
            }
        )

    def test_a_viewer_may_not_download_but_an_editor_may(self):
        self.assertEqual(self.document.with_user(self.viewer).user_permission, "view")
        self.assertFalse(
            self.document.with_user(self.viewer)._is_download_allowed(),
            "a viewer must not be able to take a copy",
        )
        self.assertEqual(self.document.with_user(self.editor).user_permission, "edit")
        self.assertTrue(self.document.with_user(self.editor)._is_download_allowed())

    def test_an_unblocked_document_is_downloadable_by_viewers(self):
        open_document = self.env["document.document"].create(
            {"name": "public.txt", "type": "binary", "raw": b"open"}
        )
        open_document.action_update_access_rights(
            partners={self.viewer.partner_id: ("view", False)}
        )
        self.assertTrue(open_document.with_user(self.viewer)._is_download_allowed())

    def test_a_shortcut_follows_its_target(self):
        shortcut = self.document.with_user(self.editor).action_create_shortcut(
            location_user_folder_id="MY"
        )
        self.assertFalse(
            shortcut.with_user(self.viewer)._is_download_allowed(),
            "a shortcut must not be a way around the target's setting",
        )

    def test_the_setting_propagates_into_a_folder(self):
        folder = self.env["document.document"].create(
            {"name": "Restricted folder", "type": "folder"}
        )
        child = self.env["document.document"].create(
            {"name": "inside.txt", "type": "binary", "folder_id": folder.id}
        )

        folder.action_update_access_rights(is_download_blocked=True)
        child.invalidate_recordset()

        self.assertTrue(folder.is_download_blocked)
        self.assertTrue(child.is_download_blocked, "the contents are blocked too")

    def test_rejects_a_non_boolean(self):
        with self.assertRaises(UserError):
            self.document.action_update_access_rights(is_download_blocked="yes")


@tagged("post_install", "-at_install")
class TestDocumentsDownloadBlockedRoutes(HttpCase):
    def test_blocked_content_is_viewable_but_not_downloadable(self):
        document = self.env["document.document"].create(
            {
                "name": "watch-only.txt",
                "type": "binary",
                "raw": b"secret",
                "access_via_link": "view",
                "is_download_blocked": True,
            }
        )

        preview = self.url_open(
            f"/documents/content/{document.access_token}?download=false"
        )
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview.content, b"secret")

        download = self.url_open(f"/documents/content/{document.access_token}")
        self.assertEqual(download.status_code, 403)

    def test_blocked_children_are_left_out_of_a_folder_archive(self):
        folder = self.env["document.document"].create(
            {"name": "Mixed", "type": "folder", "access_via_link": "view"}
        )
        subfolder = self.env["document.document"].create(
            {
                "name": "Deeper",
                "type": "folder",
                "folder_id": folder.id,
                "access_via_link": "view",
            }
        )
        self.env["document.document"].create(
            [
                {
                    "name": "free.txt",
                    "type": "binary",
                    "folder_id": folder.id,
                    "access_via_link": "view",
                    "raw": b"free",
                },
                {
                    "name": "blocked.txt",
                    "type": "binary",
                    "folder_id": subfolder.id,
                    "access_via_link": "view",
                    "raw": b"blocked",
                    "is_download_blocked": True,
                },
            ]
        )

        response = self.url_open(f"/documents/content/{folder.access_token}")
        response.raise_for_status()

        names = set(zipfile.ZipFile(BytesIO(response.content)).namelist())
        self.assertIn("free.txt", names)
        self.assertNotIn(
            "Deeper/blocked.txt",
            names,
            "a blocked file must not ride along inside a folder download",
        )


class TestDocumentsAccessLog(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Log = cls.env["document.access.log"]
        cls.document = cls.env["document.document"].create(
            {"name": "Audited", "type": "binary", "raw": b"payload"}
        )
        cls.partner = cls.env["res.partner"].create({"name": "Auditee"})

    def _entries(self, action=None):
        domain = [("document_id", "=", self.document.id)]
        if action:
            domain.append(("action", "=", action))
        return self.Log.search(domain)

    def test_repeated_history_is_kept_where_last_access_date_overwrites(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "document.access_log_window", "0"
        )
        self.Log._log(self.document, self.partner, "view")
        self.Log._log(self.document, self.partner, "download")
        self.Log._log(self.document, self.partner, "download")

        self.assertEqual(len(self._entries()), 3)
        self.assertEqual(len(self._entries("download")), 2)

    def test_repeat_visits_are_coalesced_within_the_window(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "document.access_log_window", "3600"
        )
        for _ in range(5):
            self.Log._log(self.document, self.partner, "view")

        self.assertEqual(
            len(self._entries("view")), 1, "repeats inside the window collapse"
        )

        self.Log._log(self.document, self.partner, "download")
        self.assertEqual(len(self._entries("download")), 1)

    def test_window_is_per_document_and_per_partner(self):
        other_document = self.env["document.document"].create(
            {"name": "Other audited", "type": "binary", "raw": b"x"}
        )
        other_partner = self.env["res.partner"].create({"name": "Someone else"})

        self.Log._log(self.document | other_document, self.partner, "view")
        self.Log._log(self.document, other_partner, "view")

        self.assertEqual(len(self._entries("view")), 2, "one per partner")
        self.assertEqual(
            len(self.Log.search([("document_id", "=", other_document.id)])),
            1,
            "a batch logs every document in it",
        )

    def test_the_log_is_reachable_from_a_document(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "document.access_log_window", "0"
        )
        self.Log._log(self.document, self.partner, "download")

        action = self.document.action_view_access_log()

        self.assertEqual(action["res_model"], "document.access.log")
        self.assertEqual(action["domain"], [("document_id", "=", self.document.id)])
        self.assertEqual(
            self.env["document.access.log"].search(action["domain"]).action,
            "download",
        )

    def test_a_manager_only_sees_the_log_of_documents_they_can_reach(self):
        manager = self.env["res.users"].create(
            {
                "name": "Log Manager",
                "login": "round4_log_manager",
                "group_ids": [
                    Command.link(self.env.ref("document.group_documents_manager").id)
                ],
            }
        )
        private = self.env["document.document"].create(
            {
                "name": "Not for the manager",
                "type": "binary",
                "access_internal": "none",
                "access_via_link": "none",
                "owner_id": self.env.ref("base.user_admin").id,
            }
        )
        self.env["ir.config_parameter"].sudo().set_param(
            "document.access_log_window", "0"
        )
        self.Log._log(private, self.partner, "download")

        self.assertEqual(private.with_user(manager).user_permission, "none")
        self.assertFalse(
            self.env["document.access.log"]
            .with_user(manager)
            .search([("document_id", "=", private.id)]),
            "the log must not expose a document the manager cannot reach",
        )

    def test_retention_drops_old_entries_only(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "document.access_log_retention_days", "30"
        )
        self.env["ir.config_parameter"].sudo().set_param(
            "document.access_log_window", "0"
        )
        self.Log._log(self.document, self.partner, "view")
        recent = self._entries()
        old = self.Log.create(
            {
                "document_id": self.document.id,
                "partner_id": self.partner.id,
                "action": "download",
                "access_date": fields.Datetime.subtract(fields.Datetime.now(), days=90),
            }
        )

        removed, more = self.Log._gc_access_log()

        self.assertEqual(removed, 1)
        self.assertFalse(more)
        self.assertFalse(old.exists())
        self.assertTrue(recent.exists(), "entries inside the window are kept")


@tagged("post_install", "-at_install")
class TestDocumentsAccessLogRoutes(HttpCase):
    def test_a_preview_and_a_download_are_recorded_as_different_actions(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "document.access_log_window", "0"
        )
        document = self.env["document.document"].create(
            {
                "name": "shared.txt",
                "type": "binary",
                "raw": b"secret",
                "access_via_link": "view",
            }
        )
        Log = self.env["document.access.log"]

        preview = self.url_open(
            f"/documents/content/{document.access_token}?download=false"
        )
        preview.raise_for_status()
        entries = Log.search([("document_id", "=", document.id)])
        self.assertEqual(entries.mapped("action"), ["view"])

        download = self.url_open(f"/documents/content/{document.access_token}")
        download.raise_for_status()
        self.assertEqual(download.content, b"secret")

        entries = Log.search([("document_id", "=", document.id)])
        self.assertEqual(sorted(entries.mapped("action")), ["download", "view"])
        self.assertEqual(
            entries.partner_id,
            self.env.ref("base.public_user").partner_id,
            "an anonymous retrieval is still attributable to the link",
        )


@tagged("post_install", "-at_install")
class TestDocumentsZipShortcuts(HttpCaseWithUserDemo):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Document = cls.env["document.document"]
        cls.shared_folder = Document.create(
            {
                "name": "Shared",
                "type": "folder",
                "access_via_link": "view",
                "access_internal": "none",
            }
        )
        cls.target_folder = Document.create(
            {
                "name": "Target",
                "type": "folder",
                "access_via_link": "view",
                "access_internal": "none",
            }
        )
        cls.target_child = Document.create(
            {
                "name": "inside_target.txt",
                "type": "binary",
                "datas": TEXT,
                "folder_id": cls.target_folder.id,
                "access_via_link": "view",
            }
        )
        cls.nested_folder = Document.create(
            {
                "name": "Nested",
                "type": "folder",
                "folder_id": cls.target_folder.id,
                "access_via_link": "view",
            }
        )
        cls.nested_child = Document.create(
            {
                "name": "inside_nested.txt",
                "type": "binary",
                "datas": TEXT,
                "folder_id": cls.nested_folder.id,
                "access_via_link": "view",
            }
        )
        cls.shortcut = cls.target_folder.action_create_shortcut(
            location_user_folder_id=str(cls.shared_folder.id)
        )

    def _entries(self, document):
        response = self.url_open(
            f"/documents/content/{document.access_token}", allow_redirects=False
        )
        self.assertEqual(response.status_code, 200)
        return set(zipfile.ZipFile(BytesIO(response.content)).namelist())

    def test_folder_shortcut_carries_the_target_contents(self):
        entries = self._entries(self.shared_folder)

        self.assertIn("Target/", entries, "the shortcut itself is listed")
        self.assertIn(
            "Target/inside_target.txt",
            entries,
            "a shortcut to a folder downloaded as an EMPTY directory",
        )
        self.assertIn("Target/Nested/", entries)
        self.assertIn("Target/Nested/inside_nested.txt", entries)

    def test_folder_shortcut_hides_an_unreachable_target(self):
        self.target_child.access_via_link = "none"
        self.nested_folder.access_via_link = "none"

        entries = self._entries(self.shared_folder)

        self.assertIn("Target/", entries)
        self.assertNotIn("Target/inside_target.txt", entries)
        self.assertNotIn("Target/Nested/", entries)

    def test_folder_shortcut_cycle_terminates(self):
        self.env["document.document"].create(
            {
                "name": "loop",
                "type": "folder",
                "folder_id": self.target_folder.id,
                "access_via_link": "view",
            }
        )
        self.shared_folder.action_create_shortcut(
            location_user_folder_id=str(self.target_folder.id)
        )

        entries = self._entries(self.shared_folder)

        self.assertIn("Target/inside_target.txt", entries)


@tagged("post_install", "-at_install")
class TestDocumentsDownloadAudit(HttpCase, TransactionCaseDocuments):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.doc_user.password = "doc_user_pwd"
        cls.audit_folder = cls.env["document.document"].create(
            {
                "type": "folder",
                "name": "audit folder",
                "owner_id": cls.doc_user.id,
                "access_internal": "edit",
            }
        )
        cls.audit_a, cls.audit_b = cls.env["document.document"].create(
            [
                {
                    "type": "binary",
                    "name": f"audit {letter}.gif",
                    "datas": GIF,
                    "mimetype": "image/gif",
                    "folder_id": cls.audit_folder.id,
                    "owner_id": cls.doc_user.id,
                }
                for letter in ("a", "b")
            ]
        )

    def _downloaded(self, documents):
        return (
            self.env["document.access.log"]
            .search(
                [
                    ("document_id", "in", documents.ids),
                    ("action", "=", "download"),
                ]
            )
            .document_id
        )

    def test_zip_route_records_every_document_it_ships(self):
        self.authenticate("documents@example.com", "doc_user_pwd")
        both = self.audit_a | self.audit_b
        self.assertFalse(self._downloaded(both))
        response = self.url_open(
            f"/documents/zip?file_ids={self.audit_a.id},{self.audit_b.id}"
            "&zip_name=audit.zip"
        )
        response.raise_for_status()
        self.assertEqual(response.headers["Content-Type"], "application/zip")
        self.assertEqual(self._downloaded(both), both)

    def test_folder_download_records_its_contents_too(self):
        self.authenticate("documents@example.com", "doc_user_pwd")
        response = self.url_open(
            f"/documents/content/{self.audit_folder.access_token}?download=true"
        )
        response.raise_for_status()
        whole_tree = self.audit_folder | self.audit_a | self.audit_b
        self.assertEqual(self._downloaded(whole_tree), whole_tree)

    def test_folder_token_is_never_served_read_only(self):
        from odoo.addons.document.controllers.document import ShareRoute

        self.authenticate("documents@example.com", "doc_user_pwd")
        response = self.url_open(
            f"/documents/content/{self.audit_folder.access_token}?download=false"
        )
        response.raise_for_status()
        self.assertEqual(response.headers["Content-Type"], "application/zip")
        self.assertTrue(self._downloaded(self.audit_folder))
        self.assertEqual(
            ShareRoute._split_access_token(self.audit_folder.access_token),
            (self.audit_folder.document_token, self.audit_folder.id),
        )

    def test_split_access_token_refuses_junk(self):
        for junk in ("", "no-separator", "oFF", "abco0", "abco-1", None):
            with self.subTest(token=junk):
                from odoo.addons.document.controllers.document import ShareRoute

                self.assertEqual(ShareRoute._split_access_token(junk), ("", 0))


@tagged("post_install", "-at_install")
class TestDocumentsLastAccessUpsert(TransactionCaseDocuments):
    @mute_logger("odoo.db.cursor")
    def test_upsert_last_access_date_idempotent(self):
        from odoo.addons.document.controllers.document import ShareRoute

        doc = self.document_gif
        env = self.env(user=self.internal_user)
        self.env["document.access"].sudo().search(
            [
                ("document_id", "=", doc.id),
                ("partner_id", "=", self.internal_user.partner_id.id),
            ]
        ).unlink()
        created_first = ShareRoute._upsert_last_access_date(env, doc)
        self.assertTrue(created_first, "first access should report a creation")
        created_second = ShareRoute._upsert_last_access_date(env, doc)
        self.assertFalse(created_second, "second access should be an update, no error")
        rows = (
            self.env["document.access"]
            .sudo()
            .search(
                [
                    ("document_id", "=", doc.id),
                    ("partner_id", "=", self.internal_user.partner_id.id),
                ]
            )
        )
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows.last_access_date)


@tagged("post_install", "-at_install")
class TestDocumentsDownloadBlockedLinkEditor(HttpCase):
    """`is_download_blocked` withholds content from viewers, not from editors.

    The field's own help says editors are unaffected because they can replace
    the content anyway, so withholding it from them means nothing. An `edit`
    link makes *every* reader of that document an editor -- including the
    unauthenticated visitor the document-request flow is built around, whose
    `user_permission` is structurally "none" because
    `_search_user_permission` short-circuits to FALSE for the public user.
    """

    def test_a_public_link_editor_may_download_a_blocked_document(self):
        document = self.env["document.document"].create(
            {
                "name": "fill-me-in.txt",
                "type": "binary",
                "raw": b"secret",
                "access_via_link": "edit",
                "is_download_blocked": True,
            }
        )

        response = self.url_open(f"/documents/content/{document.access_token}")

        self.assertEqual(
            response.status_code,
            200,
            "an editor reached through the link may take the content they are "
            "allowed to overwrite",
        )
        self.assertEqual(response.content, b"secret")

    def test_a_public_link_viewer_still_may_not(self):
        """The negative control: the block still blocks the audience it is for."""
        document = self.env["document.document"].create(
            {
                "name": "watch-only.txt",
                "type": "binary",
                "raw": b"secret",
                "access_via_link": "view",
                "is_download_blocked": True,
            }
        )

        self.assertEqual(
            self.url_open(f"/documents/content/{document.access_token}").status_code,
            403,
        )

    def test_a_blocked_document_in_a_link_edit_folder_rides_along_in_the_zip(self):
        folder = self.env["document.document"].create(
            {"name": "Dropbox", "type": "folder", "access_via_link": "edit"}
        )
        self.env["document.document"].create(
            {
                "name": "blocked.txt",
                "type": "binary",
                "folder_id": folder.id,
                "access_via_link": "edit",
                "raw": b"blocked",
                "is_download_blocked": True,
            }
        )

        response = self.url_open(f"/documents/content/{folder.access_token}")
        response.raise_for_status()

        self.assertIn(
            "blocked.txt",
            set(zipfile.ZipFile(BytesIO(response.content)).namelist()),
        )


@tagged("post_install", "-at_install")
class TestDocumentsLinkEditPermissionInvariant(TransactionCase):
    """Where `access_via_link` is "edit", `user_permission` is never "view".

    `_is_download_allowed` leans on this: it may answer from `access_via_link`
    alone only because no principal can hold a *viewer* permission on such a
    document. Every branch of `_direct_user_permission_domain` that yields
    "view" also requires `access_via_link in ("none", "view")`, so the value is
    "edit" or "none" and nothing between. Should that stop being true, the
    download gate silently starts exempting genuine viewers.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        other_company = cls.env["res.company"].create({"name": "Invariant Co"})

        def user(login, groups, companies=None):
            values = {
                "name": login,
                "login": login,
                "group_ids": [Command.set([cls.env.ref(group).id for group in groups])],
            }
            if companies:
                # Keep the main company in `company_ids` and merely make the
                # other one current: a user belonging ONLY to a fresh company
                # trips `digest` at create time, which is not what is under test.
                values["company_ids"] = [
                    Command.set([cls.env.company.id, *(c.id for c in companies)])
                ]
                values["company_id"] = companies[0].id
            return cls.env["res.users"].create(values)

        cls.principals = {
            "public": cls.env.ref("base.public_user"),
            "portal": user("inv_portal", ["base.group_portal"]),
            "internal": user(
                "inv_internal",
                ["base.group_user", "document.group_documents_user"],
            ),
            "manager": user(
                "inv_manager",
                ["base.group_user", "document.group_documents_manager"],
            ),
            "system": user(
                "inv_system",
                ["base.group_user", "document.group_documents_system"],
            ),
            "other_company": user(
                "inv_other_company",
                ["base.group_user", "document.group_documents_user"],
                [other_company],
            ),
        }
        cls.companies = [cls.env.company, other_company, None]

    def _permissions_on(self, access_via_link):
        seen = []
        for access_internal in ("none", "view", "edit"):
            for hidden in (False, True):
                for role in (None, "view", "edit"):
                    for company in self.companies:
                        document = self.env["document.document"].create(
                            {
                                "name": "invariant.txt",
                                "type": "binary",
                                "raw": b"x",
                                "access_via_link": access_via_link,
                                "access_internal": access_internal,
                                "is_access_via_link_hidden": hidden,
                                "company_id": company.id if company else False,
                            }
                        )
                        if role:
                            self.env["document.access"].sudo().create(
                                [
                                    {
                                        "document_id": document.id,
                                        "partner_id": user.partner_id.id,
                                        "role": role,
                                    }
                                    for label, user in self.principals.items()
                                    if label != "public"
                                ]
                            )
                        self.env.flush_all()
                        self.env.invalidate_all()
                        for label, user in self.principals.items():
                            seen.append(
                                (
                                    label,
                                    access_internal,
                                    hidden,
                                    role,
                                    document.with_user(user)
                                    .sudo(False)
                                    .user_permission,
                                )
                            )
                        document.sudo().unlink()
        return seen

    def test_a_link_editor_document_admits_no_viewer(self):
        seen = self._permissions_on("edit")
        viewers = [row for row in seen if row[-1] == "view"]

        self.assertTrue(seen, "the sweep must actually measure something")
        self.assertFalse(
            viewers,
            f"{len(viewers)} of {len(seen)} principal/configuration pairs hold "
            f"'view' on a link-edit document; _is_download_allowed would exempt "
            f"them. First: {viewers[:3]}",
        )

    def test_the_sweep_can_see_a_viewer_at_all(self):
        """Negative control: without it, an empty result proves nothing."""
        self.assertTrue(
            [row for row in self._permissions_on("view") if row[-1] == "view"],
            "the same sweep over a link-VIEW document must find viewers, or it "
            "is not capable of detecting the thing the other test asserts",
        )


@tagged("post_install", "-at_install")
class TestDocumentsDownloadBlockedInlineBypass(HttpCase):
    """`is_download_blocked` must not key on a parameter the caller chooses.

    The gate used to sit inside `if download:`, and `download` is a query
    parameter. `GET /documents/content/<token>?download=0` answered 200 with the
    whole file, its real `Content-Type: application/zip` and
    `Content-Disposition: inline; filename=payroll.zip` -- a download with one
    header changed -- and, because `_log_download` sits in the same skipped
    branch, `document.access.log` held no row for it either. The block neither
    blocked nor recorded that it had not.

    Serving inline differs from handing over only for content the browser
    renders in place; that is the line these tests pin.
    """

    def _blocked(self, name, raw, mimetype):
        document = self.env["document.document"].create(
            {
                "name": name,
                "type": "binary",
                "raw": raw,
                "access_via_link": "view",
                "is_download_blocked": True,
            }
        )
        document.attachment_id.sudo().mimetype = mimetype
        return document

    def _log_rows(self, document):
        return (
            self.env["document.access.log"]
            .sudo()
            .search_count([("document_id", "=", document.id)])
        )

    def test_a_blocked_archive_is_not_handed_over_inline(self):
        document = self._blocked("payroll.zip", b"PK\x03\x04secret", "application/zip")

        inline = self.url_open(f"/documents/content/{document.access_token}?download=0")

        self.assertEqual(
            inline.status_code,
            403,
            "a zip is not rendered in place, so serving it inline is the "
            "download the block exists to refuse",
        )
        self.assertNotIn(b"secret", inline.content)

    def test_a_blocked_document_the_browser_renders_is_still_previewable(self):
        """The control: the block is a viewing restriction, not a reading one."""
        document = self._blocked("watch.txt", b"secret", "text/plain")

        inline = self.url_open(f"/documents/content/{document.access_token}?download=0")

        self.assertEqual(inline.status_code, 200)
        self.assertEqual(inline.content, b"secret")

    def test_the_inline_path_is_recorded_in_the_access_log(self):
        """A retrieval that leaves no trace is worse than one that is refused."""
        document = self._blocked("watch2.txt", b"secret", "text/plain")
        self.assertEqual(self._log_rows(document), 0)

        self.url_open(
            f"/documents/content/{document.access_token}?download=0"
        ).raise_for_status()

        self.assertEqual(
            self._log_rows(document),
            1,
            "reading a document's bytes must appear in its access log whether "
            "the caller asked for an attachment or not",
        )

    def test_the_textual_thumbnail_route_takes_the_same_gate(self):
        """Two of its branches stream the WHOLE file, not a 4 KB head.

        The route's normal answer is the first 4 KB re-wrapped in HTML, which is
        looking rather than taking and stays ungated. Its `text/html` branch and
        its empty-prefix branch instead hand back `stream.prepare_response`, the
        same bytes `/documents/content` serves, so they answer the same question
        and now take the same gate.

        `is_mimetype_textual` and the inline-rendered set are not the same list
        -- `application/xml` and `application/documents-email` are textual and
        are not rendered in place -- so this is the seam that reopens if either
        list moves.
        """
        rendered = self._blocked("page.html", b"<b>secret</b>", "text/html")
        self.assertEqual(
            self.url_open(
                f"/documents/thumbnail_textual/{rendered.access_token}"
            ).status_code,
            200,
            "text/html IS rendered in place, so the whole-file branch is the "
            "preview and stays reachable",
        )

        opaque = self._blocked("empty.xml", b"", "application/xml")
        self.assertEqual(
            self.url_open(
                f"/documents/thumbnail_textual/{opaque.access_token}"
            ).status_code,
            403,
            "with no prefix to render, the route falls through to serving the "
            "file itself, which for a type the browser will not render is the "
            "download the block refuses",
        )

    def test_an_unblocked_document_is_unaffected_on_every_path(self):
        """Negative control: the gate must bite only where the block is set."""
        document = self.env["document.document"].create(
            {
                "name": "open.zip",
                "type": "binary",
                "raw": b"PK\x03\x04open",
                "access_via_link": "view",
            }
        )
        document.attachment_id.sudo().mimetype = "application/zip"

        for suffix in ("", "?download=0"):
            with self.subTest(suffix=suffix):
                response = self.url_open(
                    f"/documents/content/{document.access_token}{suffix}"
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.content, b"PK\x03\x04open")
