import odoo.tests


class TestUi(odoo.tests.HttpCase):

    post_install = True
    at_install = False

    def test_admin(self):
        self.phantom_js("/", "odoo.__DEBUG__.services['web_tour.tour'].run('event_buy_tickets')", "odoo.__DEBUG__.services['web_tour.tour'].tours.event_buy_tickets.ready", login="admin")

    def test_demo(self):
        self.phantom_js("/", "odoo.__DEBUG__.services['web_tour.tour'].run('event_buy_tickets')", "odoo.__DEBUG__.services['web_tour.tour'].tours.event_buy_tickets.ready", login="demo")

    # TO DO - add public test with new address when convert to web.tour format.
