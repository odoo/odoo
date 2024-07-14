# -*- coding: utf-8 -*-

from odoo import tools
from odoo.addons.mail.tests.common import MailCommon
from odoo.addons.test_mail.data.test_mail_data import MAIL_EML_ATTACHMENT
from odoo.tools import mute_logger


class TestMailGateway(MailCommon):
    """ Test document creation on incoming mail.

    Especially that the partner_id is correctly set on the created document.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.folder = cls.env['documents.folder'].create({
            'name': 'folder',
        })
        cls.share_link = cls.env['documents.share'].create({
            'folder_id': cls.folder.id,
            'name': 'share_link_folder',
            'email_drop': True,
            'alias_name': 'shareFolder',
        })
        cls.alias = cls.env['mail.alias'].create({
            'alias_name': 'inbox-test',
            'alias_model_id': cls.env['ir.model']._get('documents.document').id,
            'alias_parent_model_id': cls.env['ir.model']._get('documents.share').id,
            'alias_parent_thread_id': cls.share_link.id,
            'alias_defaults': f"{{'folder_id': {cls.folder.id}, 'create_share_id': {cls.share_link.id}}}",
            'alias_contact': 'everyone',
        })
        cls.email_with_no_partner = tools.email_normalize('non-existing@test.com')
        cls.pre_existing_partner = cls.env['res.partner'].find_or_create('existing@test.com')
        cls.default_partner = cls.env['res.partner'].find_or_create('default@test.com')
        cls.email_filenames = ['attachment', 'original_msg.eml']

    def send_test_mail_with_attachment(self, email_from):
        with self.mock_mail_gateway():
            self.format_and_process(
                MAIL_EML_ATTACHMENT,
                email_from,
                f'inbox-test@{self.alias_domain}',
                subject='Test document creation on incoming mail',
                target_model='documents.document',
            )
        documents = self.env['documents.document'].search([('name', 'in', self.email_filenames)])
        self.assertEqual(len(documents), len(self.email_filenames))
        return documents

    def test_initial_values(self):
        self.assertFalse(self.env['res.partner'].search([('email', '=', self.email_with_no_partner)]))
        self.assertFalse(self.env['documents.document'].search([('name', 'in', self.email_filenames)]))

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_set_contact_non_existing_partner(self):
        for document in self.send_test_mail_with_attachment(self.email_with_no_partner):
            self.assertFalse(document.partner_id)

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_set_contact_existing_partner(self):
        for document in self.send_test_mail_with_attachment(self.pre_existing_partner.email):
            self.assertFalse(document.partner_id)

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_set_contact_default_partner_non_existing_partner(self):
        self.share_link.partner_id = self.default_partner
        for document in self.send_test_mail_with_attachment(self.email_with_no_partner):
            self.assertEqual(document.partner_id, self.default_partner)

    @mute_logger('odoo.addons.mail.models.mail_thread')
    def test_set_contact_default_partner_existing_partner(self):
        self.share_link.partner_id = self.default_partner
        for document in self.send_test_mail_with_attachment(self.pre_existing_partner.email):
            self.assertEqual(document.partner_id, self.default_partner)
