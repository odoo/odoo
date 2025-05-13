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
        message = self.post.message_post(
            body="TestWebsiteSlidesForum",
            message_type="comment",
        )

        # Public channel make the forum visible
        self.assertFalse(self.forum.privacy)
        self.assertEqual(channel.visibility, "public")
        channel.website_published = True
        self.assertEqual(self.forum.visibility, "public")
        self._assert_access(self.user_public, True)
        self._assert_access(self.user_employee, True)

        self.assertEqual(
            self.env["mail.message"]
            .with_user(self.user_employee)
            .search([("body", "ilike", "TestWebsiteSlidesForum")]),
            message,
        )

        # Non-published channel should remove access
        channel.website_published = False
        self._assert_access(self.user_portal, False)

        # Making the forum public should re-give access
        self.forum.privacy = "public"
        self._assert_access(self.user_public, True)

        self.assertEqual(
            self.env["mail.message"]
            .with_user(self.user_employee)
            .search([("body", "ilike", "TestWebsiteSlidesForum")]),
            message,
        )

        # Connected make it visible for portal / internal users
        channel.website_published = True
        self.forum.privacy = False
        channel.visibility = "connected"

        self._assert_access(self.user_public, False)
        self._assert_access(self.user_portal, True)
        self._assert_access(self.user_employee, True)

        self.assertEqual(
            self.env["mail.message"]
            .with_user(self.user_employee)
            .search([("body", "ilike", "TestWebsiteSlidesForum")]),
            message,
        )

        # Even if non-public, if one slide is public and published,
        # then the forum is accessible by the public user
        self.forum.privacy = "private"
        channel.visibility = "public"
        channel.website_published = True

        self._assert_access(self.user_public, True)

        # A channel privacy cannot restrict the access on the forum
        self.forum.privacy = "public"
        channel.visibility = "connected"
        channel.website_published = False

        self._assert_access(self.user_public, True)

        with self.assertRaises(AccessError):
            channel.with_user(self.user_public).name

        # Private forum can be accessed by portal / internal users
        # if one channel is "visibility == 'connected'" and if published
        self.forum.privacy = "private"
        channel.visibility = "connected"
        channel.website_published = True
        self._assert_access(self.user_public, False)
        self._assert_access(self.user_portal, True)
        self._assert_access(self.user_employee, True)

        channel.website_published = False
        self._assert_access(self.user_public, False)
        self._assert_access(self.user_portal, False)
        self._assert_access(self.user_employee, False)

        # Test the case where the users can read the forum but not the channel
        self.forum.privacy = "connected"
        channel.visibility = "members"
        self._assert_access(self.user_public, False)
        self._assert_access(self.user_portal, True)
        self._assert_access(self.user_employee, True)

        for user in (self.user_public, self.user_portal, self.user_employee):
            with self.assertRaises(AccessError):
                channel.with_user(user).name

    def _assert_access(self, user, can_access):
        forum_name = self.forum.name
        post_name = self.post.name
        self.env.invalidate_all()

        if can_access:
            self.assertEqual(self.forum.with_user(user).name, forum_name)
            self.assertEqual(self.post.with_user(user).name, post_name)
            self.assertEqual(self.env["forum.forum"].with_user(user).search(
                [("id", "=", self.forum.id)]), self.forum)
            self.assertEqual(self.env["forum.post"].with_user(user).search(
                [("id", "=", self.post.id)]), self.post)

            self.assertTrue(self.forum.with_user(user).sudo().can_access)

        else:
            with self.assertRaises(AccessError):
                self.forum.with_user(user).name
            with self.assertRaises(AccessError):
                self.post.with_user(user).name

            self.assertFalse(self.env["forum.forum"].with_user(user).search(
                [("id", "=", self.forum.id)]))
            self.assertFalse(self.env["forum.post"].with_user(user).search(
                [("id", "=", self.post.id)]))

            self.assertFalse(self.forum.with_user(user).sudo().can_access)
