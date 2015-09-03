import openerp.tests
@openerp.tests.common.at_install(False)
@openerp.tests.common.post_install(True)
class TestWebsiteHrRecruitmentForm(openerp.tests.HttpCase):
    def test_tour(self):
        self.phantom_js("/", "odoo.__DEBUG__.services['web.Tour'].run('website_hr_recruitment_tour', 'test')", "odoo.__DEBUG__.services['web.Tour'].tours.website_hr_recruitment_tour", login="admin")
        self.phantom_js("/", "odoo.__DEBUG__.services['web.Tour'].run('website_hr_recruitment_tour_results', 'test')", "odoo.__DEBUG__.services['web.Tour'].tours.website_hr_recruitment_tour_results", login="admin")
