from datetime import date

from dateutil.relativedelta import relativedelta

from odoo import Command
from odoo.tests import Form, TransactionCase, tagged


@tagged("recruitment")
@tagged("at_install", "-post_install")  # LEGACY at_install, fails post install
class TestApplicantSkills(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = date.today()

        (cls.t_skill_type, cls.t_cert_type, round_type, archived_type) = cls.env["hr.skill.type"].create(
            [
                {"name": "Skills for tests"},
                {"name": "Certification for tests", "is_certification": True},
                {"name": "Rounding"},
                {"name": "Archived"},
            ],
        )
        (
            cls.t_skill_level_1,
            cls.t_skill_level_2,
            cls.t_skill_level_3,
            cls.t_cert_level_1,
            cls.t_cert_level_2,
            round_level_none,
            round_level_low,
            round_level_high,
            archived_level,
        ) = cls.env["hr.skill.level"].create(
            [
                {"name": "Level 1", "skill_type_id": cls.t_skill_type.id, "level_progress": 34},
                {"name": "Level 2", "skill_type_id": cls.t_skill_type.id, "level_progress": 68},
                {"name": "Level 3", "skill_type_id": cls.t_skill_type.id, "level_progress": 100},
                {"name": "Half Certified", "skill_type_id": cls.t_cert_type.id, "level_progress": 50},
                {"name": "Fully Certified", "skill_type_id": cls.t_cert_type.id, "level_progress": 100},
                {"name": "None", "skill_type_id": round_type.id, "level_progress": 0},
                {"name": "Low", "skill_type_id": round_type.id, "level_progress": 5},
                {"name": "High", "skill_type_id": round_type.id, "level_progress": 100},
                {"name": "Archived", "skill_type_id": archived_type.id, "level_progress": 100},
            ],
        )
        (
            cls.t_skill_1,
            cls.t_skill_2,
            cls.t_skill_3,
            cls.t_cert_1,
            round_skill_1,
            round_skill_2,
            archived_skill,
        ) = cls.env["hr.skill"].create(
            [
                {"name": "Test Skill 1", "skill_type_id": cls.t_skill_type.id},
                {"name": "Test Skill 3", "skill_type_id": cls.t_skill_type.id},
                {"name": "Test Skill 2", "skill_type_id": cls.t_skill_type.id},
                {"name": "Certification 1", "skill_type_id": cls.t_cert_type.id},
                {"name": "Round 1", "skill_type_id": round_type.id},
                {"name": "Round 2", "skill_type_id": round_type.id},
                {"name": "Archived", "skill_type_id": archived_type.id},
            ],
        )
        degree_low, degree_high, degree_zero = cls.env["hr.recruitment.degree"].create([
            {"name": "Low", "score": 0.25},
            {"name": "High", "score": 0.5},
            {"name": "Zero", "score": 0},
        ])

        # Matching score: jobs and applicants covering the rules of the score
        (
            cls.t_job,
            cls.job_skills,
            cls.job_degree_only,
            job_zero,
            cls.job_empty,
            cls.job_round,
        ) = cls.env["hr.job"].create([
            {"name": "Test Job"},
            {
                "name": "Skills Job",
                "expected_degree": degree_high.id,
                "job_skill_ids": [
                    Command.create({
                        "skill_id": cls.t_skill_1.id,
                        "skill_type_id": cls.t_skill_type.id,
                        "skill_level_id": cls.t_skill_level_1.id,
                    }),
                    Command.create({
                        "skill_id": cls.t_skill_2.id,
                        "skill_type_id": cls.t_skill_type.id,
                        "skill_level_id": cls.t_skill_level_2.id,
                    }),
                    # expired requirement (e.g. the level was changed since): must be ignored
                    Command.create({
                        "skill_id": cls.t_skill_2.id,
                        "skill_type_id": cls.t_skill_type.id,
                        "skill_level_id": cls.t_skill_level_3.id,
                        "valid_from": cls.today - relativedelta(months=3),
                        "valid_to": cls.today - relativedelta(months=1),
                    }),
                    Command.create({
                        "skill_id": cls.t_cert_1.id,
                        "skill_type_id": cls.t_cert_type.id,
                        "skill_level_id": cls.t_cert_level_1.id,
                    }),
                    # its skill type is archived below: must be ignored
                    Command.create({
                        "skill_id": archived_skill.id,
                        "skill_type_id": archived_type.id,
                        "skill_level_id": archived_level.id,
                    }),
                ],
            },
            {"name": "Degree Only Job", "expected_degree": degree_low.id},
            {
                "name": "Zero Job",
                "expected_degree": degree_zero.id,
                "job_skill_ids": [
                    Command.create({
                        "skill_id": round_skill_1.id,
                        "skill_type_id": round_type.id,
                        "skill_level_id": round_level_none.id,
                    }),
                ],
            },
            {"name": "Empty Job"},
            {
                "name": "Round Job",
                "job_skill_ids": [
                    Command.create({
                        "skill_id": round_skill_1.id,
                        "skill_type_id": round_type.id,
                        "skill_level_id": round_level_high.id,
                    }),
                    Command.create({
                        "skill_id": round_skill_2.id,
                        "skill_type_id": round_type.id,
                        "skill_level_id": round_level_high.id,
                    }),
                ],
            },
        ])
        cls.matching_jobs = cls.job_skills | cls.job_degree_only | job_zero | cls.job_empty | cls.job_round
        archived_type.active = False

        (
            cls.t_applicant,
            cls.app_expired_cert,
            cls.app_cap,
            cls.app_round,
            app_nothing,
        ) = cls.env["hr.applicant"].create([
            {
                "partner_name": "Test Applicant",
                "job_id": cls.t_job.id,
                "type_id": degree_high.id,
                "applicant_skill_ids": [
                    Command.create({
                        "skill_id": cls.t_skill_2.id,
                        "skill_type_id": cls.t_skill_type.id,
                        "skill_level_id": cls.t_skill_level_1.id,
                        "valid_from": cls.today - relativedelta(months=4),
                        "valid_to": cls.today - relativedelta(months=3, days=1),
                    }),
                    Command.create({
                        "skill_id": cls.t_skill_1.id,
                        "skill_type_id": cls.t_skill_type.id,
                        "skill_level_id": cls.t_skill_level_2.id,
                        "valid_from": cls.today - relativedelta(months=3),
                        "valid_to": False,
                    }),
                    Command.create({
                        "skill_id": cls.t_skill_2.id,
                        "skill_type_id": cls.t_skill_type.id,
                        "skill_level_id": cls.t_skill_level_2.id,
                        "valid_from": cls.today - relativedelta(months=2),
                        "valid_to": False,
                    }),
                    Command.create({
                        "skill_id": cls.t_cert_1.id,
                        "skill_type_id": cls.t_cert_type.id,
                        "skill_level_id": cls.t_cert_level_1.id,
                        "valid_from": cls.today - relativedelta(months=4),
                        "valid_to": cls.today + relativedelta(months=8),
                    }),
                    Command.create({
                        "skill_id": cls.t_cert_1.id,
                        "skill_type_id": cls.t_cert_type.id,
                        "skill_level_id": cls.t_cert_level_2.id,
                        "valid_from": cls.today - relativedelta(months=3),
                        "valid_to": False,
                    }),
                ],
            },
            {
                "partner_name": "Expired Cert",
                "applicant_skill_ids": [
                    Command.create({
                        "skill_id": cls.t_cert_1.id,
                        "skill_type_id": cls.t_cert_type.id,
                        "skill_level_id": cls.t_cert_level_1.id,
                        "valid_from": cls.today - relativedelta(months=6),
                        "valid_to": cls.today - relativedelta(months=2),
                    }),
                    Command.create({
                        "skill_id": cls.t_cert_1.id,
                        "skill_type_id": cls.t_cert_type.id,
                        "skill_level_id": cls.t_cert_level_2.id,
                        "valid_from": cls.today - relativedelta(months=6),
                        "valid_to": cls.today - relativedelta(months=1),
                    }),
                ],
            },
            {
                "partner_name": "Capped",
                "type_id": degree_low.id,
                "applicant_skill_ids": [
                    Command.create({
                        "skill_id": cls.t_skill_1.id,
                        "skill_type_id": cls.t_skill_type.id,
                        "skill_level_id": cls.t_skill_level_3.id,
                    }),
                ],
            },
            {
                "partner_name": "Round",
                "applicant_skill_ids": [
                    Command.create({
                        "skill_id": round_skill_1.id,
                        "skill_type_id": round_type.id,
                        "skill_level_id": round_level_low.id,
                    }),
                ],
            },
            {"partner_name": "Nothing"},
        ])
        cls.t_applicant_skill_1, cls.t_applicant_skill_2, cls.t_applicant_cert_1, _others = (
            cls.t_applicant.applicant_skill_ids.partitioned(
                lambda s: s.skill_id == cls.t_skill_1,
                lambda s: s.skill_id == cls.t_skill_2 and not s.valid_to,
                lambda s: s.skill_level_id == cls.t_cert_level_1,
            )
        )
        cls.matching_applicants = cls.t_applicant | cls.app_expired_cert | cls.app_cap | cls.app_round | app_nothing
        # Expected score of each (applicant, job) pair, 0 when missing.
        # Skills Job total: skill_1 34 + skill_2 68 + cert_1 50 + degree 50 = 202
        # (the expired skill_2 requirement and the archived skill type are ignored)
        # Zero Job total: a skill at level 0 + degree 0 = 0, so every score is 0 (no division by zero)
        cls.expected_scores = {
            # skills: 68 + 68 + MAX(50, 100) capped to 100 = 236 -> 117, degree: 50 -> 25
            (cls.t_applicant, cls.job_skills): 142,
            # the latest expired certification (100) is used -> 50
            (cls.app_expired_cert, cls.job_skills): 50,
            # skill_1 at 100 capped to 2 x 34 = 68 -> 34, degree: 25 -> 12
            (cls.app_cap, cls.job_skills): 46,
            (cls.app_cap, cls.job_degree_only): 100,
            (cls.t_applicant, cls.job_degree_only): 200,
            # 100 * 5 / 200 = 2.5 rounds half to even
            (cls.app_round, cls.job_round): 2,
        }

    def _assert_sql_scores(self, model, field_name, records, expected):
        domain = [("id", "in", records.ids)]
        groups = model._read_group(domain, [field_name], ["id:recordset"])
        self.assertEqual(
            {record: score for score, group in groups for record in group},
            expected,
            "Grouping by the score must give the same scores as reading them",
        )
        self.assertEqual(
            model.search(domain, order=f"{field_name} desc, id").ids,
            records.sorted(lambda record: (-expected[record], record.id)).ids,
            "Sorting by the score must follow the scores read",
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
        index = applicant_form.current_applicant_skill_ids.ids.index(self.t_applicant_skill_1.id)
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
        index = applicant_form.current_applicant_skill_ids.ids.index(self.t_applicant_cert_1.id)
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
        index = applicant_form.current_applicant_skill_ids.ids.index(self.t_applicant_cert_1.id)
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
        index = applicant_form.current_applicant_skill_ids.ids.index(self.t_applicant_cert_1.id)
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
        index = applicant_form.current_applicant_skill_ids.ids.index(self.t_applicant_skill_2.id)
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

        index = applicant_form.current_applicant_skill_ids.ids.index(new_skill.id)
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

        index = applicant_form.current_applicant_skill_ids.ids.index(self.t_applicant_skill_1.id)
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

        index = applicant_form.current_applicant_skill_ids.ids.index(new_skill.id)
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

        index = applicant_form.current_applicant_skill_ids.ids.index(self.t_applicant_cert_1.id)
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
        index = applicant_form.current_applicant_skill_ids.ids.index(new_cert.id)
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

    def test_compute_matching_skill_ids_scores_and_missing_skills(self):
        applicant = self.env["hr.applicant"].create({
            "partner_name": "Matching Applicant",
            "job_id": self.t_job.id,
        })
        applicant.write({
            "applicant_skill_ids": [
                (
                    0,
                    0,
                    {
                        "skill_id": self.t_skill_1.id,
                        "skill_level_id": self.t_skill_level_2.id,
                        "skill_type_id": self.t_skill_type.id,
                    },
                ),
            ],
        })
        applicant_degree = self.env["hr.recruitment.degree"].create({
            "name": "Bachelor",
            "score": 0.75,
        })
        job_degree = self.env["hr.recruitment.degree"].create({
            "name": "Master",
            "score": 0.5,
        })
        applicant.type_id = applicant_degree
        self.t_job.expected_degree = job_degree
        self.env["hr.job.skill"].create([
            {
                "job_id": self.t_job.id,
                "skill_id": self.t_skill_1.id,
                "skill_type_id": self.t_skill_type.id,
                "skill_level_id": self.t_skill_level_1.id,
            },
            {
                "job_id": self.t_job.id,
                "skill_id": self.t_skill_3.id,
                "skill_type_id": self.t_skill_type.id,
                "skill_level_id": self.t_skill_level_3.id,
            },
        ])

        self.assertEqual(applicant.matching_skill_ids, self.t_skill_1)
        self.assertEqual(applicant.missing_skill_ids, self.t_skill_3)
        self.assertEqual(applicant.degree_score, 41)
        self.assertEqual(applicant.skills_score, 37)
        self.assertEqual(applicant.matching_score, 78)
        self.assertTrue(applicant.is_degree_score_matching)

    def test_matching_score_rules(self):
        """
        A test that asserts that the score of an applicant for the job chosen in a dialog follows the rules of the
        matching score (see expected_scores), and is the same on the applicant and on the job side.
        """
        for applicant in self.matching_applicants:
            for job in self.matching_jobs:
                with self.subTest(applicant=applicant.partner_name, job=job.name):
                    expected = self.expected_scores.get((applicant, job), 0)
                    self.assertEqual(
                        applicant.with_context(active_job_id=job.id).job_matching_score,
                        expected,
                        "Wrong score of the applicant for the job chosen in the dialog",
                    )
                    self.assertEqual(
                        job.with_context(active_applicant_id=applicant.id).applicant_matching_score,
                        expected,
                        "The job side must give the same score as the applicant side",
                    )

    def test_matching_skills_of_job_in_context(self):
        """
        A test that asserts that the matching and missing skills of an applicant are the ones of the job chosen in a
        dialog.
        """
        applicant = self.app_cap.with_context(active_job_id=self.job_skills.id)
        self.assertEqual(applicant.matching_skill_ids, self.t_skill_1)
        self.assertEqual(applicant.missing_skill_ids, self.t_skill_2 | self.t_cert_1)
        self.assertFalse(applicant.is_degree_score_matching, "The applicant degree is lower than the job degree")
        self.assertFalse(self.t_applicant.with_context(active_job_id=self.job_skills.id).missing_skill_ids)
        applicant = self.t_applicant.with_context(active_job_id=self.job_empty.id)
        self.assertFalse(applicant.matching_skill_ids, "A job without requirements has no matching skills")
        self.assertFalse(applicant.missing_skill_ids, "A job without requirements has no missing skills")
        self.assertFalse(applicant.is_degree_score_matching, "A job without expected degree has no degree to match")

    def test_job_matching_score_sql(self):
        """
        A test that asserts that grouping and sorting the applicants on the score of the job chosen in a dialog give
        the same values as reading it.
        """
        applicants = self.matching_applicants
        for job in self.matching_jobs:
            with self.subTest(job=job.name):
                self._assert_sql_scores(
                    self.env["hr.applicant"].with_context(active_job_id=job.id),
                    "job_matching_score",
                    applicants,
                    {applicant: self.expected_scores.get((applicant, job), 0) for applicant in applicants},
                )

    def test_applicant_matching_score_sql(self):
        """
        A test that asserts that grouping and sorting the jobs on the score of the applicant chosen in a dialog give
        the same values as reading it.
        """
        jobs = self.matching_jobs
        for applicant in self.matching_applicants:
            with self.subTest(applicant=applicant.partner_name):
                self._assert_sql_scores(
                    self.env["hr.job"].with_context(active_applicant_id=applicant.id),
                    "applicant_matching_score",
                    jobs,
                    {job: self.expected_scores.get((applicant, job), 0) for job in jobs},
                )

    def test_matching_score_sql_without_context(self):
        """
        A test that asserts that without a job or an applicant chosen in a dialog, every score is 0 in SQL.
        """
        self._assert_sql_scores(
            self.env["hr.applicant"],
            "job_matching_score",
            self.matching_applicants,
            dict.fromkeys(self.matching_applicants, 0),
        )
        self._assert_sql_scores(
            self.env["hr.job"],
            "applicant_matching_score",
            self.matching_jobs,
            dict.fromkeys(self.matching_jobs, 0),
        )

    def test_matching_score_name_search(self):
        """
        A test that asserts that the dialog pickers sort the applicants and jobs by score and show the score in their
        name.
        """
        applicants, jobs = self.matching_applicants, self.matching_jobs
        applicants_for_skills_job = self.env["hr.applicant"].with_context(
            show_matching_score_in_name=True,
            active_job_id=self.job_skills.id,
        )
        self.assertEqual(
            applicants_for_skills_job.name_search("", [("id", "in", applicants.ids)], limit=3),
            [
                (self.t_applicant.id, "Test Applicant (142%)"),
                (self.app_expired_cert.id, "Expired Cert (50%)"),
                (self.app_cap.id, "Capped (46%)"),
            ],
            "The best matching applicants come first",
        )
        self.assertEqual(
            applicants_for_skills_job.name_search("cap", [("id", "in", applicants.ids)]),
            [(self.app_cap.id, "Capped (46%)")],
        )

        jobs_for_capped_applicant = self.env["hr.job"].with_context(
            show_matching_score_in_name=True,
            active_applicant_id=self.app_cap.id,
        )
        self.assertEqual(
            jobs_for_capped_applicant.name_search("", [("id", "in", jobs.ids)], limit=2),
            [
                (self.job_degree_only.id, "Degree Only Job (100%)"),
                (self.job_skills.id, "Skills Job (46%)"),
            ],
            "The best matching jobs come first",
        )
        self.assertEqual(
            jobs_for_capped_applicant.name_search("skills", [("id", "in", jobs.ids)]),
            [(self.job_skills.id, "Skills Job (46%)")],
        )

        self.assertEqual(
            applicants_for_skills_job.with_context(formatted_display_name=True).browse(self.app_cap.id).display_name,
            "Capped \t --46%--",
            "The dropdown shows the score muted",
        )
        self.assertEqual(
            jobs_for_capped_applicant.with_context(formatted_display_name=True).browse(self.job_skills.id).display_name,
            "Skills Job \t --46%--",
            "The dropdown shows the score muted",
        )
        self.assertEqual(
            self.env["hr.job"].with_context(show_matching_score_in_name=True).name_search("", [("id", "in", jobs.ids)]),
            self.env["hr.job"].name_search("", [("id", "in", jobs.ids)]),
            "Without applicant (e.g. several applicants), the jobs keep their usual order",
        )
        self.assertEqual(self.app_cap.display_name, "Capped", "The score must not leak outside of the dialog")
        self.assertEqual(self.job_skills.display_name, "Skills Job", "The score must not leak outside of the dialog")

    def test_expired_certifications_ending_the_same_day(self):
        """
        A test that asserts that among expired certifications of a skill ending the same day, the highest level counts,
        in Python and in SQL.
        """
        expired = {
            "valid_from": self.today - relativedelta(months=6),
            "valid_to": self.today - relativedelta(months=1),
        }
        applicant = self.env["hr.applicant"].create({
            "partner_name": "Same End Date",
            "job_id": self.job_skills.id,
            "applicant_skill_ids": [
                Command.create({
                    "skill_id": self.t_cert_1.id,
                    "skill_type_id": self.t_cert_type.id,
                    "skill_level_id": self.t_cert_level_1.id,
                    **expired,
                }),
                Command.create({
                    "skill_id": self.t_cert_1.id,
                    "skill_type_id": self.t_cert_type.id,
                    "skill_level_id": self.t_cert_level_2.id,
                    **expired,
                }),
            ],
        })
        # cert_1 at 100 on a total of 202 -> 50
        self.assertEqual(applicant.matching_score, 50)
        self.assertEqual(
            self.env["hr.applicant"].with_context(active_job_id=self.job_skills.id).search_count([
                ("id", "=", applicant.id),
                ("job_matching_score", "=", 50),
            ]),
            1,
            "SQL must pick the same certification level as Python",
        )

    def test_stored_matching_score_ignores_job_in_context(self):
        """
        A test that asserts that the stored matching score is always the one of the applicant's own job, even when
        the applicant is edited from a dialog opened for another job.
        """
        self.app_cap.job_id = self.job_degree_only
        applicant_in_skills_job_dialog = self.app_cap.with_context(active_job_id=self.job_skills.id)
        applicant_in_skills_job_dialog.write({
            "applicant_skill_ids": [
                Command.create({
                    "skill_id": self.t_skill_2.id,
                    "skill_type_id": self.t_skill_type.id,
                    "skill_level_id": self.t_skill_level_2.id,
                }),
            ],
        })
        # the score is recomputed in the context of the dialog
        self.assertEqual(
            applicant_in_skills_job_dialog.matching_score,
            100,
            "The stored score must stay the one of the applicant's own job",
        )

    def test_job_matching_score_with_zero_progress_skill(self):
        level_0 = self.env["hr.skill.level"].create({
            "name": "No experience",
            "skill_type_id": self.t_skill_type.id,
            "level_progress": 0,
        })
        self.env["hr.job.skill"].create({
            "job_id": self.t_job.id,
            "skill_id": self.t_skill_1.id,
            "skill_type_id": self.t_skill_type.id,
            "skill_level_id": level_0.id,
        })
        job = self.t_job.with_context(active_applicant_id=self.t_applicant.id)
        self.assertEqual(job.applicant_matching_score, 0)
