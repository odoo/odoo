import openerp.tests

@openerp.tests.category('website')
@openerp.tests.at_install(False)
@openerp.tests.post_install(True)
class TestUi(openerp.tests.HttpCase):
    def test_admin(self):
        self.phantom_js("/", "odoo.__DEBUG__.services['web.Tour'].run('event_buy_tickets', 'test')", "odoo.__DEBUG__.services['web.Tour'].tours.event_buy_tickets", login="admin")

    def test_demo(self):
        self.phantom_js("/", "odoo.__DEBUG__.services['web.Tour'].run('event_buy_tickets', 'test')", "odoo.__DEBUG__.services['web.Tour'].tours.event_buy_tickets", login="demo")

    def test_public(self):
        self.phantom_js("/", "odoo.__DEBUG__.services['web.Tour'].run('event_buy_tickets', 'test')", "odoo.__DEBUG__.services['web.Tour'].tours.event_buy_tickets")
