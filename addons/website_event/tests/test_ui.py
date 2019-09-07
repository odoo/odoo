import odoo.tests


@odoo.tests.tagged('post_install', '-at_install')
class TestUi(odoo.tests.HttpCase):
    def test_admin(self):
        self.start_tour("/", 'event', login='admin')
