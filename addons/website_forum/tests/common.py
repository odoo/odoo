# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import Counter

from odoo.tests import common
from odoo.tools import mute_logger

KARMA = {
    'ask': 5, 'ans': 10,
    'com_own': 5, 'com_all': 10,
    'com_conv_all': 50,
    'upv': 5, 'dwv': 10,
    'edit_own': 10, 'edit_all': 20,
    'close_own': 10, 'close_all': 20,
    'unlink_own': 10, 'unlink_all': 20,
    'post': 100, 'flag': 500, 'moderate': 1000,
    'gen_que_new': 1, 'gen_que_upv': 5, 'gen_que_dwv': -10,
    'gen_ans_upv': 10, 'gen_ans_dwv': -20, 'gen_ans_flag': -45,
    'tag_create': 30,
}


class TestForumCommon(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestForumCommon, cls).setUpClass()

        # default base data
        cls.base_website = cls.env.ref("website.default_website")
        cls.base_forum = cls.env.ref("website_forum.forum_help")

        Forum = cls.env['forum.forum']
        Post = cls.env['forum.post']

        # Test users
        TestUsersEnv = cls.env['res.users'].with_context({'no_reset_password': True})
        group_employee_id = cls.env.ref('base.group_user').id
        group_portal_id = cls.env.ref('base.group_portal').id
        group_public_id = cls.env.ref('base.group_public').id
        cls.user_employee = TestUsersEnv.create({
            'name': 'Armande Employee',
            'login': 'Armande',
            'email': 'armande.employee@example.com',
            'karma': 0,
            'groups_id': [(6, 0, [group_employee_id])]
        })
        cls.user_employee_2 = cls.env['res.users'].create({
            'name': 'Merlin Employee',
            'login': 'Merlin',
            'email': 'merlin.employee@example.com',
            'karma': KARMA['ask'],
            'groups_id': [(6, 0, [cls.env.ref('base.group_user').id])],
        })
        cls.user_portal = TestUsersEnv.create({
            'name': 'Beatrice Portal',
            'login': 'Beatrice',
            'email': 'beatrice.employee@example.com',
            'karma': 0,
            'groups_id': [(6, 0, [group_portal_id])]
        })
        cls.user_public = TestUsersEnv.create({
            'name': 'Cedric Public',
            'login': 'Cedric',
            'email': 'cedric.employee@example.com',
            'karma': 0,
            'groups_id': [(6, 0, [group_public_id])]
        })
        cls.user_admin = cls.env.ref('base.user_admin')

        # Test forum
        cls.forum = Forum.create({
            'name': 'TestForum',
            'karma_ask': KARMA['ask'],
            'karma_answer': KARMA['ans'],
            'karma_comment_own': KARMA['com_own'],
            'karma_comment_all': KARMA['com_all'],
            'karma_answer_accept_own': 9999,
            'karma_answer_accept_all': 9999,
            'karma_upvote': KARMA['upv'],
            'karma_downvote': KARMA['dwv'],
            'karma_edit_own': KARMA['edit_own'],
            'karma_edit_all': KARMA['edit_all'],
            'karma_close_own': KARMA['close_own'],
            'karma_close_all': KARMA['close_all'],
            'karma_unlink_own': KARMA['unlink_own'],
            'karma_unlink_all': KARMA['unlink_all'],
            'karma_post': KARMA['post'],
            'karma_comment_convert_all': KARMA['com_conv_all'],
            'karma_gen_question_new': KARMA['gen_que_new'],
            'karma_gen_question_upvote': KARMA['gen_que_upv'],
            'karma_gen_question_downvote': KARMA['gen_que_dwv'],
            'karma_gen_answer_upvote': KARMA['gen_ans_upv'],
            'karma_gen_answer_downvote': KARMA['gen_ans_dwv'],
            'karma_gen_answer_accept': 9999,
            'karma_gen_answer_accepted': 9999,
            'karma_gen_answer_flagged': KARMA['gen_ans_flag'],
        })
        cls.post = Post.create({
            'name': 'TestQuestion',
            'content': 'I am not a bird.',
            'forum_id': cls.forum.id,
            'tag_ids': [(0, 0, {'name': 'Tag2', 'forum_id': cls.forum.id})]
        })
        cls.answer = Post.create({
            'name': 'TestAnswer',
            'content': 'I am an anteater.',
            'forum_id': cls.forum.id,
            'parent_id': cls.post.id,
        })

    @classmethod
    def _activate_multi_website(cls):
        cls.website_2 = cls.env['website'].create({
            'name': 'Second Website on same company',
        })

    @mute_logger("odoo.models.unlink")
    def _activate_tags_for_counts(self):
        self.env['forum.tag'].search([]).unlink()
        self.tags = self.env['forum.tag'].create(
            [
                {'forum_id': forum_id.id, 'name': f'Test Tag {tag_idx}'}
                for forum_id in self.forum | self.base_forum
                for tag_idx in range(1, 8)
            ]
        )


class TestForumPostCommon(TestForumCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_portal_2 = cls.user_portal.copy({
            'name': 'Portal user 2',
            'login': 'portalUser2',
            'email': 'pu2@odoo.com',
        })
        cls.reason_duplicate = cls.env.ref('website_forum.reason_1')
        cls.reason_insulting = cls.env.ref('website_forum.reason_11')

    def _generate_posts(self, user):
        """Create multiple posts disregarding current user rights to post."""
        user_karma = user.karma
        user.karma = KARMA['moderate']
        posts = self.env['forum.post'].with_user(user).create([
            {
                'name': f"{user.name}'s Post - {values.get('state', 'active')} - {values.get('visible', True)}",
                'forum_id': self.forum.id,
                **values,
            }
            for values in [
                {'state': 'active'},
                {'state': 'flagged'},  # should be same as active
                {'state': 'pending'},
                {'state': 'close', 'closed_reason_id': self.reason_duplicate.id},
                {'state': 'close', 'closed_reason_id': self.reason_duplicate.id, 'visible': False},
                {'state': 'offensive', 'closed_reason_id': self.reason_insulting.id},
                {'state': 'offensive', 'closed_reason_id': self.reason_insulting.id, 'visible': False},
            ]
        ])
        self.assertDictEqual(
            Counter(posts.mapped('state')),
            {
                'active': 1,
                'pending': 1,
                'flagged': 1,
                'close': 2,
                'offensive': 2,
            },
        )
        user.karma = user_karma
        return posts

    def _check_post_can_view_cases(self, cases, all_posts):
        for user, expected_viewable in cases:
            with self.subTest(user=user.name, op='='):
                ForumPostUser = self.env['forum.post'].with_user(user)
                viewable_posts = ForumPostUser.search([('can_view', '=', True)])
                not_viewable_posts = ForumPostUser.sudo().search([('can_view', '=', False)])
                expected_viewable_posts_names = set(expected_viewable.mapped('name'))
                self.assertSetEqual(set(viewable_posts.mapped('name')), expected_viewable_posts_names)
                self.assertSetEqual(set(not_viewable_posts.mapped('name')), set(all_posts.mapped('name')) - expected_viewable_posts_names)

            with self.subTest(user=user.name, op='='):
                viewable_posts_redo = ForumPostUser.search([('can_view', '!=', False)])
                not_viewable_posts_redo = ForumPostUser.sudo().search([('can_view', '!=', True)])
                self.assertEqual(viewable_posts, viewable_posts_redo)
                self.assertEqual(not_viewable_posts, not_viewable_posts_redo)
