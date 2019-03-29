import odoo.tests
# Part of Odoo. See LICENSE file for full copyright and licensing details.


@odoo.tests.tagged('post_install', '-at_install')
class TestUi(odoo.tests.HttpCase):
    def test_01_event_configurator(self):
        self.phantom_js("/web", "odoo.__DEBUG__.services['web_tour.tour'].run('event_configurator_tour')", "odoo.__DEBUG__.services['web_tour.tour'].tours.event_configurator_tour.ready", login="admin")
