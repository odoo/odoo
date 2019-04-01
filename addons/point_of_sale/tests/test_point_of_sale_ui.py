# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests


@odoo.tests.tagged('post_install', '-at_install')
class TestUi(odoo.tests.HttpCase):

    def test_01_point_of_sale_tour(self):
        self.start_tour("/web", 'point_of_sale_tour', login="admin")
