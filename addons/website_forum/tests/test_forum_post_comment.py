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
