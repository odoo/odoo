import openerp.tests

@openerp.tests.common.at_install(False)
@openerp.tests.common.post_install(True)
class TestUi(openerp.tests.HttpCase):
    def test_admin(self):
        self.phantom_js("/", "openerp.Tour.run('event_buy_tickets', 'test')", "openerp.Tour.tours.event_buy_tickets")

    def test_demo(self):
        self.phantom_js("/", "openerp.Tour.run('event_buy_tickets', 'test')", "openerp.Tour.tours.event_buy_tickets", login="demo", password="demo");

    def test_public(self):
        self.phantom_js("/", "openerp.Tour.run('event_buy_tickets', 'test')", "openerp.Tour.tours.event_buy_tickets", login=None);

