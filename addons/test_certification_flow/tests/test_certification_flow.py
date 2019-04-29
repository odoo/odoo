# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests


@odoo.tests.tagged('post_install', '-at_install')
class TestUi(odoo.tests.HttpCase):

    def test_01_certification_flow_tour(self):
        self.phantom_js("/", "odoo.__DEBUG__.services['web_tour.tour'].run('certification_flow_tour')", "odoo.__DEBUG__.services['web_tour.tour'].tours.certification_flow_tour.ready", login="demo")
