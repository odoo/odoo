from lxml.html import fromstring

from odoo.tests import common

from odoo.addons.website.tools import add_seo_rels_to_links, text_from_element


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


class TestTextFromElement(common.TransactionCase):

    def test_text_from_element(self):
        for markup, text in [
            ('<b>Tony</b>, <i>e</i>-<s>commerce</s> <a href="/x">link</a>s!', 'Tony, e-commerce links!'),
            ('<h1>Title</h1><ul><li>One</li><li>Two</li></ul>Line<br/>break', 'Title One Two Line break'),
            ('&nbsp; Lots\n\tof   <span>space</span> ', 'Lots of space'),
            ('To<!-- comment -->ny', 'Tony'),
        ]:
            with self.subTest(markup=markup):
                self.assertEqual(text_from_element(fromstring(f'<div>{markup}</div>')), text)
