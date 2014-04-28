import openerp.tests

class TestUi(openerp.tests.HttpCase):
    def test_admin(self):
        self.phantom_js("/", "openerp.website.Tour.run('event', 'test')", "openerp.website.Tour.tours.event")

