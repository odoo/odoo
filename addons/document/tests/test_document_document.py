import base64
from collections import defaultdict
from contextlib import ExitStack, contextmanager
from datetime import timedelta
from unittest.mock import patch

from odoo import Command, fields, http
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase, new_test_user, tagged, users
from odoo.tools import mute_logger

from .test_document_common import GIF, TEXT, WEBP, TransactionCaseDocuments
from odoo.addons.mail.tools import link_preview

DATA = "data:application/zip;base64,R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs="
file_a = {
    "name": "doc.zip",
    "datas": "data:application/zip;base64,R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs=",
}


class TestCaseDocuments(TransactionCaseDocuments):
    def test_documents_action_create_shortcut(self):
        self.document_gif.partner_id = self.env.user.partner_id
        shortcut = self.document_gif.action_create_shortcut()
        self.assertFalse(shortcut.attachment_id)
        original_file_size = self.document_gif.file_size
        for field_name in self.env["document.document"]._get_fields_shortcuts_copy():
            with self.subTest(field_name=field_name):
                self.assertEqual(shortcut[field_name], self.document_gif[field_name])
        attachment = self.env["ir.attachment"].create(
            {
                **file_a,
                "res_model": False,
                "res_id": False,
            }
        )
        self.document_gif.attachment_id = attachment
        self.assertNotEqual(self.document_gif.file_size, original_file_size)
        self.assertEqual(shortcut.file_size, self.document_gif.file_size)
        self.assertEqual(shortcut.file_extension, self.document_gif.file_extension)

    def test_duplicate_multiple_shortcuts_same_target(self):
        shortcut_1 = self.document_gif.action_create_shortcut()
        shortcut_2 = self.document_gif.action_create_shortcut()
        self.assertEqual(
            (shortcut_1 | shortcut_2).shortcut_document_id, self.document_gif
        )
        copies = (shortcut_1 | shortcut_2).copy()
        self.assertEqual(len(copies), 2, "one copy per duplicated shortcut")
        self.assertEqual(
            copies.shortcut_document_id,
            self.document_gif,
            "copies still point at the original target, not at a shortcut",
        )

    def test_res_record_link_requires_target_write(self):
        target = self.env["res.partner"].create({"name": "Unwritable target"})
        Document = self.env["document.document"].with_user(self.doc_user)
        self.assertFalse(
            self.env["res.partner"].with_user(self.doc_user).has_access("write")
        )

        with self.assertRaises(AccessError):
            self.env["ir.attachment"].with_user(self.doc_user).create(
                {
                    "name": "direct.txt",
                    "datas": GIF,
                    "res_model": "res.partner",
                    "res_id": target.id,
                }
            )

        with self.assertRaises(AccessError):
            Document.create(
                {
                    "name": "planted.txt",
                    "datas": GIF,
                    "folder_id": self.folder_a.id,
                    "res_model": "res.partner",
                    "res_id": target.id,
                }
            )

        doc = Document.create(
            {
                "name": "own.txt",
                "datas": GIF,
                "folder_id": self.folder_a.id,
            }
        )
        with self.assertRaises(AccessError):
            doc.write({"res_model": "res.partner", "res_id": target.id})

        self.assertEqual(doc.attachment_id.res_model, "document.document")
        self.assertEqual(doc.attachment_id.res_id, doc.id)

    def test_write_active_false_routes_through_action_archive(self):
        folder = self.env["document.document"].create(
            {
                "name": "Team folder",
                "type": "folder",
                "access_internal": "view",
            }
        )
        doc = self.env["document.document"].create(
            {
                "name": "team.txt",
                "type": "binary",
                "datas": TEXT,
                "folder_id": folder.id,
            }
        )
        doc.action_update_access_rights(
            partners={self.doc_user.partner_id.id: ("edit", False)}
        )
        doc_as_user = doc.with_user(self.doc_user)
        self.assertEqual(doc_as_user.user_permission, "edit")
        self.assertEqual(folder.with_user(self.doc_user).user_permission, "view")

        with self.assertRaises(UserError):
            doc_as_user.action_archive()
        self.assertTrue(doc.active)

        with self.assertRaises(UserError):
            doc_as_user.write({"active": False})
        doc.invalidate_recordset()
        self.assertTrue(doc.active, "write({'active': False}) bypassed the guard")

        doc_as_user.sudo().write({"active": False})
        doc.invalidate_recordset()
        self.assertFalse(doc.active)

    def test_cascade_unlink_reclaims_descendant_attachments(self):

        def build(tag):
            folder = self.env["document.document"].create(
                {"name": f"F_{tag}", "type": "folder"}
            )
            attachment = self.env["ir.attachment"].create(
                {
                    "name": f"{tag}.txt",
                    "datas": TEXT,
                    "res_model": "res.partner",
                    "res_id": self.env.user.partner_id.id,
                }
            )
            document = self.env["document.document"].create(
                {
                    "name": f"{tag}.txt",
                    "type": "binary",
                    "folder_id": folder.id,
                    "attachment_id": attachment.id,
                }
            )
            return folder, document, attachment

        _folder, document, attachment = build("direct")
        document.unlink()
        self.assertFalse(attachment.exists())

        folder, _document, attachment = build("cascade")
        folder.unlink()
        self.assertFalse(
            attachment.exists(),
            "deleting a folder orphaned its descendant's attachment",
        )

    def test_shortcut_cannot_target_another_shortcut(self):
        real = self.env["document.document"].create(
            {
                "name": "real.txt",
                "type": "binary",
                "datas": TEXT,
                "folder_id": self.folder_a.id,
            }
        )
        shortcut = real.action_create_shortcut()
        self.assertEqual(shortcut.shortcut_document_id, real)

        with self.assertRaises(ValidationError):
            self.env["document.document"].create(
                {
                    "name": "chained",
                    "type": "binary",
                    "shortcut_document_id": shortcut.id,
                    "folder_id": self.folder_a.id,
                }
            )

        self.assertEqual(shortcut.action_create_shortcut().shortcut_document_id, real)

    def test_create_rejects_a_non_folder_parent_like_write(self):
        real_folder = self.env["document.document"].create(
            {"name": "RealF", "type": "folder"}
        )
        a_file = self.env["document.document"].create(
            {
                "name": "afile.txt",
                "type": "binary",
                "datas": TEXT,
                "folder_id": real_folder.id,
            }
        )

        with self.assertRaises(UserError):
            self.env["document.document"].create(
                {
                    "name": "child.txt",
                    "type": "binary",
                    "datas": TEXT,
                    "folder_id": a_file.id,
                }
            )

        existing = self.env["document.document"].create(
            {
                "name": "moved.txt",
                "type": "binary",
                "datas": TEXT,
                "folder_id": real_folder.id,
            }
        )
        with self.assertRaises(UserError):
            existing.write({"folder_id": a_file.id})
        self.assertEqual(existing.folder_id, real_folder)

    def test_user_permission_parent_lookup_is_batched(self):
        user = new_test_user(
            self.env,
            "perm_batch",
            groups="base.group_user,document.group_documents_user",
        )

        def measure(n_folders):
            folders = self.env["document.document"].create(
                [
                    {"name": f"F{i}", "type": "folder", "access_internal": "view"}
                    for i in range(n_folders)
                ]
            )
            documents = self.env["document.document"].create(
                [
                    {
                        "name": f"d{i}.txt",
                        "type": "binary",
                        "datas": TEXT,
                        "folder_id": folders[i % n_folders].id,
                        "access_via_link": "view",
                        "access_internal": "none",
                    }
                    for i in range(40)
                ]
            )
            self.env.flush_all()
            self.env.invalidate_all()
            as_user = documents.with_user(user)
            count0 = self.cr.sql_statement_count
            as_user.mapped("user_permission")
            return self.cr.sql_statement_count - count0

        few, many = measure(2), measure(20)
        self.assertLess(
            many,
            few + 10,
            f"parent-folder permission lookup is not batched ({few} -> {many} queries)",
        )

    def test_documents_action_delete_from_history(self):
        current_attachment = self.document_gif.attachment_id

        with self.assertRaises(UserError):
            self.document_gif.action_delete_from_history(current_attachment.id)
        self.assertTrue(current_attachment.exists())

        new_attachment, other_attachment = self.env["ir.attachment"].create(
            [{"name": "Test"}] * 2
        )
        self.document_gif.previous_attachment_ids = new_attachment

        with self.assertRaises(UserError):
            self.document_gif.action_delete_from_history(other_attachment.id)
        self.assertTrue(current_attachment.exists())
        self.assertTrue(new_attachment.exists())
        self.assertTrue(other_attachment.exists())

        self.document_gif.action_delete_from_history(new_attachment.id)
        self.assertFalse(
            new_attachment.exists(), "The attachment should have been deleted"
        )
        self.assertTrue(current_attachment.exists())

        current_attachment = self.document_gif.attachment_id
        versions = self.env["ir.attachment"].create([{"name": "Test"}] * 3)
        self.document_gif.previous_attachment_ids = versions
        self.document_gif.action_delete_from_history(current_attachment.id)
        self.assertFalse(current_attachment.exists())
        self.assertEqual(self.document_gif.attachment_id.id, max(versions.ids))

    def test_documents_create_from_attachment(self):
        attachment = self.env["ir.attachment"].create(
            {
                "datas": GIF,
                "name": "attachmentGif.gif",
                "res_model": "document.document",
                "res_id": 0,
            }
        )
        document_a = self.env["document.document"].create(
            {
                "folder_id": self.folder_b.id,
                "name": "new name",
                "attachment_id": attachment.id,
            }
        )
        self.assertEqual(
            document_a.attachment_id.id,
            attachment.id,
            "the attachment should be the attachment given in the create values",
        )
        self.assertEqual(document_a.name, "new name", "the name given should be used")
        self.assertFalse(document_a.res_model)
        self.assertFalse(document_a.res_id)

    def test_documents_create_res_model(self):
        attachment = self.env["ir.attachment"].create(
            {"name": "test", "res_model": "document.document"}
        )
        doc = self.env["document.document"].create({"attachment_id": attachment.id})
        self.assertEqual(attachment.res_model, "document.document")
        self.assertEqual(attachment.res_id, doc.id)

        attachment = self.env["ir.attachment"].create(
            {"name": "test", "res_model": "document.document"}
        )
        partner = self.env["res.partner"].create({"name": "partner"})
        doc = self.env["document.document"].create(
            {
                "attachment_id": attachment.id,
                "res_model": "res.partner",
                "res_id": partner.id,
            }
        )
        self.assertEqual(attachment.res_model, "res.partner")
        self.assertEqual(attachment.res_id, partner.id)
        self.assertEqual(doc.res_model, "res.partner")
        self.assertEqual(doc.res_id, partner.id)

        user = self.portal_user
        attachment = self.env["ir.attachment"].create(
            {"name": "test", "res_model": "res.users", "res_id": user.id}
        )
        doc = self.env["document.document"].create({"attachment_id": attachment.id})
        self.assertEqual(attachment.res_model, "res.users")
        self.assertEqual(attachment.res_id, user.id)
        self.assertEqual(doc.res_model, "res.users")
        self.assertEqual(doc.res_id, user.id)

        doc.attachment_id = False
        doc.name = "test"
        doc.datas = "ZGF0YQ=="
        self.assertEqual(doc.attachment_id.res_model, "res.users")
        self.assertEqual(doc.attachment_id.res_id, user.id)
        self.assertEqual(doc.attachment_id.name, "test")

        doc.write({"attachment_id": False, "res_model": False, "res_id": False})
        doc.datas = "ZGF0YQ=="
        self.assertEqual(doc.attachment_id.res_model, "document.document")
        self.assertEqual(doc.attachment_id.res_id, doc.id)
        self.assertEqual(doc.attachment_id.name, "test")

        doc = self.env["document.document"].create({"datas": "ZGF0YQ=="})
        self.assertFalse(doc.res_model)
        self.assertFalse(doc.res_id)
        self.assertEqual(doc.attachment_id.res_model, "document.document")
        self.assertEqual(doc.attachment_id.res_id, doc.id)

    @users("documents@example.com")
    def test_documents_create_write(self):
        document_a = self.env["document.document"].create(
            {
                "name": "Test mimetype gif",
                "datas": GIF,
                "folder_id": self.folder_b.id,
            }
        )
        self.assertFalse(document_a.res_model)
        self.assertFalse(document_a.res_id)
        self.assertEqual(
            document_a.attachment_id.res_model,
            "document.document",
            "the res_model should be set as document by default",
        )
        self.assertEqual(
            document_a.attachment_id.res_id,
            document_a.id,
            "the res_id should be set as the document id by default to allow access right inheritance",
        )
        self.assertEqual(
            document_a.attachment_id.datas, GIF, "the document should have a GIF data"
        )
        document_no_attachment = self.env["document.document"].create(
            {
                "name": "Test mimetype gif",
                "folder_id": self.folder_b.id,
            }
        )
        self.assertFalse(
            document_no_attachment.attachment_id,
            "the new document shouldnt have any attachment_id",
        )
        document_no_attachment.write({"datas": TEXT})
        self.assertEqual(
            document_no_attachment.attachment_id.datas,
            TEXT,
            "the document should have an attachment",
        )

    def test_documents_create_performance(self):
        folders = self.env["document.document"].create(
            [
                {"type": "folder", "name": f"Folder {i}", "access_internal": "view"}
                for i in range(50)
            ]
        )
        folders.flush_recordset()
        folders.invalidate_recordset()
        # 10 fixed + 2 per document: `name` and `thumbnail` are recursive
        # stored computes (a shortcut takes its target's), and the ORM
        # evaluates a recursive field one record at a time. Was 8 + 3 per
        # document until the parent-folder check, the res_model constraint
        # and the thumbnail write stopped running once per record.
        with self.assertQueryCount(110):
            self.env["document.document"].create(
                [
                    {
                        "folder_id": folder.id,
                        "type": "binary",
                    }
                    for folder in folders
                ]
            )

    def test_default_res_id_model(self):
        document = self.env["document.document"].create({"folder_id": self.folder_b.id})
        attachment = (
            self.env["ir.attachment"]
            .with_context(
                default_res_id=document.id,
                default_res_model=document._name,
            )
            .create(
                {
                    "name": "attachmentGif.gif",
                    "datas": GIF,
                }
            )
        )
        self.assertEqual(
            attachment.res_id, document.id, "It should be linked to the default res_id"
        )
        self.assertEqual(
            attachment.res_model,
            document._name,
            "It should be linked to the default res_model",
        )
        self.assertEqual(
            document.attachment_id,
            attachment,
            "Document should be linked to the created attachment",
        )

    def test_versioning(self):
        document = self.env["document.document"].create(
            {
                "datas": GIF,
                "folder_id": self.folder_b.id,
                "res_model": "res.users",
                "res_id": self.doc_user.id,
            }
        )

        def check_attachment_res_fields(
            attachment, expected_res_model, expected_res_id
        ):
            self.assertEqual(
                attachment.res_model,
                expected_res_model,
                "The attachment should be linked to the right model",
            )
            self.assertEqual(
                attachment.res_id,
                expected_res_id,
                "The attachment should be linked to the right record",
            )

        self.assertEqual(
            len(document.previous_attachment_ids.ids), 0, "The history should be empty"
        )
        original_attachment = document.attachment_id
        check_attachment_res_fields(original_attachment, "res.users", self.doc_user.id)
        document.write({"datas": TEXT})
        new_attachment = document.previous_attachment_ids
        check_attachment_res_fields(original_attachment, "res.users", self.doc_user.id)
        check_attachment_res_fields(new_attachment, "document.document", document.id)
        self.assertEqual(len(document.previous_attachment_ids), 1)
        self.assertNotEqual(document.previous_attachment_ids, original_attachment)
        self.assertEqual(
            document.previous_attachment_ids[0].datas,
            GIF,
            "The history should have the right content",
        )
        self.assertEqual(
            document.attachment_id.datas,
            TEXT,
            "The document should have the right content",
        )
        old_attachment = document.attachment_id
        document.write({"attachment_id": new_attachment.id})
        check_attachment_res_fields(new_attachment, "res.users", self.doc_user.id)
        check_attachment_res_fields(old_attachment, "document.document", document.id)
        self.assertEqual(
            document.attachment_id.id,
            new_attachment.id,
            "the document should contain the new attachment",
        )
        self.assertEqual(
            document.previous_attachment_ids,
            original_attachment,
            "the history should contain the original attachment",
        )
        document.write({"attachment_id": document.attachment_id.id})
        check_attachment_res_fields(new_attachment, "res.users", self.doc_user.id)
        self.assertEqual(
            document.attachment_id.id,
            new_attachment.id,
            "the document attachment should not have changed",
        )
        self.assertTrue(
            new_attachment not in document.previous_attachment_ids,
            "the history should not contain the new attachment",
        )
        document.write({"datas": DATA})
        self.assertEqual(document.attachment_id, new_attachment)

    def test_write_mimetype(self):
        document = (
            self.env["document.document"]
            .with_user(self.doc_user.id)
            .create({"datas": GIF, "folder_id": self.folder_b.id})
        )
        document.with_user(self.doc_user.id).write(
            {"datas": TEXT, "mimetype": "text/plain"}
        )
        self.assertEqual(
            document.mimetype,
            "text/plain",
            "the new mimetype should be the one given on write",
        )
        document.with_user(self.doc_user.id).write(
            {
                "datas": TEXT,
                "mimetype": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            }
        )
        self.assertEqual(
            document.mimetype,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "should preserve office mime type",
        )

    def test_cascade_delete(self):
        document = self.env["document.document"].create(
            {"datas": GIF, "folder_id": self.folder_b.id}
        )
        self.assertTrue(document.exists(), "the document should exist")
        document.attachment_id.unlink()
        self.assertFalse(document.exists(), "the document should not exist")

    def test_is_user_favorite(self):
        user = new_test_user(
            self.env, "test user", groups="document.group_documents_user"
        )
        document = self.env["document.document"].create(
            {"datas": GIF, "folder_id": self.folder_b.id}
        )
        document.favorite_user_ids = user
        self.assertFalse(document.is_user_favorite)
        self.assertTrue(document.with_user(user).is_user_favorite)

    def test_neuter_mimetype(self):
        self.folder_b.action_update_access_rights(
            partners={self.doc_user.partner_id: ("edit", False)}
        )
        document = self.env["document.document"].create(
            {"datas": GIF, "folder_id": self.folder_b.id}
        )

        document.with_user(self.doc_user.id).write(
            {"datas": TEXT, "mimetype": "text/xml"}
        )
        self.assertEqual(
            document.mimetype, "text/plain", "XML mimetype should be forced to text"
        )
        document.with_user(self.doc_user.id).write(
            {"datas": TEXT, "mimetype": "image/svg+xml"}
        )
        self.assertEqual(
            document.mimetype, "text/plain", "SVG mimetype should be forced to text"
        )
        document.with_user(self.doc_user.id).write(
            {"datas": TEXT, "mimetype": "text/html"}
        )
        self.assertEqual(
            document.mimetype, "text/plain", "HTML mimetype should be forced to text"
        )
        document.with_user(self.doc_user.id).write(
            {"datas": TEXT, "mimetype": "application/xhtml+xml"}
        )
        self.assertEqual(
            document.mimetype, "text/plain", "XHTML mimetype should be forced to text"
        )

    def test_create_from_message_invalid_tags(self):
        message = self.env["document.document"].message_new(
            {
                "subject": "Test",
            },
            {
                "tag_ids": [(6, 0, [self.tag_b.id, -1])],
                "folder_id": self.folder_a.id,
            },
        )
        self.assertEqual(
            message.tag_ids.ids, [self.tag_b.id], "Should only keep the existing tag"
        )

    def test_file_extension(self):
        sanitized_extension = "txt"
        for extension in (".txt", " .txt", "..txt", ".txt ", " .txt ", "  .txt   "):
            document = self.env["document.document"].create(
                {
                    "datas": base64.b64encode(b"Test"),
                    "name": f"name{extension}",
                    "mimetype": "text/plain",
                    "folder_id": self.folder_b.id,
                }
            )
            self.assertEqual(
                document.file_extension,
                sanitized_extension,
                f'"{extension}" must be sanitized to "{sanitized_extension}" at creation',
            )
        for extension in (
            "txt",
            "  txt",
            "  txt   ",
            ".txt",
            " .txt",
            " .txt  ",
            "..txt",
            "  ..txt ",
        ):
            document.file_extension = extension
            self.assertEqual(
                document.file_extension,
                sanitized_extension,
                f'"{extension}" must be sanitized to "{sanitized_extension}" at edition',
            )

        document.name = "test.png"
        self.assertEqual(
            document.file_extension,
            "png",
            "extension must be updated on change in filename",
        )

    def test_restricted_folder_multi_company(self):

        company_a = self.env.company
        company_b = self.env["res.company"].create({"name": "Company B"})

        user_b = self.env["res.users"].create(
            {
                "name": "User of company B",
                "login": "user_b",
                "group_ids": [(6, 0, [self.ref("document.group_documents_manager")])],
                "company_id": company_b.id,
                "company_ids": [(6, 0, [company_b.id])],
            }
        )

        self.folder_a.company_id = company_a
        self.assertEqual(
            self.folder_a.display_name,
            "folder A",
            "The parent folder's name should not be hidden",
        )
        self.assertEqual(
            self.folder_a.with_user(user_b).display_name,
            "Restricted",
            "The parent folder's name should be hidden",
        )
        self.assertEqual(
            self.folder_a_a.display_name,
            "folder A - A",
            "The parent folder name should not be included in the name",
        )

    def test_unlink_attachments_with_documents(self):
        documents = self.env["document.document"].create(
            [
                {
                    "datas": GIF,
                    "folder_id": self.folder_b.id,
                    "res_model": res_model,
                    "res_id": res_id,
                }
                for res_model, res_id in (
                    ("res.partner", self.internal_user.partner_id.id),
                    (False, False),
                )
            ]
        )
        self.assertFalse(documents[1].res_model)
        self.assertEqual(documents[1].attachment_id.res_model, "document.document")
        for document in documents:
            with self.subTest(res_model=document.res_model):
                self.assertTrue(document.attachment_id.exists())
                attachment = document.attachment_id
                document.unlink()
                self.assertFalse(attachment.exists())

    def test_archive_and_unarchive_document(self):
        self.document_txt.action_archive()
        self.assertFalse(self.document_txt.active, "the document should be inactive")
        self.document_txt.action_unarchive()
        self.assertTrue(self.document_txt.active, "the document should be active")

    def test_archived_documents_operations(self):
        folder_1, folder_2, folder_3 = self.env["document.document"].create(
            [{"name": f"Test Folder {idx + 1}", "type": "folder"} for idx in range(3)]
        )
        folder_3.folder_id = folder_1
        request = self.env["document.document"].create(
            {"name": "Test Request", "folder_id": folder_3.id}
        )

        folder_2.action_archive()
        with self.assertRaises(UserError):
            folder_3.folder_id = folder_2
        folder_2.action_unarchive()

        folder_1.action_archive()
        folder_3.folder_id = folder_1

        with self.assertRaises(UserError):
            folder_3.folder_id = folder_2
        with self.assertRaises(UserError):
            folder_3.user_folder_id = str(folder_2.id)

        with self.assertRaises(UserError):
            folder_3.write({"folder_id": folder_2.id, "active": True})
        (folder_1 | folder_3).write({"folder_id": folder_2.id, "active": True})

        self.assertFalse(
            request.active, "folder_3's content should still be in the trash"
        )

    def test_unarchive_document_with_archived_parent(self):
        document = self.document_txt

        def check_error_message(document):
            with self.assertRaises(UserError) as err:
                document.action_unarchive()
            self.assertEqual(
                err.exception.args[0],
                "Item(s) you wish to restore are included in archived folders. "
                "To restore these items, you must restore the following including folders instead:"
                "\n"
                "- folder B",
            )

        self.folder_b.folder_id = self.folder_a
        self.folder_b.action_archive()
        check_error_message(document)

        self.folder_b.folder_id = False
        check_error_message(document)

    def test_delete_document(self):
        self.document_txt.action_archive()
        self.assertFalse(self.document_txt.active, "the document should be inactive")
        self.document_txt.unlink()
        self.assertFalse(self.document_txt.exists(), "the document should not exist")

    def test_copy_document(self):
        @contextmanager
        def patched_compute_methods():
            fields_to_recompute = self.env[
                "document.document"
            ]._get_fields_to_recompute(depends=["attachment_id"])
            self.assertSetEqual(
                {f.name for f in fields_to_recompute},
                {
                    "name",
                    "is_multipage",
                    "thumbnail",
                    "thumbnail_status",
                    "url_preview_image",
                    "file_extension",
                },
            )
            computes_to_mock = defaultdict(list)
            for field in fields_to_recompute:
                computes_to_mock[field.compute].append(field)
            with ExitStack() as stack:
                for compute, fields in computes_to_mock.items():
                    stack.enter_context(
                        patch.object(
                            self.registry["document.document"],
                            compute,
                            autospec=True,
                            side_effect=self.failureException(
                                f"The compute stored field `{'|'.join(f.name for f in fields)}` must not be triggered "
                                "after a copy upon flushing, its value should be just copied or explicitly set."
                            ),
                        )
                    )
                yield

        with patched_compute_methods():
            with mute_logger("odoo.addons.document.models.document_document"):
                copy = self.document_txt.copy()
            self.assertEqual(copy.name, "file.txt (copy)")
            self.assertNotEqual(
                copy.attachment_id.check_singleton().id,
                self.document_txt.attachment_id.id,
                "There must be a new attachment",
            )
            self.assertEqual(copy.raw, self.document_txt.raw)

            self.env.flush_all()

            self.assertEqual(copy.is_multipage, self.document_txt.is_multipage)

        with mute_logger("odoo.addons.document.models.document_document"):
            copy_with_default = self.document_txt.copy({"name": "test"})
        self.assertEqual(copy_with_default.name, "test")
        self.assertNotEqual(
            copy.attachment_id.check_singleton().id,
            self.document_txt.attachment_id.id,
            "There must be a new attachment",
        )
        self.assertEqual(copy.raw, self.document_txt.raw)

        self.assertFalse(self.folder_a.folder_id)
        self.folder_a.owner_id = False
        self.folder_a.access_internal = "edit"

        with self.assertRaises(AccessError):
            self.folder_a.with_user(self.internal_user).check_access("write")
        self.assertEqual(
            self.folder_a.with_user(self.internal_user).user_permission, "edit"
        )

        self.document_txt.folder_id = self.folder_a
        self.document_txt.with_user(self.internal_user).copy()

        self.assertNotEqual(self.document_txt.folder_id, self.document_gif.folder_id)
        copied_documents = (
            (self.document_txt | self.document_gif).with_user(self.internal_user).copy()
        )
        self.assertEqual(copied_documents[0].name, f"{self.document_txt.name} (copy)")
        self.assertEqual(copied_documents[1].name, f"{self.document_gif.name} (copy)")

        document_txt_copy = self.document_txt.with_user(self.internal_user).copy()
        copied_documents = (
            (self.document_txt | document_txt_copy).with_user(self.internal_user).copy()
        )
        self.document_txt.unlink()
        for copied_document in copied_documents:
            self.assertFalse(copied_document.res_id)
            self.assertFalse(copied_document.res_model)
            self.assertEqual(copied_document.attachment_id.res_id, copied_document.id)
            self.assertEqual(
                copied_document.attachment_id.res_model, "document.document"
            )
            self.assertTrue(copied_document.exists())

        self.document_gif.write(
            {
                "res_model": "res.partner",
                "res_id": self.env.user.partner_id.id,
            }
        )
        with mute_logger("odoo.addons.document.models.document_document"):
            copied_document = self.document_gif.copy()
        self.assertFalse(copied_document.res_id, copied_document.id)
        self.assertFalse(copied_document.res_model)
        self.assertEqual(copied_document.attachment_id.res_id, copied_document.id)
        self.assertEqual(copied_document.attachment_id.res_model, "document.document")

    def test_copy_document_company_to_company(self):
        copied_folder = self.company_root_folder.with_user(self.document_manager).copy(
            default={"user_folder_id": "COMPANY"}
        )
        self.assertTrue(copied_folder)
        self.assertFalse(
            copied_folder.owner_id, "Copied folder should not have owner_id set"
        )

        copied_doc = self.company_root_document.with_user(self.document_manager).copy(
            default={"user_folder_id": "COMPANY"}
        )
        self.assertTrue(copied_doc)
        self.assertFalse(
            copied_doc.owner_id, "Copied document should not have owner_id set"
        )

    def test_copy_document_company_to_my_drive(self):
        copied_folder = self.company_root_folder.with_user(self.document_manager).copy(
            default={"user_folder_id": "MY"}
        )
        self.assertTrue(
            copied_folder.owner_id, "Copied folder should have owner_id set"
        )
        self.assertEqual(
            copied_folder.owner_id.id,
            self.document_manager.id,
            "Copied folder owner should be the manager",
        )

        copied_doc = self.company_root_document.with_user(self.document_manager).copy(
            default={"user_folder_id": "MY"}
        )
        self.assertTrue(copied_doc.owner_id, "Copied document should have owner_id set")
        self.assertEqual(
            copied_doc.owner_id.id,
            self.document_manager.id,
            "Copied document owner should be the manager",
        )

        copied_folder = self.company_root_folder.with_user(self.doc_user).copy(
            default={"user_folder_id": "MY"}
        )
        self.assertTrue(
            copied_folder.owner_id, "Copied folder should have owner_id set"
        )
        self.assertEqual(
            copied_folder.owner_id.id,
            self.doc_user.id,
            "Copied folder owner should be the internal user",
        )

        copied_doc = self.company_root_document.with_user(self.doc_user).copy(
            default={"user_folder_id": "MY"}
        )
        self.assertTrue(copied_doc.owner_id, "Copied document should have owner_id set")
        self.assertEqual(
            copied_doc.owner_id.id,
            self.doc_user.id,
            "Copied document owner should be the internal user",
        )

    def test_copy_document_to_itself(self):
        folder = self.company_root_folder
        sub_folder = self.company_sub_folder
        with self.assertRaisesRegex(UserError, "cannot copy a folder into itself"):
            folder.with_user(self.document_manager).copy(
                default={"user_folder_id": str(folder.id)}
            )

        with self.assertRaisesRegex(UserError, "cannot copy a folder into itself"):
            sub_folder.with_user(self.document_manager).copy(
                default={"user_folder_id": str(sub_folder.id)}
            )

        with self.assertRaisesRegex(UserError, "cannot copy a folder into itself"):
            folder.with_user(self.document_manager).copy(
                default={"user_folder_id": str(sub_folder.id)}
            )

    def test_copy_document_keeps_the_record_link_it_is_given(self):
        partner = self.env.user.partner_id
        self.document_gif.write({"res_model": "res.partner", "res_id": partner.id})

        with mute_logger("odoo.addons.document.models.document_document"):
            detached = self.document_gif.copy()
            from_default = self.document_gif.copy(
                {"res_model": "res.partner", "res_id": partner.id}
            )
            from_record_panel = self.document_gif.with_context(
                default_res_model="res.partner", default_res_id=partner.id
            ).copy()

        self.assertFalse(detached.res_model)
        for copied in (from_default, from_record_panel):
            self.assertEqual(
                (copied.res_model, copied.res_id), ("res.partner", partner.id)
            )
            self.assertEqual(
                (copied.attachment_id.res_model, copied.attachment_id.res_id),
                ("res.partner", partner.id),
            )
            self.assertNotEqual(copied.attachment_id, self.document_gif.attachment_id)

    def test_copy_shortcut(self):
        manager_shortcut = self.document_txt.with_user(
            self.document_manager
        ).action_create_shortcut()
        self.assertTrue(manager_shortcut.folder_id)
        self.assertEqual(
            manager_shortcut.copy({"user_folder_id": "MY"}).user_folder_id, "MY"
        )
        self.assertEqual(
            manager_shortcut.copy({"user_folder_id": "COMPANY"}).user_folder_id,
            "COMPANY",
        )
        self.assertEqual(
            manager_shortcut.copy(
                {"user_folder_id": str(manager_shortcut.folder_id.id)}
            ).user_folder_id,
            str(manager_shortcut.folder_id.id),
        )

    def test_embedding_actions(self):
        self.env["res.lang"]._activate_lang("fr_FR")
        doc = self.env["document.document"].create(
            {"name": "A request", "folder_id": self.folder_a.id}
        )
        self.assertFalse(doc.available_embedded_actions_ids)
        self.server_action.with_context(lang="fr_FR").name = "Blablabla"
        self.env["document.document"].action_folder_embed_action(
            self.folder_a.id, self.server_action.id
        )
        doc.invalidate_recordset(["available_embedded_actions_ids"])
        embedded_action = doc.available_embedded_actions_ids
        self.assertEqual(embedded_action.name, self.server_action.name)
        self.assertEqual(embedded_action.with_context(lang="fr_FR").name, "Blablabla")

    def test_embedding_actions_permission(self):
        user_no_rights = new_test_user(
            self.env, login="user_no_doc_rights", groups="base.group_user"
        )

        folder = self.env["document.document"].create(
            {"name": "Test Folder", "type": "folder"}
        )
        action = self.env["ir.actions.server"].create(
            {
                "name": "Test Server Action",
                "model_id": self.env["ir.model"]._get("document.document").id,
                "state": "code",
            }
        )

        self.env["document.document"].with_user(
            user_no_rights
        ).sudo().action_folder_embed_action(folder.id, action.id)
        embedded = self.env["ir.embedded.actions"].search(
            [
                ("action_id", "=", action.id),
                ("parent_res_id", "=", folder.id),
                ("parent_res_model", "=", "document.document"),
            ]
        )
        self.assertTrue(embedded, "The action should have been embedded in sudo mode")

        with self.assertRaises(AccessError):
            self.env["document.document"].with_user(
                user_no_rights
            ).action_folder_embed_action(folder.id, action.id)
        self.assertTrue(
            embedded,
            "The action should not have been unembedded without rights or sudo",
        )

    def test_embedding_actions_requires_folder_edit(self):
        action = self.env["ir.actions.server"].create(
            {
                "name": "Test Server Action",
                "model_id": self.env["ir.model"]._get("document.document").id,
                "state": "code",
            }
        )
        viewer = new_test_user(
            self.env, login="doc_viewer", groups="document.group_documents_user"
        )
        self.folder_a.action_update_access_rights(
            partners={viewer.partner_id: ("view", False)}
        )
        self.assertEqual(self.folder_a.with_user(viewer).user_permission, "view")
        with self.assertRaises(AccessError):
            self.env["document.document"].with_user(viewer).action_folder_embed_action(
                self.folder_a.id, action.id
            )

    def test_embedding_actions_obsolescence_gc(self):
        doc = self.env["document.document"].create(
            {
                "name": "A request",
                "folder_id": self.folder_a.id,
            }
        )
        parent_base = self.server_action
        parent_base.group_ids = [
            Command.create(
                {"name": "Test Gr", "user_ids": [Command.link(self.env.user.id)]}
            )
        ]
        child_base = parent_base.copy()
        self.assertTrue(child_base.group_ids)

        self.env["document.document"].action_folder_embed_action(
            self.folder_a.id, parent_base.id
        )
        self.env["document.document"].action_folder_embed_action(
            self.folder_a.id, child_base.id
        )
        self.env["ir.embedded.actions"].with_user(
            self.env.ref("base.user_root")
        )._gc_documents_obsolete()
        embedded_action = (
            self.env["ir.embedded.actions"]
            .search([("action_id", "in", (child_base | parent_base).ids)])
            .grouped(lambda a: a.action_id.id)
        )

        def _visible_action_ids():
            actions = self.env["document.document"].get_documents_actions(
                folder_id=self.folder_a.id
            )
            return {a["id"] for a in actions}

        actions_init = _visible_action_ids()
        self.assertIn(parent_base.id, actions_init)
        self.assertIn(child_base.id, actions_init)

        doc.invalidate_recordset(["available_embedded_actions_ids"])

        parent_base.write(
            {
                "child_ids": [Command.link(child_base.id)],
            }
        )

        actions_before = _visible_action_ids()
        self.assertIn(parent_base.id, actions_before)
        self.assertNotIn(child_base.id, actions_before)
        self.assertNotIn(
            child_base.id, doc.available_embedded_actions_ids.action_id.ids
        )
        doc_in_context = self.env["document.document"].with_context(
            active_model="document.document", active_id=doc.id
        )
        child_embedded = embedded_action[child_base.id].exists()
        self.assertTrue(child_embedded)
        with self.assertRaises(UserError):
            doc_in_context.action_execute_embedded_action(
                embedded_action[child_base.id].id
            )
        self.env["ir.embedded.actions"].with_user(
            self.ref("base.user_root")
        )._gc_documents_obsolete()
        self.assertFalse(child_embedded.exists())
        doc_in_context.action_execute_embedded_action(
            embedded_action[parent_base.id].id
        )

    def test_document_thumbnail_status(self):
        for mimetype in ["application/pdf", "application/pdf;base64"]:
            with self.subTest(mimetype=mimetype):
                pdf_document = self.env["document.document"].create(
                    {
                        "name": "Test PDF doc",
                        "mimetype": mimetype,
                        "datas": "JVBERi0gRmFrZSBQREYgY29udGVudA==",
                        "folder_id": self.folder_b.id,
                    }
                )
                self.assertEqual(pdf_document.thumbnail, False)
                self.assertEqual(pdf_document.thumbnail_status, "client_generated")

        word_document = self.env["document.document"].create(
            {
                "name": "Test DOC doc",
                "mimetype": "application/msword",
                "folder_id": self.folder_b.id,
            }
        )
        self.assertEqual(word_document.thumbnail, False)
        self.assertEqual(word_document.thumbnail_status, False)

        webp_document = self.env["document.document"].create(
            {
                "name": "Test WEBP doc",
                "mimetype": "image/webp",
                "datas": WEBP,
                "folder_id": self.folder_b.id,
            }
        )
        self.assertEqual(webp_document.thumbnail, False)
        self.assertEqual(webp_document.thumbnail_status, "client_generated")

        image_documents = self.env["document.document"].create(
            [
                {
                    "name": "Test image doc",
                    "mimetype": mimetype,
                    "datas": GIF,
                    "folder_id": self.folder_b.id,
                }
                for mimetype in [
                    "image/bmp",
                    "image/gif",
                    "image/jpeg",
                    "image/png",
                    "image/svg+xml",
                    "image/tiff",
                    "image/x-icon",
                ]
            ]
        )
        for image_document in image_documents:
            with self.subTest(mimetype=image_document.mimetype):
                self.assertEqual(image_document.thumbnail, GIF)
                self.assertEqual(image_document.thumbnail_status, "present")

        text_documents = self.env["document.document"].create(
            [
                {
                    "name": "Test Special Case Text doc",
                    "mimetype": mimetype,
                    "datas": TEXT,
                    "folder_id": self.folder_b.id,
                }
                for mimetype in [
                    "text/html",
                    "text/csv",
                    "text/plain",
                    "text/javascript",
                    "text/css",
                    "text/markdown",
                    "text/xml",
                    "application/json",
                    "application/xml",
                    "text/calendar",
                ]
            ]
        )
        for text_document in text_documents:
            with self.subTest(mimetype=text_document.mimetype):
                self.assertEqual(text_document.thumbnail, False)
                self.assertEqual(text_document.thumbnail_status, False)

    def test_document_max_upload_limit(self):
        Doc = self.env["document.document"]
        ICP = self.env["ir.config_parameter"]
        key_doc = "document.max_fileupload_size"
        key_web = "web.max_file_upload_size"

        ICP.set_param(key_doc, 20)
        ICP.set_param(key_web, 10)
        self.assertEqual(Doc.get_document_max_upload_limit(), 20)

        ICP.set_param(key_doc, 0)
        self.assertEqual(Doc.get_document_max_upload_limit(), None)

        ICP.search([("key", "=", key_doc)]).unlink()
        self.assertEqual(Doc.get_document_max_upload_limit(), 10)

        ICP.search([("key", "=", key_web)]).unlink()
        self.assertEqual(
            Doc.get_document_max_upload_limit(), http.DEFAULT_MAX_CONTENT_LENGTH
        )

    def test_document_order_by_is_folder(self):
        doc_1 = self.env["document.document"].create([{"name": "D1"}])
        doc_2 = self.env["document.document"].create([{"name": "D2", "type": "folder"}])
        doc_3 = self.env["document.document"].create([{"name": "D3", "type": "url"}])
        doc_4 = self.env["document.document"].create([{"name": "D4"}])
        docs = doc_1 | doc_2 | doc_3 | doc_4
        result = self.env["document.document"].search(
            [("id", "in", docs.ids)], order="is_folder DESC, create_date DESC, id DESC"
        )

        self.assertEqual(result[0], doc_2)
        self.assertEqual(result[1], doc_4)
        self.assertEqual(result[2], doc_3)
        self.assertEqual(result[3], doc_1)

    def test_document_order_by_last_access_date(self):
        documents = self.env["document.document"].create(
            [{"name": "D1"}, {"name": "D2"}]
        )
        self.env["document.access"].create(
            [
                {
                    "document_id": documents[0].id,
                    "last_access_date": fields.Datetime.now() + timedelta(days=1),
                    "partner_id": self.env.user.partner_id.id,
                },
                {
                    "document_id": documents[1].id,
                    "last_access_date": fields.Datetime.now() + timedelta(days=2),
                    "partner_id": self.env.user.partner_id.id,
                },
            ]
        )

        result = self.env["document.document"].search(
            [("id", "in", documents.ids)], order="last_access_date_group DESC"
        )
        self.assertEqual(result[0], documents[1])
        self.assertEqual(result[1], documents[0])

        result = self.env["document.document"].search(
            [("id", "in", documents.ids)], order="last_access_date_group ASC"
        )
        self.assertEqual(result[0], documents[0])
        self.assertEqual(result[1], documents[1])

    def test_document_group_by_last_access_date(self):
        Doc = self.env["document.document"]
        documents = Doc.create([{"name": f"D{i}"} for i in range(6)])
        self.env["document.access"].create(
            [
                {
                    "document_id": documents[0].id,
                    "last_access_date": fields.Datetime.now() - timedelta(hours=1),
                    "partner_id": self.env.user.partner_id.id,
                },
                {
                    "document_id": documents[1].id,
                    "last_access_date": fields.Datetime.now() - timedelta(days=2),
                    "partner_id": self.env.user.partner_id.id,
                },
                {
                    "document_id": documents[2].id,
                    "last_access_date": fields.Datetime.now() - timedelta(days=8),
                    "partner_id": self.env.user.partner_id.id,
                },
                {
                    "document_id": documents[3].id,
                    "last_access_date": fields.Datetime.now() - timedelta(days=40),
                    "partner_id": self.env.user.partner_id.id,
                },
                {
                    "document_id": documents[4].id,
                    "last_access_date": fields.Datetime.now() - timedelta(minutes=1),
                    "partner_id": self.env.user.partner_id.id,
                },
                {
                    "document_id": documents[5].id,
                    "last_access_date": fields.Datetime.now()
                    - timedelta(days=1, hours=5),
                    "partner_id": self.env.user.partner_id.id,
                },
            ]
        )

        result = Doc.formatted_read_group(
            [("id", "in", documents.ids)],
            groupby=["last_access_date_group"],
            aggregates=["__count"],
            order="last_access_date_group DESC",
        )

        self.assertEqual(len(result), 4)

        self.assertEqual(result[0]["last_access_date_group"], "3_day")
        self.assertEqual(result[0]["__count"], 2)
        result_day = Doc.search(result[0]["__extra_domain"])
        self.assertEqual(result_day[0], documents[4])
        self.assertEqual(result_day[1], documents[0])
        self.assertEqual(result_day.mapped("last_access_date_group"), ["3_day"] * 2)

        self.assertEqual(result[1]["last_access_date_group"], "2_week")
        self.assertEqual(result[1]["__count"], 2)
        result_week = Doc.search(result[1]["__extra_domain"])
        self.assertEqual(result_week[0], documents[5])
        self.assertEqual(result_week[1], documents[1])
        self.assertEqual(result_week.mapped("last_access_date_group"), ["2_week"] * 2)

        self.assertEqual(result[2]["last_access_date_group"], "1_month")
        self.assertEqual(result[2]["__count"], 1)
        self.assertEqual(Doc.search(result[2]["__extra_domain"]), documents[2])
        self.assertEqual(documents[2].last_access_date_group, "1_month")

        self.assertEqual(result[3]["last_access_date_group"], "0_older")
        self.assertEqual(result[3]["__count"], 1)
        self.assertEqual(Doc.search(result[3]["__extra_domain"]), documents[3])
        self.assertEqual(documents[3].last_access_date_group, "0_older")

    def test_link_constrains(self):
        folder = self.env["document.document"].create(
            {"name": "folder", "type": "folder"}
        )
        for url in (
            "wrong URL format",
            "https:/ example.com",
            "test https://example.com",
        ):
            with self.assertRaises(ValidationError):
                self.env["document.document"].create(
                    {
                        "name": "Test Document",
                        "folder_id": folder.id,
                        "url": url,
                    }
                )

    def test_document_shortcut_to_my_drive(self):
        shortcut_1 = self.document_txt.action_create_shortcut(
            location_user_folder_id=str(self.folder_b.id)
        )
        shortcut_2 = shortcut_1.with_user(self.internal_user).action_create_shortcut(
            location_user_folder_id="MY"
        )
        self.assertEqual(shortcut_2.folder_id.id, False)
        self.assertEqual(shortcut_2.with_user(self.internal_user).user_folder_id, "MY")

    def test_document_upload_from_chatter(self):
        folder = self.env["document.document"].create(
            [{"type": "folder", "name": "folder", "access_internal": "view"}]
        )
        attachment = self.env["ir.attachment"].create(
            {
                "datas": GIF,
                "name": "TestAttachment.gif",
                "res_model": "document.document",
                "res_id": folder.id,
            }
        )
        self.assertNotEqual(
            attachment.name, folder.name, "the folder name should not change"
        )

    def test_document_toggle_lock(self):

        self.document_txt.write({"owner_id": self.document_manager.id})
        self.document_txt.access_ids.filtered("role").unlink()

        self.document_txt.with_user(self.document_manager).toggle_lock()
        with self.assertRaises(AccessError):
            self.document_txt.with_user(self.doc_user).toggle_lock()
        self.assertEqual(
            self.document_txt.lock_uid.id,
            self.document_manager.id,
            "viewer should not have unlocked",
        )

        self.document_txt.access_internal = "edit"
        self.document_txt.with_user(self.doc_user).toggle_lock()
        self.assertFalse(self.document_txt.lock_uid, "editor should have unlocked")

    def test_lock_blocks_every_way_of_changing_the_content(self):
        self.document_txt.write({"owner_id": self.document_manager.id})
        self.document_txt.access_internal = "edit"
        self.document_txt.with_user(self.document_manager).toggle_lock()
        original = self.document_txt.attachment_id.raw
        self.assertTrue(original, "the fixture must start with content")

        for vals in (
            {"raw": b""},
            {"raw": False},
            {"datas": b""},
            {"datas": False},
            {"attachment_id": False},
            {"raw": b"replaced"},
        ):
            with self.subTest(vals=vals), self.assertRaises(UserError):
                self.document_txt.with_user(self.doc_user).write(dict(vals))

        self.assertEqual(
            self.document_txt.attachment_id.raw,
            original,
            "a user who does not hold the lock changed the content",
        )

    def test_res_name_recompute_with_deleted_record(self):
        partner = self.env["res.partner"].create({"name": "Test Partner"})
        doc = self.env["document.document"].create(
            {
                "name": "Test",
                "res_id": partner.id,
                "res_model": "res.partner",
            }
        )
        self.assertEqual(doc.res_name, "Test Partner")
        partner.unlink()
        self.assertFalse(doc.res_name)


