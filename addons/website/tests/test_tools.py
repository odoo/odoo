from odoo.tests import common

from odoo.addons.website.tools import add_seo_rels_to_links


class TestWebsiteSeoRels(common.TransactionCase):
    def test_do_not_modify_html_without_links(self):
        html = "<p>Hello world</p>"

        result = add_seo_rels_to_links(html)

        self.assertEqual(result, html)

    def test_do_not_modify_plain_text(self):
        html = "There aren't any tags here."

        result = add_seo_rels_to_links(html)

        self.assertEqual(result, html)

    def test_add_ugc_no_follow_to_link(self):
        html = '<p>Check <a href="https://example.com">this</a> out</p>'

        result = add_seo_rels_to_links(html)

        self.assertEqual(
            result,
            '<p>Check <a href="https://example.com" rel="nofollow noopener noreferrer ugc">this</a> out</p>',
        )

    def test_add_ugc_no_follow_to_links_existing_rel(self):
        html = '<a href="https://example.com" rel="noreferrer">link</a>'

        result = add_seo_rels_to_links(html)

        self.assertEqual(
            result,
            '<a href="https://example.com" rel="nofollow noopener noreferrer ugc">link</a>',
        )

    def test_add_ugc_no_follow_to_links_multiple_links(self):
        html = (
            '<p><a href="https://a.com">A</a></p>'
            '<p><a href="https://b.com" rel="nofollow">B</a></p>'
            '<p><a href="https://c.com">C</a></p>'
        )

        result = add_seo_rels_to_links(html)

        self.assertEqual(result.count("ugc"), 3)
        self.assertEqual(result.count("nofollow"), 3)

    def test_does_not_remove_plain_text(self):
        html = 'Hello <a href="https://odoo.com">link</a> bye'

        result = add_seo_rels_to_links(html)

        self.assertEqual(
            result,
            'Hello <a href="https://odoo.com" rel="nofollow noopener noreferrer ugc">link</a> bye',
        )

    def test_do_not_modify_relative_links(self):
        html = '<p><a href="/shop">Shop</a> <a href="#top">Top</a> <a href="?page=2">Next</a></p>'

        result = add_seo_rels_to_links(html, "https://www.my-website.com")

        self.assertEqual(result, html)

    def test_do_not_modify_links_to_current_website(self):
        html = (
            '<p><a href="https://www.my-website.com/shop">A</a></p>'
            '<p><a href="https://my-website.com/blog">B</a></p>'
            '<p><a href="https://MY-WEBSITE.COM/event">C</a></p>'
            '<p><a href="//my-website.com/forum">D</a></p>'
        )

        result = add_seo_rels_to_links(html, "https://www.my-website.com")

        self.assertEqual(result, html)

    def test_add_ugc_no_follow_to_links_disguised_as_relative(self):
        html = (
            '<p><a href="///other-website.com/page">A</a></p>'
            '<p><a href="/\\other-website.com">B</a></p>'
            '<p><a href=" //other-website.com">C</a></p>'
            '<p><a href="https://my-website.com@other-website.com">D</a></p>'
        )

        result = add_seo_rels_to_links(html, "https://my-website.com")

        self.assertEqual(result.count("nofollow"), 4)

    def test_add_ugc_no_follow_to_malformed_links(self):
        html = '<a href="https://[">link</a>'

        result = add_seo_rels_to_links(html, "https://my-website.com")

        self.assertIn('rel="nofollow noopener noreferrer ugc"', result)

    def test_add_ugc_no_follow_to_links_to_other_websites(self):
        html = (
            '<p><a href="https://other-website.com/my-website.com">A</a></p>'
            '<p><a href="//my-website.com.evil.com">B</a></p>'
            '<p><a href="/shop">C</a></p>'
        )

        result = add_seo_rels_to_links(html, "https://my-website.com")

        self.assertEqual(
            result,
            '<p><a href="https://other-website.com/my-website.com" rel="nofollow noopener noreferrer ugc">A</a></p>'
            '<p><a href="//my-website.com.evil.com" rel="nofollow noopener noreferrer ugc">B</a></p>'
            '<p><a href="/shop">C</a></p>',
        )
