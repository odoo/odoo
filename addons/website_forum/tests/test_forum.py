# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .common import KARMA, TestForumCommon
from odoo.exceptions import UserError, AccessError
from odoo.tools import mute_logger
from psycopg2 import IntegrityError


class TestForum(TestForumCommon):

    def test_crud_rights(self):
        Post = self.env['forum.post']
        Vote = self.env['forum.post.vote']
        self.user_portal.karma = 500
        self.user_employee.karma = 500

        # create some posts
        self.admin_post = self.post
        self.portal_post = Post.with_user(self.user_portal).create({
            'name': 'Post from Portal User',
            'content': 'I am not a bird.',
            'forum_id': self.forum.id,
        })
        self.employee_post = Post.with_user(self.user_employee).create({
            'name': 'Post from Employee User',
            'content': 'I am not a bird.',
            'forum_id': self.forum.id,
        })

        # vote on some posts
        self.employee_vote_on_admin_post = Vote.with_user(self.user_employee).create({
            'post_id': self.admin_post.id,
            'vote': '1',
        })
        self.portal_vote_on_admin_post = Vote.with_user(self.user_portal).create({
            'post_id': self.admin_post.id,
            'vote': '1',
        })
        self.admin_vote_on_portal_post = Vote.create({
            'post_id': self.portal_post.id,
            'vote': '1',
        })
        self.admin_vote_on_employee_post = Vote.create({
            'post_id': self.employee_post.id,
            'vote': '1',
        })

        # One should not be able to modify someone else's vote
        with self.assertRaises(UserError):
            self.admin_vote_on_portal_post.with_user(self.user_employee).write({
                'vote': '-1',
            })
        with self.assertRaises(UserError):
            self.admin_vote_on_employee_post.with_user(self.user_portal).write({
                'vote': '-1',
            })

        # One should not be able to give his vote to someone else
        self.employee_vote_on_admin_post.with_user(self.user_employee).write({
            'user_id': 1,
        })
        self.assertEqual(self.employee_vote_on_admin_post.user_id, self.user_employee, 'User employee should not be able to give its vote ownership to someone else')
        # One should not be able to change his vote's post to a post of his own (would be self voting)
        with self.assertRaises(UserError):
            self.employee_vote_on_admin_post.with_user(self.user_employee).write({
                'post_id': self.employee_post.id,
            })

        # One should not be able to give his vote to someone else
        self.portal_vote_on_admin_post.with_user(self.user_portal).write({
            'user_id': 1,
        })
        self.assertEqual(self.portal_vote_on_admin_post.user_id, self.user_portal, 'User portal should not be able to give its vote ownership to someone else')
        # One should not be able to change his vote's post to a post of his own (would be self voting)
        with self.assertRaises(UserError):
            self.portal_vote_on_admin_post.with_user(self.user_portal).write({
                'post_id': self.portal_post.id,
            })

        # One should not be able to vote for its own post
        with self.assertRaises(UserError):
            Vote.with_user(self.user_employee).create({
                'post_id': self.employee_post.id,
                'vote': '1',
            })
        # One should not be able to vote for its own post
        with self.assertRaises(UserError):
            Vote.with_user(self.user_portal).create({
                'post_id': self.portal_post.id,
                'vote': '1',
            })

        with mute_logger('odoo.sql_db'):
            with self.assertRaises(IntegrityError):
                with self.cr.savepoint():
                    # One should not be able to vote more than once on a same post
                    Vote.with_user(self.user_employee).create({
                        'post_id': self.admin_post.id,
                        'vote': '1',
                    })
            with self.assertRaises(IntegrityError):
                with self.cr.savepoint():
                    # One should not be able to vote more than once on a same post
                    Vote.with_user(self.user_employee).create({
                        'post_id': self.admin_post.id,
                        'vote': '1',
                    })

        # One should not be able to create a vote for someone else
        new_employee_vote = Vote.with_user(self.user_employee).create({
            'post_id': self.portal_post.id,
            'user_id': 1,
            'vote': '1',
        })
        self.assertEqual(new_employee_vote.user_id, self.user_employee, 'Creating a vote for someone else should not be allowed. It should create it for yourself instead')
        # One should not be able to create a vote for someone else
        new_portal_vote = Vote.with_user(self.user_portal).create({
            'post_id': self.employee_post.id,
            'user_id': 1,
            'vote': '1',
        })
        self.assertEqual(new_portal_vote.user_id, self.user_portal, 'Creating a vote for someone else should not be allowed. It should create it for yourself instead')

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.models')
    def test_ask(self):
        Post = self.env['forum.post']

        # Public user asks a question: not allowed
        with self.assertRaises(AccessError):
            Post.with_user(self.user_public).create({
                'name': " Question ?",
                'forum_id': self.forum.id,
            })

        # Portal user asks a question with tags: not allowed, unsufficient karma
        with self.assertRaises(AccessError):
            Post.with_user(self.user_portal).create({
                'name': " Q_0",
                'forum_id': self.forum.id,
                'tag_ids': [(0, 0, {'name': 'Tag0', 'forum_id': self.forum.id})]
            })

        # Portal user asks a question with tags: ok if enough karma
        self.user_portal.karma = KARMA['tag_create']
        Post.with_user(self.user_portal).create({
            'name': " Q0",
            'forum_id': self.forum.id,
            'tag_ids': [(0, 0, {'name': 'Tag1', 'forum_id': self.forum.id})]
        })
        self.assertEqual(self.user_portal.karma, KARMA['tag_create'], 'website_forum: wrong karma generation when asking question')

        self.user_portal.karma = KARMA['post']
        Post.with_user(self.user_portal).create({
            'name': " Q0",
            'forum_id': self.forum.id,
            'tag_ids': [(0, 0, {'name': 'Tag42', 'forum_id': self.forum.id})]
        })
        self.assertEqual(self.user_portal.karma, KARMA['post'] + KARMA['gen_que_new'], 'website_forum: wrong karma generation when asking question')

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.models')
    def test_answer(self):
        Post = self.env['forum.post']

        # Answers its own question: not allowed, unsufficient karma
        with self.assertRaises(AccessError):
            Post.with_user(self.user_employee).create({
                'name': " A0",
                'forum_id': self.forum.id,
                'parent_id': self.post.id,
            })

        # Answers on question: ok if enough karma
        self.user_employee.karma = KARMA['ans']
        Post.with_user(self.user_employee).create({
            'name': " A0",
            'forum_id': self.forum.id,
            'parent_id': self.post.id,
        })
        self.assertEqual(self.user_employee.karma, KARMA['ans'], 'website_forum: wrong karma generation when answering question')

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.models')
    def test_vote_crash(self):
        Post = self.env['forum.post']
        self.user_employee.karma = KARMA['ans']
        emp_answer = Post.with_user(self.user_employee).create({
            'name': 'TestAnswer',
            'forum_id': self.forum.id,
            'parent_id': self.post.id})

        # upvote its own post
        with self.assertRaises(UserError):
            emp_answer.vote(upvote=True)

        # not enough karma
        with self.assertRaises(AccessError):
            self.post.with_user(self.user_portal).vote(upvote=True)

    def test_vote(self):
        def check_vote_records_count_and_integrity(expected_total_votes_count):
            groups = self.env['forum.post.vote'].read_group([], fields=['__count'], groupby=['post_id', 'user_id'], lazy=False)
            self.assertEqual(len(groups), expected_total_votes_count)
            for post_user_group in groups:
                self.assertEqual(post_user_group['__count'], 1)

        ORIGIN_COUNT = len(self.env['forum.post.vote'].search([]).post_id)
        check_vote_records_count_and_integrity(ORIGIN_COUNT)
        self.post.create_uid.karma = KARMA['ask']
        self.user_portal.karma = KARMA['dwv']
        initial_vote_count = self.post.vote_count
        post_as_portal = self.post.with_user(self.user_portal)
        res = post_as_portal.vote(upvote=True)

        self.assertEqual(res['user_vote'], '1')
        self.assertEqual(res['vote_count'], initial_vote_count + 1)
        self.assertEqual(post_as_portal.user_vote, 1)
        self.assertEqual(self.post.create_uid.karma, KARMA['ask'] + KARMA['gen_que_upv'], 'website_forum: wrong karma generation of upvoted question author')

        # On voting again with the same value, nothing changes
        res = post_as_portal.vote(upvote=True)
        self.assertEqual(res['vote_count'], initial_vote_count + 1)
        self.assertEqual(res['user_vote'], '1')
        self.post.invalidate_recordset()
        self.assertEqual(post_as_portal.user_vote, 1)

        # On reverting vote, vote cancels
        res = post_as_portal.vote(upvote=False)
        self.assertEqual(res['vote_count'], initial_vote_count)
        self.assertEqual(res['user_vote'], '0')
        self.post.invalidate_recordset()
        self.assertEqual(post_as_portal.user_vote, 0)

        # Everything works from "0" too
        res = post_as_portal.vote(upvote=False)
        self.assertEqual(res['vote_count'], initial_vote_count - 1)
        self.assertEqual(res['user_vote'], '-1')
        self.post.invalidate_recordset()
        self.assertEqual(post_as_portal.user_vote, -1)

        check_vote_records_count_and_integrity(ORIGIN_COUNT + 1)

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.models')
    def test_downvote_crash(self):
        Post = self.env['forum.post']
        self.user_employee.karma = KARMA['ans']
        emp_answer = Post.with_user(self.user_employee).create({
            'name': 'TestAnswer',
            'forum_id': self.forum.id,
            'parent_id': self.post.id})

        # downvote its own post
        with self.assertRaises(UserError):
            emp_answer.vote(upvote=False)

        # not enough karma
        with self.assertRaises(AccessError):
            self.post.with_user(self.user_portal).vote(upvote=False)

    def test_downvote(self):
        self.post.create_uid.karma = 50
        self.user_portal.karma = KARMA['dwv']
        self.post.with_user(self.user_portal).vote(upvote=False)
        self.assertEqual(self.post.create_uid.karma, 50 + KARMA['gen_que_dwv'], 'website_forum: wrong karma generation of downvoted question author')

    def test_comment_crash(self):
        with self.assertRaises(AccessError):
            self.post.with_user(self.user_portal).message_post(body='Should crash', message_type='comment')

    def test_comment(self):
        self.post.with_user(self.user_employee).message_post(body='Test0', message_type='notification')
        self.user_employee.karma = KARMA['com_all']
        self.post.with_user(self.user_employee).message_post(body='Test1', message_type='comment')
        self.assertEqual(len(self.post.message_ids), 4, 'website_forum: wrong behavior of message_post')

    def test_flag_a_post(self):
        Post = self.env['forum.post']
        self.user_portal.karma = KARMA['ask']
        post = Post.with_user(self.user_portal).create({
            'name': "Q0",
            'forum_id': self.forum.id,
        })

        # portal user flags a post: not allowed, unsufficient karma
        with self.assertRaises(AccessError):
            post.with_user(self.user_portal).flag()

        # portal user flags a post: ok if enough karma
        self.user_portal.karma = KARMA['flag']
        post.state = 'active'
        post.with_user(self.user_portal).flag()
        self.assertEqual(post.state, 'flagged', 'website_forum: wrong state when flagging a post')

    def test_validate_a_post(self):
        Post = self.env['forum.post']
        self.user_portal.karma = KARMA['ask']
        post = Post.with_user(self.user_portal).create({
            'name': "Q0",
            'forum_id': self.forum.id,
        })

        # portal user validate a post: not allowed, unsufficient karma
        with self.assertRaises(AccessError):
            post.with_user(self.user_portal).validate()

        # portal user validate a pending post
        self.user_portal.karma = KARMA['moderate']
        post.state = 'pending'
        init_karma = post.create_uid.karma
        post.with_user(self.user_portal).validate()
        self.assertEqual(post.state, 'active', 'website_forum: wrong state when validate a post after pending')
        self.assertEqual(post.create_uid.karma, init_karma + KARMA['gen_que_new'], 'website_forum: wrong karma when validate a post after pending')

        # portal user validate a flagged post: ok if enough karma
        self.user_portal.karma = KARMA['moderate']
        post.state = 'flagged'
        post.with_user(self.user_portal).validate()
        self.assertEqual(post.state, 'active', 'website_forum: wrong state when validate a post after flagged')

        # portal user validate an offensive post: ok if enough karma
        self.user_portal.karma = KARMA['moderate']
        post.state = 'offensive'
        init_karma = post.create_uid.karma
        post.with_user(self.user_portal).validate()
        self.assertEqual(post.state, 'active', 'website_forum: wrong state when validate a post after offensive')

    def test_refuse_a_post(self):
        Post = self.env['forum.post']
        self.user_portal.karma = KARMA['ask']
        post = Post.with_user(self.user_portal).create({
            'name': "Q0",
            'forum_id': self.forum.id,
        })

        # portal user validate a post: not allowed, unsufficient karma
        with self.assertRaises(AccessError):
            post.with_user(self.user_portal).refuse()

        # portal user validate a pending post
        self.user_portal.karma = KARMA['moderate']
        post.state = 'pending'
        init_karma = post.create_uid.karma
        post.with_user(self.user_portal).refuse()
        self.assertEqual(post.moderator_id, self.user_portal, 'website_forum: wrong moderator_id when refusing')
        self.assertEqual(post.create_uid.karma, init_karma, 'website_forum: wrong karma when refusing a post')

    def test_mark_a_post_as_offensive(self):
        Post = self.env['forum.post']
        self.user_portal.karma = KARMA['ask']
        post = Post.with_user(self.user_portal).create({
            'name': "Q0",
            'forum_id': self.forum.id,
        })

        # portal user mark a post as offensive: not allowed, unsufficient karma
        with self.assertRaises(AccessError):
            post.with_user(self.user_portal).mark_as_offensive(12)

        # portal user mark a post as offensive
        self.user_portal.karma = KARMA['moderate']
        post.state = 'flagged'
        init_karma = post.create_uid.karma
        post.with_user(self.user_portal).mark_as_offensive(12)
        self.assertEqual(post.state, 'offensive', 'website_forum: wrong state when marking a post as offensive')
        self.assertEqual(post.create_uid.karma, init_karma + KARMA['gen_ans_flag'], 'website_forum: wrong karma when marking a post as offensive')

    def test_convert_answer_to_comment_crash(self):
        Post = self.env['forum.post']

        # converting a question does nothing
        new_msg = self.post.with_user(self.user_portal).convert_answer_to_comment()
        self.assertEqual(new_msg.id, False, 'website_forum: question to comment conversion failed')
        self.assertEqual(Post.search([('name', '=', 'TestQuestion')])[0].forum_id.name, 'TestForum', 'website_forum: question to comment conversion failed')

        with self.assertRaises(AccessError):
            self.answer.with_user(self.user_portal).convert_answer_to_comment()

    def test_convert_answer_to_comment(self):
        self.user_portal.karma = KARMA['com_conv_all']
        post_author = self.answer.create_uid.partner_id
        new_msg = self.answer.with_user(self.user_portal).convert_answer_to_comment()
        self.assertEqual(len(new_msg), 1, 'website_forum: wrong answer to comment conversion')
        self.assertEqual(new_msg.author_id, post_author, 'website_forum: wrong answer to comment conversion')
        self.assertIn('I am an anteater', new_msg.body, 'website_forum: wrong answer to comment conversion')

    def test_edit_post_crash(self):
        with self.assertRaises(AccessError):
            self.post.with_user(self.user_portal).write({'name': 'I am not your father.'})

    def test_edit_post(self):
        self.post.create_uid.karma = KARMA['edit_own']
        self.post.write({'name': 'Actually I am your dog.'})
        self.user_portal.karma = KARMA['edit_all']
        self.post.with_user(self.user_portal).write({'name': 'Actually I am your cat.'})

    def test_close_post_crash(self):
        with self.assertRaises(AccessError):
            self.post.with_user(self.user_portal).close(None)

    def test_close_post_own(self):
        self.post.create_uid.karma = KARMA['close_own']
        self.post.close(None)

    def test_close_post_all(self):
        self.user_portal.karma = KARMA['close_all']
        self.post.with_user(self.user_portal).close(None)

    def test_deactivate_post_crash(self):
        with self.assertRaises(AccessError):
            self.post.with_user(self.user_portal).write({'active': False})

    def test_deactivate_post_own(self):
        self.post.create_uid.karma = KARMA['unlink_own']
        self.post.write({'active': False})

    def test_deactivate_post_all(self):
        self.user_portal.karma = KARMA['unlink_all']
        self.post.with_user(self.user_portal).write({'active': False})

    def test_unlink_post_crash(self):
        with self.assertRaises(AccessError):
            self.post.with_user(self.user_portal).unlink()

    def test_unlink_post_own(self):
        self.post.create_uid.karma = KARMA['unlink_own']
        self.post.unlink()

    def test_unlink_post_all(self):
        self.user_portal.karma = KARMA['unlink_all']
        self.post.with_user(self.user_portal).unlink()

    def test_forum_mode_questions(self):
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
        answer_to_questions_post = Post.create({
            'name': 'This is an answer',
            'forum_id': forum_questions.id,
            'parent_id': questions_post.id,
        })
        self.assertEqual(
            not questions_post.uid_has_answered or questions_post.forum_id.mode == 'discussions', False)
        self.assertEqual(
            questions_post.uid_has_answered and questions_post.forum_id.mode == 'questions', True)

    def test_forum_mode_discussions(self):
        Forum = self.env['forum.forum']
        forum_discussions = Forum.create({
            'name': 'Discussions Forum',
            'mode': 'discussions',
            'active': True
        })
        Post = self.env['forum.post']
        discussions_post = Post.create({
            'name': 'My First Post',
            'forum_id': forum_discussions.id,
            'parent_id': self.post.id,
        })
        answer_to_discussions_post = Post.create({
            'name': 'This is an answer',
            'forum_id': forum_discussions.id,
            'parent_id': discussions_post.id,
        })
        self.assertEqual(
            not discussions_post.uid_has_answered or discussions_post.forum_id.mode == 'discussions', True)
        self.assertEqual(
            discussions_post.uid_has_answered and discussions_post.forum_id.mode == 'questions', False)

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
