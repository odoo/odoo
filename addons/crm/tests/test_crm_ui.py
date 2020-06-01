# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests


@odoo.tests.tagged('post_install','-at_install')
class TestUi(odoo.tests.HttpCase):

    def test_01_crm_tour(self):
        with self.assertQueryCount(__system__=4893):
            self.start_tour("/web", 'crm_tour', login="admin")