@tagged("post_install", "-at_install")
class TestDocumentsResName(TransactionCaseDocuments):
    def test_f4_compute_res_name_is_batched(self):
        partners = self.env["res.partner"].create(
            [{"name": f"audit3 partner {i}"} for i in range(20)]
        )
        documents = self.env["document.document"].create(
            [
                {
                    "type": "binary",
                    "name": f"audit3 linked {i}",
                    "folder_id": self.folder_b.id,
                    "owner_id": self.doc_user.id,
                    "res_model": "res.partner",
                    "res_id": partner.id,
                }
                for i, partner in enumerate(partners)
            ]
        )
        self.assertFalse(documents.attachment_id)

        self.env.flush_all()
        documents.invalidate_recordset()
        self.env.invalidate_all()
        count0 = self.cr.sql_statement_count
        names = documents.mapped("res_name")
        queries = self.cr.sql_statement_count - count0

        self.assertEqual(names, partners.mapped("display_name"))
        self.assertLess(
            queries,
            len(documents),
            f"_compute_res_name still scales linearly ({queries} queries for "
            f"{len(documents)} documents)",
        )

    def test_f4_compute_res_name_fallbacks_preserved(self):
        param = self.env["ir.config_parameter"].create(
            {"key": "document.audit3_probe", "value": "x"}
        )
        ghost = self.env["res.partner"].create({"name": "audit3 ghost"})
        doc_restricted, doc_missing = self.env["document.document"].create(
            [
                {
                    "type": "binary",
                    "name": "audit3 restricted link",
                    "folder_id": self.folder_b.id,
                    "owner_id": self.doc_user.id,
                    "res_model": "ir.config_parameter",
                    "res_id": param.id,
                },
                {
                    "type": "binary",
                    "name": "audit3 missing link",
                    "folder_id": self.folder_b.id,
                    "owner_id": self.doc_user.id,
                    "res_model": "res.partner",
                    "res_id": ghost.id,
                },
            ]
        )
        ghost.unlink()
        self.env.invalidate_all()

        self.assertEqual(doc_restricted.with_user(self.doc_user).res_name, "Restricted")
        self.assertFalse(doc_missing.res_name)

    def test_f4_compute_res_name_ignores_whether_an_attachment_exists(self):
        param = self.env["ir.config_parameter"].create(
            {"key": "document.audit3_probe_attached", "value": "x"}
        )
        with_attachment, without_attachment = self.env["document.document"].create(
            [
                {
                    "type": "binary",
                    "name": "audit3 attached restricted link",
                    "folder_id": self.folder_b.id,
                    "owner_id": self.doc_user.id,
                    "datas": TEXT,
                    "res_model": "ir.config_parameter",
                    "res_id": param.id,
                },
                {
                    "type": "binary",
                    "name": "audit3 bare restricted link",
                    "folder_id": self.folder_b.id,
                    "owner_id": self.doc_user.id,
                    "res_model": "ir.config_parameter",
                    "res_id": param.id,
                },
            ]
        )
        self.assertTrue(with_attachment.attachment_id)
        self.assertFalse(without_attachment.attachment_id)
        self.env.invalidate_all()

        self.assertEqual(
            with_attachment.with_user(self.doc_user).res_name, "Restricted"
        )
        self.assertEqual(
            without_attachment.with_user(self.doc_user).res_name, "Restricted"
        )

        plain = self.env["document.document"].create(
            {
                "type": "binary",
                "name": "audit3 plain upload",
                "folder_id": self.folder_b.id,
                "owner_id": self.doc_user.id,
                "datas": TEXT,
            }
        )
        self.assertTrue(plain.attachment_id)
        self.assertEqual(plain.attachment_id.res_model, "document.document")
        self.assertFalse(plain.res_model)
        self.assertFalse(plain.res_name)

    def test_f4_compute_res_name_survives_an_uninstalled_model(self):
        doc = self.env["document.document"].create(
            {
                "type": "binary",
                "name": "audit3 stale model link",
                "folder_id": self.folder_b.id,
                "owner_id": self.doc_user.id,
            }
        )
        doc.invalidate_recordset()
        self.env.cr.execute(
            "UPDATE document_document SET res_model = %s, res_id = %s WHERE id = %s",
            ["gone.model", 1, doc.id],
        )
        doc.invalidate_recordset()
        self.assertFalse(doc.res_name)

    def test_s4_res_name_hidden_for_inaccessible_record(self):
        secret = self.env["res.partner"].create({"name": "SECRET_AUDIT_PARTNER"})
        self.env["ir.rule"].create(
            {
                "name": "hide secret audit partner",
                "model_id": self.env["ir.model"]._get_id("res.partner"),
                "domain_force": "[('name', '!=', 'SECRET_AUDIT_PARTNER')]",
                "perm_read": True,
                "perm_write": True,
                "perm_create": False,
                "perm_unlink": False,
            }
        )
        doc = (
            self.env["document.document"]
            .with_user(self.document_manager)
            .create(
                {
                    "type": "binary",
                    "name": "linked",
                    "user_folder_id": "COMPANY",
                    "res_model": "res.partner",
                    "res_id": secret.id,
                }
            )
        )
        doc.action_update_access_rights(access_internal="view")
        self.env.invalidate_all()
        with self.assertRaises(AccessError):
            secret.with_user(self.internal_user).read(["name"])
        self.assertNotEqual(
            doc.with_user(self.internal_user).res_name,
            "SECRET_AUDIT_PARTNER",
            "res_name must not leak the name of an inaccessible linked record",
        )


