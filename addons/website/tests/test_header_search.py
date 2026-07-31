# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import html as lxml_html

from odoo import tests


@tests.tagged("post_install", "-at_install")
class TestHeaderSearch(tests.HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env.ref("base.default_website")

    def test_a_scope_whose_module_is_gone_falls_back_to_the_main_search(self):
        self.website.header_search_type = "from_an_uninstalled_module"
        self.assertEqual(
            self.website._get_header_search_scope(),
            {"search_type": "all", "url": "/website/search"},
        )

    def test_zero_suggestions_is_stored(self):
        self.website.set_header_search(limit=0)
        self.assertEqual(self.website.header_search_limit, 0)

    def test_the_configured_scope_is_rendered_in_the_header(self):
        self.website.write({
            "header_search_type": "pages",
            "header_search_order_by": "write_date desc",
            "header_search_limit": 3,
        })
        tree = lxml_html.fromstring(self.url_open("/").content)
        form = tree.xpath("//form[contains(@class, 'o_header_searchbar')]")[0]
        search_input = form.xpath(".//input[contains(@class, 'search-query')]")[0]
        self.assertEqual(
            (
                form.get("action"),
                search_input.get("data-search-type"),
                search_input.get("data-order-by"),
                search_input.get("data-limit"),
            ),
            ("/pages", "pages", "write_date desc", "3"),
        )
