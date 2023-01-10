# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import html

import odoo
import odoo.tests
from odoo.addons.website.tools import MockRequest


@odoo.tests.common.tagged('post_install', '-at_install', 'website_snippets')
class TestSnippets(odoo.tests.HttpCase):

    def test_01_empty_parents_autoremove(self):
        self.start_tour("/?enable_editor=1", "snippet_empty_parent_autoremove", login='admin')

    def test_02_default_shape_gets_palette_colors(self):
        self.start_tour("/?enable_editor=1", "default_shape_gets_palette_colors", login='admin')

    def test_03_snippets_all_drag_and_drop(self):
        with MockRequest(self.env, website=self.env['website'].browse(1)):
            snippets_template = self.env['ir.ui.view'].render_public_asset('website.snippets')
        html_template = html.fromstring(snippets_template)
        data_snippet_els = html_template.xpath("//*[@class='o_panel' and not(contains(@class, 'd-none'))]//*[@data-snippet]")
        blacklist = [
            's_facebook_page',  # avoid call to external services (facebook.com)
            's_map',  # avoid call to maps.google.com
        ]
        snippets_names = ','.join(set(el.attrib['data-snippet'] for el in data_snippet_els if el.attrib['data-snippet'] not in blacklist))
        self.start_tour("/?enable_editor=1&snippets_names=%s" % snippets_names, "snippets_all_drag_and_drop", login='admin', timeout=300)

    def test_04_countdown_preview(self):
        self.start_tour("/?enable_editor=1", "snippet_countdown", login='admin')

    def test_05_snippet_popup_add_remove(self):
        self.start_tour('/?enable_editor=1', 'snippet_popup_add_remove', login='admin')
