import openerp.tests

class TestUi(openerp.tests.HttpCase):
    def test_admin(self):
        self.phantom_js("/", "openerp.website.Tour.run_test('question')", "openerp.website.Tour")

