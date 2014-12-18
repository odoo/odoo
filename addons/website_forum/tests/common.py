# -*- coding: utf-8 -*-

from openerp.tests import common

KARMA = {
    'ask': 5, 'ans': 10,
    'com_own': 5, 'com_all': 10,
    'com_conv_all': 50,
    'upv': 5, 'dwv': 10,
    'edit_own': 10, 'edit_all': 20,
    'close_own': 10, 'close_all': 20,
    'unlink_own': 10, 'unlink_all': 20,
    'gen_que_new': 1, 'gen_que_upv': 5, 'gen_que_dwv': -10,
    'gen_ans_upv': 10, 'gen_ans_dwv': -20,
}


class TestForumCommon(common.TransactionCase):

    def setUp(self):
        super(TestForumCommon, self).setUp()

        Forum = self.env['forum.forum']
        Post = self.env['forum.post']

        # Test users
        TestUsersEnv = self.env['res.users'].with_context({'no_reset_password': True})
        group_employee_id = self.ref('base.group_user')
        group_portal_id = self.ref('base.group_portal')
        group_public_id = self.ref('base.group_public')
        self.user_employee = TestUsersEnv.create({
            'name': 'Armande Employee',
            'login': 'Armande',
            'alias_name': 'armande',
            'email': 'armande.employee@example.com',
            'karma': 0,
            'groups_id': [(6, 0, [group_employee_id])]
        })
        self.user_portal = TestUsersEnv.create({
            'name': 'Beatrice Portal',
            'login': 'Beatrice',
            'alias_name': 'beatrice',
            'email': 'beatrice.employee@example.com',
            'karma': 0,
            'groups_id': [(6, 0, [group_portal_id])]
        })
        self.user_public = TestUsersEnv.create({
            'name': 'Cedric Public',
            'login': 'Cedric',
            'alias_name': 'cedric',
            'email': 'cedric.employee@example.com',
            'karma': 0,
            'groups_id': [(6, 0, [group_public_id])]
        })

        # Test forum
        self.forum = Forum.create({
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
            'karma_comment_convert_all': KARMA['com_conv_all'],
            'karma_gen_question_new': KARMA['gen_que_new'],
            'karma_gen_question_upvote': KARMA['gen_que_upv'],
            'karma_gen_question_downvote': KARMA['gen_que_dwv'],
            'karma_gen_answer_upvote': KARMA['gen_ans_upv'],
            'karma_gen_answer_downvote': KARMA['gen_ans_dwv'],
            'karma_gen_answer_accept': 9999,
            'karma_gen_answer_accepted': 9999,
        })
        self.post = Post.create({
            'name': 'TestQuestion',
            'content': 'I am not a bird.',
            'forum_id': self.forum.id,
            'tag_ids': [(0, 0, {'name': 'Tag0', 'forum_id': self.forum.id})]
        })
        self.answer = Post.create({
            'name': 'TestAnswer',
            'content': 'I am an anteater.',
            'forum_id': self.forum.id,
            'parent_id': self.post.id,
        })
