# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import html as lxml_html

from odoo import tests


@tests.tagged("post_install", "-at_install")
class TestSetHeaderIcons(tests.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env.ref("base.default_website")

    def test_set_header_icons_refuses_unknown_names_and_icons(self):
        self.website.set_header_icons({
            "unknown": {"icon": "explore"},
            "search": {"icon": 'search" onclick="alert(1)'},
        })
        for icon in ("search:filled", "not_an_icon", None):
            self.website.set_header_icons({"search": {"icon": icon}})
        self.assertEqual(
            self.website._get_header_icon("search"),
            {"icon": "search", "filled": False},
            "The stored icon should be unchanged",
        )

    def test_set_header_icons_accepts_every_icon_of_the_picker(self):
        self.website.set_header_icons({"search": {"icon": "oi_cc-paypal"}})
        self.assertEqual(
            self.website._get_header_icon("search"),
            {"icon": "oi_cc-paypal", "filled": False},
            "Any icon of the picker should be stored",
        )


@tests.tagged("post_install", "-at_install")
class TestHeaderIcons(tests.HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env.ref("base.default_website")

    def _get_header_icons(self, xpath, url="/"):
        tree = lxml_html.fromstring(self.url_open(url).content)
        return {(icon.get("data-icon"), "oi-filled" in icon.classes) for icon in tree.xpath(xpath)}

    def test_the_header_search_icon_is_the_one_stored_on_the_website(self):
        header_icon = "//form[contains(@class, 'o_header_searchbar')]//i[@data-header-icon='search']"
        self.assertEqual(
            self._get_header_icons(header_icon),
            {("search", False)},
            "By default, the header search icon should be the outlined magnifier",
        )

        self.website.set_header_icons({"search": {"icon": "explore", "filled": True}})
        self.assertEqual(
            self._get_header_icons(header_icon),
            {("explore", True)},
            "The header should render the icon stored on the website",
        )

        page_icon = "//form[not(contains(@class, 'o_header_searchbar'))]//i[@data-icon]"
        self.assertEqual(
            self._get_header_icons(page_icon, "/website/search?search=x"),
            {("search", False)},
            "The search bar of the results page should keep the default icon",
        )
        self.assertFalse(
            self._get_header_icons(
                "//form[not(contains(@class, 'o_header_searchbar'))]//i[@data-header-icon]",
                "/website/search?search=x",
            ),
            "Only the header search icon should be replaceable as a header icon",
        )

    def test_the_header_language_icon_is_the_one_stored_on_the_website(self):
        self.website.language_ids |= self.env["res.lang"]._activate_lang("fr_FR")
        self.env.ref("website.header_language_selector_show_icon").active = True
        header_icon = "//header//i[@data-header-icon='language']"
        self.assertEqual(
            self._get_header_icons(header_icon),
            {("translate", False)},
            "By default, the header language icon should be the translate icon",
        )

        self.website.set_header_icons({"language": {"icon": "public"}})
        self.assertEqual(
            self._get_header_icons(header_icon),
            {("public", False)},
            "The header should render the icon stored on the website",
        )
