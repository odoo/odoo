import openerp.tests

class TestUi(openerp.tests.HttpCase):
    def test_admin(self):
        self.phantom_js("/", "openerp.website.Tour.run('blog', 'test')", "openerp.website.Tour.tours.blog")