@tagged("post_install", "-at_install")
class TestDocumentsCreateContract(TransactionCaseDocuments):
    def test_create_preserves_vals_list_order(self):
        partner = self.env["res.partner"].create({"name": "linked record"})
        attachments = (
            self.env["ir.attachment"]
            .with_context(no_document=True)
            .create(
                [
                    {"name": "a.txt", "raw": b"AAA"},
                    {
                        "name": "b.txt",
                        "raw": b"BBB",
                        "res_model": "res.partner",
                        "res_id": partner.id,
                    },
                    {"name": "c.txt", "raw": b"CCC"},
                ]
            )
        )
        vals_list = [
            {"name": name, "attachment_id": attachment.id}
            for name, attachment in zip("ABC", attachments, strict=True)
        ]

        documents = self.env["document.document"].create(vals_list)

        self.assertEqual(documents.mapped("name"), ["A", "B", "C"])
        for document, vals in zip(documents, vals_list, strict=True):
            self.assertEqual(document.attachment_id.id, vals["attachment_id"])
        for document in documents:
            attachment = document.attachment_id
            if attachment.res_model == "document.document":
                self.assertEqual(attachment.res_id, document.id)

    def test_create_in_folder_inherits_members_in_order(self):
        partner = self.env["res.partner"].create({"name": "folder member"})
        folder = self.env["document.document"].create(
            {"name": "shared folder", "type": "folder"}
        )
        folder.action_update_access_rights(partners={partner.id: ("edit", False)})

        documents = self.env["document.document"].create(
            [
                {"name": "inherits", "type": "binary", "folder_id": folder.id},
                {
                    "name": "opts out",
                    "type": "binary",
                    "folder_id": folder.id,
                    "access_ids": [Command.set([])],
                },
            ]
        )
        self.assertEqual(documents.mapped("name"), ["inherits", "opts out"])
        self.assertIn(partner, documents[0].access_ids.partner_id)
        self.assertNotIn(partner, documents[1].access_ids.filtered("role").partner_id)


