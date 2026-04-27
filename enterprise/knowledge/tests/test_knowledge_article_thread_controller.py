from .common import KnowledgeArticlePermissionsCase
from odoo.tests import HttpCase

class TestKnowledgeArticleThreadController(KnowledgeArticlePermissionsCase, HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Threads = cls.env['knowledge.article.thread'].with_context({'mail_create_nolog': True})
        # readable article for portal and employee
        cls.readable_article = cls.article_read_contents[1]
        # readable and writable thread for portal and employee
        cls.readable_article_thread = cls.Threads.create({
            'article_id': cls.readable_article.id
        })

    def test_mail_threads_messages_as_portal(self):
        """
        Test that a portal user can properly access attachments through
        access tokens for comments in the Thread of an Article they have read
        access to."""
        employee_attachment = self.env['ir.attachment'].create({
            'name': 'Employee attachment',
            'raw': b'Attachment',
            'res_model': 'mail.compose.message',
        })
        portal_attachment = self.env['ir.attachment'].create({
            'name': 'Portal attachment',
            'raw': b'Attachment',
            'res_model': 'mail.compose.message',
        })
        employee_message = (
            self.readable_article_thread
            .message_post(body='Employee comment', author_id=self.partner_employee.id,
                attachment_ids=employee_attachment.ids)
        )
        portal_message = (
            self.readable_article_thread
            .message_post(body='Portal comment', author_id=self.partner_portal.id,
                attachment_ids=portal_attachment.ids)
        )
        self.authenticate('portal_test', 'portal_test')
        result = self.make_jsonrpc_request('/knowledge/threads/messages', {
            "thread_model": 'knowledge.article.thread',
            "thread_ids": [self.readable_article_thread.id]
        })
        result_thread_data = result[str(self.readable_article_thread.id)]['data']
        result_threads = result_thread_data['mail.thread']
        self.assertEqual(len(result_threads), 1)
        self.assertEqual(self.readable_article_thread.id, result_threads[0]['id'])
        result_messages = result_thread_data['mail.message']
        self.assertSetEqual(
            {message['id'] for message in result_messages},
            {employee_message.id, portal_message.id}
        )
        result_attachments = result_thread_data['ir.attachment']
        self.assertSetEqual(
            {attachment['id'] for attachment in result_attachments},
            {employee_attachment.id, portal_attachment.id}
        )
        self.assertTrue(result_attachments[0].get('access_token'))
        self.assertTrue(result_attachments[1].get('access_token'))
