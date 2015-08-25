import openerp.tests
@openerp.tests.common.at_install(False)
@openerp.tests.common.post_install(True)
class TestWebsiteCrm(openerp.tests.HttpCase):
    def test_tour(self):
        self.phantom_js("/", "odoo.__DEBUG__.services['web.Tour'].run('website_crm_tour', 'test')", "odoo.__DEBUG__.services['web.Tour'].tours.website_crm_tour", login="admin")
        self.phantom_js("/", "odoo.__DEBUG__.services['web.Tour'].run('website_crm_tour_results', 'test')", "odoo.__DEBUG__.services['web.Tour'].tours.website_crm_tour_results", login="admin")