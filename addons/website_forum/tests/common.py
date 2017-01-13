# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common

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


class TestForumCommon(common.SavepointCase):

    @classmethod
    def setUpClass(cls):
        super(TestForumCommon, cls).setUpClass()

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
