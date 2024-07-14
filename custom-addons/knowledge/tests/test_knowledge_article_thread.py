# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import tagged, HttpCase
from odoo.addons.mail.tests.common import mail_new_test_user


@tagged('post_install', '-at_install', 'knowledge', 'knowledge_tour', 'knowledge_comments')
class TestKnowledgeArticleTours(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.thread_test_user = mail_new_test_user(
            cls.env, login='thread_test_user', groups='base.group_user', name='Thread Testing User'
        )
        cls.article_to_test = cls.env['knowledge.article'].create([{
            'name': 'Sepultura',
            'body': '<p class="to-select">Lorem ipsum dolor sit amet,</p><p>consectetur adipiscing elit</p>',
            'is_article_visible_by_everyone': True
        }])


    def _init_body_with_comment(self):
        thread = self.env['knowledge.article.thread'].create({
            'article_id': self.article_to_test.id,
        })

        thread.message_post(body='War for Territory')

        self.article_to_test.write({
            'body': f'''<p class="to-select"><span data-id="{thread.id}" class="knowledge-thread-comment knowledge-thread-highlighted-comment" >
                        Lorem ipsum dolor</span> sit amet,</p><p>consectetur adipiscing elit</p>'''
        })
        return thread

    def test_knowledge_create_thread_tour(self):
        self.start_tour('/web', 'knowledge_article_thread_main_tour', login='thread_test_user')

    def test_knowledge_answer_comment_tour(self):
        self._init_body_with_comment()

        self.start_tour('/web', 'knowledge_article_thread_answer_comment_tour', login='thread_test_user')

    def test_knowledge_resolve_comment_tour(self):
        thread = self._init_body_with_comment()
        thread.message_post(body='Refuse/Resist')

        self.start_tour('/web', 'knowledge_article_thread_resolve_comment_tour', login='thread_test_user')

    def test_knowledge_comments_panel_tour(self):
        thread = self._init_body_with_comment()
        thread.message_post(body='Refuse/Resist')

        self.start_tour('/web', 'knowledge_article_thread_panel_tour', login='thread_test_user')
