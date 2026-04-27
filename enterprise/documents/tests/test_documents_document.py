# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from datetime import datetime, timedelta
from unittest import skip
from unittest.mock import patch

from odoo import Command, http
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import new_test_user
from odoo.tests import users

from .test_documents_common import TransactionCaseDocuments, GIF, TEXT

DATA = "data:application/zip;base64,R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs="
file_a = {'name': 'doc.zip', 'datas': 'data:application/zip;base64,R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs='}


class TestCaseDocuments(TransactionCaseDocuments):

    @skip("TODO: move to controller")
    @users('documents@example.com')
    def test_documents_action_log_access_archived(self):
        access = self.env['documents.access'].search([
            ('document_id', '=', self.document_txt.id),
            ('partner_id', '=', self.env.user.partner_id.id),
        ])
        self.assertFalse(access)
        self.document_txt.action_archive()
        self.env['documents.document'].action_log_access(
            self.document_txt.access_token)
        access = self.env['documents.access'].search([
            ('document_id', '=', self.document_txt.id),
            ('partner_id', '=', self.env.user.partner_id.id),
        ])
        self.assertTrue(access)

    def test_documents_action_create_shortcut(self):
        # Make sure we test copying m2o too
        self.document_gif.partner_id = self.env.user.partner_id
        shortcut = self.document_gif.action_create_shortcut()
        self.assertFalse(shortcut.attachment_id)
        original_file_size = self.document_gif.file_size
        for field_name in self.env['documents.document']._get_shortcuts_copy_fields():
            with self.subTest(field_name=field_name):
                self.assertEqual(shortcut[field_name], self.document_gif[field_name])
        attachment = self.env['ir.attachment'].create({
            **file_a,
            'res_model': 'documents.document',
            'res_id': 0,
        })
        self.document_gif.attachment_id = attachment
        self.assertNotEqual(self.document_gif.file_size, original_file_size)
        self.assertEqual(shortcut.file_size, self.document_gif.file_size)
        self.assertEqual(shortcut.file_extension, self.document_gif.file_extension)

    def test_documents_action_delete_from_history(self):
        """Test the `action_delete_from_history` action of documents."""
        current_attachment = self.document_gif.attachment_id

        # We can not delete the attachment if the history is empty
        with self.assertRaises(UserError):
            self.document_gif.action_delete_from_history(current_attachment.id)
        self.assertTrue(current_attachment.exists())

        new_attachment, other_attachment = self.env['ir.attachment'].create([{'name': 'Test'}] * 2)
        self.document_gif.previous_attachment_ids = new_attachment

        # We can not delete the attachment if it's not in the history of the document
        with self.assertRaises(UserError):
            self.document_gif.action_delete_from_history(other_attachment.id)
        self.assertTrue(current_attachment.exists())
        self.assertTrue(new_attachment.exists())
        self.assertTrue(other_attachment.exists())

        # Delete the history version delete the attachment
        self.document_gif.action_delete_from_history(new_attachment.id)
        self.assertFalse(new_attachment.exists(), "The attachment should have been deleted")
        self.assertTrue(current_attachment.exists())

        # Deleting the current attachment restore the most recent version
        current_attachment = self.document_gif.attachment_id
        versions = self.env['ir.attachment'].create([{'name': 'Test'}] * 3)
        self.document_gif.previous_attachment_ids = versions
        self.document_gif.action_delete_from_history(current_attachment.id)
        self.assertFalse(current_attachment.exists())
        self.assertEqual(self.document_gif.attachment_id.id, max(versions.ids))

    def test_documents_create_from_attachment(self):
        """
        Tests a documents.document create method when created from an already existing ir.attachment.
        """
        attachment = self.env['ir.attachment'].create({
            'datas': GIF,
            'name': 'attachmentGif.gif',
            'res_model': 'documents.document',
            'res_id': 0,
        })
        document_a = self.env['documents.document'].create({
            'folder_id': self.folder_b.id,
            'name': 'new name',
            'attachment_id': attachment.id,
        })
        self.assertEqual(document_a.attachment_id.id, attachment.id,
                         'the attachment should be the attachment given in the create values')
        self.assertEqual(document_a.name, 'new name',
                         'the name given should be used')
        self.assertEqual(document_a.res_model, 'documents.document',
                         'the res_model should be set as document by default')
        self.assertEqual(document_a.res_id, document_a.id,
                         'the res_id should be set as its own id by default to allow access right inheritance')

    @users('documents@example.com')
    def test_documents_create_write(self):
        """
        Tests a documents.document create and write method,
        documents should automatically create a new ir.attachments in relevant cases.
        """
        document_a = self.env['documents.document'].create({
            'name': 'Test mimetype gif',
            'datas': GIF,
            'folder_id': self.folder_b.id,
        })
        self.assertEqual(document_a.res_model, 'documents.document',
                         'the res_model should be set as document by default')
        self.assertEqual(document_a.res_id, document_a.id,
                         'the res_id should be set as its own id by default to allow access right inheritance')
        self.assertEqual(document_a.attachment_id.datas, GIF, 'the document should have a GIF data')
        document_no_attachment = self.env['documents.document'].create({
            'name': 'Test mimetype gif',
            'folder_id': self.folder_b.id,
        })
        self.assertFalse(document_no_attachment.attachment_id, 'the new document shouldnt have any attachment_id')
        document_no_attachment.write({'datas': TEXT})
        self.assertEqual(document_no_attachment.attachment_id.datas, TEXT, 'the document should have an attachment')

    def test_documents_create_performance(self):
        folders = self.env['documents.document'].create([
            {'type': 'folder', 'name': f'Folder {i}', 'access_internal': 'view'}
            for i in range(50)
        ])
        folders.flush_recordset()
        folders.invalidate_recordset()
        with self.assertQueryCount(161):
            self.env['documents.document'].create([{
                'folder_id': folder.id,
                'type': 'binary',
            } for folder in folders])

    def test_default_res_id_model(self):
        """
        Test default res_id and res_model from context are used for linking attachment to document.
        """
        document = self.env['documents.document'].create({'folder_id': self.folder_b.id})
        attachment = self.env['ir.attachment'].with_context(
            default_res_id=document.id,
            default_res_model=document._name,
        ).create({
            'name': 'attachmentGif.gif',
            'datas': GIF,
        })
        self.assertEqual(attachment.res_id, document.id, "It should be linked to the default res_id")
        self.assertEqual(attachment.res_model, document._name, "It should be linked to the default res_model")
        self.assertEqual(document.attachment_id, attachment, "Document should be linked to the created attachment")

    @users('documents@example.com')
    def test_versioning(self):
        """
        Tests the versioning/history of documents
        """
        document = self.env["documents.document"].create(
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

        self.assertEqual(len(document.previous_attachment_ids.ids), 0, "The history should be empty")
        original_attachment = document.attachment_id
        check_attachment_res_fields(original_attachment, "res.users", self.doc_user.id)
        document.write({'datas': TEXT})
        new_attachment = document.previous_attachment_ids
        check_attachment_res_fields(original_attachment, "res.users", self.doc_user.id)
        check_attachment_res_fields(new_attachment, "documents.document", document.id)
        self.assertEqual(len(document.previous_attachment_ids), 1)
        self.assertNotEqual(document.previous_attachment_ids, original_attachment)
        self.assertEqual(document.previous_attachment_ids[0].datas, GIF, "The history should have the right content")
        self.assertEqual(document.attachment_id.datas, TEXT, "The document should have the right content")
        old_attachment = document.attachment_id
        document.write({'attachment_id': new_attachment.id})
        check_attachment_res_fields(new_attachment, "res.users", self.doc_user.id)
        check_attachment_res_fields(old_attachment, "documents.document", document.id)
        self.assertEqual(document.attachment_id.id, new_attachment.id, "the document should contain the new attachment")
        self.assertEqual(document.previous_attachment_ids, original_attachment, "the history should contain the original attachment")
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
        document.write({'datas': DATA})
        self.assertEqual(document.attachment_id, new_attachment)

    def test_write_mimetype(self):
        """
        Tests the consistency of documents' mimetypes
        """
        document = self.env['documents.document'].with_user(self.doc_user.id).create({'datas': GIF, 'folder_id': self.folder_b.id})
        document.with_user(self.doc_user.id).write({'datas': TEXT, 'mimetype': 'text/plain'})
        self.assertEqual(document.mimetype, 'text/plain', "the new mimetype should be the one given on write")
        document.with_user(self.doc_user.id).write({'datas': TEXT, 'mimetype': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'})
        self.assertEqual(document.mimetype, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', "should preserve office mime type")

    def test_cascade_delete(self):
        """
        Makes sure that documents are unlinked when their attachment is unlinked.
        """
        document = self.env['documents.document'].create({'datas': GIF, 'folder_id': self.folder_b.id})
        self.assertTrue(document.exists(), 'the document should exist')
        document.attachment_id.unlink()
        self.assertFalse(document.exists(), 'the document should not exist')

    def test_is_favorited(self):
        user = new_test_user(self.env, "test user", groups='documents.group_documents_user')
        document = self.env['documents.document'].create({'datas': GIF, 'folder_id': self.folder_b.id})
        document.favorited_ids = user
        self.assertFalse(document.is_favorited)
        self.assertTrue(document.with_user(user).is_favorited)

    def test_neuter_mimetype(self):
        """
        Tests that potentially harmful mimetypes (XML mimetypes that can lead to XSS attacks) are converted to text

        In fact this logic is implemented in the base `IrAttachment` model but was originally duplicated.
        The test stays duplicated here to ensure the de-duplicated logic still catches our use cases.
        """
        self.folder_b.action_update_access_rights(partners={self.doc_user.partner_id: ('edit', False)})
        document = self.env['documents.document'].create({'datas': GIF, 'folder_id': self.folder_b.id})

        document.with_user(self.doc_user.id).write({'datas': TEXT, 'mimetype': 'text/xml'})
        self.assertEqual(document.mimetype, 'text/plain', "XML mimetype should be forced to text")
        document.with_user(self.doc_user.id).write({'datas': TEXT, 'mimetype': 'image/svg+xml'})
        self.assertEqual(document.mimetype, 'text/plain', "SVG mimetype should be forced to text")
        document.with_user(self.doc_user.id).write({'datas': TEXT, 'mimetype': 'text/html'})
        self.assertEqual(document.mimetype, 'text/plain', "HTML mimetype should be forced to text")
        document.with_user(self.doc_user.id).write({'datas': TEXT, 'mimetype': 'application/xhtml+xml'})
        self.assertEqual(document.mimetype, 'text/plain', "XHTML mimetype should be forced to text")

    def test_create_from_message_invalid_tags(self):
        """
        Create a new document from message with a deleted tag, it should keep only existing tags.
        """
        message = self.env['documents.document'].message_new({
            'subject': 'Test',
        }, {
            'tag_ids': [(6, 0, [self.tag_b.id, -1])],
            'folder_id': self.folder_a.id,
        })
        self.assertEqual(message.tag_ids.ids, [self.tag_b.id], "Should only keep the existing tag")

    def test_file_extension(self):
        """ Test the detection of the file extension and its edition. """
        sanitized_extension = 'txt'
        for extension in ('.txt', ' .txt', '..txt', '.txt ', ' .txt ', '  .txt   '):
            document = self.env['documents.document'].create({
                'datas': base64.b64encode(b"Test"),
                'name': f'name{extension}',
                'mimetype': 'text/plain',
                'folder_id': self.folder_b.id,
            })
            self.assertEqual(document.file_extension, sanitized_extension,
                             f'"{extension}" must be sanitized to "{sanitized_extension}" at creation')
        for extension in ('txt', '  txt', '  txt   ', '.txt', ' .txt', ' .txt  ', '..txt', '  ..txt '):
            document.file_extension = extension
            self.assertEqual(document.file_extension, sanitized_extension,
                             f'"{extension}" must be sanitized to "{sanitized_extension}" at edition')

        # test extension when filename is changed (i.e. name is edited or file is replaced)
        document.name = 'test.png'
        self.assertEqual(document.file_extension, 'png', "extension must be updated on change in filename")

    def test_restricted_folder_multi_company(self):
        """
        Tests the behavior of a restricted folder in a multi-company environment
        """

        company_a = self.env.company
        company_b = self.env['res.company'].create({'name': 'Company B'})

        user_b = self.env['res.users'].create({
            'name': 'User of company B',
            'login': 'user_b',
            'groups_id': [(6, 0, [self.ref('documents.group_documents_manager')])],
            'company_id': company_b.id,
            'company_ids': [(6, 0, [company_b.id])]
        })

        self.folder_a.company_id = company_a
        self.assertEqual(self.folder_a.display_name, 'folder A',
                         "The parent folder's name should not be hidden")
        self.assertEqual(self.folder_a.with_user(user_b).display_name, 'Restricted',
                         "The parent folder's name should be hidden")
        self.assertEqual(self.folder_a_a.display_name, "folder A - A",
                         "The parent folder name should not be included in the name")

    def test_unlink_attachments_with_documents(self):
        """
        Tests a documents.document unlink method.
        Attachments should be deleted when related documents are deleted,
        for which res_model is not 'documents.document' or `False`.

        Test case description:
            Case 1:
            - upload a document with res_model 'res.partner'.
            - check if attachment exists.
            - unlink the document.
            - check if attachment exists or not.

            Case 2:
            - ensure the existing flow for res_model 'documents.document'
              does not break.

            Case 3:
            - ensure the existing flow for res_model `False` does not break.
        """
        documents = self.env['documents.document'].create([{
                'datas': GIF,
                'folder_id': self.folder_b.id,
                'res_model': res_model,
            } for res_model in ('res.partner', 'documents.document', False)
        ])
        documents[2].res_model = False
        for document in documents:
            with self.subTest(res_model=document.res_model):
                self.assertTrue(document.attachment_id.exists())
                attachment = document.attachment_id
                document.unlink()
                self.assertFalse(attachment.exists())

    def test_archive_and_unarchive_document(self):
        self.document_txt.action_archive()
        self.assertFalse(self.document_txt.active, 'the document should be inactive')
        self.document_txt.action_unarchive()
        self.assertTrue(self.document_txt.active, 'the document should be active')

    def test_unarchive_document_with_archived_parent(self):
        """Unarchive a document whose parent folder is archived should send an error."""
        document = self.document_txt

        def check_error_message(document):
            with self.assertRaises(UserError) as err:
                document.action_unarchive()
            self.assertEqual(
                err.exception.args[0],
                "Item(s) you wish to restore are included in archived folders. "
                "To restore these items, you must restore the following including folders instead:"
                "\n"
                "- folder B"
            )

        self.folder_b.folder_id = self.folder_a  # when the parent has folder_id
        self.folder_b.action_archive()
        check_error_message(document)

        self.folder_b.folder_id = False  # when the parent has folder_id False
        check_error_message(document)

    def test_delete_document(self):
        self.document_txt.action_archive()
        self.assertFalse(self.document_txt.active, 'the document should be inactive')
        self.document_txt.unlink()
        self.assertFalse(self.document_txt.exists(), 'the document should not exist')

    def test_copy_document(self):
        with patch.object(
            self.registry['documents.document'],
            '_compute_is_multipage',
            autospec=True,
            side_effect=self.failureException(
                "The compute stored field `is_multipage` must not be triggered "
                "after a copy upon flushing, its value should be just copied."
            ),
        ):
            copy = self.document_txt.copy()
            self.assertEqual(copy.name, "file.txt (copy)")
            self.assertNotEqual(
                copy.attachment_id.ensure_one().id,
                self.document_txt.attachment_id.id,
                "There must be a new attachment"
            )
            self.assertEqual(copy.raw, self.document_txt.raw)

            self.env.flush_all()  # trigger recomputes

            self.assertEqual(copy.is_multipage, self.document_txt.is_multipage)

        copy_with_default = self.document_txt.copy({"name": "test"})
        self.assertEqual(copy_with_default.name, "test")
        self.assertNotEqual(
            copy.attachment_id.ensure_one().id,
            self.document_txt.attachment_id.id,
            "There must be a new attachment"
        )
        self.assertEqual(copy.raw, self.document_txt.raw)

        # check that we can copy in a folder inside the company folder
        self.assertFalse(self.folder_a.folder_id)
        self.folder_a.owner_id = self.env.ref("base.user_root")
        self.folder_a.access_internal = 'edit'

        # Special case where we can not write, but `user_permission == edit` because
        # the folder is in the company root
        with self.assertRaises(AccessError):
            self.folder_a.with_user(self.internal_user).check_access('write')
        self.assertEqual(self.folder_a.with_user(self.internal_user).user_permission, 'edit')

        self.document_txt.folder_id = self.folder_a
        self.document_txt.with_user(self.internal_user).copy()

        # copy in batch documents of different folder
        self.assertNotEqual(self.document_txt.folder_id, self.document_gif.folder_id)
        copied_documents = (self.document_txt | self.document_gif).with_user(self.internal_user).copy()
        self.assertEqual(copied_documents[0].name, f'{self.document_txt.name} (copy)')
        self.assertEqual(copied_documents[1].name, f'{self.document_gif.name} (copy)')

        # Check that copied documents res_model and res_id are pointing to themselves
        document_txt_copy = self.document_txt.with_user(self.internal_user).copy()
        copied_documents = (self.document_txt | document_txt_copy).with_user(self.internal_user).copy()
        self.document_txt.unlink()
        for copied_document in copied_documents:
            self.assertEqual(copied_document.res_id, copied_document.id)
            self.assertEqual(copied_document.res_model, "documents.document")
            self.assertTrue(copied_document.exists())

        self.document_gif.write({
            "res_model": "res.partner",
            "res_id": self.env.user.partner_id.id,
        })
        copied_document = self.document_gif.copy()
        self.assertEqual(copied_document.res_id, copied_document.id)
        self.assertEqual(copied_document.res_model, "documents.document")

    def test_embedding_actions(self):
        """Check that embedded actions name is translated."""
        self.env['res.lang']._activate_lang('fr_FR')
        doc = self.env['documents.document'].create({'name': 'A request', 'folder_id': self.folder_a.id})
        self.assertFalse(doc.available_embedded_actions_ids)
        server_action = self.env.ref('documents.ir_actions_server_tag_add_validated')
        server_action.with_context(lang='fr_FR').name = "Blablabla"
        self.env['documents.document'].action_folder_embed_action(self.folder_a.id, server_action.id)
        doc.invalidate_recordset(['available_embedded_actions_ids'])
        embedded_action = doc.available_embedded_actions_ids
        self.assertEqual(embedded_action.name, server_action.name)
        self.assertEqual(embedded_action.with_context(lang='fr_FR').name, "Blablabla")

    def test_embedding_actions_permission(self):
        """Test that embedding actions enforces permissions but allows sudo bypass."""
        user_no_rights = new_test_user(self.env, login='user_no_doc_rights', groups='base.group_user')

        folder = self.env['documents.document'].create({
            'name': 'Test Folder',
            'type': 'folder'
        })
        action = self.env['ir.actions.server'].create({
            'name': 'Test Server Action',
            'model_id': self.env['ir.model']._get('documents.document').id,
            'state': 'code',
        })

        self.env['documents.document'].with_user(user_no_rights).sudo().action_folder_embed_action(folder.id, action.id)
        embedded = self.env['ir.embedded.actions'].search([
            ('action_id', '=', action.id),
            ('parent_res_id', '=', folder.id),
            ('parent_res_model', '=', 'documents.document'),
        ])
        self.assertTrue(embedded, "The action should have been embedded in sudo mode")

        with self.assertRaises(AccessError):
            self.env['documents.document'].with_user(user_no_rights).action_folder_embed_action(folder.id, action.id)
        self.assertTrue(embedded, "The action should not have been unembedded without rights or sudo")

    def test_embedding_actions_unembed_child_not_visible_anymore(self):
        """Embedded child actions should disappear from the folder list once unembedded."""
        doc = self.env['documents.document'].create({
            'name': 'A request',
            'folder_id': self.folder_a.id,
        })
        Documents = self.env['documents.document']

        parent_base = self.env.ref('documents.ir_actions_server_tag_add_validated')
        child_base = parent_base.copy()

        Documents.action_folder_embed_action(self.folder_a.id, parent_base.id)
        Documents.action_folder_embed_action(self.folder_a.id, child_base.id)

        doc.invalidate_recordset(['available_embedded_actions_ids'])

        parent_base.write({
            'child_ids': [Command.link(child_base.id)],
        })

        def _visible_action_ids():
            actions = Documents.get_documents_actions(folder_id=self.folder_a.id)
            return {a['id'] for a in actions}

        actions_before = _visible_action_ids()
        self.assertIn(parent_base.id, actions_before)
        self.assertIn(child_base.id, actions_before)

        Documents.action_folder_embed_action(self.folder_a.id, child_base.id)

        actions_after = _visible_action_ids()
        self.assertIn(parent_base.id, actions_after)
        self.assertNotIn(child_base.id, actions_after)

    def test_document_thumbnail_status(self):
        for mimetype in ['application/pdf', 'application/pdf;base64']:
            with self.subTest(mimetype=mimetype):
                pdf_document = self.env['documents.document'].create({
                    'name': 'Test PDF doc',
                    'mimetype': mimetype,
                    'datas': "JVBERi0gRmFrZSBQREYgY29udGVudA==",
                    'folder_id': self.folder_b.id,
                })
                self.assertEqual(pdf_document.thumbnail, False)
                self.assertEqual(pdf_document.thumbnail_status, 'client_generated')

            word_document = self.env['documents.document'].create({
                'name': 'Test DOC',
                'mimetype': 'application/msword',
                'folder_id': self.folder_b.id,
            })
            self.assertEqual(word_document.thumbnail, False)
            self.assertEqual(word_document.thumbnail_status, False)
        for mimetype in ['image/bmp', 'image/gif', 'image/jpeg', 'image/png', 'image/svg+xml', 'image/tiff', 'image/x-icon', 'image/webp']:
            with self.subTest(mimetype=mimetype):
                image_document = self.env['documents.document'].create({
                    'name': 'Test image doc',
                    'mimetype': mimetype,
                    'datas': GIF,
                    'folder_id': self.folder_b.id,
                })
                self.assertEqual(image_document.thumbnail, GIF)
                self.assertEqual(image_document.thumbnail_status, 'present')

    def test_document_max_upload_limit(self):
        Doc = self.env['documents.document']
        ICP = self.env['ir.config_parameter']
        key_doc = 'document.max_fileupload_size'
        key_web = 'web.max_file_upload_size'

        ICP.set_param(key_doc, 20)
        ICP.set_param(key_web, 10)
        self.assertEqual(Doc.get_document_max_upload_limit(), 20)

        ICP.set_param(key_doc, 0)
        self.assertEqual(Doc.get_document_max_upload_limit(), None)

        ICP.search([('key', '=', key_doc)]).unlink()
        self.assertEqual(Doc.get_document_max_upload_limit(), 10)

        ICP.search([('key', '=', key_web)]).unlink()
        self.assertEqual(
            Doc.get_document_max_upload_limit(),
            http.DEFAULT_MAX_CONTENT_LENGTH
        )

    def test_document_order_by_is_folder(self):
        # check that the order is "folder first", and then most recent first
        doc_1 = self.env['documents.document'].create([{'name': 'D1'}])
        doc_2 = self.env['documents.document'].create([{'name': 'D2', 'type': 'folder'}])
        doc_3 = self.env['documents.document'].create([{'name': 'D3', 'type': 'url'}])
        doc_4 = self.env['documents.document'].create([{'name': 'D4'}])
        docs = doc_1 | doc_2 | doc_3 | doc_4
        result = self.env['documents.document'].search([('id', 'in', docs.ids)], order='is_folder, create_date DESC, id DESC')

        self.assertEqual(result[0], doc_2)
        self.assertEqual(result[1], doc_4)
        self.assertEqual(result[2], doc_3)
        self.assertEqual(result[3], doc_1)

    def test_document_order_by_last_access_date(self):
        documents = self.env['documents.document'].create([{'name': 'D1'}, {'name': 'D2'}])
        self.env['documents.access'].create([{
            'document_id': documents[0].id,
            'last_access_date': datetime.now() + timedelta(days=1),
            'partner_id': self.env.user.partner_id.id,
        }, {
            'document_id': documents[1].id,
            'last_access_date': datetime.now() + timedelta(days=2),
            'partner_id': self.env.user.partner_id.id,
        }])

        result = self.env['documents.document'].search([('id', 'in', documents.ids)], order='last_access_date_group DESC')
        self.assertEqual(result[0], documents[1])
        self.assertEqual(result[1], documents[0])

        result = self.env['documents.document'].search([('id', 'in', documents.ids)], order='last_access_date_group ASC')
        self.assertEqual(result[0], documents[0])
        self.assertEqual(result[1], documents[1])

    def test_document_group_by_last_access_date(self):
        Doc = self.env['documents.document']
        documents = Doc.create([{'name': f'D{i}'} for i in range(6)])
        self.env['documents.access'].create([{
            'document_id': documents[0].id,
            'last_access_date': datetime.now() - timedelta(hours=1),
            'partner_id': self.env.user.partner_id.id,
        }, {
            'document_id': documents[1].id,
            'last_access_date': datetime.now() - timedelta(days=2),
            'partner_id': self.env.user.partner_id.id,
        }, {
            'document_id': documents[2].id,
            'last_access_date': datetime.now() - timedelta(days=8),
            'partner_id': self.env.user.partner_id.id,
        }, {
            'document_id': documents[3].id,
            'last_access_date': datetime.now() - timedelta(days=40),
            'partner_id': self.env.user.partner_id.id,
        }, {
            'document_id': documents[4].id,
            'last_access_date': datetime.now() - timedelta(minutes=1),
            'partner_id': self.env.user.partner_id.id,
        }, {
            'document_id': documents[5].id,
            'last_access_date': datetime.now() - timedelta(days=1, hours=5),
            'partner_id': self.env.user.partner_id.id,
        }])

        result = Doc. web_read_group(
            [('id', 'in', documents.ids)],
            ['id', 'name'],
            groupby=['last_access_date_group'],
            orderby='last_access_date_group DESC')['groups']

        self.assertEqual(len(result), 4)

        self.assertEqual(result[0]['last_access_date_group'], '3_day')
        self.assertEqual(result[0]['last_access_date_group_count'], 2)
        result_day = Doc.search(result[0]['__domain'])
        self.assertEqual(result_day[0], documents[4])
        self.assertEqual(result_day[1], documents[0])
        self.assertEqual(result_day.mapped('last_access_date_group'), ['3_day'] * 2)

        self.assertEqual(result[1]['last_access_date_group'], '2_week')
        self.assertEqual(result[1]['last_access_date_group_count'], 2)
        result_week = Doc.search(result[1]['__domain'])
        self.assertEqual(result_week[0], documents[5])
        self.assertEqual(result_week[1], documents[1])
        self.assertEqual(result_week.mapped('last_access_date_group'), ['2_week'] * 2)

        self.assertEqual(result[2]['last_access_date_group'], '1_month')
        self.assertEqual(result[2]['last_access_date_group_count'], 1)
        self.assertEqual(Doc.search(result[2]['__domain']), documents[2])
        self.assertEqual(documents[2].last_access_date_group, '1_month')

        self.assertEqual(result[3]['last_access_date_group'], '0_older')
        self.assertEqual(result[3]['last_access_date_group_count'], 1)
        self.assertEqual(Doc.search(result[3]['__domain']), documents[3])
        self.assertEqual(documents[3].last_access_date_group, '0_older')

    def test_link_constrains(self):
        folder = self.env['documents.document'].create({'name': 'folder', 'type': 'folder'})
        for url in ("wrong URL format", "https:/ example.com", "test https://example.com"):
            with self.assertRaises(ValidationError):
                self.env['documents.document'].create({
                    'name': 'Test Document',
                    'folder_id': folder.id,
                    'url': url,
                })

    def test_document_shortcut_to_my_drive(self):
        shortcut_1 = self.document_txt.action_create_shortcut(location_folder_id=self.folder_b.id)
        shortcut_2 = shortcut_1.action_create_shortcut(location_folder_id=False)
        self.assertEqual(shortcut_2.folder_id.id, False)

    def test_document_upload_from_chatter(self):
        folder = self.env['documents.document'].create([
            {'type': 'folder', 'name': 'folder', 'access_internal': 'view'}
        ])
        attachment = self.env['ir.attachment'].create({
            'datas': GIF,
            'name': 'TestAttachment.gif',
            'res_model': 'documents.document',
            'res_id':folder.id
        })
        self.assertNotEqual(attachment.name, folder.name,'the folder name should not change')

    def test_thumbnail_fix(self):
        """Test the thumbnail fix that force the status to "present" for image when it is False."""
        read = (self.document_gif | self.document_txt).web_read({'thumbnail_status': {}, 'mimetype': {}})
        self.assertEqual(self.document_gif.thumbnail_status, 'present')
        self.assertEqual(self.document_txt.thumbnail_status, False)
        self.assertEqual(read, [
            {'id': self.document_gif.id, 'thumbnail_status': 'present', 'mimetype': 'image/gif'},
            {'id': self.document_txt.id, 'thumbnail_status': False, 'mimetype': 'text/plain'},
        ])
        self.document_gif.thumbnail_status = False
        read = (self.document_gif | self.document_txt).web_read({'thumbnail_status': {}, 'mimetype': {}})
        self.assertEqual(read, [
            {'id': self.document_gif.id, 'thumbnail_status': 'present', 'mimetype': 'image/gif'},
            {'id': self.document_txt.id, 'thumbnail_status': False, 'mimetype': 'text/plain'},
        ])
        read = (self.document_gif | self.document_txt).web_read({'thumbnail_status': {}, 'name': {}})
        self.assertEqual(read, [
            {'id': self.document_gif.id, 'thumbnail_status': False, 'name': self.document_gif.name},
            {'id': self.document_txt.id, 'thumbnail_status': False, 'name': self.document_txt.name},
        ])
        self.document_gif.thumbnail_status = 'error'
        self.document_txt.thumbnail_status = 'client_generated'
        read = (self.document_gif | self.document_txt).web_read({'thumbnail_status': {}, 'name': {}})
        self.assertEqual(read, [
            {'id': self.document_gif.id, 'thumbnail_status': 'error', 'name': self.document_gif.name},
            {'id': self.document_txt.id, 'thumbnail_status': 'client_generated', 'name': self.document_txt.name},
        ])

    def test_res_name_recompute_with_deleted_record(self):
        partner = self.env['res.partner'].create({'name': 'Test Partner'})
        doc = self.env['documents.document'].create({
            'name': 'Test',
            'res_id': partner.id,
            'res_model': 'res.partner',
        })
        self.assertEqual(doc.res_name, "Test Partner")
        partner.unlink()
        self.assertFalse(doc.res_name)
