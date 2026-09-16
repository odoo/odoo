"""Regression tests for the round-3 documents audit (controllers + wizards)."""

import zipfile
from datetime import datetime, timedelta
from io import BytesIO

from odoo import Command, fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import HttpCase, TransactionCase, new_test_user, tagged

from odoo.addons.document.tests.test_document_common import (
    TEXT,
    TransactionCaseDocuments,
)

PRIVATE_CONTENT = b"top secret payroll data"
SHARED_CONTENT = b"legitimately link-shared content"


@tagged("post_install", "-at_install")
class TestDocumentsZipShortcutLeak(HttpCase):
    """A shortcut must never widen access to its target through ``_get_zip_response``.

    ``ShareRoute._get_folder_children`` searches in ``sudo``, so its permission
    clauses only constrain the *shortcut* record. Dereferencing
    ``shortcut_document_id`` in ``_get_zip_response`` therefore used to serve the
    target's real filename and full plaintext to anybody holding the enclosing
    folder's share link.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Doc = cls.env["document.document"]

        cls.internal_user = cls.env["res.users"].create(
            {
                "login": "audit3_internal",
                "name": "Audit3 Internal",
                "group_ids": [
                    Command.link(cls.env.ref("document.group_documents_user").id)
                ],
            }
        )

        # A folder shared through its link: this is the token the attacker holds.
        cls.shared_folder = Doc.create(
            {
                "type": "folder",
                "name": "shared folder",
                "access_internal": "edit",
                "access_via_link": "edit",
            }
        )
        # Private vault, unreachable both anonymously and for internal_user.
        cls.private_folder = Doc.create(
            {
                "type": "folder",
                "name": "private folder",
                "access_internal": "none",
                "access_via_link": "none",
            }
        )
        cls.private_target = Doc.create(
            {
                "type": "binary",
                "name": "private-target.txt",
                "folder_id": cls.private_folder.id,
                "access_internal": "none",
                "access_via_link": "none",
                "is_access_via_link_hidden": True,
                "raw": PRIVATE_CONTENT,
            }
        )
        # A target that *is* legitimately link-shared: must keep working.
        cls.shared_target = Doc.create(
            {
                "type": "binary",
                "name": "shared-target.txt",
                "folder_id": cls.private_folder.id,
                "access_internal": "view",
                "access_via_link": "view",
                "is_access_via_link_hidden": False,
                "raw": SHARED_CONTENT,
            }
        )
        # A plain (non-shortcut) file of the shared folder, always included.
        cls.shared_file = Doc.create(
            {
                "type": "binary",
                "name": "shared-file.txt",
                "folder_id": cls.shared_folder.id,
                "access_internal": "edit",
                "access_via_link": "view",
                "raw": TEXT,
            }
        )

        cls.leak_shortcut = cls.private_target.sudo().action_create_shortcut(
            str(cls.shared_folder.id)
        )
        cls.legit_shortcut = cls.shared_target.sudo().action_create_shortcut(
            str(cls.shared_folder.id)
        )
        # The shortcut carries permissive rights of its own while its target
        # stays private -- e.g. the target's rights were revoked afterwards.
        cls.leak_shortcut.sudo().write(
            {
                "access_internal": "edit",
                "access_via_link": "view",
                "is_access_via_link_hidden": False,
            }
        )

    def _zip_namelist(self, folder):
        res = self.url_open(f"/documents/content/{folder.access_token}")
        res.raise_for_status()
        self.assertEqual(res.headers["Content-Type"], "application/zip")
        with zipfile.ZipFile(BytesIO(res.content)) as res_zip:
            return sorted(res_zip.namelist()), b"".join(
                res_zip.read(name) for name in res_zip.namelist()
            )

    def test_zip_public_does_not_leak_shortcut_target(self):
        """Anonymous folder zip must skip a shortcut to a private document."""
        self.authenticate(None, None)
        names, blob = self._zip_namelist(self.shared_folder)

        self.assertNotIn(
            "private-target.txt",
            names,
            "the private target's filename leaked into the public zip",
        )
        self.assertNotIn(
            PRIVATE_CONTENT, blob, "the private target's content leaked into the zip"
        )
        # ... but do not over-block: the legitimately shared target stays in.
        self.assertEqual(names, ["shared-file.txt", "shared-target.txt"])
        self.assertIn(SHARED_CONTENT, blob)

    def test_zip_internal_does_not_leak_shortcut_target(self):
        """Same for an internal user with ``user_permission='none'`` on the target."""
        self.assertEqual(
            self.private_target.with_user(self.internal_user).user_permission,
            "none",
            "test setup: the target must be inaccessible to this user",
        )
        self.authenticate("audit3_internal", "audit3_internal")
        names, blob = self._zip_namelist(self.shared_folder)

        self.assertNotIn("private-target.txt", names)
        self.assertNotIn(PRIVATE_CONTENT, blob)
        self.assertIn("shared-target.txt", names)

    def test_zip_shortcut_target_own_token_is_refused(self):
        """Sanity check: the direct routes already refuse both tokens."""
        self.authenticate(None, None)
        for document in (self.private_target, self.leak_shortcut):
            with self.subTest(document=document.name):
                res = self.url_open(f"/documents/content/{document.access_token}")
                self.assertEqual(res.status_code, 404)


@tagged("post_install", "-at_install")
class TestDocumentsActivityExpirationSync(TransactionCaseDocuments):
    """``mail.activity.write`` must not re-date a *permanent* access grant."""

    def _prepare_request(self):
        """Create a document request and return (document, activity, access)."""
        wizard = self.env["document.request_wizard"].create(
            {
                "name": "Audit3 Request",
                "requestee_id": self.internal_user.partner_id.id,
                "folder_id": self.folder_a.id,
                "activity_date_deadline_range": 5,
            }
        )
        document = wizard.request_document()
        activity = document.request_activity_id
        access = self.env["document.access"].search(
            [
                ("document_id", "=", document.id),
                ("partner_id", "=", self.internal_user.partner_id.id),
            ]
        )
        self.assertTrue(access.expiration_date, "test setup: the grant expires")
        return document, activity, access

    def test_permanent_grant_is_never_expired(self):
        """A permanent (``expiration_date = False``) grant must stay permanent.

        Odoo renders ``!=`` as ``col != v OR col IS NULL``, so the sync domain
        used to match permanent grants too and silently gave them the deadline.
        """
        __, activity, access = self._prepare_request()
        # The requestee was subsequently granted *permanent* access (e.g. via
        # the sharing dialog).
        access.expiration_date = False

        # `action_reschedule_today` writes `date_deadline` unconditionally.
        activity.action_reschedule_today()

        self.assertFalse(
            access.expiration_date,
            "a permanent grant was silently turned into an expiring one",
        )

    def test_noop_deadline_write_does_not_resync_expiration(self):
        """Writing the *same* deadline must not snap the expiration back."""
        __, activity, access = self._prepare_request()
        activity.date_deadline = fields.Date.context_today(activity)
        # The grant was manually extended past the deadline.
        extended = datetime.combine(
            activity.date_deadline + timedelta(days=10), datetime.max.time()
        )
        access.expiration_date = extended

        # A no-op write: the deadline is already today.
        activity.action_reschedule_today()

        self.assertEqual(
            access.expiration_date,
            extended,
            "a no-op deadline write reset the requestee's expiration date",
        )

    def test_real_deadline_change_still_syncs_expiration(self):
        """Do not over-block: a genuine deadline change must still sync."""
        __, activity, access = self._prepare_request()
        new_deadline = activity.date_deadline + timedelta(days=3)

        activity.date_deadline = new_deadline

        self.assertEqual(
            access.expiration_date,
            datetime.combine(new_deadline, datetime.max.time()),
            "the requestee's expiring grant must follow the new deadline",
        )


@tagged("post_install", "-at_install")
class TestDocumentsRequestWizardSelfRequest(TransactionCaseDocuments):
    """Requesting a document from yourself must keep the permanent grant."""

    def test_self_request_keeps_permanent_grant(self):
        """When requester == requestee, the permanent grant must win."""
        document = (
            self.env["document.request_wizard"]
            .with_user(self.doc_user)
            .create(
                {
                    "name": "Self Request",
                    "requestee_id": self.doc_user.partner_id.id,
                    "folder_id": self.folder_a.id,
                    "activity_date_deadline_range": 5,
                }
            )
            .request_document()
        )
        access = self.env["document.access"].search(
            [
                ("document_id", "=", document.id),
                ("partner_id", "=", self.doc_user.partner_id.id),
            ]
        )
        self.assertEqual(len(access), 1)
        self.assertEqual(access.role, "edit")
        self.assertFalse(
            access.expiration_date,
            "the requester's permanent grant was overwritten by the expiring one",
        )


@tagged("post_install", "-at_install")
class TestDocumentsOperationBatch(TransactionCaseDocuments):
    """``_compute_destination_children_ids`` must pair wizards to folders by id."""

    def test_destination_children_are_not_shifted_in_batch(self):
        """Computing in batch must not swap one wizard's children for another's."""
        Doc = self.env["document.document"]
        child_a, child_b = Doc.create(
            [
                {
                    "type": "binary",
                    "name": f"child in {folder.name}",
                    "folder_id": folder.id,
                    "raw": TEXT,
                }
                for folder in (self.folder_a, self.folder_b)
            ]
        )
        # Reverse order on purpose: `search_fetch` returns `_order`, not this.
        wizards = self.env["document.operation"].create(
            [
                {"operation": "move", "destination": str(folder.id)}
                for folder in (self.folder_b, self.folder_a)
            ]
        )
        wizard_b, wizard_a = wizards
        wizards.invalidate_recordset(["destination_children_ids"])

        self.assertIn(child_b, wizard_b.destination_children_ids)
        self.assertNotIn(child_a, wizard_b.destination_children_ids)
        self.assertIn(child_a, wizard_a.destination_children_ids)
        self.assertNotIn(child_b, wizard_a.destination_children_ids)


@tagged("post_install", "-at_install")
class TestDocumentsLinkToRecordWizard(TransactionCaseDocuments):
    """Small hardening fixes of the link-to-record wizard."""

    def test_link_to_without_record_raises_user_error(self):
        """``link_to()`` is RPC-callable and must not raise AttributeError."""
        wizard = self.env["document.link_to_record_wizard"].create({})
        with self.assertRaises(UserError):
            wizard.link_to()

    def test_target_model_selection_uses_a_real_boolean(self):
        """The ``is_mail_thread`` domain must compare against a boolean."""
        models = dict(
            self.env["document.link_to_record_wizard"]._selection_target_model()
        )
        self.assertIn("res.partner", models)
        self.assertNotIn("document.document", models)
        self.assertNotIn(
            "ir.model.fields",
            models,
            "a non mail-thread model must not be offered as a link target",
        )

    def test_dead_field_is_gone(self):
        """``accessible_model_ids`` was dead code and must stay removed."""
        self.assertNotIn(
            "accessible_model_ids",
            self.env["document.link_to_record_wizard"]._fields,
        )


@tagged("post_install", "-at_install")
class TestDocumentsInboxAlias(TransactionCase):
    """The seeded Inbox alias must expose its parent document."""

    def test_inbox_alias_has_a_parent_model(self):
        """Without ``alias_parent_model_id`` the parent document is unreachable."""
        alias = self.env.ref(
            "document.document_inbox_folder_mail_alias", raise_if_not_found=False
        )
        if not alias:
            self.skipTest("Inbox alias not seeded in this database")
        self.assertEqual(alias.alias_parent_model_id.model, "document.document")
        self.assertEqual(
            alias.alias_parent_thread_id,
            self.env.ref("document.document_inbox_folder").id,
        )


@tagged("post_install", "-at_install")
class TestDocumentsOperationWizard(TransactionCaseDocuments):
    """`document.operation.action_confirm`, which nothing reached.

    Coverage over `document` and nine bridge modules -- 691 tests -- executed
    none of this method's four branches. It is what the Documents UI runs for
    Move, Duplicate to, Create shortcuts and Add attachment to Documents.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.operator = new_test_user(
            cls.env,
            login="operation_user",
            groups="base.group_user,document.group_documents_user",
        )
        cls.Operation = cls.env["document.operation"].with_user(cls.operator)
        cls.target_folder = (
            cls.env["document.document"]
            .with_user(cls.operator)
            .create({"name": "Target", "type": "folder"})
        )

    def _document(self, name="movable.txt"):
        return (
            self.env["document.document"]
            .with_user(self.operator)
            .create({"name": name, "type": "binary", "raw": b"payload"})
        )

    def _run(self, **values):
        wizard = self.Operation.create(
            {"destination": str(self.target_folder.id), **values}
        )
        wizard.action_confirm()
        return wizard

    def test_move_puts_the_documents_in_the_destination(self):
        document = self._document()

        self._run(operation="move", document_ids=[Command.set(document.ids)])

        self.assertEqual(document.folder_id, self.target_folder)

    def test_copy_leaves_the_original_where_it_was(self):
        document = self._document()

        self._run(operation="copy", document_ids=[Command.set(document.ids)])

        self.assertFalse(document.folder_id, "the original does not move")
        copies = self.env["document.document"].search(
            [("folder_id", "=", self.target_folder.id)]
        )
        self.assertEqual(len(copies), 1)
        self.assertEqual(copies.attachment_id.raw, b"payload")

    def test_shortcut_points_at_the_original(self):
        document = self._document()

        self._run(operation="shortcut", document_ids=[Command.set(document.ids)])

        shortcut = self.env["document.document"].search(
            [("folder_id", "=", self.target_folder.id)]
        )
        self.assertEqual(shortcut.shortcut_document_id, document)

    def test_add_a_file_attachment_copies_it_in(self):
        attachment = (
            self.env["ir.attachment"]
            .with_context(no_document=True)
            .create({"name": "report.txt", "type": "binary", "raw": b"content"})
        )

        self._run(operation="add", attachment_id=attachment.id)

        document = self.env["document.document"].search(
            [("folder_id", "=", self.target_folder.id)]
        )
        self.assertEqual(document.type, "binary")
        self.assertEqual(document.attachment_id.raw, b"content")
        self.assertNotEqual(
            document.attachment_id,
            attachment,
            "the source attachment is copied, not moved",
        )

    def test_add_a_url_attachment_keeps_its_address(self):
        """A url document keeps its address in its OWN url field.

        Copying only the attachment's `type` produced `type = "url"` with
        `url = False`: `/documents/content` then answers 404 because
        `_is_safe_redirect_url(False)` is False, and the entry silently points
        nowhere.
        """
        attachment = (
            self.env["ir.attachment"]
            .with_context(no_document=True)
            .create(
                {
                    "name": "Odoo",
                    "type": "url",
                    "url": "https://www.odoo.com/page/x",
                }
            )
        )

        self._run(operation="add", attachment_id=attachment.id)

        document = self.env["document.document"].search(
            [("folder_id", "=", self.target_folder.id)]
        )
        self.assertEqual(document.type, "url")
        self.assertEqual(document.url, "https://www.odoo.com/page/x")

    def test_add_a_url_attachment_odoo_cannot_serve_is_refused(self):
        """An `ir.attachment` may hold a relative url; a document may not.

        `_check_url` says a document url must be complete. Before, such an
        attachment became a url document with no url at all -- broken, and
        silently so. Refusing names the reason.
        """
        attachment = (
            self.env["ir.attachment"]
            .with_context(no_document=True)
            .create({"name": "Internal", "type": "url", "url": "/web/content/42"})
        )

        with self.assertRaises(ValidationError):
            self._run(operation="add", attachment_id=attachment.id)

    def test_add_without_an_attachment_is_refused(self):
        with self.assertRaises(UserError):
            self._run(operation="add")
