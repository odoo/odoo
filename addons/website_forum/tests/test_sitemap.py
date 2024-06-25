# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time
from unittest.mock import patch

from odoo.addons.website_forum.tests.common import TestForumCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestWebsiteControllers(TestForumCommon):

    def test_01_forum_sitemap(self):
        website = self.env['website'].browse(1)

        # Simulate post from 2023-05-31
        datetime = '2023-05-31'
        with freeze_time(datetime), patch.object(self.env.cr, 'now', lambda: datetime):
            self.post.name = "RenameIt"  # update write_date
            self.post._update_last_activity()  # update last_activity_date

        locs = website._enumerate_pages(query_string='/forum/%s' % self.env['ir.http']._slug(self.forum))
        self.assertEqual(next(iter(locs))['lastmod'].strftime("%Y-%m-%d"), datetime)

        # Edit post content the 2024-01-01
        datetime = '2024-01-01'
        with freeze_time(datetime), patch.object(self.env.cr, 'now', lambda: datetime):
            self.post.content = "I am a bird"  # update write_date

        locs = website._enumerate_pages(query_string='/forum/%s' % self.env['ir.http']._slug(self.forum))
        self.assertEqual(next(iter(locs))['lastmod'].strftime("%Y-%m-%d"), datetime)
