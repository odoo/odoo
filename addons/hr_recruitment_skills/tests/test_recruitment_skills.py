# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import Form, TransactionCase, tagged
from odoo.tests.common import new_test_user


@tagged("recruitment")
class TestRecruitmentSkills(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.t_talent_pool = cls.env["hr.talent.pool"].create({"name": "Test Talent Pool"})
        cls.t_job = cls.env["hr.job"].create({"name": "Test Job"})
        cls.t_skill_type = cls.env["hr.skill.type"].create({"name": "Skills for tests"})
        cls.t_skill_level_1, cls.t_skill_level_2, cls.t_skill_level_3 = cls.env["hr.skill.level"].create(
            [
                {"name": "Level 1", "skill_type_id": cls.t_skill_type.id, "level_progress": 0},
                {"name": "Level 2", "skill_type_id": cls.t_skill_type.id, "level_progress": 50},
                {"name": "Level 3", "skill_type_id": cls.t_skill_type.id, "level_progress": 10},
            ]
        )
        cls.t_skill_1, cls.t_skill_2 = cls.env["hr.skill"].create(
            [
                {"name": "Test Skill 1", "skill_type_id": cls.t_skill_type.id},
                {"name": "Test Skill 2", "skill_type_id": cls.t_skill_type.id},
            ]
        )
        cls.t_applicant = cls.env["hr.applicant"].create(
            {
                "partner_name": "Test Applicant",
                "job_id": cls.t_job.id,
            }
        )

    def test_add_a_skill_to_applicant(self):
        """
        Test that adding a skill to an applicant works
        """
        app_form = Form(self.t_applicant)
        with app_form.current_applicant_skill_ids.new() as skill:
            skill.skill_type_id = self.t_skill_type
            skill.skill_id = self.t_skill_1
            skill.skill_level_id = self.t_skill_level_1
        app_form.save()

        expected_skill = {"id": self.t_skill_1, "level": self.t_skill_level_1, "type": self.t_skill_type}
        app_skill = {
            "id": self.t_applicant.applicant_skill_ids.skill_id,
            "level": self.t_applicant.applicant_skill_ids.skill_level_id,
            "type": self.t_applicant.applicant_skill_ids.skill_type_id,
        }

        self.assertTrue(self.t_applicant.applicant_skill_ids, "The applicant should have a skill")
        self.assertEqual(expected_skill, app_skill, "The applicant should have the test skill")

    def test_add_a_skill_to_applicant_twice(self):
        """
        Assert that adding the same skill twice to an applicant does not work
        """
        app_form = Form(self.t_applicant)
        with app_form.current_applicant_skill_ids.new() as skill:
            skill.skill_type_id = self.t_skill_type
            skill.skill_id = self.t_skill_1
            skill.skill_level_id = self.t_skill_level_1
        app_form.save()
        self.assertEqual(len(self.t_applicant.applicant_skill_ids), 1)

        with app_form.current_applicant_skill_ids.new() as skill:
            skill.skill_type_id = self.t_skill_type
            skill.skill_id = self.t_skill_1
            skill.skill_level_id = self.t_skill_level_1
        app_form.save()
        self.assertEqual(len(self.t_applicant.applicant_skill_ids), 1)

    def test_access_error_on_adding_applicant(self):
        """
        Test that adding an applicant to a talent pool via the wizard
        fails with AccessError if the user lacks read access on Employees.
        """
        # Create a fresh applicant never added to any pool
        new_applicant = self.env["hr.applicant"].create({
            "partner_name": "New Applicant Access Test",
            "job_id": self.t_job.id,
        })

        # Create a restricted user with Recruitment access only
        recruitment_group = self.env.ref('hr_recruitment.group_hr_recruitment_user')
        user_demo = self.env["res.users"].create({
            "name": "Recruitment User",
            "login": "recruitment_user@example.com",
            "email": "recruitment_user@example.com",
            "group_ids": [Command.set(recruitment_group.ids)],
        })

        # No error should be raised.
        self.env["talent.pool.add.applicants"].create({
            "applicant_ids": [(6, 0, [new_applicant.id])],
            "talent_pool_ids": [(6, 0, [self.t_talent_pool.id])],
        }).with_user(user_demo).action_add_applicants_to_pool()

        talent_pool_applicants = self.t_talent_pool.talent_ids
        self.assertEqual(len(talent_pool_applicants), 1)

    def test_one_skill_is_copied_from_applicant_to_talent(self):
        """
        Assert that a skill is copied from the applicant to the talent when the talent is created
        """
        app_form = Form(self.t_applicant)
        with app_form.current_applicant_skill_ids.new() as skill:
            skill.skill_type_id = self.t_skill_type
            skill.skill_id = self.t_skill_1
            skill.skill_level_id = self.t_skill_level_1
        app_form.save()

        talent = (
            self.env["talent.pool.add.applicants"]
            .create({"applicant_ids": self.t_applicant, "talent_pool_ids": self.t_talent_pool})
            ._add_applicants_to_pool()
        )

        expected = {"id": self.t_skill_1, "level": self.t_skill_level_1, "type": self.t_skill_type}
        talent_skill = {
            "id": talent.applicant_skill_ids.skill_id,
            "level": talent.applicant_skill_ids.skill_level_id,
            "type": talent.applicant_skill_ids.skill_type_id,
        }
        app_skill = {
            "id": self.t_applicant.applicant_skill_ids.skill_id,
            "level": self.t_applicant.applicant_skill_ids.skill_level_id,
            "type": self.t_applicant.applicant_skill_ids.skill_type_id,
        }
        self.assertEqual(expected, talent_skill, f"The talent should have the following skill: ${talent_skill}")
        self.assertEqual(app_skill, talent_skill, "The skill from the applicant should have been copied to the talent")

    def test_multi_skill_is_copied_from_applicant_to_talent(self):
        """
        Assert that multiple skills are copied from the applicant to the talent when the talent is created
        """
        skills = [self.t_skill_1, self.t_skill_2]
        app_form = Form(self.t_applicant)
        for skill in skills:
            with app_form.current_applicant_skill_ids.new() as new_skill:
                new_skill.skill_type_id = self.t_skill_type
                new_skill.skill_id = skill
                new_skill.skill_level_id = self.t_skill_level_1
        app_form.save()

        talent = (
            self.env["talent.pool.add.applicants"]
            .create({"applicant_ids": self.t_applicant, "talent_pool_ids": self.t_talent_pool})
            ._add_applicants_to_pool()
        )

        expected = [
            {"id": self.t_skill_1, "level": self.t_skill_level_1, "type": self.t_skill_type},
            {"id": self.t_skill_2, "level": self.t_skill_level_1, "type": self.t_skill_type},
        ]
        talent_skill = [
            {
                "id": skill.skill_id,
                "level": skill.skill_level_id,
                "type": skill.skill_type_id,
            }
            for skill in talent.applicant_skill_ids
        ]
        app_skill = [
            {
                "id": skill.skill_id,
                "level": skill.skill_level_id,
                "type": skill.skill_type_id,
            }
            for skill in self.t_applicant.applicant_skill_ids
        ]
        self.assertCountEqual(expected, talent_skill, f"The talent should have the following skills: ${talent_skill}")
        self.assertCountEqual(
            app_skill, talent_skill, "The skills from the applicant should have been copied to the talent"
        )

    def test_add_skill_to_applicant_with_talent_without_skill(self):
        """
        Verify one-way skill synchronization between an applicant its linked talent.

        This test ensures that when a skill is added on an applicant, the same skill is also added or updated on the talent.
        In this test the skill does not exist on the talent prior to adding it to the applicant.
        """
        app_form = Form(self.t_applicant)

        talent = (
            self.env["talent.pool.add.applicants"]
            .create({"applicant_ids": self.t_applicant, "talent_pool_ids": self.t_talent_pool})
            ._add_applicants_to_pool()
        )

        with app_form.current_applicant_skill_ids.new() as skill:
            skill.skill_type_id = self.t_skill_type
            skill.skill_id = self.t_skill_1
            skill.skill_level_id = self.t_skill_level_1

        app_form.save()

        expected = {"id": self.t_skill_1, "level": self.t_skill_level_1, "type": self.t_skill_type}
        talent_skill = {
            "id": talent.applicant_skill_ids.skill_id,
            "level": talent.applicant_skill_ids.skill_level_id,
            "type": talent.applicant_skill_ids.skill_type_id,
        }
        app_skill = {
            "id": self.t_applicant.applicant_skill_ids.skill_id,
            "level": self.t_applicant.applicant_skill_ids.skill_level_id,
            "type": self.t_applicant.applicant_skill_ids.skill_type_id,
        }
        self.assertEqual(expected, talent_skill, f"The talent should have the following skill: ${talent_skill}")
        self.assertEqual(
            app_skill,
            talent_skill,
            "After adding a skill to the applicant, the talent and the applicant should have the same skill",
        )

    def test_add_skill_to_applicant_with_talent_with_skill(self):
        """
        Verify one-way skill synchronization between an applicant its linked talent.

        This test ensures that when a skill is added on an applicant, the same skill is also added or updated on the talent.
        In this test the skill exists on the talent prior to adding it to the applicant.
        """
        app_form = Form(self.t_applicant)

        talent = (
            self.env["talent.pool.add.applicants"]
            .create({"applicant_ids": self.t_applicant, "talent_pool_ids": self.t_talent_pool})
            ._add_applicants_to_pool()
        )
        with Form(talent) as talent_form:
            with talent_form.current_applicant_skill_ids.new() as skill:
                skill.skill_type_id = self.t_skill_type
                skill.skill_id = self.t_skill_1
                skill.skill_level_id = self.t_skill_level_1

        with app_form.current_applicant_skill_ids.new() as skill:
            skill.skill_type_id = self.t_skill_type
            skill.skill_id = self.t_skill_1
            skill.skill_level_id = self.t_skill_level_1

        app_form.save()

        expected = {"id": self.t_skill_1, "level": self.t_skill_level_1, "type": self.t_skill_type}
        talent_skill = {
            "id": talent.applicant_skill_ids.skill_id,
            "level": talent.applicant_skill_ids.skill_level_id,
            "type": talent.applicant_skill_ids.skill_type_id,
        }
        app_skill = {
            "id": self.t_applicant.applicant_skill_ids.skill_id,
            "level": self.t_applicant.applicant_skill_ids.skill_level_id,
            "type": self.t_applicant.applicant_skill_ids.skill_type_id,
        }
        self.assertEqual(expected, talent_skill, f"The talent should have the following skill: ${talent_skill}")
        self.assertEqual(
            app_skill,
            talent_skill,
            "After adding a skill to the applicant that already existed on the talent, the talent and the applicant should have the same skill",
        )

    def test_update_skill_on_applicant_with_talent_without_skill(self):
        """
        Verify one-way skill synchronization between an applicant its linked talent.

        This test ensures that when a skill is updated on an applicant, the same skill is also added or updated on the talent.
        In this test the skill does not exist on the talent prior to updating it to the applicant.
        """
        app_form = Form(self.t_applicant)
        with app_form.current_applicant_skill_ids.new() as skill:
            skill.skill_type_id = self.t_skill_type
            skill.skill_id = self.t_skill_1
            skill.skill_level_id = self.t_skill_level_1
        app_form.save()

        talent = (
            self.env["talent.pool.add.applicants"]
            .create({"applicant_ids": self.t_applicant, "talent_pool_ids": self.t_talent_pool})
            ._add_applicants_to_pool()
        )
        with Form(talent) as talent_form:
            talent_form.current_applicant_skill_ids.remove(0)

        with app_form.current_applicant_skill_ids.edit(0) as skill:
            skill.skill_type_id = self.t_skill_type
            skill.skill_id = self.t_skill_1
            skill.skill_level_id = self.t_skill_level_2
        app_form.save()

        expected = {"id": self.t_skill_1, "level": self.t_skill_level_2, "type": self.t_skill_type}
        talent_skill = {
            "id": talent.applicant_skill_ids.skill_id,
            "level": talent.applicant_skill_ids.skill_level_id,
            "type": talent.applicant_skill_ids.skill_type_id,
        }
        app_skill = {
            "id": self.t_applicant.applicant_skill_ids.skill_id,
            "level": self.t_applicant.applicant_skill_ids.skill_level_id,
            "type": self.t_applicant.applicant_skill_ids.skill_type_id,
        }
        self.assertEqual(expected, talent_skill, f"The talent should have the following skill: ${talent_skill}")
        self.assertEqual(
            app_skill,
            talent_skill,
            "After updating a skill on the applicant, the talent and the applicant should have the same skill",
        )

    def test_update_skill_on_applicant_with_talent_with_skill(self):
        """
        Verify one-way skill synchronization between an applicant its linked talent.

        This test ensures that when a skill is updated on an applicant, the same skill is also added or updated on the talent.
        In this test the skill exists on the talent prior to updating it to the applicant.
        """
        app_form = Form(self.t_applicant)
        with app_form.current_applicant_skill_ids.new() as skill:
            skill.skill_type_id = self.t_skill_type
            skill.skill_id = self.t_skill_1
            skill.skill_level_id = self.t_skill_level_1
        app_form.save()

        talent = (
            self.env["talent.pool.add.applicants"]
            .create({"applicant_ids": self.t_applicant, "talent_pool_ids": self.t_talent_pool})
            ._add_applicants_to_pool()
        )

        with app_form.current_applicant_skill_ids.edit(0) as skill:
            skill.skill_type_id = self.t_skill_type
            skill.skill_id = self.t_skill_1
            skill.skill_level_id = self.t_skill_level_2
        app_form.save()

        expected = {"id": self.t_skill_1, "level": self.t_skill_level_2, "type": self.t_skill_type}
        talent_skill = {
            "id": talent.applicant_skill_ids.skill_id,
            "level": talent.applicant_skill_ids.skill_level_id,
            "type": talent.applicant_skill_ids.skill_type_id,
        }
        app_skill = {
            "id": self.t_applicant.applicant_skill_ids.skill_id,
            "level": self.t_applicant.applicant_skill_ids.skill_level_id,
            "type": self.t_applicant.applicant_skill_ids.skill_type_id,
        }
        self.assertEqual(expected, talent_skill, f"The talent should have the following skill: ${talent_skill}")
        self.assertEqual(
            app_skill,
            talent_skill,
            "After updating a skill on the applicant that already existed on the talent, the talent and the applicant should have the same skill",
        )

    def test_delete_skill_on_applicant_with_talent_without_skill(self):
        """
        Verify one-way skill synchronization between an applicant its linked talent.

        This test ensures that when a skill is deleted on an applicant, the same skill is also deleted on the talent.
        In this test the skill does not exist on the talent prior to deleting it on the applicant.
        """
        app_form = Form(self.t_applicant)
        with app_form.current_applicant_skill_ids.new() as skill:
            skill.skill_type_id = self.t_skill_type
            skill.skill_id = self.t_skill_1
            skill.skill_level_id = self.t_skill_level_1
        app_form.save()

        talent = (
            self.env["talent.pool.add.applicants"]
            .create({"applicant_ids": self.t_applicant, "talent_pool_ids": self.t_talent_pool})
            ._add_applicants_to_pool()
        )
        with Form(talent) as talent_form:
            talent_form.current_applicant_skill_ids.remove(0)

        app_form.current_applicant_skill_ids.remove(0)

        app_form.save()

        self.assertFalse(self.t_applicant.applicant_skill_ids, "The applicant should not have any skills")
        self.assertFalse(
            talent.applicant_skill_ids,
            "The talent should not have any skills",
        )

    def test_delete_skill_on_applicant_with_talent_with_skill(self):
        """
        Verify one-way skill synchronization between an applicant its linked talent.

        This test ensures that when a skill is deleted on an applicant, the same skill is also deleted on the talent.
        In this test the skill exists on the talent prior to deleting it on the applicant.
        """
        app_form = Form(self.t_applicant)
        with app_form.current_applicant_skill_ids.new() as skill:
            skill.skill_type_id = self.t_skill_type
            skill.skill_id = self.t_skill_1
            skill.skill_level_id = self.t_skill_level_1
        app_form.save()

        talent = (
            self.env["talent.pool.add.applicants"]
            .create({"applicant_ids": self.t_applicant, "talent_pool_ids": self.t_talent_pool})
            ._add_applicants_to_pool()
        )

        app_form.current_applicant_skill_ids.remove(0)

        app_form.save()

        self.assertFalse(self.t_applicant.applicant_skill_ids, "The applicant should not have any skills")
        self.assertFalse(
            talent.applicant_skill_ids,
            "The talent should not have any skills after removing the skill from the applicant",
        )

    def test_adding_a_skill_on_a_talent_does_not_affect_applicants(self):
        """
        Verify one-way skill synchronization between an applicant its linked talent.

        This test ensures that when a skill is added on a talent, the linked applicants are unaffected.
        """
        talent = (
            self.env["talent.pool.add.applicants"]
            .create({"applicant_ids": self.t_applicant, "talent_pool_ids": self.t_talent_pool})
            ._add_applicants_to_pool()
        )
        talent_form = Form(talent)
        with talent_form.current_applicant_skill_ids.new() as skill:
            skill.skill_type_id = self.t_skill_type
            skill.skill_id = self.t_skill_1
            skill.skill_level_id = self.t_skill_level_1
        talent_form.save()

        expected_talent = {"id": self.t_skill_1, "level": self.t_skill_level_1, "type": self.t_skill_type}

        talent_skill = {
            "id": talent.applicant_skill_ids.skill_id,
            "level": talent.applicant_skill_ids.skill_level_id,
            "type": talent.applicant_skill_ids.skill_type_id,
        }

        self.assertFalse(self.t_applicant.applicant_skill_ids, "The applicant should not have any skills")
        self.assertEqual(expected_talent, talent_skill, f"The talent should have the following skill: {talent_skill}")
        return

    def test_updating_a_skill_on_a_talent_does_not_affect_applicants(self):
        """
        Verify one-way skill synchronization between an applicant its linked talent.

        This test ensures that when a skill is updated on a talent, the linked applicants are unaffected.
        """
        app_form = Form(self.t_applicant)
        with app_form.current_applicant_skill_ids.new() as skill:
            skill.skill_type_id = self.t_skill_type
            skill.skill_id = self.t_skill_1
            skill.skill_level_id = self.t_skill_level_1
        app_form.save()

        talent = (
            self.env["talent.pool.add.applicants"]
            .create({"applicant_ids": self.t_applicant, "talent_pool_ids": self.t_talent_pool})
            ._add_applicants_to_pool()
        )
        talent_form = Form(talent)
        with talent_form.current_applicant_skill_ids.edit(0) as skill:
            skill.skill_type_id = self.t_skill_type
            skill.skill_id = self.t_skill_1
            skill.skill_level_id = self.t_skill_level_2
        talent_form.save()

        expected_app = {"id": self.t_skill_1, "level": self.t_skill_level_1, "type": self.t_skill_type}
        expected_talent = {"id": self.t_skill_1, "level": self.t_skill_level_2, "type": self.t_skill_type}

        talent_skill = {
            "id": talent.applicant_skill_ids.skill_id,
            "level": talent.applicant_skill_ids.skill_level_id,
            "type": talent.applicant_skill_ids.skill_type_id,
        }
        app_skill = {
            "id": self.t_applicant.applicant_skill_ids.skill_id,
            "level": self.t_applicant.applicant_skill_ids.skill_level_id,
            "type": self.t_applicant.applicant_skill_ids.skill_type_id,
        }

        self.assertEqual(expected_app, app_skill, "The skill on the applicant should not have changed")
        self.assertEqual(expected_talent, talent_skill, "The skill on the talent should have updated")

    def test_removing_a_skill_on_a_talent_does_not_affect_applicants(self):
        """
        Verify one-way skill synchronization between an applicant its linked talent.

        This test ensures that when a skill is deleted on a talent, the linked applicants are unaffected.
        """
        app_form = Form(self.t_applicant)
        with app_form.current_applicant_skill_ids.new() as skill:
            skill.skill_type_id = self.t_skill_type
            skill.skill_id = self.t_skill_1
            skill.skill_level_id = self.t_skill_level_1
        app_form.save()

        talent = (
            self.env["talent.pool.add.applicants"]
            .create({"applicant_ids": self.t_applicant, "talent_pool_ids": self.t_talent_pool})
            ._add_applicants_to_pool()
        )
        with Form(talent) as talent_form:
            talent_form.current_applicant_skill_ids.remove(0)

        expected_app = {"id": self.t_skill_1, "level": self.t_skill_level_1, "type": self.t_skill_type}
        app_skill = {
            "id": self.t_applicant.applicant_skill_ids.skill_id,
            "level": self.t_applicant.applicant_skill_ids.skill_level_id,
            "type": self.t_applicant.applicant_skill_ids.skill_type_id,
        }

        self.assertEqual(expected_app, app_skill, f"The applicant should have the expected skill: {expected_app}")
        self.assertFalse(talent.applicant_skill_ids, "The talent should not have any skills")

    def test_move_applicant_to_matching_job(self):
        """
        Test that moving an applicant to a job works
        """
        applicant = self.t_applicant
        first_job = self.env["hr.job"].create({"name": "First Job"})
        second_job = self.env["hr.job"].create({"name": "Second Job"})
        applicant.job_id = first_job

        app_form = Form(self.t_applicant)
        with app_form.current_applicant_skill_ids.new() as applicant_skill:
            applicant_skill.skill_type_id = self.t_skill_type
            applicant_skill.skill_id = self.t_skill_1
            applicant_skill.skill_level_id = self.t_skill_level_1
        app_form.save()

        self.env["hr.job.skill"].create(
            {
                "job_id": second_job.id,
                "skill_id": self.t_skill_1.id,
                "skill_type_id": self.t_skill_type.id,
                "skill_level_id": self.t_skill_level_1.id,
            }
        )

        action = second_job.action_search_matching_applicants()
        domain = action["domain"]
        context = action["context"]
        model = self.env[action["res_model"]]
        applicants = model.with_context(context).search(domain)
        self.assertIn(applicant.id, applicants.ids, "The applicant should be in the matching applicants")
        applicant.with_context(context).action_add_to_job()
        self.assertEqual(applicant.job_id, second_job, "The applicant should be moved to the second job")

    def test_create_employee_from_skilled_applicant(self):
        applicant = self.t_applicant
        applicant.write({
            "applicant_skill_ids": [
                (
                    0,
                    0,
                    {
                        "skill_id": self.t_skill_1.id,
                        "skill_level_id": self.t_skill_level_1.id,
                        "skill_type_id": self.t_skill_type.id,
                    },
                ),
                (
                    0,
                    0,
                    {
                        "skill_id": self.t_skill_2.id,
                        "skill_level_id": self.t_skill_level_3.id,
                        "skill_type_id": self.t_skill_type.id,
                    },
                )
            ]
        })
        applicant.create_employee_from_applicant()
        applicant_skills_name_list = applicant.applicant_skill_ids.mapped(lambda s: (s.skill_id, s.skill_type_id, s.skill_level_id))
        employee_skills_name_list = applicant.employee_id.employee_skill_ids.mapped(lambda s: (s.skill_id, s.skill_type_id, s.skill_level_id))
        self.assertCountEqual(applicant_skills_name_list, employee_skills_name_list)

    def test_interviewer_skills_access(self):
        """
        Test that an interviewer can see the skills of an applicant
        """
        interviewer_user = new_test_user(self.env, 'itw',
            groups='base.group_user,hr_recruitment.group_hr_recruitment_interviewer',
            name='Recruitment Interviewer', email='itw@example.com')

        self.t_job.expected_degree = self.env['hr.recruitment.degree'].create({
            'name': 'Master',
            'score': 0.5,
        })
        self.t_applicant.interviewer_ids = interviewer_user.ids
        # flush to force compute methods when reading fields
        self.env.flush_all()
        matching_skill_ids = self.t_applicant.with_user(interviewer_user).matching_skill_ids
        self.assertEqual(matching_skill_ids, self.t_applicant.matching_skill_ids, "The interviewer should see the skills of the applicant")

    def test_applicant_from_talent_preserve_skills(self):
        """
        Verify that when an applicant is created from a talent pool applicant, the new applicant
        has the same skills as the talent and the talent retains all its skills.
        """
        talent = (
            self.env["talent.pool.add.applicants"]
            .create({"applicant_ids": self.t_applicant, "talent_pool_ids": self.t_talent_pool})
            ._add_applicants_to_pool()
        )
        talent_form = Form(talent)
        with talent_form.current_applicant_skill_ids.new() as skill:
            skill.skill_type_id = self.t_skill_type
            skill.skill_id = self.t_skill_1
            skill.skill_level_id = self.t_skill_level_1
        talent_form.save()

        test_job = self.env["hr.job"].create({"name": "Test Job"})
        applicant = (
            self.env["job.add.applicants"]
            .create({"applicant_ids": talent.ids, "job_ids": test_job})
            ._add_applicants_to_job()
        )

        self.assertEqual(applicant.applicant_skill_ids.skill_type_id, self.t_skill_type)
        self.assertEqual(applicant.applicant_skill_ids.skill_level_id, self.t_skill_level_1)
        self.assertEqual(applicant.applicant_skill_ids.skill_id, self.t_skill_1)

        self.assertEqual(talent.applicant_skill_ids.skill_type_id, applicant.applicant_skill_ids.skill_type_id)
        self.assertEqual(talent.applicant_skill_ids.skill_level_id, applicant.applicant_skill_ids.skill_level_id)
        self.assertEqual(talent.applicant_skill_ids.skill_id, applicant.applicant_skill_ids.skill_id)
