# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests

@odoo.tests.common.at_install(False)
@odoo.tests.common.post_install(True)
class TestUi(odoo.tests.HttpCase):

    post_install = True
    at_install = False

    def test_01_admin_rte(self):
        self.phantom_js("/web", "odoo.__DEBUG__.services['web_tour.tour'].run('rte')", "odoo.__DEBUG__.services['web_tour.tour'].tours.rte.ready", login='admin')

    def test_02_admin_rte_inline(self):
        self.phantom_js("/web", "odoo.__DEBUG__.services['web_tour.tour'].run('rte_inline')", "odoo.__DEBUG__.services['web_tour.tour'].tours.rte_inline.ready", login='admin')
