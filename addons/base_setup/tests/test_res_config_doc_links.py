# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import HttpCase, tagged
import re


@tagged('-standard', 'external', 'post_install', '-at_install') # nightly is not a real tag
class TestResConfigDocLinks(HttpCase):
    """
    Parse the 'res_config' view to extract all documentation links and
    check that every links are still valid.
    """

    def setUp(self):
        """
        Set-up the test environment
        """
        super(TestResConfigDocLinks, self).setUp()
        self.re = re.compile("<a href=\"(\\S+/documentation/\\S+)\"")
        self.links = set()

    def test_01_links(self):
        """
        Firs test: check that all documentation links in 'res_config_settings'
        views are not broken.
        """
        self._parse_view(self.env.ref('base.res_config_settings_view_form'))

        for link in self.links:
            self._check_link(link)

    def _check_link(self, link):
        """
        Try to open the link and check the response status code
        """
        res = self.url_open(url=link)

        self.assertEqual(
            res.status_code, 200,
            "The following link is broken: '%s'" % (link)
        )

    def _parse_view(self, view):
        """
        Analyse the view to extract documentation links and store them
        in a set.
        Then, parse its children if any.
        """

        # search the documentation links in the current view
        for match in re.finditer(self.re, view.arch):
            self.links.add(match.group(1))

        # and then, search inside children
        for child in view.inherit_children_ids:
            self._parse_view(child)
