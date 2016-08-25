import odoo.tests
# Part of Odoo. See LICENSE file for full copyright and licensing details.


class TestUi(odoo.tests.HttpCase):

    post_install = True
    at_install = False

    def test_01_admin_survey_tour(self):
        self.phantom_js("/", "odoo.__DEBUG__.services['web_tour.tour'].run('test_survey')", "odoo.__DEBUG__.services['web_tour.tour'].tours.test_survey.ready", login="admin")

    def test_02_demo_survey_tour(self):
        self.phantom_js("/", "odoo.__DEBUG__.services['web_tour.tour'].run('test_survey')", "odoo.__DEBUG__.services['web_tour.tour'].tours.test_survey.ready", login="demo")

    def test_03_public_survey_tour(self):
        self.phantom_js("/", "odoo.__DEBUG__.services['web_tour.tour'].run('test_survey')", "odoo.__DEBUG__.services['web_tour.tour'].tours.test_survey.ready")
