import openerp.tests

class TestUi(openerp.tests.HttpCase):
    def test_admin(self):
        self.phantom_js("/", "openerp.Tour.run('blog', 'test')", "openerp.Tour.tours.blog")

