# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_forum.tests.common import TestForumCommon
from odoo.exceptions import AccessError


class TestWebsiteSlidesForum(TestForumCommon):
    def test_website_slides_forum_access(self):
        channel = self.env["slide.channel"].create(
            {
                "name": "Channel",
                "forum_id": self.forum.id,
            }
        )
        comment = self.env["forum.post.comment"].create(
            {
                "post_id": self.post.id,
                "body": "TestWebsiteSlidesForum",
            }
        )

        # Public channel make the forum visible
        self.assertFalse(self.forum.privacy)
        self.assertEqual(channel.visibility, "public")
        channel.website_published = True
        self.env.invalidate_all()
        self.assertEqual(self.forum.visibility, "public")
        self.assertEqual(self.forum.with_user(self.user_public).name, "TestForum")
        self.assertEqual(self.post.with_user(self.user_public).name, "TestQuestion")
        self.assertEqual(self.post.with_user(self.user_employee).name, "TestQuestion")

        self.assertEqual(
            self.env["forum.post.comment"]
            .with_user(self.user_employee)
            .search([("body", "ilike", "TestWebsiteSlidesForum")]),
            comment,
        )

        # Non-published channel should remove access
        channel.website_published = False
        self.env.invalidate_all()

        with self.assertRaises(AccessError):
            self.forum.with_user(self.user_portal).name

        with self.assertRaises(AccessError):
            self.post.with_user(self.user_portal).name

        # Making the forum public should re-give access
        self.forum.privacy = "public"
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertEqual(
            self.env["forum.forum"]
            .with_user(self.user_public)
            .search([("id", "=", self.forum.id)]),
            self.forum,
        )
        self.assertEqual(self.forum.with_user(self.user_public).name, "TestForum")
        self.assertEqual(self.forum.with_user(self.user_employee).name, "TestForum")
        self.assertEqual(
            self.env["forum.post.comment"]
            .with_user(self.user_employee)
            .search([("body", "ilike", "TestWebsiteSlidesForum")]),
            comment,
        )

        # Connected make it visible for portal / internal users
        channel.website_published = True
        self.forum.privacy = False
        self.env.invalidate_all()
        channel.visibility = "connected"
        with self.assertRaises(AccessError):
            self.post.with_user(self.user_public).name

        self.assertEqual(self.post.with_user(self.user_portal).name, "TestQuestion")
        self.assertEqual(self.post.with_user(self.user_employee).name, "TestQuestion")

        self.assertEqual(
            self.env["forum.post.comment"]
            .with_user(self.user_employee)
            .search([("body", "ilike", "TestWebsiteSlidesForum")]),
            comment,
        )
