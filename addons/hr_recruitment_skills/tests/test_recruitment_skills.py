from datetime import date

from dateutil.relativedelta import relativedelta

from odoo import Command
from odoo.tests import Form, TransactionCase, tagged
from odoo.tests.common import new_test_user


@tagged("recruitment")
class TestRecruitmentSkills(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.t_talent_pool = cls.env["hr.talent.pool"].create(
            {"name": "Test Talent Pool"}
        )
        cls.t_job = cls.env["hr.job"].create({"name": "Test Job"})
        cls.t_skill_type = cls.env["hr.skill.type"].create({"name": "Skills for tests"})
        cls.t_skill_level_1, cls.t_skill_level_2, cls.t_skill_level_3 = cls.env[
            "hr.skill.level"
        ].create(
            [
                {
                    "name": "Level 1",
                    "skill_type_id": cls.t_skill_type.id,
                    "level_progress": 0,
                },
                {
                    "name": "Level 2",
                    "skill_type_id": cls.t_skill_type.id,
                    "level_progress": 50,
                },
                {
                    "name": "Level 3",
                    "skill_type_id": cls.t_skill_type.id,
                    "level_progress": 10,
                },
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

    def test_matching_score_zero_total_no_div_error(self):
        self.t_job.write(
            {
                "job_skill_ids": [
                    Command.create(
                        {
                            "skill_type_id": self.t_skill_type.id,
                            "skill_id": self.t_skill_1.id,
                            "skill_level_id": self.t_skill_level_1.id,
                        }
                    )
                ],
            }
        )
        score = self.t_job.with_context(
            active_applicant_id=self.t_applicant.id
        ).applicant_matching_score
        self.assertEqual(score, 0)

    def test_add_a_skill_to_applicant(self):
        app_form = Form(self.t_applicant)
        with app_form.current_applicant_skill_ids.new() as skill:
            skill.skill_type_id = self.t_skill_type
            skill.skill_id = self.t_skill_1
            skill.skill_level_id = self.t_skill_level_1
        app_form.save()

        expected_skill = {
            "id": self.t_skill_1,
            "level": self.t_skill_level_1,
            "type": self.t_skill_type,
        }
        app_skill = {
            "id": self.t_applicant.applicant_skill_ids.skill_id,
            "level": self.t_applicant.applicant_skill_ids.skill_level_id,
            "type": self.t_applicant.applicant_skill_ids.skill_type_id,
        }

        self.assertTrue(
            self.t_applicant.applicant_skill_ids, "The applicant should have a skill"
        )
        self.assertEqual(
            expected_skill, app_skill, "The applicant should have the test skill"
        )

    def test_add_a_skill_to_applicant_twice(self):
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
        new_applicant = self.env["hr.applicant"].create(
            {
                "partner_name": "New Applicant Access Test",
                "job_id": self.t_job.id,
            }
        )

        recruitment_group = self.env.ref("hr_recruitment.group_hr_recruitment_user")
        user_demo = self.env["res.users"].create(
            {
                "name": "Recruitment User",
                "login": "recruitment_user@example.com",
                "email": "recruitment_user@example.com",
                "group_ids": [Command.set(recruitment_group.ids)],
            }
        )

        self.env["talent.pool.add.applicants"].create(
            {
                "applicant_ids": [(6, 0, [new_applicant.id])],
                "talent_pool_ids": [(6, 0, [self.t_talent_pool.id])],
            }
        ).with_user(user_demo).action_add_applicants_to_pool()

        talent_pool_applicants = self.t_talent_pool.talent_ids
        self.assertEqual(len(talent_pool_applicants), 1)

    def test_one_skill_is_copied_from_applicant_to_talent(self):
        app_form = Form(self.t_applicant)
        with app_form.current_applicant_skill_ids.new() as skill:
            skill.skill_type_id = self.t_skill_type
            skill.skill_id = self.t_skill_1
            skill.skill_level_id = self.t_skill_level_1
        app_form.save()

        talent = (
            self.env["talent.pool.add.applicants"]
            .create(
                {
                    "applicant_ids": self.t_applicant,
                    "talent_pool_ids": self.t_talent_pool,
                }
            )
            ._add_applicants_to_pool()
        )

        expected = {
            "id": self.t_skill_1,
            "level": self.t_skill_level_1,
            "type": self.t_skill_type,
        }
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
        self.assertEqual(
            expected,
            talent_skill,
            f"The talent should have the following skill: ${talent_skill}",
        )
        self.assertEqual(
            app_skill,
            talent_skill,
            "The skill from the applicant should have been copied to the talent",
        )

    def test_multi_skill_is_copied_from_applicant_to_talent(self):
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
            .create(
                {
                    "applicant_ids": self.t_applicant,
                    "talent_pool_ids": self.t_talent_pool,
                }
            )
            ._add_applicants_to_pool()
        )

        expected = [
            {
                "id": self.t_skill_1,
                "level": self.t_skill_level_1,
                "type": self.t_skill_type,
            },
            {
                "id": self.t_skill_2,
                "level": self.t_skill_level_1,
                "type": self.t_skill_type,
            },
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
        self.assertCountEqual(
            expected,
            talent_skill,
            f"The talent should have the following skills: ${talent_skill}",
        )
        self.assertCountEqual(
            app_skill,
            talent_skill,
            "The skills from the applicant should have been copied to the talent",
        )

    def test_add_skill_to_applicant_with_talent_without_skill(self):
        app_form = Form(self.t_applicant)

        talent = (
            self.env["talent.pool.add.applicants"]
            .create(
                {
                    "applicant_ids": self.t_applicant,
                    "talent_pool_ids": self.t_talent_pool,
                }
            )
            ._add_applicants_to_pool()
        )

        with app_form.current_applicant_skill_ids.new() as skill:
            skill.skill_type_id = self.t_skill_type
            skill.skill_id = self.t_skill_1
            skill.skill_level_id = self.t_skill_level_1

        app_form.save()

        expected = {
            "id": self.t_skill_1,
            "level": self.t_skill_level_1,
            "type": self.t_skill_type,
        }
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
        self.assertEqual(
            expected,
            talent_skill,
            f"The talent should have the following skill: ${talent_skill}",
        )
        self.assertEqual(
            app_skill,
            talent_skill,
            "After adding a skill to the applicant, the talent and the applicant should have the same skill",
        )

    def test_add_skill_to_applicant_with_talent_with_skill(self):
        app_form = Form(self.t_applicant)

        talent = (
            self.env["talent.pool.add.applicants"]
            .create(
                {
                    "applicant_ids": self.t_applicant,
                    "talent_pool_ids": self.t_talent_pool,
                }
            )
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

        expected = {
            "id": self.t_skill_1,
            "level": self.t_skill_level_1,
            "type": self.t_skill_type,
        }
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
        self.assertEqual(
            expected,
            talent_skill,
            f"The talent should have the following skill: ${talent_skill}",
        )
        self.assertEqual(
            app_skill,
            talent_skill,
            "After adding a skill to the applicant that already existed on the talent, the talent and the applicant should have the same skill",
        )

    def test_update_skill_on_applicant_with_talent_without_skill(self):
        app_form = Form(self.t_applicant)
        with app_form.current_applicant_skill_ids.new() as skill:
            skill.skill_type_id = self.t_skill_type
            skill.skill_id = self.t_skill_1
            skill.skill_level_id = self.t_skill_level_1
        app_form.save()

        talent = (
            self.env["talent.pool.add.applicants"]
            .create(
                {
                    "applicant_ids": self.t_applicant,
                    "talent_pool_ids": self.t_talent_pool,
                }
            )
            ._add_applicants_to_pool()
        )
        with Form(talent) as talent_form:
            talent_form.current_applicant_skill_ids.remove(0)

        with app_form.current_applicant_skill_ids.edit(0) as skill:
            skill.skill_type_id = self.t_skill_type
            skill.skill_id = self.t_skill_1
            skill.skill_level_id = self.t_skill_level_2
        app_form.save()

        expected = {
            "id": self.t_skill_1,
            "level": self.t_skill_level_2,
            "type": self.t_skill_type,
        }
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
        self.assertEqual(
            expected,
            talent_skill,
            f"The talent should have the following skill: ${talent_skill}",
        )
        self.assertEqual(
            app_skill,
            talent_skill,
            "After updating a skill on the applicant, the talent and the applicant should have the same skill",
        )

    def test_update_skill_on_applicant_with_talent_with_skill(self):
        app_form = Form(self.t_applicant)
        with app_form.current_applicant_skill_ids.new() as skill:
            skill.skill_type_id = self.t_skill_type
            skill.skill_id = self.t_skill_1
            skill.skill_level_id = self.t_skill_level_1
        app_form.save()

        talent = (
            self.env["talent.pool.add.applicants"]
            .create(
                {
                    "applicant_ids": self.t_applicant,
                    "talent_pool_ids": self.t_talent_pool,
                }
            )
            ._add_applicants_to_pool()
        )

        with app_form.current_applicant_skill_ids.edit(0) as skill:
            skill.skill_type_id = self.t_skill_type
            skill.skill_id = self.t_skill_1
            skill.skill_level_id = self.t_skill_level_2
        app_form.save()

        expected = {
            "id": self.t_skill_1,
            "level": self.t_skill_level_2,
            "type": self.t_skill_type,
        }
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
        self.assertEqual(
            expected,
            talent_skill,
            f"The talent should have the following skill: ${talent_skill}",
        )
        self.assertEqual(
            app_skill,
            talent_skill,
            "After updating a skill on the applicant that already existed on the talent, the talent and the applicant should have the same skill",
        )

    def test_delete_skill_on_applicant_with_talent_without_skill(self):
        app_form = Form(self.t_applicant)
        with app_form.current_applicant_skill_ids.new() as skill:
            skill.skill_type_id = self.t_skill_type
            skill.skill_id = self.t_skill_1
            skill.skill_level_id = self.t_skill_level_1
        app_form.save()

        talent = (
            self.env["talent.pool.add.applicants"]
            .create(
                {
                    "applicant_ids": self.t_applicant,
                    "talent_pool_ids": self.t_talent_pool,
                }
            )
            ._add_applicants_to_pool()
        )
        with Form(talent) as talent_form:
            talent_form.current_applicant_skill_ids.remove(0)

        app_form.current_applicant_skill_ids.remove(0)

        app_form.save()

        self.assertFalse(
            self.t_applicant.applicant_skill_ids,
            "The applicant should not have any skills",
        )
        self.assertFalse(
            talent.applicant_skill_ids,
            "The talent should not have any skills",
        )

    def test_delete_skill_on_applicant_with_talent_with_skill(self):
        app_form = Form(self.t_applicant)
        with app_form.current_applicant_skill_ids.new() as skill:
            skill.skill_type_id = self.t_skill_type
            skill.skill_id = self.t_skill_1
            skill.skill_level_id = self.t_skill_level_1
        app_form.save()

        talent = (
            self.env["talent.pool.add.applicants"]
            .create(
                {
                    "applicant_ids": self.t_applicant,
                    "talent_pool_ids": self.t_talent_pool,
                }
            )
            ._add_applicants_to_pool()
        )

        app_form.current_applicant_skill_ids.remove(0)

        app_form.save()

        self.assertFalse(
            self.t_applicant.applicant_skill_ids,
            "The applicant should not have any skills",
        )
        self.assertFalse(
            talent.applicant_skill_ids,
            "The talent should not have any skills after removing the skill from the applicant",
        )

    def test_adding_a_skill_on_a_talent_does_not_affect_applicants(self):
        talent = (
            self.env["talent.pool.add.applicants"]
            .create(
                {
                    "applicant_ids": self.t_applicant,
                    "talent_pool_ids": self.t_talent_pool,
                }
            )
            ._add_applicants_to_pool()
        )
        talent_form = Form(talent)
        with talent_form.current_applicant_skill_ids.new() as skill:
            skill.skill_type_id = self.t_skill_type
            skill.skill_id = self.t_skill_1
            skill.skill_level_id = self.t_skill_level_1
        talent_form.save()

        expected_talent = {
            "id": self.t_skill_1,
            "level": self.t_skill_level_1,
            "type": self.t_skill_type,
        }

        talent_skill = {
            "id": talent.applicant_skill_ids.skill_id,
            "level": talent.applicant_skill_ids.skill_level_id,
            "type": talent.applicant_skill_ids.skill_type_id,
        }

        self.assertFalse(
            self.t_applicant.applicant_skill_ids,
            "The applicant should not have any skills",
        )
        self.assertEqual(
            expected_talent,
            talent_skill,
            f"The talent should have the following skill: {talent_skill}",
        )

    def test_updating_a_skill_on_a_talent_does_not_affect_applicants(self):
        app_form = Form(self.t_applicant)
        with app_form.current_applicant_skill_ids.new() as skill:
            skill.skill_type_id = self.t_skill_type
            skill.skill_id = self.t_skill_1
            skill.skill_level_id = self.t_skill_level_1
        app_form.save()

        talent = (
            self.env["talent.pool.add.applicants"]
            .create(
                {
                    "applicant_ids": self.t_applicant,
                    "talent_pool_ids": self.t_talent_pool,
                }
            )
            ._add_applicants_to_pool()
        )
        talent_form = Form(talent)
        with talent_form.current_applicant_skill_ids.edit(0) as skill:
            skill.skill_type_id = self.t_skill_type
            skill.skill_id = self.t_skill_1
            skill.skill_level_id = self.t_skill_level_2
        talent_form.save()

        expected_app = {
            "id": self.t_skill_1,
            "level": self.t_skill_level_1,
            "type": self.t_skill_type,
        }
        expected_talent = {
            "id": self.t_skill_1,
            "level": self.t_skill_level_2,
            "type": self.t_skill_type,
        }

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

        self.assertEqual(
            expected_app,
            app_skill,
            "The skill on the applicant should not have changed",
        )
        self.assertEqual(
            expected_talent, talent_skill, "The skill on the talent should have updated"
        )

    def test_removing_a_skill_on_a_talent_does_not_affect_applicants(self):
        app_form = Form(self.t_applicant)
        with app_form.current_applicant_skill_ids.new() as skill:
            skill.skill_type_id = self.t_skill_type
            skill.skill_id = self.t_skill_1
            skill.skill_level_id = self.t_skill_level_1
        app_form.save()

        talent = (
            self.env["talent.pool.add.applicants"]
            .create(
                {
                    "applicant_ids": self.t_applicant,
                    "talent_pool_ids": self.t_talent_pool,
                }
            )
            ._add_applicants_to_pool()
        )
        with Form(talent) as talent_form:
            talent_form.current_applicant_skill_ids.remove(0)

        expected_app = {
            "id": self.t_skill_1,
            "level": self.t_skill_level_1,
            "type": self.t_skill_type,
        }
        app_skill = {
            "id": self.t_applicant.applicant_skill_ids.skill_id,
            "level": self.t_applicant.applicant_skill_ids.skill_level_id,
            "type": self.t_applicant.applicant_skill_ids.skill_type_id,
        }

        self.assertEqual(
            expected_app,
            app_skill,
            f"The applicant should have the expected skill: {expected_app}",
        )
        self.assertFalse(
            talent.applicant_skill_ids, "The talent should not have any skills"
        )

    def test_move_applicant_to_matching_job(self):
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
        self.assertIn(
            applicant.id,
            applicants.ids,
            "The applicant should be in the matching applicants",
        )
        applicant.with_context(context).action_add_to_job()
        self.assertEqual(
            applicant.job_id,
            second_job,
            "The applicant should be moved to the second job",
        )

    def test_create_employee_from_skilled_applicant(self):
        applicant = self.t_applicant
        applicant.write(
            {
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
                    ),
                ]
            }
        )
        applicant.create_employee_from_applicant()
        applicant_skills_name_list = applicant.applicant_skill_ids.mapped(
            lambda s: (s.skill_id, s.skill_type_id, s.skill_level_id)
        )
        employee_skills_name_list = applicant.employee_id.employee_skill_ids.mapped(
            lambda s: (s.skill_id, s.skill_type_id, s.skill_level_id)
        )
        self.assertCountEqual(applicant_skills_name_list, employee_skills_name_list)

    def test_a_new_employee_gets_the_levels_the_applicant_holds_now(self):
        today = date.today()
        self.env["hr.applicant.skill"].create(
            [
                {
                    "applicant_id": self.t_applicant.id,
                    "skill_id": self.t_skill_1.id,
                    "skill_level_id": level.id,
                    "skill_type_id": self.t_skill_type.id,
                    "valid_from": valid_from,
                    "valid_to": valid_to,
                }
                for level, valid_from, valid_to in (
                    (
                        self.t_skill_level_2,
                        today - relativedelta(years=2),
                        today - relativedelta(years=1, days=1),
                    ),
                    (self.t_skill_level_3, today - relativedelta(years=1), False),
                )
            ]
        )
        self.t_applicant.create_employee_from_applicant()

        rows = self.t_applicant.employee_id.employee_skill_ids
        self.assertEqual(rows.skill_level_id, self.t_skill_level_3)
        self.assertEqual(rows.valid_from, today - relativedelta(years=1))

    def test_unlinking_a_pooled_applicant_skill_ends_the_talent_copy(self):
        self.t_applicant.write(
            {
                "current_applicant_skill_ids": [
                    Command.create(
                        {
                            "skill_id": self.t_skill_1.id,
                            "skill_level_id": self.t_skill_level_1.id,
                            "skill_type_id": self.t_skill_type.id,
                        }
                    )
                ]
            }
        )
        talent = (
            self.env["talent.pool.add.applicants"]
            .create(
                {
                    "applicant_ids": self.t_applicant,
                    "talent_pool_ids": self.t_talent_pool,
                }
            )
            ._add_applicants_to_pool()
        )
        self.assertTrue(talent.current_applicant_skill_ids)

        self.t_applicant.write(
            {
                "current_applicant_skill_ids": [
                    Command.unlink(self.t_applicant.applicant_skill_ids.id)
                ]
            }
        )

        self.assertFalse(self.t_applicant.current_applicant_skill_ids)
        self.assertFalse(talent.current_applicant_skill_ids)

    def _job_with_history(self):
        today = date.today()
        job = self.env["hr.job"].create({"name": "Job with history"})
        self.env["hr.job.skill"].create(
            [
                {
                    "job_id": job.id,
                    "skill_id": skill.id,
                    "skill_level_id": level.id,
                    "skill_type_id": self.t_skill_type.id,
                    "valid_from": valid_from,
                    "valid_to": valid_to,
                }
                for skill, level, valid_from, valid_to in (
                    (
                        self.t_skill_1,
                        self.t_skill_level_2,
                        today - relativedelta(years=1),
                        today - relativedelta(months=6),
                    ),
                    (
                        self.t_skill_2,
                        self.t_skill_level_2,
                        today - relativedelta(years=1),
                        today - relativedelta(months=6),
                    ),
                    (
                        self.t_skill_1,
                        self.t_skill_level_3,
                        today - relativedelta(months=6, days=-1),
                        False,
                    ),
                )
            ]
        )
        return job

    def test_a_dropped_requirement_neither_lowers_the_score_nor_goes_missing(self):
        job = self._job_with_history()
        self.t_applicant.write(
            {
                "job_id": job.id,
                "current_applicant_skill_ids": [
                    Command.create(
                        {
                            "skill_id": self.t_skill_1.id,
                            "skill_level_id": self.t_skill_level_3.id,
                            "skill_type_id": self.t_skill_type.id,
                        }
                    )
                ],
            }
        )

        self.assertEqual(self.t_applicant.matching_score, 100)
        self.assertEqual(self.t_applicant.matching_skill_ids, self.t_skill_1)
        self.assertFalse(self.t_applicant.missing_skill_ids)
        self.assertEqual(
            job.with_context(
                active_applicant_id=self.t_applicant.id
            ).applicant_matching_score,
            100,
        )

    def test_matching_applicants_hold_a_skill_the_job_still_asks_for(self):
        job = self._job_with_history()
        holder, former = self.env["hr.applicant"].create(
            [{"partner_name": "Holds skill 1"}, {"partner_name": "Holds skill 2"}]
        )
        for applicant, skill in ((holder, self.t_skill_1), (former, self.t_skill_2)):
            applicant.write(
                {
                    "current_applicant_skill_ids": [
                        Command.create(
                            {
                                "skill_id": skill.id,
                                "skill_level_id": self.t_skill_level_1.id,
                                "skill_type_id": self.t_skill_type.id,
                            }
                        )
                    ]
                }
            )
        action = job.action_search_matching_applicants()
        found = (
            self.env["hr.applicant"]
            .with_context(action["context"])
            .search(action["domain"])
        )
        self.assertIn(holder, found)
        self.assertNotIn(former, found)

    def test_interviewer_skills_access(self):
        interviewer_user = new_test_user(
            self.env,
            "itw",
            groups="base.group_user,hr_recruitment.group_hr_recruitment_interviewer",
            name="Recruitment Interviewer",
            email="itw@example.com",
        )

        self.t_job.expected_degree = self.env["hr.recruitment.degree"].create(
            {
                "name": "Master",
                "score": 0.5,
            }
        )
        self.t_applicant.interviewer_ids = interviewer_user.ids
        self.env.flush_all()
        matching_skill_ids = self.t_applicant.with_user(
            interviewer_user
        ).matching_skill_ids
        self.assertEqual(
            matching_skill_ids,
            self.t_applicant.matching_skill_ids,
            "The interviewer should see the skills of the applicant",
        )

    def test_applicant_from_talent_preserve_skills(self):
        talent = (
            self.env["talent.pool.add.applicants"]
            .create(
                {
                    "applicant_ids": self.t_applicant,
                    "talent_pool_ids": self.t_talent_pool,
                }
            )
            ._add_applicants_to_pool()
        )
        talent_form = Form(talent)
        with talent_form.current_applicant_skill_ids.new() as skill:
            skill.skill_type_id = self.t_skill_type
            skill.skill_id = self.t_skill_1
            skill.skill_level_id = self.t_skill_level_1
        talent_form.save()

        test_job = self.env["hr.job"].create({"name": "Test Job For Transfer"})
        applicant = (
            self.env["job.add.applicants"]
            .create({"applicant_ids": talent.ids, "job_ids": test_job})
            ._add_applicants_to_job()
        )

        self.assertEqual(applicant.applicant_skill_ids.skill_type_id, self.t_skill_type)
        self.assertEqual(
            applicant.applicant_skill_ids.skill_level_id, self.t_skill_level_1
        )
        self.assertEqual(applicant.applicant_skill_ids.skill_id, self.t_skill_1)

        self.assertEqual(
            talent.applicant_skill_ids.skill_type_id,
            applicant.applicant_skill_ids.skill_type_id,
        )
        self.assertEqual(
            talent.applicant_skill_ids.skill_level_id,
            applicant.applicant_skill_ids.skill_level_id,
        )
        self.assertEqual(
            talent.applicant_skill_ids.skill_id, applicant.applicant_skill_ids.skill_id
        )
