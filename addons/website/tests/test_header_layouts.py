# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import html as lxml_html

from odoo import tests


@tests.tagged("post_install", "-at_install")
class TestHeaderLayouts(tests.HttpCase):
    def test_content_width_is_marked_on_every_layout(self):
        """ The builder previews the header's content width on the elements
        marked `o_header_content_width`: every layout marks the elements
        printing the width, and not the mobile header's container. """
        website = self.env.ref("base.default_website")
        Website = self.env["website"].with_context(website_id=website.id)
        default = Website.viewref("website.template_header_default")
        full = Website.viewref("website.header_width_full")
        small = Website.viewref("website.header_width_small")
        # The sidebar has no content width (a width of its own).
        layouts = [Website.viewref(f"website.template_header_{layout}") for layout in [
            "default", "hamburger", "stretch", "vertical", "search", "boxed",
            "sales_one", "sales_two", "sales_three", "sales_four",
        ]]
        # Every layout in Full; Regular and Small are other values of the same
        # variable, so the default layout is enough for them.
        cases = [(full | layout, "container-fluid") for layout in layouts]
        cases += [(default, "container"), (small | default, "o_container_small")]
        default.active = False
        for views, width_class in cases:
            with self.subTest(views=views.mapped("key")):
                views.write({"active": True})
                tree = lxml_html.fromstring(self.url_open("/").content)
                views.write({"active": False})
                marked = tree.xpath("//header[@id='top']//*[contains(concat(' ', @class, ' '), ' o_header_content_width ')]")
                self.assertTrue(marked)
                for el in marked:
                    self.assertIn(width_class, el.get("class").split())
                    self.assertFalse(el.xpath("ancestor::*[contains(@class, 'o_header_mobile')]"))
