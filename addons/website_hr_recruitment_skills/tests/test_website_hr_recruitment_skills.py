import odoo.tests


@odoo.tests.tagged('post_install', '-at_install')
class TestWebsiteHrRecruitmentSkillsForm(odoo.tests.HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.skill_type = cls.env['hr.skill.type'].create({
            'name': 'Programming',
            'skill_ids': [
                (0, 0, {'name': 'Python', 'sequence': 1}),
                (0, 0, {'name': 'JavaScript', 'sequence': 2}),
            ],
            'skill_level_ids': [
                (0, 0, {'name': 'Beginner', 'level_progress': 10}),
                (0, 0, {'name': 'Good', 'level_progress': 50, 'default_level': True}),
            ],
        })
        cls.skill_a, cls.skill_b = cls.skill_type.skill_ids
        cls.job = cls.env['hr.job'].create({'name': 'Developer', 'is_published': True})

    def _apply(self, **values):
        """ Post an application on the published job as a public visitor. """
        self.authenticate(None, None)
        return self.url_open('/website/form/hr.applicant', data={
            'partner_name': 'John Smith',
            'email_from': 'john@smith.com',
            'partner_phone': '118.218',
            'job_id': self.job.id,
            **values,
        })

    def _applicant(self, response):
        return self.env['hr.applicant'].browse(response.json().get('id'))

    def test_apply_job_with_skills(self):
        """ The skills selected on the website form are linked to the applicant.

        The form itself (adding the skills field in the editor and filling it as
        an applicant) is covered by the steps patched onto the
        `website_hr_recruitment` tours.
        """
        applicant = self._applicant(self._apply(
            skill_ids=f'{self.skill_a.id},{self.skill_b.id}',
        ))
        self.assertEqual(applicant.applicant_skill_ids.skill_id, self.skill_a + self.skill_b)
        self.assertEqual(
            applicant.applicant_skill_ids.skill_level_id,
            self.skill_type.skill_level_ids.filtered('default_level'),
            "The default level of the skill type should be set on the applicant skills",
        )

    def test_duplicate_skill_ids_do_not_lose_the_application(self):
        """ One active skill per skill_id is enforced by hr.individual.skill.mixin.

        Two rows for the same skill raise, and that rollback takes the applicant
        record with it, so duplicates have to be dropped before the insert.
        """
        applicant = self._applicant(self._apply(
            skill_ids=f'{self.skill_a.id},{self.skill_a.id}',
        ))
        self.assertTrue(applicant.exists(), "the application must survive a duplicated checkbox")
        self.assertEqual(applicant.applicant_skill_ids.skill_id, self.skill_a)

    def test_a_failed_submission_still_reports_its_error(self):
        """ super() returns {'error_fields': ...} rather than an id on failure.

        Reading ['id'] unconditionally turned a clean validation response into a
        500 whenever skills were part of the submission.
        """
        response = self._apply(job_id='not-an-id', skill_ids=str(self.skill_a.id))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertNotIn('id', payload)
        self.assertTrue(payload.get('error') or payload.get('error_fields'), payload)
