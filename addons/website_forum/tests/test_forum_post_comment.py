from odoo.tests import tagged

from odoo.addons.website_forum.tests.common import TestForumCommon


@tagged("forum_internals")
class TestWebsiteForumPostComment(TestForumCommon):

    def test_links_in_comments_created_by_users_have_seo_rel_attributes(self):
        body = '<p>Check <a href="https://example.com">this</a> out</p>'
        message = self.env["forum.post.comment"].create(
            {"body": body, "post_id": self.post.id}
        )
        self.assertEqual(
            message.body,
            '<p>Check <a href="https://example.com" rel="nofollow noopener noreferrer ugc">this</a> out</p>',
        )

    def test_links_in_comments_updated_by_users_have_seo_rel_attributes(self):
        message = self.env["forum.post.comment"].create(
            {"body": '<p>No links</p>', "post_id": self.post.id}
        )
        message.write(
            {"body": '<p><a href="https://example.com">click here</a></p>'}
        )
        self.assertEqual(
            message.body,
            '<p><a href="https://example.com" rel="nofollow noopener noreferrer ugc">click here</a></p>',
        )

    def test_links_to_post_website_in_comments_have_no_seo_rel_attributes(self):
        self.forum.website_id = self.env["website"].create(
            {"name": "My Website", "domain": "https://my-website.com"}
        )
        body = '<p><a href="https://my-website.com/shop">click here</a></p>'
        message = (
            self.env["forum.post.comment"]
            .with_context(default_post_id=self.post.id)
            .create({"body": body})
        )
        self.assertEqual(message.body, body)

        other_post = self.env["forum.post"].create({
            "name": "Other Post",
            "forum_id": self.env["forum.forum"].create({"name": "Other Forum"}).id,
        })
        messages = message | self.env["forum.post.comment"].create(
            {"body": "<p>No links</p>", "post_id": other_post.id}
        )
        messages.write({"body": body})
        self.assertEqual(
            message.body,
            '<p><a href="https://my-website.com/shop" rel="nofollow noopener noreferrer ugc">click here</a></p>',
        )
