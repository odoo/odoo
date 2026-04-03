# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.http_routing.tests.common import MockRequest
from odoo.addons.website_blog.controllers.main import WebsiteBlog
from odoo.addons.website_blog.tests.common import TestWebsiteBlogCommon


@tagged("post_install", "-at_install")
class TestWebsiteBlogJsonLd(TestWebsiteBlogCommon):
    def test_blog_structured_data(self):
        website = self.env.ref("website.default_website")
        json_ld = self.test_blog._to_structured_data(website)
        markup_data = json_ld._render()
        self.assertEqual(markup_data["@type"], "Blog")
        self.assertEqual(markup_data["name"], self.test_blog.name)
        self.assertEqual(markup_data["url"], f"{website.get_base_url()}{self.test_blog.website_url}")

    def test_blog_post_structured_data(self):
        website = self.env.ref("website.default_website")
        summary_json_ld = self.test_blog_post._to_structured_data_summary(website)[0]._render()
        full_json_ld = self.test_blog_post._to_structured_data(website)[0]._render()
        self.assertEqual(summary_json_ld["@type"], "BlogPosting")
        self.assertEqual(full_json_ld["@type"], "BlogPosting")

        for field in ("description", "dateModified", "inLanguage", "wordCount"):
            self.assertNotIn(field, summary_json_ld)
            self.assertIn(field, full_json_ld)

    def test_listing_structured_data_for_blog_and_index_pages(self):
        website = self.env.ref("website.default_website")
        controller = WebsiteBlog()

        with MockRequest(self.env, website=website):
            blog_listing = controller._prepare_blog_listing_structured_data(
                website,
                self.test_blog,
                self.test_blog_post,
            )[0]._render()
            index_listing = controller._prepare_blog_listing_structured_data(
                website,
                False,
                self.test_blog_post,
            )[-1]._render()
        base_url = website.get_base_url()

        # Blog listing page schema
        self.assertEqual(blog_listing["@type"], "Blog")
        blog_slug = self.env['ir.http']._slug(self.test_blog)
        blog_url = f"{base_url}/blog/{blog_slug}"
        self.assertEqual(blog_listing["@id"], f"{blog_url}/#blog")
        self.assertEqual(blog_listing["url"], f"{blog_url}")
        self.assertEqual(blog_listing["name"], self.test_blog.name)
        self.assertIn("publisher", blog_listing)
        self.assertEqual(blog_listing["publisher"]["@id"], f"{base_url}/#organization")
        # Index listing page schema
        self.assertEqual(index_listing["@type"], "CollectionPage")
        self.assertNotIn("@id", index_listing)
        self.assertNotIn("publisher", index_listing)
        # Nested BlogPosting schema validation
        blog_post_slug = self.env['ir.http']._slug(self.test_blog_post)
        for listing in (blog_listing, index_listing):
            post = listing["hasPart"]
            self.assertEqual(post["@type"], "BlogPosting")
            self.assertEqual(post["headline"], self.test_blog_post.name)
            self.assertEqual(post["url"], f"{blog_url}/{blog_post_slug}")
            self.assertEqual(post["articleSection"], self.test_blog.name)
            self.assertIn("author", post)
            self.assertIn("publisher", post)
            self.assertIn("datePublished", post)
            # Ensure schema graph consistency
            self.assertEqual(post["isPartOf"]["@id"], f"{blog_url}/#blog")
