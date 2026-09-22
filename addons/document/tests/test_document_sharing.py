from datetime import timedelta

from dateutil.relativedelta import relativedelta

from odoo import Command, fields
from odoo.exceptions import AccessError
from odoo.tests import Form, freeze_time, users

from odoo.addons.document.tests.test_document_common import TransactionCaseDocuments
from odoo.addons.mail.tests.common import MockEmail


class TestDocumentsSharing(TransactionCaseDocuments, MockEmail):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.manager_doc, cls.user_doc = cls.env["document.document"].create(
            [
                {
                    "name": "Manager document",
                    "folder_id": cls.folder_a.id,
                    "owner_id": cls.document_manager.id,
                    "access_ids": False,
                },
                {
                    "name": "User document",
                    "folder_id": cls.folder_a.id,
                    "owner_id": cls.doc_user.id,
                    "access_ids": False,
                },
            ]
        )
        cls.manager_doc_shortcut, cls.user_doc_shortcut = cls.env[
            "document.document"
        ].create(
            [
                {
                    "name": "Manager document (shortcut)",
                    "shortcut_document_id": cls.manager_doc.id,
                },
                {
                    "name": "User document (shortcut)",
                    "shortcut_document_id": cls.user_doc.id,
                },
            ]
        )
        cls.partner_without_user = cls.env["res.partner"].create(
            {
                "name": "Dave",
                "email": "dave@odoo.com",
            }
        )
        cls.portal_user.email = "portal_user_doc_sharing@example.com"
        cls.portal_partner = cls.portal_user.partner_id
        cls.internal_user.email = "internal_doc_sharing@example.com"

    def set_documents_env_user_to_current(self):
        """Helper to ensure the env of the test documents are self.env.user (to work with @users decorator)."""
        self.manager_doc = self.manager_doc.with_user(self.env.user)
        self.user_doc = self.user_doc.with_user(self.env.user)
        self.manager_doc_shortcut = self.manager_doc_shortcut.with_user(self.env.user)
        self.user_doc_shortcut = self.user_doc_shortcut.with_user(self.env.user)
        self.folder_a = self.folder_a.with_user(self.env.user)
        self.folder_b = self.folder_b.with_user(self.env.user)

    @staticmethod
    def form_get_access_edit(form, partner):
        """Get a sub-form of the form to edit the share_access_id of the given partner."""
        access_idx = next(
            idx
            for idx, a in enumerate(form.share_access_ids._records)
            if a["partner_id"] == partner.id
        )
        return form.share_access_ids.edit(access_idx)

    def create_documents_sharing(self, documents):
        return self.env["document.sharing"].browse(
            [self.env["document.sharing"].action_open(documents.ids)["res_id"]]
        )

    def assert_open_wizard(self, action, documents):
        """Assert the action will open the wizard with the given documents and return the wizard instance."""
        res_id = action["res_id"]
        document0 = documents[0]
        self.assertEqual(
            self.env["document.sharing"].browse([res_id]).document_ids, documents
        )
        self.assertEqual(
            action,
            {
                "context": {
                    "dialog_size": "medium",
                },
                "name": f"Share: {document0.name}"
                if len(documents) == 1
                else f"Share: {len(documents)} files",
                "res_id": res_id,
                "res_model": "document.sharing",
                "target": "new",
                "type": "ir.actions.act_window",
                "view_mode": "form",
                "views": [[False, "form"]],
            },
        )
        return self.env["document.sharing"].browse([action["res_id"]])

    @freeze_time("2025-02-26 15:02:00")
    def test_filtered_relevant_access(self):
        """Check filtered_relevant_access on document access."""
        YESTERDAY = fields.Datetime.now() - timedelta(days=1)
        TOMORROW = fields.Datetime.now() + timedelta(days=1)
        user_doc2 = self.env["res.users"].create(
            [
                {
                    "email": "documents2@example.com",
                    "group_ids": [
                        Command.link(self.env.ref("document.group_documents_user").id)
                    ],
                    "login": "documents2@example.com",
                    "name": "Documents User 2",
                }
            ]
        )
        self.document_gif.action_update_access_rights(
            partners={
                user_id.partner_id: (role, expiration_date)
                for user_id, role, expiration_date in (
                    (
                        self.doc_user,
                        "edit",
                        False,
                    ),  # should be ignored as doc_user is the owner
                    (user_doc2, "edit", TOMORROW),
                    (self.document_manager, "edit", False),
                    (
                        self.internal_user,
                        "view",
                        YESTERDAY,
                    ),  # should be ignored as expired
                )
            },
            access_via_link="view",
        )
        # Simulate access as a portal user by writing an access log
        self.env["document.access"].sudo().create(
            [
                {
                    "document_id": self.document_gif.id,
                    "partner_id": self.portal_user.partner_id.id,
                    "last_access_date": fields.Datetime.now(),
                }
            ]
        )
        self.assertEqual(len(self.document_gif.access_ids), 5)
        self.assertEqual(self.document_gif.owner_id, self.doc_user)

        self.assertEqual(
            set(
                self.env["document.sharing"]
                ._filtered_relevant_access(self.document_gif)
                .mapped(lambda a: (a.partner_id, a.role, a.expiration_date))
            ),
            {
                (user_doc2.partner_id, "edit", TOMORROW),
                (self.document_manager.partner_id, "edit", False),
            },
            "filtered_relevant_access must filter out access logs, owner and expired access.",
        )

    @users("documents@example.com")
    def test_warning_self_access_loss(self):
        """The wizard warns when pending rights would strip the editor's own access."""
        self.set_documents_env_user_to_current()
        # Manager-owned doc: doc_user has an edit membership, no internal/link access.
        doc = self.manager_doc
        doc.sudo().action_update_access_rights(
            access_internal="none",
            access_via_link="none",
            partners={self.doc_user.partner_id: ("edit", False)},
        )
        with Form(self.create_documents_sharing(doc)) as form:
            # Keeping the membership -> no warning.
            self.assertFalse(form.has_warning_self_access_loss)
            # Removing the editor's own membership -> they would lose all access.
            with self.form_get_access_edit(form, self.doc_user.partner_id) as line:
                line.is_deleted = True
            self.assertTrue(form.has_warning_self_access_loss)
            # Restoring an access path (internal view) clears the warning.
            form.access_internal = "write_view"
            self.assertFalse(form.has_warning_self_access_loss)

    @users("documents@example.com")
    def test_init_multi_owners(self):
        """Test that the owner isn't shown when all the doc doesn't have the same owner (but well in the accesses)."""
        self.set_documents_env_user_to_current()
        user_doc_copy = self.user_doc.copy(default={"owner_id": False})
        self.assertEqual(self.user_doc.owner_id, self.doc_user)
        self.assertFalse(user_doc_copy.owner_id)
        owner_and_no_owner_docs = self.user_doc | user_doc_copy
        with Form(self.create_documents_sharing(owner_and_no_owner_docs)) as form:
            self.assertFalse(form.owner_id)
            self.assertEqual(
                [(r["partner_id"], r["role"]) for r in form.share_access_ids._records],
                [(self.doc_user.partner_id.id, "mixed")],
            )
        user_doc_copy.sudo().owner_id = self.doc_user
        mono_owner_docs = self.user_doc | user_doc_copy
        with Form(self.create_documents_sharing(mono_owner_docs)) as form:
            self.assertEqual(form.owner_id, self.user_doc.owner_id)
            self.assertFalse(
                [(r["partner_id"], r["role"]) for r in form.share_access_ids._records]
            )
        multi_owner_docs = self.manager_doc | self.user_doc
        with Form(self.create_documents_sharing(multi_owner_docs)) as form:
            self.assertFalse(form.owner_id)
            self.assertEqual(
                {(r["partner_id"], r["role"]) for r in form.share_access_ids._records},
                {
                    (self.doc_user.partner_id.id, "mixed"),
                    (self.document_manager.partner_id.id, "mixed"),
                },
            )

    def test_init_with_log_and_owner(self):
        """Test that owner and logs are not shown as document access members."""
        doc = self.manager_doc
        self.assertEqual(doc.access_ids.partner_id, self.document_manager.partner_id)
        self.env["document.access"].create(
            {
                "document_id": doc.id,
                "last_access_date": fields.Datetime.now(),
                "partner_id": self.internal_user.partner_id.id,
                "role": False,
            }
        )
        doc.owner_id = False
        self.assertEqual(len(doc.access_ids), 2)
        with Form(self.create_documents_sharing(doc)) as form:
            self.assertEqual(len(form.share_access_ids._records), 1)
            self.assertEqual(
                form.share_access_ids._records[0]["partner_id"],
                self.document_manager.partner_id.id,
                "Non-owner should be shown",
            )
        doc.owner_id = self.document_manager
        self.assertEqual(len(doc.access_ids), 2)
        with Form(self.create_documents_sharing(doc)) as form:
            self.assertFalse(
                form.share_access_ids._records, "Owner, and logs shouldn't be shown"
            )

    @users("documents@example.com")
    def test_invite_members(self):
        """Test invitation."""
        DocumentsSharing = self.env["document.sharing"]
        self.set_documents_env_user_to_current()
        doc = self.user_doc
        doc.access_internal = "edit"
        doc.access_via_link = "view"
        doc1, doc2, doc3, doc4, doc5 = [
            self.user_doc.copy(default={"name": f"doc{i + 1}"}) for i in range(5)
        ]

        for sender, documents, recipients, role, notify, notify_message in (
            (
                self.document_manager,
                doc1,
                self.partner_without_user,
                "view",
                True,
                "Notify message",
            ),
            (self.doc_user, doc2 | doc3, self.portal_partner, "edit", False, False),
            (self.doc_user, doc4, self.internal_user.partner_id, "view", True, False),
            (
                self.doc_user,
                doc5,
                (self.document_manager | self.internal_user).partner_id,
                "edit",
                True,
                False,
            ),
        ):
            with (
                self.with_user(sender.login),
                self.subTest(
                    sender=sender.email,
                    documents=documents.mapped("name"),
                    recipients=recipients.mapped("email"),
                ),
            ):
                self.assertTrue(all(r.email for r in recipients))
                self.assertFalse(DocumentsSharing._filtered_relevant_access(documents))
                action = self.env["document.sharing"].action_open(documents.ids)
                doc_sharing = self.assert_open_wizard(action, documents)
                with Form(doc_sharing) as form:
                    form.invite_partner_ids = recipients
                    self.assertTrue(form.invite_notify, "Notify is enabled by default")
                    self.assertEqual(
                        form.invite_role, "view", "Role is view by default"
                    )
                    form.invite_role = role
                    form.invite_notify = notify
                    if notify:
                        form.invite_notify_message = notify_message
                with self.mock_mail_gateway():
                    action = doc_sharing.action_invite_members()
                    self.assertEqual(action["params"]["type"], "success")
                    self.assert_open_wizard(action["params"]["next"], documents)
                self.assertEqual(
                    DocumentsSharing._filtered_relevant_access(documents).partner_id,
                    recipients,
                )
                self.assertEqual(
                    set(
                        DocumentsSharing._filtered_relevant_access(documents).mapped(
                            "role"
                        )
                    ),
                    {role},
                )
                if notify:
                    for recipient in recipients:
                        if notify_message:
                            self.assertMailMail(
                                recipient,
                                "outgoing",
                                content=notify_message,
                                author=sender.partner_id,
                            )
                        for document in documents:
                            self.assertMailMail(
                                recipient,
                                "outgoing",
                                content=document.name,
                                author=sender.partner_id,
                            )
                else:
                    self.assertNoMail(recipient, author=sender.partner_id)

    @users("documents@example.com")
    def test_invite_missing_email_notification_warning(self):
        """Test partner email missing notification warning."""
        self.set_documents_env_user_to_current()
        self.partner_without_user.email = False
        doc_sharing = self.create_documents_sharing(self.user_doc)
        with Form(doc_sharing) as form:
            form.invite_partner_ids = self.partner_without_user
        action = doc_sharing.action_invite_members()
        self.assertEqual(action["params"]["type"], "warning")
        self.assertEqual(action["params"]["title"], "Some emails are missing")
        self.assertFalse(action.get("next"), "The wizard remains open.")

    @users("documents@example.com")
    def test_invite_no_partner_notification_warning(self):
        """Test no partner notification warning."""
        self.set_documents_env_user_to_current()
        self.partner_without_user.email = False
        action = self.create_documents_sharing(self.user_doc).action_invite_members()
        self.assertEqual(action["params"]["type"], "warning")
        self.assertEqual(action["params"]["title"], "No partners")
        self.assertFalse(action.get("next"), "The wizard remains open.")

    @users("documents@example.com")
    def test_invite_warning_partners_without_access(self):
        """Test the warning about sharing documents to external partners without access (without user)."""
        self.set_documents_env_user_to_current()
        (self.user_doc | self.manager_doc).sudo().access_internal = "edit"
        for documents in (self.user_doc, self.user_doc.copy() | self.manager_doc):
            with self.subTest(documents=documents.mapped("name")):
                action = self.env["document.sharing"].action_open(documents.ids)
                doc_sharing = self.assert_open_wizard(action, documents)
                with Form(doc_sharing) as form:
                    self.assertFalse(form.has_warning_partners_without_access)
                    form.invite_partner_ids = (
                        self.partner_without_user | self.internal_user.partner_id
                    )
                action = doc_sharing.action_invite_members()
                self.assertTrue(action)
                self.assertTrue(
                    {"type": "ir.actions.client", "tag": "display_notification"}.items()
                    <= action.items()
                )
                self.assertTrue(
                    {"type": "success", "title": "Successfully Shared"}.items()
                    <= action.get("params", {}).items()
                )
                self.assert_open_wizard(action.get("params", {}).get("next"), documents)

                with Form(self.create_documents_sharing(documents)) as form:
                    self.assertTrue(form.has_warning_partners_without_access)
                    with (
                        self.form_get_access_edit(
                            form, self.internal_user.partner_id
                        ) as access_internal_form,
                        self.form_get_access_edit(
                            form, self.partner_without_user
                        ) as access_part_without_user_form,
                    ):
                        self.assertFalse(access_internal_form.has_warning_no_access)
                        self.assertTrue(
                            access_part_without_user_form.has_warning_no_access
                        )
                    form.save()
                    form.record.action_allow_link_access()

                with Form(self.create_documents_sharing(documents)) as form:
                    self.assertFalse(form.has_warning_partners_without_access)
                    with (
                        self.form_get_access_edit(
                            form, self.internal_user.partner_id
                        ) as access_internal_form,
                        self.form_get_access_edit(
                            form, self.partner_without_user
                        ) as access_part_without_user_form,
                    ):
                        self.assertFalse(access_internal_form.has_warning_no_access)
                        self.assertFalse(
                            access_part_without_user_form.has_warning_no_access
                        )

    def test_open_wizard_with_shortcuts(self):
        """Test that open sharing wizard on shortcuts open the wizard on the target of the shortcut."""
        DocumentSharing = self.env["document.sharing"]
        self.assert_open_wizard(
            DocumentSharing.action_open(self.user_doc_shortcut.ids), self.user_doc
        )
        self.assert_open_wizard(
            DocumentSharing.action_open(
                (self.user_doc_shortcut | self.manager_doc_shortcut).ids
            ),
            self.user_doc | self.manager_doc,
        )
        self.assert_open_wizard(
            DocumentSharing.action_open(
                (self.user_doc | self.manager_doc_shortcut).ids
            ),
            self.user_doc | self.manager_doc,
        )

    @users("documents@example.com")
    def test_readonly(self):
        """Test that the form is read-only when the user doesn't have edit access to all the selected documents"""
        self.set_documents_env_user_to_current()
        self.assertTrue(self.create_documents_sharing(self.manager_doc).is_readonly)
        self.assertFalse(self.create_documents_sharing(self.user_doc).is_readonly)
        self.assertTrue(
            self.create_documents_sharing(self.manager_doc | self.user_doc).is_readonly
        )
        self.manager_doc.sudo().action_update_access_rights(
            partners={self.doc_user.partner_id: ("edit", False)}
        )
        self.assertFalse(
            self.create_documents_sharing(self.manager_doc | self.user_doc).is_readonly
        )

    def check_update_access_right(
        self, doc_main, doc_other=None, doc_child=None, must_propagate=False
    ):
        """Check update rights using the wizard.

        :param doc_main: The main document or folder on which the update is performed.
        :param doc_other: The other document or folder on which the update is performed.
        :param doc_child: Child of doc_main if defined. In that case doc_main must be a folder.
        :param must_propagate: whether to check if the update performed on doc_main is propagated to doc_child.
        """
        doc_child = doc_child or self.env["document.document"]
        doc_main = doc_main or self.env["document.document"]
        doc_other = doc_other or self.env["document.document"]
        self.assertTrue(
            not doc_child
            or (doc_main.type == "folder" and doc_child.folder_id == doc_main)
        )
        portal_user_2 = self.portal_user.copy()
        portal_partner, portal_partner_2 = self.portal_partner, portal_user_2.partner_id
        documents = doc_main | doc_other
        all_docs = documents | doc_child
        all_docs.owner_id = self.doc_user
        all_docs.action_update_access_rights(
            partners={self.doc_user.partner_id: (False, False)}
        )
        all_docs.access_internal = "none"
        all_docs.access_via_link = "none"
        all_docs.is_access_via_link_hidden = True
        is_single_doc = len(documents) == 1
        docs_to_check = documents if not must_propagate else documents | doc_child
        doc_main.action_update_access_rights(
            partners={portal_partner: ("view", None), portal_partner_2: ("view", None)},
            no_propagation=True,
        )

        # Check update a member right
        action = self.env["document.sharing"].action_open(documents.ids)
        doc_sharing = self.assert_open_wizard(action, documents)
        form = Form(doc_sharing)
        # Check initialization
        self.assertFalse(doc_sharing.is_access_modified)
        self.assertEqual(form.owner_id, self.doc_user)
        self.assertEqual(
            {a["role"] for a in form.share_access_ids._records},
            {"view" if is_single_doc else "mixed"},
        )
        self.assertEqual(form.access_internal, "none")
        self.assertEqual(form.access_via_link, "none")
        self.assertEqual(form.access_via_link_mode, "link_required")
        # Update and check modification
        with self.form_get_access_edit(form, portal_partner) as access_edit_form:
            access_edit_form.role = "write_edit"
        self.assertTrue(form.is_access_modified)
        form.save()
        self.assertEqual(
            doc_sharing._get_update_rights_params(),
            {"partners": {portal_partner: ("edit", False if is_single_doc else None)}},
        )
        action = doc_sharing.action_update_rights()
        self.assert_open_wizard(action, documents)
        self.assertTrue(
            all(
                d.access_ids.filtered(lambda a: a.partner_id == portal_partner).role
                == "edit"
                for d in docs_to_check
            )
        )
        self.assertFalse(
            (doc_other | doc_child).access_ids.filtered(
                lambda a: a.partner_id == portal_partner_2 and a.role
            )
        )

        # Check change multiple values and remove a member
        doc_other.access_via_link = "view"
        doc_other.is_access_via_link_hidden = False
        doc_sharing = self.create_documents_sharing(documents)
        form = Form(doc_sharing)
        # Check initialization
        self.assertFalse(form.is_access_modified)
        self.assertEqual(
            {s["partner_id"]: s["role"] for s in form.share_access_ids._records},
            {
                portal_partner.id: "edit",
                portal_partner_2.id: "view" if is_single_doc else "mixed",
            },
        )
        self.assertEqual(form.access_internal, "none")
        self.assertEqual(form.access_via_link, "none" if is_single_doc else "mixed")
        self.assertEqual(
            form.access_via_link_mode, "link_required" if is_single_doc else "mixed"
        )
        # Update and check modification
        # Expiration is only supported with single document selection
        expiration_date = (
            fields.Datetime.now() + relativedelta(days=1, hour=11)
            if is_single_doc
            else False
        )
        with self.form_get_access_edit(form, portal_partner_2) as access_edit_form:
            access_edit_form.role = "write_edit"
            access_edit_form.expiration_date = expiration_date
        with self.form_get_access_edit(form, portal_partner) as access_edit_form:
            access_edit_form.is_deleted = True
        form.access_internal = "write_edit"
        form.access_via_link = "write_view"
        form.access_via_link_mode = "write_discoverable"
        self.assertTrue(form.is_access_modified)
        form.save()
        self.assertEqual(
            doc_sharing._get_update_rights_params(),
            {
                "partners": {
                    portal_partner_2: (
                        "edit",
                        expiration_date if is_single_doc else None,
                    ),
                    portal_partner: (False, False),
                },
                "access_internal": "edit",
                "access_via_link": "view",
                "is_access_via_link_hidden": False,
            },
        )
        action = doc_sharing.action_update_rights()
        self.assert_open_wizard(action, documents)
        self.assertEqual(set(docs_to_check.mapped("access_internal")), {"edit"})
        self.assertEqual(
            {
                (a.partner_id, a.role, a.expiration_date)
                for a in docs_to_check.access_ids.filtered("role")
            },
            {(portal_partner_2, "edit", expiration_date if is_single_doc else False)},
        )
        self.assertEqual(set(docs_to_check.mapped("access_via_link")), {"view"})
        # No propagation for is_access_via_link_hidden
        self.assertEqual(set(documents.mapped("is_access_via_link_hidden")), {False})
        if doc_child:
            self.assertEqual(set(doc_child.mapped("is_access_via_link_hidden")), {True})

    @users("dtdm")
    def test_update_access_rights_expiration_date(self):
        """Test that expiration are unaltered when updating rights on multiple documents."""
        self.set_documents_env_user_to_current()
        expiration_date = fields.Datetime.now() + relativedelta(days=1, hour=11)
        self.manager_doc.action_update_access_rights(
            partners={self.portal_partner: ("view", expiration_date)}
        )
        doc_sharing = self.create_documents_sharing(self.user_doc | self.manager_doc)
        with (
            Form(doc_sharing) as form,
            self.form_get_access_edit(form, self.portal_partner) as portal_access_form,
        ):
            self.assertFalse(
                portal_access_form.expiration_date,
                "Expiration not supported with multiple documents",
            )
            self.assertEqual(portal_access_form.role, "mixed")
            portal_access_form.role = "write_view"
        self.assertEqual(
            doc_sharing._get_update_rights_params(),
            {"partners": {self.portal_partner: ("view", None)}},
        )
        doc_sharing.action_update_rights()
        portal_access_manager_doc = self.manager_doc.access_ids.filtered(
            lambda a: a.partner_id == self.portal_partner
        )
        self.assertEqual(
            portal_access_manager_doc.expiration_date,
            expiration_date,
            "Expiration must remain untouched",
        )
        self.assertEqual(portal_access_manager_doc.role, "view")
        portal_access_user_doc = self.user_doc.access_ids.filtered(
            lambda a: a.partner_id == self.portal_partner
        )
        self.assertFalse(portal_access_user_doc.expiration_date)
        self.assertEqual(portal_access_user_doc.role, "view")

    @users("dtdm")
    def test_update_access_rights_of_owners(self):
        """Test modifying member access of partner that owns some of the selected documents."""
        DocumentsSharing = self.env["document.sharing"]
        self.set_documents_env_user_to_current()
        self.assertFalse(self.user_doc.access_ids.filtered("role"))
        self.assertFalse(self.manager_doc.access_ids.filtered("role"))
        doc_sharing = self.create_documents_sharing(self.user_doc | self.manager_doc)
        with Form(doc_sharing) as form:
            self.assertFalse(form.owner_id)
            self.assertEqual(
                self.form_get_access_edit(form, self.doc_user.partner_id).role, "mixed"
            )
            self.assertEqual(
                self.form_get_access_edit(form, self.document_manager.partner_id).role,
                "mixed",
            )
            with self.form_get_access_edit(
                form, self.doc_user.partner_id
            ) as access_edit_form:
                access_edit_form.role = "write_edit"
        doc_sharing.action_update_rights()
        self.assertEqual(
            {
                a.partner_id: a.role
                for a in DocumentsSharing._filtered_relevant_access(self.manager_doc)
            },
            {self.doc_user.partner_id: "edit"},
        )
        doc_sharing = self.create_documents_sharing(self.user_doc | self.manager_doc)
        with Form(doc_sharing) as form:
            self.assertFalse(form.owner_id)
            self.assertEqual(
                self.form_get_access_edit(form, self.doc_user.partner_id).role, "edit"
            )
            self.assertEqual(
                self.form_get_access_edit(form, self.document_manager.partner_id).role,
                "mixed",
            )
            with self.form_get_access_edit(
                form, self.doc_user.partner_id
            ) as access_edit_form:
                access_edit_form.is_deleted = True
        doc_sharing.action_update_rights()
        self.assertFalse(DocumentsSharing._filtered_relevant_access(self.manager_doc))

    @users("documents@example.com")
    def test_update_access_rights_multi_mixed(self):
        """Test access rights edition on a documents and a folder."""
        self.set_documents_env_user_to_current()
        self.check_update_access_right(
            self.folder_b,
            self.user_doc,
            doc_child=self.document_gif,
            must_propagate=False,
        )

    @users("documents@example.com")
    def test_update_access_rights_multi_folders(self):
        """Test access rights edition on multiple folders."""
        self.set_documents_env_user_to_current()
        self.check_update_access_right(
            self.folder_b,
            self.folder_a,
            doc_child=self.document_gif,
            must_propagate=True,
        )

    @users("documents@example.com")
    def test_update_access_rights_multi_documents(self):
        """Test access rights edition on multiple documents."""
        self.set_documents_env_user_to_current()
        self.check_update_access_right(self.user_doc, self.user_doc.copy())

    @users("documents@example.com")
    def test_update_access_rights_single_document(self):
        """Test access rights edition on a single document."""
        self.set_documents_env_user_to_current()
        self.check_update_access_right(self.user_doc)

    @users("documents@example.com")
    def test_update_access_rights_single_folder(self):
        """Test access rights edition on a single folder."""
        self.set_documents_env_user_to_current()
        self.check_update_access_right(
            self.folder_b, doc_child=self.document_gif, must_propagate=True
        )

    @users("documents@example.com")
    def test_update_access_rights_warning_link_with_more_rights(self):
        """Test the warning about sharing documents with more rights when having the link than the internal users."""
        self.set_documents_env_user_to_current()
        for documents in (self.user_doc, self.user_doc.copy() | self.user_doc.copy()):
            with self.subTest(documents=documents):
                documents.access_internal = "edit"
                documents.access_via_link = "edit"
                doc_sharing = self.create_documents_sharing(documents)
                with Form(doc_sharing) as form:
                    self.assertFalse(form.has_warning_link_with_more_rights)
                    form.access_internal = "write_view"
                    self.assertTrue(form.has_warning_link_with_more_rights)
                action = doc_sharing.action_update_rights()
                doc_sharing = self.assert_open_wizard(action, documents)
                self.assertEqual(set(documents.mapped("access_internal")), {"view"})
                self.assertTrue(doc_sharing.has_warning_link_with_more_rights)

    @users("documents@example.com")
    def test_an_editor_rotates_the_link_from_the_sharing_dialog(self):
        self.set_documents_env_user_to_current()
        self.user_doc.access_via_link = "view"
        old_token = self.user_doc.document_token
        doc_sharing = self.create_documents_sharing(self.user_doc)
        arch = doc_sharing.get_views([(False, "form")])["views"]["form"]["arch"]
        self.assertIn('name="action_rotate_links"', arch)

        action = doc_sharing.action_rotate_links()

        self.assert_open_wizard(action, self.user_doc)
        self.assertNotEqual(self.user_doc.document_token, old_token)

    @users("documents@example.com")
    def test_a_viewer_cannot_rotate_the_link_from_the_sharing_dialog(self):
        self.set_documents_env_user_to_current()
        old_token = self.manager_doc.sudo().document_token
        doc_sharing = self.create_documents_sharing(self.manager_doc)
        self.assertTrue(doc_sharing.is_readonly)

        with self.assertRaises(AccessError):
            doc_sharing.action_rotate_links()
        self.assertEqual(self.manager_doc.sudo().document_token, old_token)
