import re

from odoo.release import url, version
from odoo.tests import HttpCase, tagged


@tagged("-standard", "external", "post_install", "-at_install")
class TestResConfigDocLinks(HttpCase):
    """Verify that all documentation links in the Settings view are reachable."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.settings_view = cls.env.ref("base.res_config_settings_view_form")

    def test_01_href_links(self):
        """All ``<a href>`` documentation links in the settings views return HTTP 200."""
        links_regex = re.compile(r'<a href="(\S+/documentation/\S+)"')
        for link in self._extract_links_from_settings_view(
            links_regex, self.settings_view
        ):
            self._check_link(link)

    def test_02_setting_nodes_documentation_links(self):
        """All ``documentation=`` attributes in ``<setting>`` nodes return HTTP 200."""
        links_regex = re.compile(r'<setting .* documentation="(\S+)"')
        checked_links = set()
        for link in self._extract_links_from_settings_view(
            links_regex, self.settings_view
        ):
            if not link.startswith("http"):
                if link in checked_links:
                    continue
                self._check_link(
                    f"{url}/documentation/{version if 'alpha' not in version else 'master'}{link}"
                )
                checked_links.add(link)

    def _check_link(self, link):
        res = self.url_open(url=link)
        self.assertEqual(res.status_code, 200, f"Broken documentation link: {link!r}")

    def _extract_links_from_settings_view(self, links_regex, view):
        """Recursively yield all regex matches from a view and its inherited children."""
        yield from (m.group(1) for m in re.finditer(links_regex, view.arch))
        for child in view.inherit_children_ids:
            yield from self._extract_links_from_settings_view(links_regex, child)
