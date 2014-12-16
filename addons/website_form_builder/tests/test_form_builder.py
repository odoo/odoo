import openerp.tests
from openerp import SUPERUSER_ID
@openerp.tests.common.at_install(False)
@openerp.tests.common.post_install(True)
class TestFormBuilder(openerp.tests.HttpCase):
    def test_tour(self):
        self.phantom_js("/", "openerp.Tour.run('website_form_builder_tour', 'test')", "openerp.Tour.tours.website_form_builder_tour", login="admin")