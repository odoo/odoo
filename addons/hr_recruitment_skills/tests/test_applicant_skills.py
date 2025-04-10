from datetime import date

from dateutil.relativedelta import relativedelta

from odoo.tests import Form, TransactionCase, tagged


@tagged("recruitment")
class TestApplicantSkills(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = date.today()

        cls.t_job = cls.env["hr.job"].create({"name": "Test Job"})
        cls.t_skill_type, cls.t_cert_type = cls.env["hr.skill.type"].create(
            [{"name": "Skills for tests"}, {"name": "Certification for tests", "is_certification": True}],
        )
        cls.t_skill_level_1, cls.t_skill_level_2, cls.t_skill_level_3, cls.t_cert_level_1, cls.t_cert_level_2 = cls.env[
            "hr.skill.level"
        ].create(
            [
                {"name": "Level 1", "skill_type_id": cls.t_skill_type.id, "level_progress": 34},
                {"name": "Level 2", "skill_type_id": cls.t_skill_type.id, "level_progress": 68},
                {"name": "Level 3", "skill_type_id": cls.t_skill_type.id, "level_progress": 100},
                {"name": "Half Certified", "skill_type_id": cls.t_cert_type.id, "level_progress": 50},
                {"name": "Fully Certified", "skill_type_id": cls.t_cert_type.id, "level_progress": 100},
            ],
        )
        cls.t_skill_1, cls.t_skill_2, cls.t_skill_3, cls.t_cert_1 = cls.env["hr.skill"].create(
            [
                {"name": "Test Skill 1", "skill_type_id": cls.t_skill_type.id},
                {"name": "Test Skill 3", "skill_type_id": cls.t_skill_type.id},
                {"name": "Test Skill 2", "skill_type_id": cls.t_skill_type.id},
                {"name": "Certification 1", "skill_type_id": cls.t_cert_type.id},
            ],
        )
        cls.t_applicant = cls.env["hr.applicant"].create(
            {
                "partner_name": "Test Applicant",
                "job_id": cls.t_job.id,
            },
        )
        cls.t_applicant_skill_3 = cls.env["hr.applicant.skill"].create(
            {
                "applicant_id": cls.t_applicant.id,
                "skill_id": cls.t_skill_2.id,
                "skill_level_id": cls.t_skill_level_1.id,
                "skill_type_id": cls.t_skill_type.id,
                "valid_from": cls.today - relativedelta(months=4),
                "valid_to": cls.today - relativedelta(months=3, days=1),
            },
        )
        (
            cls.t_applicant_skill_1,
            cls.t_applicant_skill_2,
            cls.t_applicant_cert_1,
            cls.t_applicant_cert_2,
        ) = cls.env["hr.applicant.skill"].create(
            [
                {
                    "applicant_id": cls.t_applicant.id,
                    "skill_id": cls.t_skill_1.id,
                    "skill_level_id": cls.t_skill_level_2.id,
                    "skill_type_id": cls.t_skill_type.id,
                    "valid_from": cls.today - relativedelta(months=3),
                    "valid_to": False,
                },
                {
                    "applicant_id": cls.t_applicant.id,
                    "skill_id": cls.t_skill_2.id,
                    "skill_level_id": cls.t_skill_level_2.id,
                    "skill_type_id": cls.t_skill_type.id,
                    "valid_from": cls.today - relativedelta(months=2),
                    "valid_to": False,
                },
                {
                    "applicant_id": cls.t_applicant.id,
                    "skill_id": cls.t_cert_1.id,
                    "skill_level_id": cls.t_cert_level_1.id,
                    "skill_type_id": cls.t_cert_type.id,
                    "valid_from": cls.today - relativedelta(months=4),
                    "valid_to": cls.today + relativedelta(months=8),
                },
                {
                    "applicant_id": cls.t_applicant.id,
                    "skill_id": cls.t_cert_1.id,
                    "skill_level_id": cls.t_cert_level_2.id,
                    "skill_type_id": cls.t_cert_type.id,
                    "valid_from": cls.today - relativedelta(months=3),
                    "valid_to": False,
                },
            ],
        )

    def test_add_skill_1_level_3(self):
        """
        A test that asserts that adding a new skill both creates a new applicant
        skill and also archives the previous applicant skill that has the same skill_id.
        """
        applicant_form = Form(self.t_applicant)
        old_applicant_skills = self.t_applicant.applicant_skill_ids
        with applicant_form.current_applicant_skill_ids.new() as cas:
            cas.skill_type_id = self.t_skill_type
            cas.skill_id = self.t_skill_1
            cas.skill_level_id = self.t_skill_level_3
        applicant_form.save()
        new_skill = self.t_applicant.applicant_skill_ids - old_applicant_skills

        self.assertTrue(new_skill)
        self.assertEqual(len(self.t_applicant.applicant_skill_ids.ids), 6)
        self.assertEqual(new_skill.valid_from, date.today())
        self.assertEqual(self.t_applicant_skill_1.valid_to, date.today() - relativedelta(days=1))

    def test_edit_skill_1_level_2_to_level_3(self):
        """
        A test that asserts that when editing a skill, the skill that
        is being edited is archived and a new skill is created but with different
        valid_from and valid_to from the original.
        """
        applicant_form = Form(self.t_applicant)
        old_applicant_skills = self.t_applicant.applicant_skill_ids
        index = self.t_applicant.current_applicant_skill_ids.ids.index(self.t_applicant_skill_1.id)
        with applicant_form.current_applicant_skill_ids.edit(index) as cas:
            cas.skill_level_id = self.t_skill_level_3
        applicant_form.save()
        new_skill = self.t_applicant.applicant_skill_ids - old_applicant_skills

        self.assertTrue(new_skill)
        self.assertEqual(len(self.t_applicant.applicant_skill_ids.ids), 6)
        self.assertEqual(new_skill.valid_from, date.today())
        self.assertEqual(self.t_applicant_skill_1.valid_to, date.today() - relativedelta(days=1))

    def test_edit_cert_1_level_1_to_level_2(self):
        """
        A test that asserts that when editing a certification, the certification that
        is being edited is archived and a new certification is created but with the
        same valid_from and valid_to as the original.
        """
        applicant_form = Form(self.t_applicant)
        old_applicant_skills = self.t_applicant.applicant_skill_ids
        index = self.t_applicant.current_applicant_skill_ids.ids.index(self.t_applicant_cert_1.id)
        with applicant_form.current_applicant_skill_ids.edit(index) as cas:
            cas.skill_level_id = self.t_cert_level_2
        applicant_form.save()
        new_skill = self.t_applicant.applicant_skill_ids - old_applicant_skills

        self.assertTrue(new_skill)
        self.assertEqual(len(self.t_applicant.applicant_skill_ids.ids), 6)
        self.assertEqual(new_skill.valid_from, date.today() - relativedelta(months=4))
        self.assertEqual(new_skill.valid_to, date.today() + relativedelta(months=8))

    def test_edit_cert_1_stop_date(self):
        """
        Assert that editing the stop_date of a certification does delete it and
        create a new one with the new values.
        """
        applicant_form = Form(self.t_applicant)
        old_applicant_skills = self.t_applicant.applicant_skill_ids
        index = self.t_applicant.current_applicant_skill_ids.ids.index(self.t_applicant_cert_1.id)
        with applicant_form.current_applicant_skill_ids.edit(index) as cas:
            cas.valid_to = date.today() + relativedelta(months=2)
        applicant_form.save()
        new_skill = self.t_applicant.applicant_skill_ids - old_applicant_skills

        self.assertFalse(new_skill)
        self.assertEqual(len(self.t_applicant.applicant_skill_ids.ids), 5)

    def test_edit_cert_1_to_skill_1_level_1(self):
        """
        Assert that when you edit a certification into a skill the certification
        is archived and the new skill is created.
        """
        applicant_form = Form(self.t_applicant)
        old_applicant_skills = self.t_applicant.applicant_skill_ids
        index = self.t_applicant.current_applicant_skill_ids.ids.index(self.t_applicant_cert_1.id)
        with applicant_form.current_applicant_skill_ids.edit(index) as cas:
            cas.skill_type_id = self.t_skill_type
            cas.skill_id = self.t_skill_1
            cas.skill_level_id = self.t_skill_level_1
        applicant_form.save()
        new_skill = self.t_applicant.applicant_skill_ids - old_applicant_skills
        deleted_skill = old_applicant_skills - self.t_applicant.applicant_skill_ids

        self.assertTrue(new_skill)
        self.assertEqual(len(self.t_applicant.applicant_skill_ids.ids), 6)
        self.assertEqual(len(deleted_skill.ids), 0)
        self.assertEqual(new_skill.valid_from, date.today())
        self.assertFalse(new_skill.valid_to)

    def test_edit_skill_2_level_2_to_cert_full_from_1_jan_to_1_june(self):
        """
        Assert that when you edit a skill into a certification the skill
        is archived and the new certification is created.
        """
        applicant_form = Form(self.t_applicant)
        old_applicant_skills = self.t_applicant.applicant_skill_ids
        index = self.t_applicant.current_applicant_skill_ids.ids.index(self.t_applicant_skill_2.id)
        with applicant_form.current_applicant_skill_ids.edit(index) as cas:
            cas.skill_type_id = self.t_cert_type
            cas.skill_id = self.t_cert_1
            cas.skill_level_id = self.t_cert_level_2
            cas.valid_from = date.today() - relativedelta(months=5)
            cas.valid_to = date.today() + relativedelta(months=7)
        applicant_form.save()
        new_skill = self.t_applicant.applicant_skill_ids - old_applicant_skills

        self.assertTrue(new_skill)
        self.assertEqual(self.t_applicant_skill_2.valid_to, date.today() - relativedelta(days=1))
        self.assertEqual(self.t_applicant_skill_2.valid_from, self.today - relativedelta(months=2))
        self.assertEqual(new_skill.valid_from, date.today() - relativedelta(months=5))
        self.assertEqual(new_skill.valid_to, date.today() + relativedelta(months=7))

    def test_add_cert_level_2_from_2_mar_to_infinity(self):
        """
        Assert that when you add a certification with the exact same values as
        an already existing certification, nothing happens. Note that if the
        valid_from and valid_to are not the same a new certification will be created.
        """
        applicant_form = Form(self.t_applicant)
        old_applicant_skills = self.t_applicant.applicant_skill_ids
        with applicant_form.current_applicant_skill_ids.new() as cas:
            cas.skill_type_id = self.t_cert_type
            cas.skill_id = self.t_cert_1
            cas.skill_level_id = self.t_cert_level_2
            cas.valid_from = self.today - relativedelta(months=3)
            cas.valid_to = False
        applicant_form.save()
        new_skill = self.t_applicant.applicant_skill_ids - old_applicant_skills

        self.assertFalse(new_skill, "A certificate with the exact same values already exists")
        self.assertEqual(len(self.t_applicant.applicant_skill_ids), 5)

    def test_add_cert_level_2_from_4_mar_to_infinity(self):
        """
        Assert that when you add a certification with almost the same values as
        an already existing certification, a new certification is created.
        """
        applicant_form = Form(self.t_applicant)
        old_applicant_skills = self.t_applicant.applicant_skill_ids
        with applicant_form.current_applicant_skill_ids.new() as cas:
            cas.skill_type_id = self.t_cert_type
            cas.skill_id = self.t_cert_1
            cas.skill_level_id = self.t_cert_level_2
            cas.valid_from = date(2025, 3, 4)
            cas.valid_to = False
        applicant_form.save()
        new_skill = self.t_applicant.applicant_skill_ids - old_applicant_skills

        self.assertTrue(new_skill, "A certificate should have been created")
        self.assertEqual(len(self.t_applicant.applicant_skill_ids), 6)

    def test_add_cert_level_1_from_2_mar_to_infinity(self):
        """
        Assert that when you add a certification with almost the same values as
        an already existing certification, a new certification is created.
        """
        applicant_form = Form(self.t_applicant)
        old_applicant_skills = self.t_applicant.applicant_skill_ids
        with applicant_form.current_applicant_skill_ids.new() as cas:
            cas.skill_type_id = self.t_cert_type
            cas.skill_id = self.t_cert_1
            cas.skill_level_id = self.t_cert_level_1
            cas.valid_from = date(2025, 3, 2)
            cas.valid_to = False
        applicant_form.save()
        new_skill = self.t_applicant.applicant_skill_ids - old_applicant_skills

        self.assertTrue(new_skill, "A certificate should have been created")
        self.assertEqual(len(self.t_applicant.applicant_skill_ids), 6)

    def test_add_skill_1_level_2(self):
        """
        Assert that when you add a certification with the exact same values as
        an already existing certification, nothing happens. Note that if the
        valid_from and valid_to are not the same a new certification will be created.
        """
        applicant_form = Form(self.t_applicant)
        old_applicant_skills = self.t_applicant.applicant_skill_ids
        with applicant_form.current_applicant_skill_ids.new() as cas:
            cas.skill_type_id = self.t_skill_type
            cas.skill_id = self.t_skill_1
            cas.skill_level_id = self.t_skill_level_2
        applicant_form.save()
        new_skill = self.t_applicant.applicant_skill_ids - old_applicant_skills

        self.assertEqual(new_skill.valid_from, date.today())
        self.assertFalse(new_skill.valid_to)
        self.assertEqual(self.t_applicant_skill_1.valid_to, date.today() - relativedelta(days=1))
        self.assertEqual(len(self.t_applicant.applicant_skill_ids), 6)

    def test_add_skill_1_level_1_and_edit_it_after_to_skill_1_level_2(self):
        applicant_form = Form(self.t_applicant)
        old_applicant_skills = self.t_applicant.applicant_skill_ids
        with applicant_form.current_applicant_skill_ids.new() as cas:
            cas.skill_type_id = self.t_skill_type
            cas.skill_id = self.t_skill_1
            cas.skill_level_id = self.t_skill_level_1
        applicant_form.save()
        new_skill = self.t_applicant.applicant_skill_ids - old_applicant_skills

        self.assertEqual(new_skill.valid_from, date.today())
        self.assertFalse(new_skill.valid_to)
        self.assertEqual(len(self.t_applicant.applicant_skill_ids), 6)

        index = self.t_applicant.current_applicant_skill_ids.ids.index(new_skill.id)
        with applicant_form.current_applicant_skill_ids.edit(index) as cas:
            cas.skill_level_id = self.t_skill_level_2
        applicant_form.save()
        new_skill = self.t_applicant.applicant_skill_ids - old_applicant_skills
        self.assertEqual(new_skill.valid_from, date.today())
        self.assertEqual(new_skill.skill_level_id, self.t_skill_level_2)
        self.assertEqual(len(self.t_applicant.applicant_skill_ids), 6)

    def test_archiving_vs_deleting_a_skill(self):
        """
        If a skill's create_date is more than 1 day in the past the skill will
        be archived instead of deleted. Archiving in this context means that
        the valid_to field will be set to 1 in the past from now.
        """
        applicant_form = Form(self.t_applicant)
        self.assertEqual(
            len(self.t_applicant.applicant_skill_ids.ids),
            5,
            "The test applicant should start with 5 skills.",
        )

        index = self.t_applicant.current_applicant_skill_ids.ids.index(self.t_applicant_skill_1.id)
        applicant_form.current_applicant_skill_ids.remove(index=index)
        applicant_form.save()
        self.assertEqual(
            len(self.t_applicant.applicant_skill_ids.ids),
            5,
            "The test applicant should still have 5 skills, as the archived skill was not created within the last day",
        )
        self.assertEqual(
            self.t_applicant_skill_1.valid_to,
            date.today() - relativedelta(days=1),
            "The skill that got removed should have valid_to set to one day before now",
        )
        prev_skills = self.t_applicant.applicant_skill_ids
        # Add a brand new skill
        with applicant_form.current_applicant_skill_ids.new() as cas:
            cas.skill_type_id = self.t_skill_type
            cas.skill_id = self.t_skill_1
            cas.skill_level_id = self.t_skill_level_2
        applicant_form.save()
        new_skill = self.t_applicant.applicant_skill_ids - prev_skills
        self.assertEqual(
            len(self.t_applicant.applicant_skill_ids.ids),
            6,
            "Creating a new skill should result in the applicant having 6 skills.",
        )

        index = self.t_applicant.current_applicant_skill_ids.ids.index(new_skill.id)
        # Remove the brand new skill
        applicant_form.current_applicant_skill_ids.remove(index=index)
        applicant_form.save()
        self.assertEqual(
            len(self.t_applicant.applicant_skill_ids.ids),
            5,
            "The skill that got removed should have been deleted as it was created within the last day",
        )

    def test_archiving_vs_deleting_a_certificate(self):
        """
        Assert that a certification will always be deleted, no matter how recently it was created.
        """
        applicant_form = Form(self.t_applicant)
        self.assertEqual(
            len(self.t_applicant.applicant_skill_ids.ids),
            5,
            "The test applicant should start with 5 skills.",
        )

        index = self.t_applicant.current_applicant_skill_ids.ids.index(self.t_applicant_cert_1.id)
        applicant_form.current_applicant_skill_ids.remove(index=index)
        applicant_form.save()
        self.assertEqual(
            len(self.t_applicant.applicant_skill_ids.ids),
            5,
            "The test applicant should still have 5 skills, as the certification was archived",
        )

        prev_skills = self.t_applicant.applicant_skill_ids
        # add a brand new certification
        with applicant_form.current_applicant_skill_ids.new() as cas:
            cas.skill_type_id = self.t_cert_type
            cas.skill_id = self.t_cert_1
            cas.skill_level_id = self.t_cert_level_1
        applicant_form.save()
        new_cert = self.t_applicant.applicant_skill_ids - prev_skills
        self.assertEqual(
            len(self.t_applicant.applicant_skill_ids.ids),
            6,
            "Creating a new certification should result in the applicant having 6 skills.",
        )

        # Remove the brand new cert
        index = self.t_applicant.current_applicant_skill_ids.ids.index(new_cert.id)
        applicant_form.current_applicant_skill_ids.remove(index=index)
        applicant_form.save()
        self.assertEqual(
            len(self.t_applicant.applicant_skill_ids.ids),
            5,
            "The skill that got removed should have been deleted as it was newly created",
        )

    def test_multiple_exact_same_skills_are_deduplicated_before_creation(self):
        """
        Assert that when you add multiple entries of the same skill:level,
        only one applicant skill will be created.
        """
        applicant_form = Form(self.t_applicant)
        old_applicant_skills = self.t_applicant.applicant_skill_ids
        for i in range(3):
            with applicant_form.current_applicant_skill_ids.new() as cas:
                cas.skill_type_id = self.t_skill_type
                cas.skill_id = self.t_skill_3
                cas.skill_level_id = self.t_skill_level_3
        applicant_form.save()
        new_skill = self.t_applicant.applicant_skill_ids - old_applicant_skills

        self.assertTrue(new_skill)
        self.assertEqual(len(new_skill), 1)
        self.assertEqual(new_skill.valid_from, date.today())
        self.assertEqual(len(self.t_applicant.applicant_skill_ids), 6)

    def test_multiple_same_skill_different_level_are_deduplicated_before_creation(self):
        """
        Assert that when you add multiple entries of the same skill but different level,
        only one applicant skill will be created.
        """
        skill_levels = [self.t_skill_level_1, self.t_skill_level_2, self.t_skill_level_3]
        applicant_form = Form(self.t_applicant)
        old_applicant_skills = self.t_applicant.applicant_skill_ids
        for level in skill_levels:
            with applicant_form.current_applicant_skill_ids.new() as cas:
                cas.skill_type_id = self.t_skill_type
                cas.skill_id = self.t_skill_3
                cas.skill_level_id = level
        applicant_form.save()
        new_skill = self.t_applicant.applicant_skill_ids - old_applicant_skills

        self.assertTrue(new_skill)
        self.assertEqual(len(new_skill), 1)
        self.assertEqual(new_skill.valid_from, date.today())
        self.assertEqual(len(self.t_applicant.applicant_skill_ids), 6)

    def test_same_certification_with_different_levels_but_same_dates_can_coexist(self):
        applicant_form = Form(self.t_applicant)
        old_applicant_skills = self.t_applicant.applicant_skill_ids
        with applicant_form.current_applicant_skill_ids.new() as cas:
            cas.skill_type_id = self.t_cert_type
            cas.skill_id = self.t_cert_1
            cas.skill_level_id = self.t_cert_level_2
            cas.valid_from = self.today - relativedelta(months=4)
            cas.valid_to = self.today + relativedelta(months=8)
        applicant_form.save()
        new_skill = self.t_applicant.applicant_skill_ids - old_applicant_skills

        self.assertTrue(new_skill)
        self.assertEqual(len(self.t_applicant.applicant_skill_ids), 6)
        self.assertEqual(len(self.t_applicant.current_applicant_skill_ids), 5)

    def test_duplicate_certifications_in_the_past_are_not_created(self):
        applicant_form = Form(self.t_applicant)
        old_applicant_skills = self.t_applicant.applicant_skill_ids
        with applicant_form.current_applicant_skill_ids.new() as cas:
            cas.skill_type_id = self.t_cert_type
            cas.skill_id = self.t_cert_1
            cas.skill_level_id = self.t_cert_level_1
            cas.valid_from = self.today - relativedelta(years=2)
            cas.valid_to = self.today - relativedelta(years=2)
        applicant_form.save()
        new_skill = self.t_applicant.applicant_skill_ids - old_applicant_skills
        new_old_applicant_skills = self.t_applicant.applicant_skill_ids
        self.assertTrue(new_skill)
        self.assertEqual(len(self.t_applicant.applicant_skill_ids), 6)
        self.assertEqual(len(self.t_applicant.current_applicant_skill_ids), 4)

        with applicant_form.current_applicant_skill_ids.new() as cas:
            cas.skill_type_id = self.t_cert_type
            cas.skill_id = self.t_cert_1
            cas.skill_level_id = self.t_cert_level_1
            cas.valid_from = self.today - relativedelta(years=2)
            cas.valid_to = self.today - relativedelta(years=2)
        applicant_form.save()
        new_skill = self.t_applicant.applicant_skill_ids - new_old_applicant_skills
        self.assertFalse(
            new_skill,
            "A certification with the exact same values already exists so a new one shouldn't be created",
        )
        self.assertEqual(len(self.t_applicant.applicant_skill_ids), 6)
        self.assertEqual(len(self.t_applicant.current_applicant_skill_ids), 4)
