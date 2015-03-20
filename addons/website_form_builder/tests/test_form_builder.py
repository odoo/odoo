import openerp.tests
@openerp.tests.common.at_install(False)
@openerp.tests.common.post_install(True)
class TestFormBuilder(openerp.tests.HttpCase):
    def test_tour(self):
        self.phantom_js("/", "odoo.__DEBUG__.services['web.Tour'].run('website_form_builder_tour', 'test')", "odoo.__DEBUG__.services['web.Tour'].tours.website_form_builder_tour", login="admin")