from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged

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
