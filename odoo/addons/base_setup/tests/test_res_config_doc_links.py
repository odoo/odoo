# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from odoo.tests import HttpCase, tagged
from odoo.release import url, version


@tagged('-standard', 'external', 'post_install', '-at_install') # nightly is not a real tag
class TestResConfigDocLinks(HttpCase):
    """
    Parse the 'res_config' view to extract all documentation links and
    check that every links are still valid.
    """

    @classmethod
    def setUpClass(cls):
        """
        Set-up the test environment
        """
        super().setUpClass()
        cls.settings_view = cls.env.ref('base.res_config_settings_view_form')

    def test_01_href_links(self):
        """
        Firs test: check that all documentation links in 'res_config_settings'
        views are not broken.
        """
        links_regex = re.compile(r"<a href=\"(\S+/documentation/\S+)\"")

        for link in self._extract_links_from_settings_view(links_regex, self.settings_view):
            self._check_link(link)

    def test_02_setting_nodes_documentation_links(self):
        links_regex = re.compile(r"<setting .* documentation=\"(\S+)\"")

        checked_links = set()
        for link in self._extract_links_from_settings_view(links_regex, self.settings_view):
            if not link.startswith("http"):
                # Only check links targeting odoo documentation, not external ones.
                if link in checked_links:
                    continue
                self._check_link(
                    f"{url}/documentation/{version if 'alpha' not in version else 'master'}{link}")
                checked_links.add(link)

    def _check_link(self, link):
        """
        Try to open the link and check the response status code
        """
        res = self.url_open(url=link)

        self.assertEqual(
            res.status_code, 200,
            "The following link is broken: '%s'" % (link)
        )

    def _extract_links_from_settings_view(self, links_regex, view):
        """
        Analyse the view to extract documentation links and store them
        in a set.
        Then, parse its children if any.
        """
        # search the documentation links in the current view
        for match in re.finditer(links_regex, view.arch):
            yield match.group(1)

        # and then, search inside children
        for child in view.inherit_children_ids:
            yield from self._extract_links_from_settings_view(links_regex, child)
