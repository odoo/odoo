# Part of Odoo. See LICENSE file for full copyright and licensing details.
import odoo.tests


@odoo.tests.common.tagged('post_install','-at_install')
class TestUi(odoo.tests.HttpCase):

    def test_01_admin_survey_tour(self):
        access_token = self.env.ref('survey.survey_feedback').access_token
        self.start_tour("/survey/start/%s" % access_token, 'test_survey', login="admin")

    def test_02_demo_survey_tour(self):
        access_token = self.env.ref('survey.survey_feedback').access_token
        self.start_tour("/survey/start/%s" % access_token, 'test_survey', login="demo")

    def test_03_public_survey_tour(self):
        access_token = self.env.ref('survey.survey_feedback').access_token
        self.start_tour("/survey/start/%s" % access_token, 'test_survey')

    def test_04_certification_success_tour(self):
        access_token = self.env.ref('survey.vendor_certification').access_token
        self.start_tour("/survey/start/%s" % access_token, 'test_certification_success', login="demo")

    def test_05_certification_failure_tour(self):
        access_token = self.env.ref('survey.vendor_certification').access_token
        self.start_tour("/survey/start/%s" % access_token, 'test_certification_failure', login="demo")

    def test_06_survey_prefill(self):
        access_token = self.env.ref('survey.survey_feedback').access_token
        self.start_tour("/survey/start/%s" % access_token, 'test_survey_prefill')
