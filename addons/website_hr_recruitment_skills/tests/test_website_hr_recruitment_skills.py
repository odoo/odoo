import odoo.tests


class TestWebsiteHrRecruitmentSkillsForm(odoo.tests.HttpCase):
    def test_tour_website_recruitment_skills(self):
        with odoo.tests.RecordCapturer(self.env['hr.applicant']) as capt:
            self.start_tour("/", 'website_hr_recruitment_skills_tour', debug=True)
        # check result
        self.assertEqual(len(capt.records), 1)
        self.assertEqual(len(capt.records.applicant_skill_ids), 1)
