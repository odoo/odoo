# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.knowledge.tests.common import  KnowledgeArticlePermissionsCase
from odoo.tests.common import tagged, users
from odoo.exceptions import AccessError

@tagged('knowledge_comments')
class TestKnowledgeArticleThreadPermissions(KnowledgeArticlePermissionsCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Threads = cls.env['knowledge.article.thread'].with_context({'mail_create_nolog': True})

        # Every internal user can write on it
        cls.writable_article = cls.article_roots[0]
        cls.writable_article.invite_members(cls.partner_portal, 'write')
        cls.workspace_thread = Threads.create({
            'article_id': cls.writable_article.id
        })
        cls.workspace_thread.message_post(body='This is a public Thread')

        # Employee is readonly
        cls.shared_article = cls.article_roots[2]
        cls.shared_thread = Threads.create({
            'article_id': cls.shared_article.id
        })
        cls.shared_thread.message_post(body='This is a shared Thread')

        # Only employee_manager can write on it
        cls.private_article = cls.env['knowledge.article'].create([
            {'article_member_ids': [
                (0, 0, {'partner_id': cls.partner_employee_manager.id,
                        'permission': 'write',
                       }),
             ],
             'internal_permission': 'none',
             'name': 'Private Root',
            }])
        cls.private_thread = Threads.create({
            'article_id': cls.private_article.id
        })
        cls.private_thread.message_post(body='This is a private Thread')

    @users('employee')
    def test_create_article_thread_as_employee(self):
        article = self.writable_article.with_env(self.env)
        # writable article
        self.env['knowledge.article.thread'].create([{
            'article_id': article.id,
        }])
        with self.assertRaises(AccessError):
            # readonly article
            self.env['knowledge.article.thread'].create([{
                'article_id': self.shared_article.with_env(self.env).id
            }])

    @users('employee')
    def test_read_article_thread_as_employee(self):
        private_thread = self.private_thread.with_env(self.env)
        shared_thread = self.shared_thread.with_env(self.env)
        workspace_thread = self.workspace_thread.with_env(self.env)

        # When you have access to an article you can write and read on threads
        self.assertFalse(workspace_thread.is_resolved)
        self.assertFalse(shared_thread.is_resolved)

        #* No access to the article = No access to the linked thread
        with self.assertRaises(AccessError):
            private_thread.is_resolved

    @users('portal_test')
    def test_read_article_thread_as_portal(self):
        private_thread = self.private_thread.with_env(self.env)
        shared_thread = self.shared_thread.with_env(self.env)
        workspace_thread = self.workspace_thread.with_env(self.env)

        # When you have access to an article you can write and read on threads
        self.assertFalse(workspace_thread.is_resolved)
        with self.assertRaises(AccessError):
            shared_thread.is_resolved

        #* No access to the article = No access to the linked thread
        with self.assertRaises(AccessError):
            private_thread.is_resolved

    @users('employee')
    def test_security_thread_resolution(self):
        base_thread = self.private_thread.with_env(self.env)

        # No access to the article
        with self.assertRaises(AccessError):
            base_thread.write({'is_resolved': True})

        base_thread = self.workspace_thread.with_env(self.env)
        # Access to the article
        self.assertFalse(base_thread.is_resolved)
        base_thread.write({'is_resolved': True})
        self.assertTrue(base_thread.is_resolved)

    @users('portal_test')
    def test_message_post_as_portal(self):
        base_thread = self.private_thread.with_env(self.env)
        with self.assertRaises(AccessError):
            base_thread.message_post(body="It raises an error because of no access")

        self.private_article.sudo().invite_members(self.partner_portal, 'read')

        self.assertMembers(self.private_article, 'none', {self.partner_employee_manager: 'write', self.env.user.partner_id: 'read'})

        message = base_thread.message_post(body="Hello Everyone", partner_ids=[self.partner_employee.id, self.partner_employee_manager.id], tracking_value_ids=[1, 2, 3])
        self.assertEqual(len(base_thread.sudo().message_ids), 2, "Portal user should be able to post a message")
        self.assertListEqual(message.tracking_value_ids.ids, [], "Tracking values should have been filltered")

    @users('employee')
    def test_message_post_as_employee(self):
        base_thread = self.shared_article.with_env(self.env)

        self.assertEqual(len(base_thread.message_ids), 1)
        base_thread.message_post(body="Hello Friend")
        self.assertEqual(len(base_thread.message_ids), 2, "A message should have been posted")

        # Access token is generated for the attachment when a user posts a message
        base_thread = self.workspace_thread.with_env(self.env)
        attachment = self.env['ir.attachment'].create({
            'name': 'Test attachment',
            'raw': b'Attachment',
            'res_model': 'mail.compose.message',
        })
        message = base_thread.message_post(body="Hello Dear!", attachment_ids=attachment.ids)
        self.assertTrue(message.attachment_ids[0].access_token)
