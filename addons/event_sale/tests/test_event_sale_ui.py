import odoo.tests
# Part of Odoo. See LICENSE file for full copyright and licensing details.


@odoo.tests.tagged('post_install', '-at_install')
class TestUi(odoo.tests.HttpCase):
    def test_01_event_configurator(self):
        self.start_tour("/web", 'event_configurator_tour', login="admin")