@tagged("post_install", "-at_install")
class TestDocumentsUrlPreview(TransactionCaseDocuments):
    def test_p1_url_preview_is_deferred(self):
        calls = []

        def spy(url, session, *args, **kwargs):
            calls.append(url)
            return {"og_title": "Real Title", "og_image": "https://img/x.png"}

        with patch.object(link_preview, "get_link_preview_from_url", spy):
            doc = self.env["document.document"].create(
                {"type": "url", "url": "https://example.com/probe"}
            )
            doc.name
            doc.url_preview_image
            self.assertEqual(calls, [], "URL preview must not be fetched synchronously")
            self.assertTrue(doc.url_preview_pending)
            self.assertEqual(doc.name, "https://example.com/probe")

            self.env["document.document"]._cron_update_url_preview()

        self.assertIn("https://example.com/probe", calls)
        self.assertFalse(doc.url_preview_pending)
        self.assertEqual(doc.name, "Real Title")
        self.assertEqual(doc.url_preview_image, "https://img/x.png")


@tagged("post_install", "-at_install")
class TestDocumentsFolderHelpers(TransactionCaseDocuments):
    def test_is_folder_containing_document(self):
        self.assertTrue(self.folder_b.is_folder_containing_document())
        empty = self.env["document.document"].create(
            {"type": "folder", "name": "empty", "owner_id": self.doc_user.id}
        )
        self.assertFalse(empty.is_folder_containing_document())
        self.env["document.document"].create(
            {"type": "folder", "name": "child", "folder_id": empty.id}
        )
        self.assertFalse(empty.is_folder_containing_document())

    def test_action_move_folder_stale_before_folder(self):
        doc_env = self.env["document.document"].with_user(self.doc_user)
        sub1, sub2 = doc_env.create(
            [
                {
                    "type": "folder",
                    "name": name,
                    "folder_id": self.folder_a.id,
                    "owner_id": self.doc_user.id,
                }
                for name in ("sub1", "sub2")
            ]
        )
        ghost_id = sub2.id
        sub2.unlink()
        sub1.action_move_folder(str(self.folder_a.id), before_folder_id=ghost_id)
        self.assertEqual(sub1.folder_id, self.folder_a)

    def test_traceback_folder_survives_a_malformed_parameter(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "document.support_folder", "not-an-int"
        )
        folder = self.env["document.document"]._get_traceback_folder_sudo()
        self.assertTrue(folder.exists())
        self.assertEqual(folder.type, "folder")


