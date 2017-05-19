# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import odoo.tests


@odoo.tests.common.at_install(False)
@odoo.tests.common.post_install(True)
class TestUi(odoo.tests.HttpCase):
    def test_01_portal_load_tour(self):
        self.phantom_js(
            "/",
            "odoo.__DEBUG__.services['web_tour.tour'].run('portal_load_homepage')",
            "",
            login="portal"
        )

