# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.website.tests.test_performance import UtilPerf


class TestForumPerformance(UtilPerf):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_employee = mail_new_test_user(
            cls.env,
            login="employee",
            groups="base.group_user",
        )
        cls.forum = cls.env['forum.forum'].create({'name': 'TestForum'})
        cls.post = cls.env['forum.post'].create({
            'name': 'TestQuestion',
            'content': "Who's afraid of Virginia Wolf?",
            'forum_id': cls.forum.id,
            'tag_ids': [
                Command.create({
                    'name': 'Tag2',
                    'forum_id': cls.forum.id,
                }
            )],
        })

    def test_perf_sql_forum_standard_data(self):
        number_of_queries = self._get_url_hot_query(self.forum._compute_website_url())
        self.assertEqual(number_of_queries, 22)
        number_of_queries = self._get_url_hot_query(self.forum._compute_website_url(), cache=False)
        self.assertLessEqual(number_of_queries, 28)
        number_of_queries = self._get_url_hot_query(self.post.website_url)
        self.assertEqual(number_of_queries, 21)
        number_of_queries = self._get_url_hot_query(self.post.website_url, cache=False)
        self.assertLessEqual(number_of_queries, 25)

    def test_perf_sql_forum_scaling_answers(self):
        self.env['forum.tag'].create([
            {
                'forum_id': self.forum.id,
                'name': f'Forum Post Test Tag {i}',
            } for i in range(20)
        ])
        answers = self.env['forum.post'].create([
            {
                'content': "You",
                'forum_id': self.forum.id,
                'is_correct': i == 0,  # Ensure to have one accepted answer
                'name': f"TestAnswer {i}",
                'parent_id': self.post.id,
            } for i in range(50)
        ])
        self.env['forum.post.vote'].create([
            {
                'post_id': answer.id,
                'user_id': self.user_employee.id,
                'vote': '1',
            } for answer in answers[:20]
        ])
        self.env.flush_all()
        number_of_queries = self._get_url_hot_query(self.post.website_url)
        self.assertEqual(number_of_queries, 24)
        number_of_queries = self._get_url_hot_query(self.post.website_url, cache=False)
        self.assertLessEqual(number_of_queries, 28)

    def test_perf_sql_forum_scaling_posts(self):
        self.env['forum.post'].create([
            {
                'content': f"Who's afraid of Virginia Wolf {i}?",
                'forum_id': self.forum.id,
                'name': f"TestQuestion {i}",
                'tag_ids': [
                    Command.create({
                        'name': f"Tag -- {i}",
                        'forum_id': self.forum.id,
                    }
                )],
            } for i in range(100)
        ])
        self.env.flush_all()
        number_of_queries = self._get_url_hot_query(self.forum._compute_website_url())
        self.assertEqual(number_of_queries, 24)
        number_of_queries = self._get_url_hot_query(self.forum._compute_website_url(), cache=False)
        self.assertLessEqual(number_of_queries, 29)
