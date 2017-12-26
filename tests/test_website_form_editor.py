# Part of Odoo. See LICENSE file for full copyright and licensing details.
# -*- coding: utf-8 -*-

import odoo.tests


@odoo.tests.tagged('post_install','-at_install')
class TestWebsiteFormEditor(odoo.tests.HttpCase):
    def test_tour(self):
        self.phantom_js("/", "odoo.__DEBUG__.services['web_tour.tour'].run('website_form_editor_tour')", "odoo.__DEBUG__.services['web_tour.tour'].tours.website_form_editor_tour.ready", login="admin")
        self.phantom_js("/", "odoo.__DEBUG__.services['web_tour.tour'].run('website_form_editor_tour_submit')", "odoo.__DEBUG__.services['web_tour.tour'].tours.website_form_editor_tour_submit.ready")
        self.phantom_js("/", "odoo.__DEBUG__.services['web_tour.tour'].run('website_form_editor_tour_results')", "odoo.__DEBUG__.services['web_tour.tour'].tours.website_form_editor_tour_results.ready", login="admin")
