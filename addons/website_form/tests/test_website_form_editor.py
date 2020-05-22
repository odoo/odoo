# Part of Odoo. See LICENSE file for full copyright and licensing details.
# -*- coding: utf-8 -*-

import odoo.tests


@odoo.tests.tagged('post_install','-at_install')
class TestWebsiteFormEditor(odoo.tests.HttpCase):
    def test_tour(self):
        with self.assertQueryCount(__system__=2209):
            self.start_tour("/", 'website_form_editor_tour', login="admin")
        with self.assertQueryCount(__system__=448):
            self.start_tour("/", 'website_form_editor_tour_submit')
        with self.assertQueryCount(__system__=1538):
            self.start_tour("/", 'website_form_editor_tour_results', login="admin")
