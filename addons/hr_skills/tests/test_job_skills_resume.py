from datetime import date

from dateutil.relativedelta import relativedelta

from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase, new_test_user


@tagged("post_install", "-at_install")
class TestCurrentJobSkills(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.job = cls.env["hr.job"].create({"name": "Skilled job"})
        cls.skill_type = cls.env["hr.skill.type"].create({"name": "JS type"})
        cls.level = cls.env["hr.skill.level"].create(
            {
                "name": "JS level",
                "skill_type_id": cls.skill_type.id,
                "level_progress": 50,
            },
        )
        cls.skill_live, cls.skill_dead = cls.env["hr.skill"].create(
            [
                {"name": "JS live", "skill_type_id": cls.skill_type.id},
                {"name": "JS dead", "skill_type_id": cls.skill_type.id},
            ],
        )
        today = date.today()
        cls.job_skill_live, cls.job_skill_dead = cls.env["hr.job.skill"].create(
            [
                {
                    "job_id": cls.job.id,
                    "skill_id": cls.skill_live.id,
                    "skill_level_id": cls.level.id,
                    "skill_type_id": cls.skill_type.id,
                    "valid_from": today - relativedelta(months=2),
                    "valid_to": False,
                },
                {
                    "job_id": cls.job.id,
                    "skill_id": cls.skill_dead.id,
                    "skill_level_id": cls.level.id,
                    "skill_type_id": cls.skill_type.id,
                    "valid_from": today - relativedelta(months=2),
                    "valid_to": today - relativedelta(months=1),
                },
            ],
        )

    def test_current_job_skills_exclude_expired(self):
        self.assertEqual(self.job.current_job_skill_ids, self.job_skill_live)

    def test_current_job_skills_searchable(self):
        jobs = self.env["hr.job"].search(
            [("current_job_skill_ids", "in", self.job_skill_live.ids)]
        )
        self.assertIn(self.job, jobs)

        jobs_dead = self.env["hr.job"].search(
            [("current_job_skill_ids", "in", self.job_skill_dead.ids)]
        )
        self.assertNotIn(self.job, jobs_dead)

    def test_current_job_skills_negated_search(self):
        jobs = self.env["hr.job"].search(
            [("current_job_skill_ids", "not in", self.job_skill_live.ids)]
        )
        self.assertNotIn(self.job, jobs)

        jobs_dead = self.env["hr.job"].search(
            [("current_job_skill_ids", "not in", self.job_skill_dead.ids)]
        )
        self.assertIn(self.job, jobs_dead)

    def test_current_job_skills_unsupported_operator(self):
        with self.assertRaises(NotImplementedError):
            self.env["hr.job"]._search_current_individual_skill_ids("=", True)


@tagged("post_install", "-at_install")
class TestInternalResumeLines(TransactionCase):
    def test_no_res_id_returns_empty(self):
        self.assertEqual(
            self.env["hr.employee"].get_internal_resume_lines(False, "hr.employee"),
            [],
        )

    def test_single_version_with_job_title_yields_one_line(self):
        employee = self.env["hr.employee"].create(
            {"name": "Resume employee", "job_title": "Chief Tester"},
        )
        lines = self.env["hr.employee"].get_internal_resume_lines(
            employee.id, "hr.employee"
        )

        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["job_title"], "Chief Tester")
        self.assertFalse(lines[0]["date_end"])

    def test_portal_user_cannot_access_resume(self):
        employee = self.env["hr.employee"].create({"name": "Guarded employee"})
        portal_user = new_test_user(
            self.env, login="portal.resume.user", groups="base.group_portal"
        )

        with self.assertRaises(AccessError):
            self.env["hr.employee"].with_user(portal_user).get_internal_resume_lines(
                employee.id, "hr.employee"
            )


@tagged("post_install", "-at_install")
class TestInternalResumeLineShapes(TransactionCase):
    """The internal resume is one line per run of versions sharing a title."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env["hr.employee"].create(
            {"name": "Shaped employee", "job_title": "Developer"},
        )
        cls.first = cls.employee.version_ids
        cls.day0 = cls.first.date_version

    def _version(self, days, title, **vals):
        return self.env["hr.version"].create(
            {
                "employee_id": self.employee.id,
                "date_version": self.day0 + relativedelta(days=days),
                "job_title": title,
                **vals,
            },
        )

    def _lines(self, clip_to_contract=True):
        self.env.invalidate_all()
        return self.env["hr.employee"]._internal_resume_lines(
            self.employee.version_ids, clip_to_contract=clip_to_contract
        )

    def test_consecutive_versions_with_one_title_are_one_line(self):
        last = self._version(100, "Developer")
        lines = self._lines()
        self.assertEqual(len(lines), 1)
        self.assertEqual(
            lines[0]["id"], last.id, "the run answers to its latest version"
        )
        self.assertEqual(lines[0]["date_start"], self.day0)
        self.assertFalse(lines[0]["date_end"])

    def test_a_title_change_ends_the_line_the_day_before(self):
        self._version(100, "Lead")
        lines = self._lines()
        self.assertEqual([line["job_title"] for line in lines], ["Lead", "Developer"])
        self.assertEqual(lines[1]["date_end"], self.day0 + relativedelta(days=99))
        self.assertEqual(lines[0]["date_start"], self.day0 + relativedelta(days=100))

    def test_a_version_without_a_title_is_a_hole(self):
        self._version(100, False)
        self._version(200, "Developer")
        lines = self._lines()
        self.assertEqual(
            len(lines), 2, "the same title on both sides of a hole is two lines"
        )
        self.assertEqual(lines[1]["date_end"], self.day0 + relativedelta(days=99))
        self.assertEqual(lines[0]["date_start"], self.day0 + relativedelta(days=200))

    def test_a_contract_end_splits_a_run(self):
        self.first.write(
            {
                "contract_date_start": self.day0,
                "contract_date_end": self.day0 + relativedelta(days=50),
            },
        )
        self._version(100, "Developer")
        lines = self._lines()
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[1]["date_end"], self.day0 + relativedelta(days=50))

    def test_a_reader_without_contract_access_sees_version_dates_only(self):
        self.first.write(
            {
                "contract_date_start": self.day0 + relativedelta(days=10),
                "contract_date_end": self.day0 + relativedelta(days=50),
            },
        )
        clipped = self._lines(clip_to_contract=True)
        plain = self._lines(clip_to_contract=False)
        self.assertEqual(clipped[0]["date_end"], self.day0 + relativedelta(days=50))
        self.assertEqual(plain[0]["date_start"], self.first.date_version)
        self.assertFalse(plain[0]["date_end"])

    def test_an_employee_without_version_access_gets_unclipped_lines(self):
        self.first.write(
            {
                "contract_date_start": self.day0 + relativedelta(days=10),
                "contract_date_end": self.day0 + relativedelta(days=50),
            },
        )
        colleague = new_test_user(
            self.env, login="resume.reader", groups="base.group_user"
        )
        self.assertFalse(
            self.env["hr.version"]
            .with_user(colleague)
            .browse(self.first.id)
            ._has_field_access(
                self.env["hr.version"]._fields["contract_date_end"], "read"
            )
        )
        lines = (
            self.env["hr.employee"]
            .with_user(colleague)
            .get_internal_resume_lines(self.employee.id, "hr.employee")
        )
        self.assertEqual(lines[0]["date_start"], self.first.date_version)
        self.assertFalse(
            lines[0]["date_end"],
            "contract dates are hr.version data a plain user cannot read; the "
            "resume must not leak them through sudo",
        )
