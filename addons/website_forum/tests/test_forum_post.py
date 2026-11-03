from odoo import fields, Command
from odoo.exceptions import UserError

from odoo.addons.website_forum.tests.common import KARMA, TestForumCommon


class TestForumPost(TestForumCommon):

    def test_get_related_posts(self):
        """Test the method returns 5 related posts based on tag similarity."""
        # Create forum posts and associate them tags
        forum_tags = self.env['forum.tag'].create([{
                'name': f'tag_{i}',
                'forum_id': self.forum.id,
            }
            for i in range(10)])
        forum_posts = self.env['forum.post'].create([{
                    'content': 'A post ...',
                    'forum_id': self.forum.id,
                    'name': 'Post...',
                    'tag_ids': forum_tags[:i],
                    'last_activity_date': fields.Datetime.subtract(fields.Datetime.now(), days=i)
                }
                for i in range(len(forum_tags) + 1)  # 11 posts with 0 to 10 tags
            ])
        # First post (no tags), should return an empty record set
        self.assertFalse(forum_posts[0].tag_ids)
        self.assertEqual(forum_posts[0]._get_related_posts(), self.env['forum.post'])
        # Second post, most similar posts should be the 5 following posts
        self.assertEqual(forum_posts[1]._get_related_posts(), forum_posts[2:7])
        # Last post, most similar posts should be the 5 preceding posts in descending order
        self.assertEqual(forum_posts[-1]._get_related_posts(),
                            forum_posts[len(forum_posts) - 6: -1][::-1])
        # A post with a unique tag, should return an empty record set
        self.assertEqual(self.post.tag_ids.post_ids, self.post)
        self.assertEqual(forum_posts[0]._get_related_posts(), self.env['forum.post'])
        # Related posts with the same list of tags are sorted by last activity date in descending order
        forum_posts.write({'tag_ids': forum_tags.ids})
        self.assertEqual(forum_posts[0]._get_related_posts(), forum_posts[1:6])
        self.assertEqual(forum_posts[-1]._get_related_posts(), forum_posts[:5])

    def test_prevent_multiple_answers_questions_mode(self):
        Post = self.env['forum.post']
        self.forum.mode = 'questions'
        self.user_employee.karma = KARMA['ans']

        Post.with_user(self.user_employee).create({
            'name': "A0",
            'forum_id': self.forum.id,
            'parent_id': self.post.id,
        })
        with self.assertRaises(UserError):
            Post.with_user(self.user_employee).create({
                'name': "A1",
                'forum_id': self.forum.id,
                'parent_id': self.post.id,
            })

        # Try create a post and then change the parent
        answer = Post.with_user(self.user_employee).create({
            'name': "A1",
            'forum_id': self.forum.id,
        })
        with self.assertRaises(UserError):
            answer.parent_id = self.post

    def test_prevent_update_flagged_post(self):
        Post = self.env['forum.post']
        self.post.state = 'flagged'
        self.user_employee.karma = KARMA['ans']

        # Cannot update flagged post
        with self.assertRaises(UserError):
            self.post.with_user(self.user_employee).write({'content': 'Test update'})

        # Cannot post answer on flagged post
        with self.assertRaises(UserError):
            Post.with_user(self.user_employee).create({
                'name': "A0",
                'forum_id': self.forum.id,
                'parent_id': self.post.id,
            })

        # Try create a post and then change the parent
        answer = Post.with_user(self.user_employee).create({
            'name': "A0",
            'forum_id': self.forum.id,
        })
        with self.assertRaises(UserError):
            answer.parent_id = self.post

    def test_validate_flagged_post_with_offensive_answer(self):
        Post = self.env['forum.post']
        self.forum.mode = 'questions'
        # keep enough karma to answer after the offensive penalty
        self.user_employee.karma = KARMA['ans'] - KARMA['gen_ans_flag']
        self.user_portal.karma = KARMA['flag']
        self.user_employee_2.karma = KARMA['moderate']

        offensive_answer = Post.with_user(self.user_employee).create({
            'name': "A0",
            'forum_id': self.forum.id,
            'parent_id': self.post.id,
        })
        offensive_answer.with_user(self.user_employee_2)._mark_as_offensive(
            self.env.ref('website_forum.reason_8').id)
        self.assertFalse(offensive_answer.active)

        # The user can answer again since the offensive answer is archived
        answer = Post.with_user(self.user_employee).create({
            'name': "A1",
            'forum_id': self.forum.id,
            'parent_id': self.post.id,
        })
        answer.with_user(self.user_admin).is_correct = True

        self.post.with_user(self.user_portal)._flag()
        self.assertEqual(self.post.state, 'flagged')

        # Marking the question as legitimate must not restore the offensive answer
        self.post.with_user(self.user_employee_2).validate()
        self.assertEqual(self.post.state, 'active')
        self.assertTrue(answer.active)
        self.assertFalse(offensive_answer.active)
        self.assertEqual(offensive_answer.state, 'offensive')

        offensive_question = Post.create({
            'name': "Q1",
            'forum_id': self.forum.id,
            'child_ids': [Command.create({'name': "A2", 'forum_id': self.forum.id})]
        })
        offensive_question_answer = offensive_question.child_ids
        offensive_question.with_user(self.user_employee_2)._mark_as_offensive(
            self.env.ref('website_forum.reason_8').id)
        self.assertFalse(offensive_question_answer.active)

        # Unarchiving the forum must restore neither offensive posts nor the
        # answers of offensive questions
        self.forum.active = False
        self.forum.active = True
        self.assertTrue(self.post.active)
        self.assertTrue(answer.active)
        self.assertFalse(offensive_answer.active)
        self.assertFalse(offensive_question.active)
        self.assertFalse(offensive_question_answer.active)

    def test_add_seo_rels_to_new_posts_created_by_users(self):
        self.user_employee.karma = KARMA['post']
        post = self.env['forum.post'].with_user(self.user_employee).create({
            'content': 'hello <a href="#">world</a>',
            'forum_id': self.forum.id,
        })

        self.assertEqual(post['content'], '<p>hello <a href="#" rel="nofollow noopener noreferrer ugc">world</a></p>')
