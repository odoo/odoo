import odoo.tests


@odoo.tests.tagged('post_install', '-at_install')
class TestWebsiteHrRecruitmentSkillsForm(odoo.tests.HttpCase):
    def test_apply_job_with_skills(self):
        """ Test the skills selected on the website form are linked to the applicant.

        The website form itself (adding the skills field in the editor and
        filling it as an applicant) is covered by the steps added on the
        `website_hr_recruitment` tours.
        """
        skill_type = self.env['hr.skill.type'].create({
            'name': 'Programming',
            'skill_ids': [(0, 0, {'name': 'Python'}), (0, 0, {'name': 'JavaScript'})],
            'skill_level_ids': [
                (0, 0, {'name': 'Beginner', 'level_progress': 10}),
                (0, 0, {'name': 'Good', 'level_progress': 50, 'default_level': True}),
                (0, 0, {'name': 'Expert', 'level_progress': 100}),
            ],
        })
        python_skill, js_skill = skill_type.skill_ids
        job = self.env['hr.job'].create({
            'name': 'Developer',
            'is_published': True,
        })

        self.authenticate(None, None)
        response = self.url_open('/website/form/hr.applicant', data={
            'partner_name': 'John Smith',
            'email_from': 'john@smith.com',
            'partner_phone': '118.218',
            'job_id': job.id,
            'skill_ids': f'{python_skill.id},{js_skill.id}',
        })
        applicant = self.env['hr.applicant'].browse(response.json().get('id'))
        self.assertTrue(applicant.exists())
        self.assertEqual(applicant.applicant_skill_ids.skill_id, python_skill + js_skill)
        self.assertEqual(
            applicant.applicant_skill_ids.skill_level_id,
            skill_type.skill_level_ids.filtered('default_level'),
            "The default level of the skill type should be set on the applicant skills",
        )
