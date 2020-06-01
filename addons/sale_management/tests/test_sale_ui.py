import odoo.tests
# Part of Odoo. See LICENSE file for full copyright and licensing details.


@odoo.tests.tagged('post_install', '-at_install')
class TestUi(odoo.tests.HttpCase):

    def test_01_sale_tour(self):
        with self.assertQueryCount(__system__=4184):
            self.start_tour("/web", 'sale_tour', login="admin", step_delay=100)
