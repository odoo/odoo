# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_forum.tests.common import KARMA, TestForumCommon
from odoo.tests import tagged
from odoo.tools import SQL


@tagged('post_install', '-at_install')
class TestWebsiteControllers(TestForumCommon):

    def test_01_forum_sitemap(self):
        website = self.env.ref('base.default_website')
        slug = self.env['ir.http']._slug
        forum_url = '/forum/%s' % slug(self.forum)

        def post_lastmod():
            # The forum query also matches sibling URLs (e.g. /forum/<slug>/faq),
            # so target the post's own sitemap entry rather than the first loc.
            post_url = '/forum/%s/%s' % (slug(self.forum), slug(self.post))
            locs = website._enumerate_pages(query_string=forum_url)
            loc = next((l for l in locs if l['loc'] == post_url), None)
            self.assertIsNotNone(loc, "post URL %s missing from the sitemap" % post_url)
            return loc['lastmod'].strftime("%Y-%m-%d")

        # Post the question and its answer before the edits below.
        self.env.cr.execute(SQL(
            "UPDATE forum_post SET create_date = %s WHERE id IN %s",
            '2023-01-01', (self.post.id, self.answer.id),
        ))
        (self.post | self.answer).invalidate_recordset(['create_date'])

        # Simulate post from 2023-05-31
        datetime = '2023-05-31'
        with self.mock_datetime_and_now(datetime):
            self.post.name = "RenameIt"  # update write_date_content
            self.post._update_last_activity()  # update last_activity_date
            self.answer.content = "I am an answer"  # the question page renders it too

        self.assertEqual(post_lastmod(), datetime)

        # Edit post content the 2024-01-01
        datetime = '2024-01-01'
        with self.mock_datetime_and_now(datetime):
            self.post.content = "I am a bird"  # update write_date_content

        self.assertEqual(post_lastmod(), datetime)

        # An answer edited later must advance the question: its page renders it.
        datetime = '2024-06-01'
        with self.mock_datetime_and_now(datetime):
            self.answer.content = "I am a newer answer"

        self.assertEqual(post_lastmod(), datetime)

        # Votes, comments and favourites leave the text of the page unchanged.
        with self.mock_datetime_and_now('2025-01-01'):
            self.post.vote(upvote=True)
            self.answer.vote(upvote=True)
            self.env['forum.post.comment'].create({'post_id': self.answer.id, 'body': "I am a comment"})
            self.post._update_last_activity()  # as posting the comment does
            self.post.user_favourite = True

        self.assertEqual(post_lastmod(), datetime)

        # A new answer advances the question as well.
        datetime = '2025-06-01'
        self.user_employee.karma = KARMA['ans']
        with self.mock_datetime_and_now(datetime):
            self.env['forum.post'].with_user(self.user_employee).create({
                'forum_id': self.forum.id,
                'parent_id': self.post.id,
                'content': "I am another answer",
            })

        self.assertEqual(post_lastmod(), datetime)

    def test_02_forum_sitemap_pending_question(self):
        website = self.env.ref('base.default_website')
        slug = self.env['ir.http']._slug
        post_url = '/forum/%s/%s' % (slug(self.forum), slug(self.post))

        def listed():
            return any(loc['loc'] == post_url for loc in website._enumerate_pages(query_string=post_url))

        self.post.state = 'pending'
        self.assertFalse(listed(), "a pending question is a 404 for visitors")
        self.post.state = 'close'
        self.assertTrue(listed(), "a closed question still renders")