@tagged("post_install", "-at_install")
class TestDocumentsCopy(TransactionCase):
    def test_copy_folders_only_returns_a_well_formed_recordset(self):
        user = self.env["res.users"].create(
            {
                "name": "Copy user",
                "login": "round4_copy",
                "group_ids": [
                    Command.link(self.env.ref("document.group_documents_user").id)
                ],
            }
        )
        Document = self.env["document.document"].with_user(user)
        folder = Document.create(
            {"name": "Copied folder", "type": "folder", "access_internal": "edit"}
        )
        document = Document.create(
            {
                "name": "Skipped file",
                "type": "binary",
                "folder_id": folder.id,
                "access_internal": "edit",
            }
        )

        copies = (
            (folder | document)
            .with_context(documents_copy_folders_only=True)
            .copy({"user_folder_id": "MY"})
        )

        self.assertEqual(len(copies), len(copies.ids), "no placeholder slots")
        self.assertEqual(len(copies), 1, "only the folder is copied")
        self.assertTrue(all(copies.mapped("name")), "the result must be readable")


@tagged("post_install", "-at_install")
class TestDocumentsCreateBatching(TransactionCaseDocuments):
    """Creating N documents that carry content costs one attachment insert.

    `assertQueryCount` only fails ABOVE its budget, so the guard that matters
    here is the SHAPE: the same budget has to hold for one document and for
    twenty, which is what a per-document insert cannot do. A budget alone would
    pass at N=1 and go on passing while the cost grew.
    """

    def _create_with_content(self, count, tag):
        return self.env["document.document"].create(
            [
                {
                    "name": f"{tag}-{index}.txt",
                    "type": "binary",
                    "raw": b"payload",
                    "folder_id": self.folder_a.id,
                }
                for index in range(count)
            ]
        )

    def test_the_cost_of_creating_documents_does_not_follow_their_number(self):
        self._create_with_content(1, "warmup")  # fill the caches the first call fills
        self.env.flush_all()

        before = self.env.cr.sql_statement_count
        self._create_with_content(1, "one")
        self.env.flush_all()
        cost_of_one = self.env.cr.sql_statement_count - before

        before = self.env.cr.sql_statement_count
        documents = self._create_with_content(20, "twenty")
        self.env.flush_all()
        cost_of_twenty = self.env.cr.sql_statement_count - before

        self.assertEqual(len(documents), 20)
        self.assertTrue(all(documents.mapped("attachment_id")))
        self.assertEqual(
            documents.mapped("name"), [f"twenty-{i}.txt" for i in range(20)]
        )
        self.assertLessEqual(
            cost_of_twenty,
            cost_of_one + 4,
            f"creating 20 documents cost {cost_of_twenty} queries against "
            f"{cost_of_one} for one: the attachment insert is running per "
            f"document again",
        )

    def test_a_batch_mixing_content_and_ready_attachments_keeps_them_paired(self):
        """The batch create must not shift an attachment onto the wrong vals."""
        existing = (
            self.env["ir.attachment"]
            .with_context(no_document=True)
            .create({"name": "ready.txt", "raw": b"ready"})
        )

        documents = self.env["document.document"].create(
            [
                {"name": "first.txt", "type": "binary", "raw": b"first"},
                {"type": "binary", "attachment_id": existing.id},
                {"name": "third.txt", "type": "binary", "raw": b"third"},
                {"name": "no-content.txt", "type": "binary"},
            ]
        )

        self.assertEqual(documents[1].attachment_id, existing)
        self.assertEqual(documents[1].name, "ready.txt", "name falls back to the file")
        self.assertEqual(documents[0].attachment_id.raw, b"first")
        self.assertEqual(documents[2].attachment_id.raw, b"third")
        self.assertFalse(documents[3].attachment_id)
        self.assertEqual(
            documents.mapped("name"),
            ["first.txt", "ready.txt", "third.txt", "no-content.txt"],
        )


