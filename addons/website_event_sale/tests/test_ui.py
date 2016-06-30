import odoo.tests


@odoo.tests.common.at_install(False)
@odoo.tests.common.post_install(True)
class TestUi(odoo.tests.HttpCase):
    def test_admin(self):
        self.phantom_js("/", "odoo.__DEBUG__.services['web.Tour'].run('event_buy_tickets', 'test')", "odoo.__DEBUG__.services['web.Tour'].tours.event_buy_tickets", login="admin")

    def test_demo(self):
        self.phantom_js("/", "odoo.__DEBUG__.services['web.Tour'].run('event_buy_tickets', 'test')", "odoo.__DEBUG__.services['web.Tour'].tours.event_buy_tickets", login="demo")

    # TO DO - add public test with new address when convert to web.tour format.
