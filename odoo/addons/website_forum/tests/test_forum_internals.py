# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_forum.models.forum_forum import MOST_USED_TAGS_COUNT
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

    def test_website_forum_last_post_id(self):
        """Check that each forum's last post is computed correctly and efficiently."""
        test_forums = self.base_forum | self.forum
        new_posts = self.env["forum.post"].create([{
            'name': f'New Post {forum_post_idx}',
            'forum_id': forum.id,
        } for forum_post_idx, forum in enumerate(test_forums)])

        with self.assertQueryCount(1):
            self.assertEqual(test_forums.last_post_id.ids, new_posts.ids)

        another_post = self.env["forum.post"].create([{
            'name': 'Another New Post',
            'forum_id': self.base_forum.id,
        }])
        with self.assertQueryCount(1):
            self.assertEqual(test_forums.last_post_id.ids, (another_post | new_posts[1]).ids)


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

    def test_tags_usage_most_used(self):
        self._activate_tags_for_counts()
        posts_per_tag = [(tag_id, post_count) for tag_id, post_count in zip(self.base_forum.tag_ids, range(2, 9))]
        vals_list = [
            {'forum_id': self.base_forum.id, 'name': 'A post', 'content': 'A content', 'tag_ids': [tag_id.id]}
            for tag_id, post_count in posts_per_tag
            for __ in range(post_count)
        ]
        self.env['forum.post'].create(vals_list)
        self.env['forum.tag'].flush_model()

        self.assertListEqual(
            self.base_forum.tag_most_used_ids.ids,
            [tag_id.id for tag_id, _ in reversed(posts_per_tag[-MOST_USED_TAGS_COUNT:])],
        )
        self.assertEqual(self.base_forum.tag_unused_ids, self.env['forum.tag'])

    def test_tags_usage_unused(self):
        self._activate_tags_for_counts()
        used_tag = self.forum.tag_ids[5]
        self.env['forum.post'].create(
            [
                {'forum_id': tag_id.forum_id.id, 'tag_ids': [tag_id.id], 'name': 'A post', 'content': 'A content'}
                for tag_id in (used_tag | self.base_forum.tag_ids)
            ]
        )
        self.env['forum.tag'].flush_model()

        # trigger batch compute
        __ = (self.forum | self.base_forum).tag_most_used_ids

        self.assertEqual(self.forum.tag_most_used_ids, used_tag)
        self.assertEqual(self.forum.tag_unused_ids, self.forum.tag_ids - used_tag)

        self.assertEqual(self.base_forum.tag_most_used_ids, self.base_forum.tag_ids[:MOST_USED_TAGS_COUNT])
        self.assertEqual(self.base_forum.tag_unused_ids, self.env['forum.tag'])

    def test_forum_post_link(self):
        content = 'This is a test link: <a href="https://www.example.com/route?param1=a&param2=b" rel="ugc">test</a> Let make sure it works.'
        self.user_portal.karma = 50
        with self.with_user(self.user_portal.login):
            post = self.env['forum.post'].create({
                'name': "Post Forum test",
                'content': content,
                'forum_id': self.forum.id,
            })
        self.assertEqual(post.content, '<p>This is a test link: <a rel="nofollow" href="https://www.example.com/route?param1=a&amp;param2=b">test</a> Let make sure it works.</p>')
