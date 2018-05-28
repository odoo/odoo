import odoo.tests


@odoo.tests.tagged('post_install', '-at_install')
class TestUi(odoo.tests.HttpCase):
    def test_admin(self):
        self.phantom_js("/", "odoo.__DEBUG__.services['web_tour.tour'].run('event')", "odoo.__DEBUG__.services['web_tour.tour'].tours.event.ready", login='admin')