@tagged("post_install", "-at_install")
class TestDocumentsResModelConstraint(TransactionCaseDocuments):
    """A document is never linked to a document, archived or not.

    The rule used to be enforced with `search_count`, which goes through
    `_search` and therefore applies `active_test`: it simply did not exist for
    an archived record. Archive, link, restore, and the forbidden state was
    live -- including `res_id == id`, a document linked to itself.
    """

    def _link_to(self, document, target):
        document.write({"res_model": "document.document", "res_id": target.id})

    def test_an_active_document_may_not_be_linked_to_a_document(self):
        target = self.env["document.document"].create(
            {"name": "target.txt", "type": "binary", "raw": b"t"}
        )
        document = self.env["document.document"].create(
            {"name": "source.txt", "type": "binary", "raw": b"s"}
        )

        with self.assertRaises(ValidationError):
            self._link_to(document, target)

    def test_an_archived_document_may_not_be_linked_either(self):
        target = self.env["document.document"].create(
            {"name": "target.txt", "type": "binary", "raw": b"t"}
        )
        document = self.env["document.document"].create(
            {"name": "sneak.txt", "type": "binary", "raw": b"s"}
        )
        self.env.flush_all()
        document.with_context(documents_archiving=True).write({"active": False})
        self.env.flush_all()

        with self.assertRaises(ValidationError):
            self._link_to(document, target)

    def test_an_archived_document_may_not_be_linked_to_itself(self):
        document = self.env["document.document"].create(
            {"name": "self.txt", "type": "binary", "raw": b"s"}
        )
        self.env.flush_all()
        document.with_context(documents_archiving=True).write({"active": False})
        self.env.flush_all()

        with self.assertRaises(ValidationError):
            self._link_to(document, document)

    def test_creating_an_archived_linked_document_is_refused(self):
        target = self.env["document.document"].create(
            {"name": "target.txt", "type": "binary", "raw": b"t"}
        )

        with self.assertRaises(ValidationError):
            self.env["document.document"].create(
                {
                    "name": "born-archived.txt",
                    "type": "binary",
                    "raw": b"s",
                    "active": False,
                    "res_model": "document.document",
                    "res_id": target.id,
                }
            )

    def test_a_document_linked_to_another_model_is_fine(self):
        """Negative control: the constraint targets one model, not all links."""
        partner = self.env["res.partner"].create({"name": "Linkable"})
        document = self.env["document.document"].create(
            {"name": "ok.txt", "type": "binary", "raw": b"s"}
        )

        document.write({"res_model": "res.partner", "res_id": partner.id})

        self.assertEqual(document.res_model, "res.partner")
        self.assertEqual(document.res_id, partner.id)
