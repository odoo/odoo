# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests.common import TransactionCase, new_test_user
from odoo.exceptions import AccessError
from odoo.tests import users
import base64

GIF = b"R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs="
TEXT = base64.b64encode(bytes("TEST", 'utf-8'))
DATA = "data:application/zip;base64,R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs="
file_a = {'name': 'doc.zip', 'data': 'data:application/zip;base64,R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs='}
file_b = {'name': 'icon.zip', 'data': 'data:application/zip;base64,R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs='}


class TestCaseDocuments(TransactionCase):
    @classmethod
    def setUpClass(self):
        super().setUpClass()
        self.doc_user = self.env['res.users'].create({
            'email': 'documents@example.com',
            'groups_id': [(4, self.env.ref('documents.group_documents_user').id, 0)],
            'login': 'documents@example.com',
            'name': 'Test user documents',
        })
        self.folder_a = self.env['documents.folder'].create({
            'name': 'folder A',
        })
        self.folder_a_a = self.env['documents.folder'].create({
            'name': 'folder A - A',
            'parent_folder_id': self.folder_a.id,
        })
        self.folder_b = self.env['documents.folder'].create({
            'name': 'folder B',
        })
        self.tag_category_b = self.env['documents.facet'].create({
            'folder_id': self.folder_b.id,
            'name': "categ_b",
        })
        self.tag_b = self.env['documents.tag'].create({
            'facet_id': self.tag_category_b.id,
            'name': "tag_b",
        })
        self.tag_category_a = self.env['documents.facet'].create({
            'folder_id': self.folder_a.id,
            'name': "categ_a",
        })
        self.tag_category_a_a = self.env['documents.facet'].create({
            'folder_id': self.folder_a_a.id,
            'name': "categ_a_a",
        })
        self.tag_a_a = self.env['documents.tag'].create({
            'facet_id': self.tag_category_a_a.id,
            'name': "tag_a_a",
        })
        self.tag_a = self.env['documents.tag'].create({
            'facet_id': self.tag_category_a.id,
            'name': "tag_a",
        })
        self.document_gif = self.env['documents.document'].create({
            'datas': GIF,
            'name': 'file.gif',
            'mimetype': 'image/gif',
            'folder_id': self.folder_b.id,
        })
        self.document_txt = self.env['documents.document'].create({
            'datas': TEXT,
            'name': 'file.txt',
            'mimetype': 'text/plain',
            'folder_id': self.folder_b.id,
        })
        self.share_link_ids = self.env['documents.share'].create({
            'document_ids': [(4, self.document_txt.id, 0)],
            'type': 'ids',
            'name': 'share_link_ids',
            'folder_id': self.folder_a_a.id,
        })
        self.share_link_folder = self.env['documents.share'].create({
            'folder_id': self.folder_a_a.id,
            'name': "share_link_folder",
        })
        self.tag_action_a = self.env['documents.workflow.action'].create({
            'action': 'add',
            'facet_id': self.tag_category_b.id,
            'tag_id': self.tag_b.id,
        })
        self.worflow_rule = self.env['documents.workflow.rule'].create({
            'domain_folder_id': self.folder_a_a.id,
            'name': 'workflow rule on f_a_a',
            'folder_id': self.folder_b.id,
            'tag_action_ids': [(4, self.tag_action_a.id, 0)],
            'remove_activities': True,
            'activity_option': True,
            'activity_type_id': self.env.ref('documents.mail_documents_activity_data_Inbox').id,
            'activity_summary': 'test workflow rule activity summary',
            'activity_date_deadline_range': 7,
            'activity_date_deadline_range_type': 'days',
            'activity_note': 'activity test note',
        })

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
                         'the name should be taken from the ir attachment')
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

    def test_documents_rules(self):
        """
        Tests a documents.workflow.rule
        """
        self.worflow_rule.apply_actions([self.document_gif.id, self.document_txt.id])
        self.assertTrue(self.tag_b.id in self.document_gif.tag_ids.ids, "failed at workflow rule add tag id")
        self.assertTrue(self.tag_b.id in self.document_txt.tag_ids.ids, "failed at workflow rule add tag id txt")
        self.assertEqual(len(self.document_gif.tag_ids.ids), 1, "failed at workflow rule add tag len")

        activity_gif = self.env['mail.activity'].search(['&',
                                                         ('res_id', '=', self.document_gif.id),
                                                         ('res_model', '=', 'documents.document')])

        self.assertEqual(len(activity_gif), 1, "failed at workflow rule activity len")
        self.assertTrue(activity_gif.exists(), "failed at workflow rule activity exists")
        self.assertEqual(activity_gif.summary, 'test workflow rule activity summary',
                         "failed at activity data summary from workflow create activity")
        self.assertEqual(activity_gif.note, '<p>activity test note</p>',
                         "failed at activity data note from workflow create activity")
        self.assertEqual(activity_gif.activity_type_id.id,
                         self.env.ref('documents.mail_documents_activity_data_Inbox').id,
                         "failed at activity data note from workflow create activity")

        self.assertEqual(self.document_gif.folder_id.id, self.folder_b.id, "failed at workflow rule set folder gif")
        self.assertEqual(self.document_txt.folder_id.id, self.folder_b.id, "failed at workflow rule set folder txt")

    def test_documents_rules_link_to_record(self):
        """
        Tests a documents.workflow.rule that links a document to a record.
        """
        workflow_rule_link = self.env['documents.workflow.rule'].create({
            'domain_folder_id': self.folder_a.id,
            'name': 'workflow rule on link to record',
            'condition_type': 'criteria',
            'create_model': 'link.to.record',
        })
        user_admin_doc = new_test_user(self.env, login='Test admin documents', groups='documents.group_documents_manager,base.group_partner_manager')

        # prepare documents that the user owns
        Document = self.env['documents.document'].with_user(user_admin_doc)
        document_gif = Document.create({
            'datas': GIF,
            'name': 'file.gif',
            'mimetype': 'image/gif',
            'folder_id': self.folder_b.id,
        })
        document_txt = Document.create({
            'datas': TEXT,
            'name': 'file.txt',
            'mimetype': 'text/plain',
            'folder_id': self.folder_b.id,
        })
        documents_to_link = [document_gif, document_txt]

        res_model = 'res.partner'
        record = {
            'res_model': res_model,
            'res_model_id': self.env['ir.model'].name_search(res_model, operator='=', limit=1)[0],
            'res_id': self.env[res_model].search([], limit=1).id,
        }
        link_to_record_ctx = workflow_rule_link.apply_actions([doc.id for doc in documents_to_link])['context']
        link_to_record_wizard = self.env['documents.link_to_record_wizard'].with_user(user_admin_doc)\
                                                                           .with_context(link_to_record_ctx).create({})
        # Link record to document_gif and document_txt
        link_to_record_wizard.model_id = record['res_model_id']
        link_to_record_wizard.resource_ref = '%s,%s' % (record['res_model'], record['res_id'])
        link_to_record_wizard.link_to()

        for doc in documents_to_link:
            self.assertEqual(doc.res_model, record['res_model'], "bad model linked to the document")
            self.assertEqual(doc.res_id, record['res_id'], "bad record linked to the document")

        # Removes the link between document_gif and record
        workflow_rule_link.unlink_record([self.document_gif.id])
        self.assertNotEqual(self.document_gif.res_model, record['res_model'],
                            "the link between document_gif and its record was not correctly removed")
        self.assertNotEqual(self.document_gif.res_id, record['res_id'],
                            "the link between document_gif and its record was not correctly removed")

    def test_documents_rule_display(self):
        """
        tests criteria of rules
        """

        self.workflow_rule_criteria = self.env['documents.workflow.rule'].create({
            'domain_folder_id': self.folder_a.id,
            'name': 'workflow rule on f_a & criteria',
            'condition_type': 'criteria',
            'required_tag_ids': [(6, 0, [self.tag_b.id])],
            'excluded_tag_ids': [(6, 0, [self.tag_a_a.id])]
        })

        self.assertFalse(self.workflow_rule_criteria.limited_to_single_record,
                         "this rule should not be limited to a single record")

        self.document_txt_criteria_a = self.env['documents.document'].create({
            'name': 'Test criteria a',
            'mimetype': 'text/plain',
            'folder_id': self.folder_a.id,
            'tag_ids': [(6, 0, [self.tag_a_a.id, self.tag_b.id])]
        })

        self.assertTrue(self.workflow_rule_criteria.id not in self.document_txt_criteria_a.available_rule_ids.ids,
                        "failed at documents_workflow_rule unavailable rule")

        self.document_txt_criteria_b = self.env['documents.document'].create({
            'name': 'Test criteria b',
            'mimetype': 'text/plain',
            'folder_id': self.folder_a.id,
            'tag_ids': [(6, 0, [self.tag_a.id])]
        })

        self.assertTrue(self.workflow_rule_criteria.id not in self.document_txt_criteria_b.available_rule_ids.ids,
                        "failed at documents_workflow_rule unavailable rule")
        self.document_txt_criteria_c = self.env['documents.document'].create({
            'datas': TEXT,
            'name': 'file.txt',
            'mimetype': 'text/plain',
            'folder_id': self.folder_a.id,
            'tag_ids': [(6, 0, [self.tag_b.id])]
        })

        self.assertTrue(self.workflow_rule_criteria.id in self.document_txt_criteria_c.available_rule_ids.ids,
                        "failed at documents_workflow_rule available rule")

        self.document_txt_criteria_d = self.env['documents.document'].create({
            'name': 'Test criteria d',
            'mimetype': 'text/plain',
            'folder_id': self.folder_b.id,
            'tag_ids': [(6, 0, [self.tag_b.id])]
        })

        self.assertTrue(self.workflow_rule_criteria.id not in self.document_txt_criteria_d.available_rule_ids.ids,
                        "failed at documents_workflow_rule unavailable rule")

    def test_documents_share_links(self):
        """
        Tests document share links
        """

        # by Folder
        vals = {
            'folder_id': self.folder_b.id,
            'domain': [],
            'tag_ids': [(6, 0, [])],
            'type': 'domain',
        }
        self.documents_share_links_a = self.env['documents.share'].create(vals)
        self.assertEqual(self.documents_share_links_a.type, 'domain', "failed at share link type domain")

        # by Folder with upload and activites
        vals = {
            'folder_id': self.folder_b.id,
            'domain': [],
            'tag_ids': [(6, 0, [])],
            'type': 'domain',
            'date_deadline': '3052-01-01',
            'action': 'downloadupload',
            'activity_option': True,
            'activity_type_id': self.ref('documents.mail_documents_activity_data_tv'),
            'activity_summary': 'test by Folder with upload and activites',
            'activity_date_deadline_range': 4,
            'activity_date_deadline_range_type': 'days',
            'activity_user_id': self.env.user.id,
        }
        self.share_folder_with_upload = self.env['documents.share'].create(vals)
        self.assertTrue(self.share_folder_with_upload.exists(), 'failed at upload folder creation')
        self.assertEqual(self.share_folder_with_upload.activity_type_id.name, 'To validate',
                         'failed at activity type for upload documents')
        self.assertEqual(self.share_folder_with_upload.state, 'live', "failed at share_link live")

        # by documents
        vals = {
            'document_ids': [(6, 0, [self.document_gif.id, self.document_txt.id])],
            'folder_id': self.folder_b.id,
            'date_deadline': '2001-11-05',
            'type': 'ids',
        }
        self.result_share_documents_act = self.env['documents.share'].create(vals)

        # Expiration date
        self.assertEqual(self.result_share_documents_act.state, 'expired', "failed at share_link expired")

    def test_documents_share_popup(self):
        share_folder = self.env['documents.folder'].create({
            'name': 'share folder',
            'document_ids': [
                Command.create({'datas': GIF, 'name': 'file.gif', 'mimetype': 'image/gif'}),
                Command.create({'type': 'url', 'url': 'https://odoo.com'}),
            ],
        })
        share_tag_category = self.env['documents.facet'].create({
            'folder_id': share_folder.id,
            'name': "share category",
        })
        share_tag = self.env['documents.tag'].create({
            'facet_id': share_tag_category.id,
            'name': "share tag",
        })
        share_folder.document_ids[0].tag_ids = [Command.set(share_tag.ids)]
        domain = [('folder_id', 'in', share_folder.id)]
        action = self.env['documents.share'].open_share_popup({
            'domain': domain,
            'folder_id': share_folder.id,
            'tag_ids': [[6, 0, [share_tag.id]]],
            'type': 'domain',
        })
        share = self.env['documents.share'].browse(action['res_id'])
        self.assertEqual(share.links_count, 0, "There should be no links counted in this share")
        action_context = action['context']
        self.assertTrue(action_context)
        self.assertEqual(action_context['default_owner_id'], self.env.user.partner_id.id, "the action should open a view with the current user as default owner")
        self.assertEqual(action_context['default_folder_id'], share_folder.id, "the action should open a view with the right default folder")
        self.assertEqual(action_context['default_tag_ids'], [[6, 0, [share_tag.id]]], "the action should open a view with the right default tags")
        self.assertEqual(action_context['default_type'], 'domain', "the action should open a view with the right default type")
        self.assertEqual(action_context['default_domain'], domain, "the action should open a view with the right default domain")

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
        document.write({'datas': DATA})
        self.assertEqual(document.attachment_id, new_attachment)

    def test_write_mimetype(self):
        """
        Tests the consistency of documents' mimetypes
        """
        document = self.env['documents.document'].create({'datas': GIF, 'folder_id': self.folder_b.id})
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
        document = self.env['documents.document'].create({'datas': GIF, 'folder_id': self.folder_b.id})

        document.with_user(self.doc_user.id).write({'datas': TEXT, 'mimetype': 'text/xml'})
        self.assertEqual(document.mimetype, 'text/plain', "XML mimetype should be forced to text")
        document.with_user(self.doc_user.id).write({'datas': TEXT, 'mimetype': 'image/svg+xml'})
        self.assertEqual(document.mimetype, 'text/plain', "SVG mimetype should be forced to text")
        document.with_user(self.doc_user.id).write({'datas': TEXT, 'mimetype': 'text/html'})
        self.assertEqual(document.mimetype, 'text/plain', "HTML mimetype should be forced to text")
        document.with_user(self.doc_user.id).write({'datas': TEXT, 'mimetype': 'application/xhtml+xml'})
        self.assertEqual(document.mimetype, 'text/plain', "XHTML mimetype should be forced to text")

    def test_create_from_message(self):
        """
        When we create the document from a message, we need to apply the defaults set on the share.
        """
        attachment = self.env['ir.attachment'].create({
            'datas': GIF,
            'name': 'attachmentGif.gif',
            'res_model': 'documents.document',
            'res_id': 0,
        })
        partner = self.env['res.partner'].create({
            'name': 'Luke Skywalker'
        })
        share = self.env['documents.share'].create({
            'owner_id': self.doc_user.partner_id.id,
            'partner_id': partner.id,
            'tag_ids': [(6, 0, [self.tag_b.id])],
            'folder_id': self.folder_a.id,
        })
        message = self.env['documents.document'].message_new({
            'subject': 'test message'
        }, {
            # this create_share_id value, is normally passed from the alias default created by the share
            'create_share_id': share.id,
            'folder_id': self.folder_a.id,
        })
        message._message_post_after_hook({ }, {
            'attachment_ids': [(4, attachment.id)]
        })
        self.assertEqual(message.active, False, 'Document created for the message should be inactive')
        self.assertNotEqual(attachment.res_id, 0, 'Should link document to attachment')
        attachment_document = self.env['documents.document'].browse(attachment.res_id)
        self.assertNotEqual(attachment_document, None, 'Should have created document')
        self.assertEqual(attachment_document.owner_id.id, self.doc_user.id, 'Should assign owner from share')
        self.assertEqual(attachment_document.partner_id.id, partner.id, 'Should assign partner from share')
        self.assertEqual(attachment_document.tag_ids.ids, [self.tag_b.id], 'Should assign tags from share')

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

        self.assertEqual(self.folder_a.display_name,
            'folder A', "The folder should not be restricted")
        self.assertEqual(self.folder_a.with_user(user_b).sudo().display_name,
            'Restricted Folder', "The folder should be restricted")
        self.assertEqual(
            self.folder_a_a.display_name,
            "folder A / folder A - A",
            "The parent folder name should not be restricted",
        )
        self.assertEqual(
            self.folder_a_a.with_user(user_b).sudo().display_name,
            "Restricted Folder / folder A - A",
            "The parent folder name should be restricted",
        )

    def test_unlink_attachments_with_documents(self):
        """
        Tests a documents.document unlink method.
        Attachments should be deleted when related documents are deleted,
        for which res_model is not 'documents.document'.

        Test case description:
            Case 1:
            - upload a document with res_model 'res.partner'.
            - check if attachment exists.
            - unlink the document.
            - check if attachment exists or not.

            Case 2:
            - ensure the existing flow for res_model 'documents.document'
              does not break.
        """
        document = self.env['documents.document'].create({
            'datas': GIF,
            'folder_id': self.folder_b.id,
            'res_model': 'res.partner',
        })
        self.assertTrue(document.attachment_id.exists(), 'the attachment should exist')
        attachment = document.attachment_id
        document.unlink()
        self.assertFalse(attachment.exists(), 'the attachment should not exist')

        self.assertTrue(self.document_txt.attachment_id.exists(), 'the attachment should exist')
        attachment_a = self.document_txt.attachment_id
        self.document_txt.unlink()
        self.assertFalse(attachment_a.exists(), 'the attachment should not exist')

    def test_archive_and_unarchive_document(self):
        self.document_txt.action_archive()
        self.assertFalse(self.document_txt.active, 'the document should be inactive')
        self.document_txt.action_unarchive()
        self.assertTrue(self.document_txt.active, 'the document should be active')

    def test_delete_document(self):
        self.document_txt.action_archive()
        self.assertFalse(self.document_txt.active, 'the document should be inactive')
        self.document_txt.unlink()
        self.assertFalse(self.document_txt.exists(), 'the document should not exist')

    def test_link_document(self):
        """
            Test whether a user can link a document to a record
            even if he does not have read access to the `ir.model`.
        """
        partner = self.env['res.partner'].create({'name': 'Partner Test'})
        attachment_txt_test = self.env['ir.attachment'].with_user(self.env.user).create({
            'datas': TEXT,
            'name': 'fileText_test.txt',
            'mimetype': 'text/plain',
            'res_model': 'res.partner',
            'res_id': partner.id,
        })
        document = self.env['documents.document'].search([('attachment_id', '=', attachment_txt_test.id)])

        res_partner_model = self.env['ir.model'].search([('model', '=', 'res.partner')], limit=1)

        workflow = self.env['documents.workflow.rule'].create({
            'name': 'test',
            'domain_folder_id': self.folder_a.id,
            'link_model': res_partner_model.id,
        })

        admin = new_test_user(self.env, login='Admin', groups='documents.group_documents_manager,base.group_partner_manager,base.group_system')
        manager = new_test_user(self.env, login='Manager', groups='documents.group_documents_manager,base.group_partner_manager')

        document.available_rule_ids.unlink_record(document.id)
        self.env['ir.model'].with_user(admin).check_access_rights('read')
        workflow.with_user(admin).link_to_record(document)

        document.available_rule_ids.unlink_record(document.id)
        with self.assertRaises(AccessError):
            self.env['ir.model'].with_user(manager).check_access_rights('read')
        workflow.with_user(manager).link_to_record(document)
