import odoo.tests
# Part of Odoo. See LICENSE file for full copyright and licensing details.


@odoo.tests.tagged('post_install', '-at_install')
class TestUi(odoo.tests.HttpCase):

    def test_01_sale_tour(self):
        import unittest; raise unittest.SkipTest("skipWOWL")
        self.start_tour("/web", 'sale_tour', login="admin", step_delay=100)
