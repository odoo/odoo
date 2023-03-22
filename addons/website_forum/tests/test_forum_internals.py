# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_forum.tests.common import KARMA, TestForumCommon
from odoo.tests import tagged, users


@tagged('forum_internals')
class TestForumInternals(TestForumCommon):

    @classmethod
    def setUpClass(cls):
        super(TestForumInternals, cls).setUpClass()
        cls._activate_multi_website()

    @users('admin')
    def test_assert_initial_values(self):
        """ To ease test setup we support tests only with base data, to avoid
        having to deal with custom / existing data in various asserts. """
        forums = self.env['forum.forum'].search([])
        self.assertEqual(forums, self.base_forum + self.forum)
        self.assertFalse(forums.website_id)

    @users('admin')
    def test_website_forum_count(self):
        """ Test synchronization of website / forum counters. """
        base_website = self.base_website.with_env(self.env)
        website_2 = self.website_2.with_env(self.env)

        self.assertEqual(base_website.forum_count, 2,
                         'Should count default global forums')
        self.assertEqual(website_2.forum_count, 2,
                         'Should count default global forums')

        new_forums = self.env['forum.forum'].create([
            {
                'name': 'New Global',
                'website_id': False,
            }, {
                'name': 'Base Website',
                'website_id': base_website.id,
            }, {
                'name': 'Website 2',
                'website_id': website_2.id,
            }, {
                'name': 'Website 2.2',
                'website_id': website_2.id,
            }
        ])
        self.assertEqual(base_website.forum_count, 4,
                         '3 globals, 1 specific')
        self.assertEqual(website_2.forum_count, 5,
                         '3 globals, 2 specific')

        new_forums.write({'website_id': False})
        self.assertEqual(base_website.forum_count, 6,
                         '6 global forums')
        self.assertEqual(website_2.forum_count, 6,
                         '6 global forums')


@tagged('forum_internals')
class TestPostInternals(TestForumCommon):

    def test_post_fields(self):
        Forum = self.env['forum.forum']
        forum_questions = Forum.create({
            'name': 'Questions Forum',
            'mode': 'questions',
            'active': True
        })
        Post = self.env['forum.post']
        questions_post = Post.create({
            'name': 'My First Post',
            'forum_id': forum_questions.id,
            'parent_id': self.post.id,
        })
        _answer = Post.create({
            'name': 'This is an answer',
            'forum_id': forum_questions.id,
            'parent_id': questions_post.id,
        })
        self.assertTrue(questions_post.uid_has_answered)


@tagged('forum_internals')
class TestTags(TestForumCommon):

    def test_tag_creation_multi_forum(self):
        Post = self.env['forum.post']
        forum_1 = self.forum
        forum_2 = forum_1.copy({
            'name': 'Questions Forum'
        })
        self.user_portal.karma = KARMA['tag_create']
        Post.with_user(self.user_portal).create({
            'name': "Post Forum 1",
            'forum_id': forum_1.id,
            'tag_ids': forum_1._tag_to_write_vals('_Food'),
        })
        Post.with_user(self.user_portal).create({
            'name': "Post Forum 2",
            'forum_id': forum_2.id,
            'tag_ids': forum_2._tag_to_write_vals('_Food'),
        })
        food_tags = self.env['forum.tag'].search([('name', '=', 'Food')])
        self.assertEqual(len(food_tags), 2, "One Food tag should have been created in each forum.")
        self.assertIn(forum_1, food_tags.forum_id, "One Food tag should have been created for forum 1.")
        self.assertIn(forum_2, food_tags.forum_id, "One Food tag should have been created for forum 2.")
