import odoo.tests


class TestWebsiteHrRecruitmentSkillsForm(odoo.tests.HttpCase):
    def test_tour_website_recruitment_skills(self):
        department = self.env['hr.department'].create({'name': 'guru team'})
        self.env['hr.job'].create({
            'name': 'Guru',
            'is_published': True,
            'department_id': department.id,
        })
        self.start_tour(self.env['website'].get_client_action_url('/jobs'), 'website_hr_recruitment_skills_tour_edit_form', login='admin')
        with odoo.tests.RecordCapturer(self.env['hr.applicant']) as capt:
            self.start_tour("/jobs", 'website_hr_recruitment_skills_tour')
        # check result the applicant has a skills attached
        self.assertEqual(len(capt.records), 1)
        self.assertEqual(len(capt.records.applicant_skill_ids), 1)
