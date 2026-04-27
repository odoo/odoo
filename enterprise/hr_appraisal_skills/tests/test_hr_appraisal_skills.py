from datetime import date

from odoo.addons.hr_appraisal.tests.test_hr_appraisal import TestHrAppraisal


class TestHrAppraisalSkills(TestHrAppraisal):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create a skill type with a level and a skill, then assign it to the employee
        cls.skill_type = cls.env['hr.skill.type'].create({'name': 'Programming Test'})
        cls.skill_level = cls.env['hr.skill.level'].create({
            'name': 'Intermediate',
            'skill_type_id': cls.skill_type.id,
            'level_progress': 50,
            'default_level': True,
        })
        cls.skill = cls.env['hr.skill'].create({
            'name': 'Python Test',
            'skill_type_id': cls.skill_type.id,
        })
        cls.env['hr.employee.skill'].create({
            'employee_id': cls.hr_employee.id,
            'skill_id': cls.skill.id,
            'skill_type_id': cls.skill_type.id,
            'skill_level_id': cls.skill_level.id,
        })

    def test_cron_appraisal_copies_employee_skills(self):
        """Test that appraisal skills are correctly populated when appraisals are created via the cron job."""
        self.hr_employee.next_appraisal_date = date.today()
        self.env['res.company']._run_employee_appraisal_plans()
        appraisal = self.HrAppraisal.search([
            ('employee_id', '=', self.hr_employee.id),
            ('state', '=', 'pending'),
        ])
        self.assertTrue(appraisal)
        self.assertEqual(len(appraisal.skill_ids), 1)
        self.assertEqual(appraisal.skill_ids.skill_id, self.skill)
