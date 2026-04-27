# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
from freezegun import freeze_time
import ast

from odoo import Command, fields, tools
from odoo.addons.mail.tests.common import MailCommon
from odoo.addons.test_mail.data.test_mail_data import MAIL_EML_ATTACHMENT, MAIL_NO_BODY
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import new_test_user
from odoo.tests.common import RecordCapturer
from odoo.tools import mute_logger


class TestMailGateway(MailCommon):
    """Test document creation/update on incoming mail.

    Mainly that the partner_id is correctly set on the created document.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tag = cls.env['documents.tag'].create({'name': 'Tag alias'})
        cls.folder = cls.env['documents.document'].create({
            'name': 'folder',
            'type': 'folder',
            'alias_tag_ids': False,
            'alias_name': 'inbox-test',
        })

        cls.folder_2 = cls.env['documents.document'].create({
            'name': 'folder',
            'type': 'folder',
            'alias_tag_ids': False,
            'alias_name': 'inbox-test-2',
            'company_id': cls.company_2.id
        })

        # edit the alias tags after the alias has been created
        cls.folder.alias_tag_ids = cls.tag.ids

        cls.email_with_no_partner = tools.email_normalize('non-existing@test.com')
        cls.pre_existing_partner = cls.env['res.partner'].find_or_create('existing@test.com')
        cls.email_filenames = ['attachment', 'original_msg.eml']
        cls.document = cls.env['documents.document'].with_context(mail_create_nolog=True).create({
            'access_internal': 'edit',
            'datas': b"R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs=",
            'name': 'file.gif',
            'mimetype': 'image/gif',
            'folder_id': cls.env['documents.document'].create({'name': 'folderA', 'type': 'folder'}).id,
        })

        cls.other_tag = cls.env['documents.tag'].create({'name': 'new tag'})
        cls.non_existing_tag_id = cls.env['documents.document'].with_context(active_test=False).search([], order='id DESC', limit=1).id + 1

        cls.test_activity_type = cls.env['mail.activity.type'].create({'name': 'Test Activity Type'})
        cls.test_activity_type2 = cls.env['mail.activity.type'].create({'name': 'Test Activity Type2'})

    def send_test_mail_with_attachment(self, email_from, msg_id=None, references=None):
        with self.mock_mail_gateway():
            self.format_and_process(
                MAIL_EML_ATTACHMENT,
                email_from,
                f'inbox-test@{self.alias_domain}',
                subject='Test document creation on incoming mail',
                target_model='documents.document',
                references=references or '<f3b9f8f8-28fa-2543-cab2-7aa68f679ebb@odoo.com>',
                msg_id=msg_id or '<cb7eaf62-58dc-2017-148c-305d0c78892f@odoo.com>',
            )
        documents = self.env['documents.document'].search([('name', 'in', self.email_filenames)])
        self.assertEqual(len(documents), len(self.email_filenames))
        return documents

    def send_test_mail_with_attachment_on_different_company(self, email_from, msg_id=None, references=None):
        with self.mock_mail_gateway():
            self.format_and_process(
                MAIL_EML_ATTACHMENT,
                email_from,
                f'inbox-test-2@{self.alias_domain_c2_name}',
                subject='Test document creation on incoming mail',
                target_model='documents.document',
                references=references or '<f3b9f8f8-28fa-2543-cab2-7aa68f679ebb@odoo.com>',
                msg_id=msg_id or '<cb7eaf62-58dc-2017-148c-305d0c78892f@odoo.com>',
            )
        documents = self.env['documents.document'].search([('name', 'in', self.email_filenames)])
        self.assertEqual(len(documents), len(self.email_filenames))
        return documents

    def test_initial_values(self):
        self.assertFalse(self.env['res.partner'].search([('email', '=', self.email_with_no_partner)]))
        self.assertFalse(self.env['documents.document'].search([('name', 'in', self.email_filenames)]))

    def test_constrains(self):
        with self.assertRaises(ValidationError):
            self.env['documents.document'].create({
                'name': 'file',
                'type': 'binary',
                'alias_name': 'test',
            })

    def test_reply_with_attachment(self):
        """ Test reply with an attachment to a message posted on a document. """
        message_ask_files = self.document.with_user(self.user_employee).message_post(
            subject='Could you send the missing files ?', subtype_xmlid='mail.mt_comment')
        with self.mock_mail_gateway(), RecordCapturer(self.env['documents.document'], []) as capture:
            self.format_and_process(
                MAIL_EML_ATTACHMENT,
                'ihavethefiles@example.com',
                'non-alias@test.com',
                msg_id='<dc8eaf62-58dc-2017-148c-305d0c78892f@odoo.com>',
                references=message_ask_files.message_id,
                subject='Please find the files in attachment',
                target_model='documents.document',
            )

        self.assertFalse(capture.records, "No new document has been created")
        self.assertEqual(self.env['ir.attachment'].search_count(
            [('res_id', '=', self.document.id), ('res_model', '=', self.document._name)]), 3)
        doc_messages = self.env['mail.message'].search(
            [('res_id', '=', self.document.id), ('model', '=', self.document._name)])
        self.assertEqual(len(doc_messages), 2)
        self.assertListEqual(
            doc_messages.mapped('subject'),
            ['Please find the files in attachment', 'Could you send the missing files ?'])

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_set_contact_non_existing_partner(self):
        documents_count = self.env['documents.document'].with_context(active_test=False).search_count([])
        for document in self.send_test_mail_with_attachment(self.email_with_no_partner):
            self.assertFalse(document.partner_id)
            self.assertEqual(document.owner_id, self.folder.owner_id)
            self.assertEqual(document.attachment_id.res_model, 'documents.document')
            self.assertEqual(document.attachment_id.res_id, document.id)
            self.assertEqual(document.folder_id, self.folder)
            self.assertEqual(document.tag_ids, self.tag)
        self.assertEqual(
            self.env['documents.document'].with_context(active_test=False).search_count([]),
            documents_count + 3,
            "2 attachments in the email, so 2 documents are created, and 1 archived with the default values",
        )

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_set_contact_existing_partner(self):
        documents_count = self.env['documents.document'].with_context(active_test=False).search_count([])

        for document in self.send_test_mail_with_attachment(self.pre_existing_partner.email):
            self.assertFalse(document.partner_id)
            self.assertEqual(document.owner_id, self.folder.owner_id)
            self.assertEqual(document.attachment_id.res_model, 'documents.document')
            self.assertEqual(document.attachment_id.res_id, document.id)
            self.assertEqual(document.folder_id, self.folder)
            self.assertEqual(document.tag_ids, self.tag)
        self.assertEqual(
            self.env['documents.document'].with_context(active_test=False).search_count([]),
            documents_count + 3,
            "2 attachments in the email, so 2 documents are created, and 1 archived with the default values",
        )

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_no_attachment(self):
        """Test the behavior when we send an email without attachment on the mail alias."""
        documents_count = self.env['documents.document'].with_context(active_test=False).search_count([])

        with self.mock_mail_gateway():
            self.format_and_process(
                MAIL_NO_BODY,
                self.pre_existing_partner.email,
                f'inbox-test@{self.alias_domain}',
                email_to=f'inbox-test@{self.alias_domain}',
                subject='Test document creation on incoming mail',
                target_model='documents.document',
            )

        self.assertEqual(
            self.env['documents.document'].with_context(active_test=False).search_count([]),
            documents_count + 1,
            "No attachment, so only the template document, archived should be created",
        )

    @freeze_time('2022-07-24 08:00:00')
    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_create_activity(self):
        """Test that an activity is created on the document if enabled on the folder. """
        self.folder.write({
            'create_activity_option': True,
            'create_activity_type_id': self.test_activity_type.id,
            'create_activity_summary': 'TODO summary',
            'create_activity_note': 'TODO note',
            'create_activity_user_id': self.user_admin.id,
            'create_activity_date_deadline_range_type': 'days',
            'create_activity_date_deadline_range': 5,
        })
        for document in self.send_test_mail_with_attachment(self.pre_existing_partner.email):
            activity_ids = self.env['mail.activity'].search(
                [('res_model', '=', 'documents.document'), ('res_id', '=', document.id)])
            self.assertEqual(len(activity_ids), 1)
            self.assertEqual(activity_ids.activity_type_id, self.test_activity_type)
            self.assertEqual(activity_ids.summary, 'TODO summary')
            self.assertEqual(activity_ids.note, '<p>TODO note</p>')
            self.assertEqual(activity_ids.user_id, self.user_admin)
            self.assertEqual(activity_ids.date_deadline, fields.Date.today() + relativedelta(days=5))

    @freeze_time('2022-07-24 08:00:00')
    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_create_activity_with_alias_defaults(self):
        """ Test that alias_defaults activity creation settings has precedence over the folder's ones. """
        defaults = ast.literal_eval(self.folder.alias_id.alias_defaults)
        defaults.update({
            'create_activity_option': True,
            'create_activity_type_id': self.test_activity_type2.id,
            'create_activity_summary': 'TODO summary defaults',
            'create_activity_note': 'TODO note defaults',
            'create_activity_user_id': self.user_employee.id,
            'create_activity_date_deadline_range_type': 'months',
            'create_activity_date_deadline_range': 1,
        })
        self.folder.alias_defaults = repr(defaults)
        self.folder.write({
            'create_activity_option': True,
            'create_activity_type_id': self.test_activity_type.id,
            'create_activity_summary': 'TODO summary',
            'create_activity_note': 'TODO note',
            'create_activity_user_id': self.user_admin.id,
            'create_activity_date_deadline_range_type': 'days',
            'create_activity_date_deadline_range': 5,
        })

        for document in self.send_test_mail_with_attachment(self.pre_existing_partner.email):
            activity_ids = self.env['mail.activity'].search(
                [('res_model', '=', 'documents.document'), ('res_id', '=', document.id)])
            self.assertEqual(len(activity_ids), 1)
            self.assertEqual(activity_ids.activity_type_id, self.test_activity_type2)
            self.assertEqual(activity_ids.summary, 'TODO summary defaults')
            self.assertEqual(activity_ids.note, '<p>TODO note defaults</p>')
            self.assertEqual(activity_ids.user_id, self.user_employee)
            self.assertEqual(activity_ids.date_deadline, fields.Date.today() + relativedelta(months=1))

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_create_activity_disabled(self):
        """Test that no activity is created on the document if not enabled on the folder. """
        for document in self.send_test_mail_with_attachment(self.pre_existing_partner.email):
            self.assertFalse(self.env['mail.activity'].search(
                [('res_model', '=', 'documents.document'), ('res_id', '=', document.id)]))

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_custom_tags_list(self):
        """Test that the custom tags have the priority over `alias_tag_ids`."""
        defaults = ast.literal_eval(self.folder.alias_id.alias_defaults)
        defaults['tag_ids'] = [self.other_tag.id, self.non_existing_tag_id]
        self.folder.alias_defaults = repr(defaults)

        for document in self.send_test_mail_with_attachment(self.pre_existing_partner.email):
            self.assertFalse(document.partner_id)
            self.assertEqual(document.attachment_id.res_model, 'documents.document')
            self.assertEqual(document.attachment_id.res_id, document.id)
            self.assertEqual(document.folder_id, self.folder)
            self.assertEqual(document.tag_ids, self.other_tag)

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_custom_tags_command_1(self):
        defaults = ast.literal_eval(self.folder.alias_id.alias_defaults)
        defaults['tag_ids'] = [(Command.LINK.value, self.other_tag.id), (Command.LINK.value, self.non_existing_tag_id)]
        self.folder.alias_id.alias_defaults = repr(defaults)
        for document in self.send_test_mail_with_attachment(self.pre_existing_partner.email):
            self.assertEqual(document.tag_ids, self.other_tag)

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_custom_tags_command_2(self):
        defaults = ast.literal_eval(self.folder.alias_id.alias_defaults)
        defaults['tag_ids'] = [(Command.SET.value, 0, [self.other_tag.id, self.non_existing_tag_id])]
        self.folder.alias_id.alias_defaults = repr(defaults)
        for document in self.send_test_mail_with_attachment(self.pre_existing_partner.email):
            self.assertEqual(document.tag_ids, self.other_tag)

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_custom_tags_false(self):
        defaults = ast.literal_eval(self.folder.alias_id.alias_defaults)
        defaults['tag_ids'] = False
        self.folder.alias_id.alias_defaults = repr(defaults)
        for document in self.send_test_mail_with_attachment(self.pre_existing_partner.email):
            self.assertFalse(document.tag_ids)

    def test_alias_access(self):
        """Test that only the documents manager can set an alias."""
        Doc = self.env['documents.document'].with_context(default_access_internal='edit')
        user = new_test_user(self.env, login='documents_user', groups='base.group_user,documents.group_documents_user')
        manager = new_test_user(self.env, login='documents_manager', groups='base.group_user,documents.group_documents_manager')

        with self.assertRaises(AccessError):
            Doc.with_user(user).create({'name': 'Test', 'alias_name': 'doc_test_1', 'type': 'folder'})

        # in SUDO, the user can set the alias
        document = Doc.with_user(user).sudo().create({'name': 'Test', 'alias_name': 'doc_test_2', 'type': 'folder'})
        self.assertEqual(document.alias_name, 'doc_test_2')

        # the manager can set the alias
        document = Doc.with_user(manager).create({'name': 'Test', 'alias_name': 'doc_test_3', 'type': 'folder'})
        self.assertEqual(document.alias_name, 'doc_test_3')

        document.with_user(user).name = 'test write'
        with self.assertRaises(AccessError):
            document.with_user(user).alias_name = 'doc_test_4'

        document.with_user(manager).alias_name = 'doc_test_5'
        self.assertEqual(document.alias_name, 'doc_test_5')

        alias = self.env['mail.alias'].create({'alias_name': 'doc_test_6', 'alias_model_id': self.env['ir.model']._get('documents.document').id})
        with self.assertRaises(AccessError):
            Doc.with_user(user).create({'name': 'Test', 'alias_id': alias.id, 'type': 'folder'})
        with self.assertRaises(AccessError):
            document.with_user(user).alias_id = alias.id

        alias.alias_name = False
        Doc.with_user(user).create({'name': 'Test', 'alias_id': alias.id, 'type': 'folder'})

    def test_send_attachment_email_multi_company(self):
        for document in self.send_test_mail_with_attachment_on_different_company(self.pre_existing_partner.email):
            self.assertIsNotNone(document)
