import os

import openerp.tests

inject = [
    ("openerp.Tour", os.path.join(os.path.dirname(__file__), '../../web/static/src/js/tour.js')),
    ("openerp.Tour.ShopTest", os.path.join(os.path.dirname(__file__), "../static/src/js/website.tour.event_sale.js")),
]

@openerp.tests.common.at_install(False)
@openerp.tests.common.post_install(True)
class TestUi(openerp.tests.HttpCase):
    def test_admin(self):
        self.phantom_js("/", "openerp.Tour.run('event_buy_tickets', 'test')", "openerp.Tour.tours.event_buy_tickets", inject=inject)

    def test_demo(self):
        self.phantom_js("/", "openerp.Tour.run('event_buy_tickets', 'test')", "openerp.Tour.tours.event_buy_tickets", login="demo", password="demo", inject=inject);

    def test_public(self):
        self.phantom_js("/", "openerp.Tour.run('event_buy_tickets', 'test')", "openerp.Tour.tours.event_buy_tickets", login=None, inject=inject);

