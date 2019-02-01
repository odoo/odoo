# Part of Odoo. See LICENSE file for full copyright and licensing details.
import odoo.tests


@odoo.tests.common.tagged('post_install','-at_install')
class TestUi(odoo.tests.HttpCase):

    def test_01_admin_survey_tour(self):
        access_token = self.env.ref('survey.survey_feedback').access_token
        self.phantom_js("/survey/start/%s" % access_token, "odoo.__DEBUG__.services['web_tour.tour'].run('test_survey')", "odoo.__DEBUG__.services['web_tour.tour'].tours.test_survey.ready", login="admin")

    def test_02_demo_survey_tour(self):
        access_token = self.env.ref('survey.survey_feedback').access_token
        self.phantom_js("/survey/start/%s" % access_token, "odoo.__DEBUG__.services['web_tour.tour'].run('test_survey')", "odoo.__DEBUG__.services['web_tour.tour'].tours.test_survey.ready", login="demo")

    def test_03_public_survey_tour(self):
        access_token = self.env.ref('survey.survey_feedback').access_token
        self.phantom_js("/survey/start/%s" % access_token, "odoo.__DEBUG__.services['web_tour.tour'].run('test_survey')", "odoo.__DEBUG__.services['web_tour.tour'].tours.test_survey.ready")

    def test_04_certification_success_tour(self):
        access_token = self.env.ref('survey.vendor_certification').access_token
        self.phantom_js("/survey/start/%s" % access_token, "odoo.__DEBUG__.services['web_tour.tour'].run('test_certification_success')", "odoo.__DEBUG__.services['web_tour.tour'].tours.test_certification_success.ready", login="demo")

    def test_05_certification_failure_tour(self):
        access_token = self.env.ref('survey.vendor_certification').access_token
        self.phantom_js("/survey/start/%s" % access_token, "odoo.__DEBUG__.services['web_tour.tour'].run('test_certification_failure')", "odoo.__DEBUG__.services['web_tour.tour'].tours.test_certification_failure.ready", login="demo")

    def test_06_survey_prefill(self):
        access_token = self.env.ref('survey.survey_feedback').access_token
        self.phantom_js("/survey/start/%s" % access_token, "odoo.__DEBUG__.services['web_tour.tour'].run('test_survey_prefill')", "odoo.__DEBUG__.services['web_tour.tour'].tours.test_survey_prefill.ready")
