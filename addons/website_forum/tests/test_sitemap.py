# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_forum.tests.common import TestForumCommon
from odoo.tests import tagged


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

        # Simulate post from 2023-05-31
        datetime = '2023-05-31'
        with self.mock_datetime_and_now(datetime):
            self.post.name = "RenameIt"  # update write_date
            self.post._update_last_activity()  # update last_activity_date
            self.answer.content = "I am an answer"  # the question page renders it too

        self.assertEqual(post_lastmod(), datetime)

        # Edit post content the 2024-01-01
        datetime = '2024-01-01'
        with self.mock_datetime_and_now(datetime):
            self.post.content = "I am a bird"  # update write_date

        self.assertEqual(post_lastmod(), datetime)

        # An answer edited later must advance the question: its page renders it.
        datetime = '2024-06-01'
        with self.mock_datetime_and_now(datetime):
            self.answer.content = "I am a newer answer"

        self.assertEqual(post_lastmod(), datetime)
