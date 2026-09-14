from datetime import date

from dateutil.relativedelta import relativedelta

from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import SkillsCase


@tagged("post_install", "-at_install")
class TestSkillIdsMeansCurrentlyHeld(SkillsCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = date.today()
        cls.employee = cls.env["hr.employee"].create({"name": "Set employee"})
        cls.env["hr.employee.skill"].create(
            [
                {
                    "employee_id": cls.employee.id,
                    "skill_id": cls.skill_piano.id,
                    "skill_level_id": cls.level_expert.id,
                    "skill_type_id": cls.skill_type.id,
                    "valid_from": cls.today - relativedelta(months=6),
                },
                {
                    "employee_id": cls.employee.id,
                    "skill_id": cls.skill_guitar.id,
                    "skill_level_id": cls.level_novice.id,
                    "skill_type_id": cls.skill_type.id,
                    "valid_from": cls.today - relativedelta(months=6),
                    "valid_to": cls.today - relativedelta(months=1),
                },
            ],
        )
        cls.env.flush_all()

    def test_a_lapsed_skill_is_not_one_the_employee_has(self):
        self.assertIn(self.skill_piano, self.employee.skill_ids)
        self.assertNotIn(
            self.skill_guitar,
            self.employee.skill_ids,
            "skill_ids answers what the employee holds; the lapsed row is "
            "history, and current_employee_skill_ids already excludes it",
        )

    def test_a_lapsed_certification_is_shown_but_not_held(self):
        self.env["hr.employee.skill"].create(
            {
                "employee_id": self.employee.id,
                "skill_id": self.certification.id,
                "skill_level_id": self.level_certified.id,
                "skill_type_id": self.certification_type.id,
                "valid_from": self.today - relativedelta(years=2),
                "valid_to": self.today - relativedelta(years=1),
            },
        )
        self.assertIn(
            self.certification, self.employee.current_employee_skill_ids.skill_id
        )
        self.assertNotIn(self.certification, self.employee.skill_ids)
        self.assertNotIn(
            self.employee,
            self.env["hr.employee"].search(
                [("skill_ids", "in", self.certification.ids)]
            ),
        )

    def test_a_skill_starting_later_is_not_held_yet(self):
        self.env["hr.employee.skill"].create(
            {
                "employee_id": self.employee.id,
                "skill_id": self.certification.id,
                "skill_level_id": self.level_certified.id,
                "skill_type_id": self.certification_type.id,
                "valid_from": self.today + relativedelta(days=10),
            },
        )
        self.assertIn(
            self.certification, self.employee.current_employee_skill_ids.skill_id
        )
        self.assertNotIn(self.certification, self.employee.skill_ids)
        self.assertNotIn(
            self.employee,
            self.env["hr.employee"].search(
                [("skill_ids", "in", self.certification.ids)]
            ),
        )

    def test_searching_the_current_list_finds_what_it_shows(self):
        lapsed = self.env["hr.employee.skill"].create(
            {
                "employee_id": self.employee.id,
                "skill_id": self.certification.id,
                "skill_level_id": self.level_certified.id,
                "skill_type_id": self.certification_type.id,
                "valid_from": self.today - relativedelta(years=2),
                "valid_to": self.today - relativedelta(years=1),
            },
        )
        self.env.flush_all()
        shown = self.employee.current_employee_skill_ids
        self.assertIn(lapsed, shown)
        Employee = self.env["hr.employee"]
        for row in self.employee.employee_skill_ids:
            with self.subTest(row=row.display_name, shown=row in shown):
                found = Employee.search(
                    [
                        ("id", "=", self.employee.id),
                        ("current_employee_skill_ids", "in", row.ids),
                    ]
                )
                self.assertEqual(bool(found), row in shown)

    def test_searching_by_skill_does_not_return_people_who_lost_it(self):
        holders = self.env["hr.employee"].search(
            [("skill_ids", "in", self.skill_piano.ids)]
        )
        self.assertIn(self.employee, holders)

        lapsed = self.env["hr.employee"].search(
            [("skill_ids", "in", self.skill_guitar.ids)]
        )
        self.assertNotIn(self.employee, lapsed)

    def test_the_negated_search_answers_the_opposite(self):
        without = self.env["hr.employee"].search(
            [("skill_ids", "not in", self.skill_piano.ids)]
        )
        self.assertNotIn(self.employee, without)

        without_guitar = self.env["hr.employee"].search(
            [("skill_ids", "not in", self.skill_guitar.ids)]
        )
        self.assertIn(self.employee, without_guitar)

    def test_an_unsupported_operator_fails_loudly(self):
        with self.assertRaises(NotImplementedError):
            self.env["hr.employee"]._search_skill_ids("=", True)


@tagged("post_install", "-at_install")
class TestJobSkillIdsMeansCurrentlyRequired(SkillsCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = date.today()
        cls.job = cls.env["hr.job"].create({"name": "Set job"})
        cls.env["hr.job.skill"].create(
            [
                {
                    "job_id": cls.job.id,
                    "skill_id": cls.skill_piano.id,
                    "skill_level_id": cls.level_expert.id,
                    "skill_type_id": cls.skill_type.id,
                    "valid_from": cls.today - relativedelta(months=6),
                },
                {
                    "job_id": cls.job.id,
                    "skill_id": cls.skill_guitar.id,
                    "skill_level_id": cls.level_novice.id,
                    "skill_type_id": cls.skill_type.id,
                    "valid_from": cls.today - relativedelta(months=6),
                    "valid_to": cls.today - relativedelta(months=1),
                },
            ],
        )
        cls.env.flush_all()

    def test_a_dropped_requirement_is_not_one_the_job_asks_for(self):
        # hr_recruitment_integration_skills_monster posts job.skill_ids to an
        # external board; a dropped requirement must not be advertised.
        self.assertEqual(self.job.skill_ids, self.skill_piano)

    def test_searching_jobs_by_skill_skips_dropped_requirements(self):
        self.assertIn(
            self.job,
            self.env["hr.job"].search([("skill_ids", "in", self.skill_piano.ids)]),
        )
        self.assertNotIn(
            self.job,
            self.env["hr.job"].search([("skill_ids", "in", self.skill_guitar.ids)]),
        )


@tagged("post_install", "-at_install")
class TestValidityMessages(SkillsCase):
    def test_each_offending_record_gets_its_own_line(self):
        employee = self.env["hr.employee"].create({"name": "Message employee"})
        today = date.today()
        with self.assertRaises(ValidationError) as caught:
            self.env["hr.employee.skill"].create(
                [
                    {
                        "employee_id": employee.id,
                        "skill_id": skill.id,
                        "skill_level_id": self.level_novice.id,
                        "skill_type_id": self.skill_type.id,
                        "valid_from": today,
                        "valid_to": today - relativedelta(days=1),
                    }
                    for skill in (self.skill_piano, self.skill_guitar)
                ],
            )
        bullets = [
            line for line in str(caught.exception).splitlines() if line.startswith("•")
        ]
        self.assertEqual(
            len(bullets), 2, "the two offending rows must not run together on one line"
        )


@tagged("post_install", "-at_install")
class TestWarningFlag(SkillsCase):
    def test_the_flag_follows_the_dates_rather_than_a_stored_value(self):
        employee = self.env["hr.employee"].create({"name": "Flag employee"})
        row = self.env["hr.employee.skill"].create(
            {
                "employee_id": employee.id,
                "skill_id": self.skill_piano.id,
                "skill_level_id": self.level_novice.id,
                "skill_type_id": self.skill_type.id,
                "valid_from": date.today(),
            },
        )
        self.assertFalse(row.display_warning_message)
        self.assertFalse(
            self.env["hr.employee.skill"]._fields["display_warning_message"].store,
            "a flag that only drives a form alert has no business in a column",
        )


@tagged("post_install", "-at_install")
class TestResumeLineColour(SkillsCase):
    def test_every_course_type_gets_a_colour(self):
        employee = self.env["hr.employee"].create({"name": "Colour employee"})
        selection = self.env["hr.resume.line"]._fields["course_type"].selection
        for course_type, _label in selection:
            line = self.env["hr.resume.line"].create(
                {
                    "employee_id": employee.id,
                    "name": f"Line {course_type}",
                    "date_start": date.today(),
                    "course_type": course_type,
                },
            )
            self.assertTrue(
                line.color,
                f"{course_type} left color unassigned; a compute must assign for "
                "every record it is given",
            )


@tagged("post_install", "-at_install")
class TestCurrentEmployeeSkillSearch(SkillsCase):
    """current_employee_skill_ids is searchable, like hr.job's counterpart, so
    a related field elsewhere (project.task.user_skill_ids) can be searched."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        today = date.today()
        cls.employee = cls.env["hr.employee"].create({"name": "Searchable"})
        cls.held, cls.lost = cls.env["hr.employee.skill"].create(
            [
                {
                    "employee_id": cls.employee.id,
                    "skill_id": cls.skill_piano.id,
                    "skill_level_id": cls.level_expert.id,
                    "skill_type_id": cls.skill_type.id,
                    "valid_from": today - relativedelta(months=6),
                },
                {
                    "employee_id": cls.employee.id,
                    "skill_id": cls.skill_guitar.id,
                    "skill_level_id": cls.level_novice.id,
                    "skill_type_id": cls.skill_type.id,
                    "valid_from": today - relativedelta(months=6),
                    "valid_to": today - relativedelta(months=1),
                },
            ],
        )
        cls.env.flush_all()

    def _search(self, domain):
        return self.env["hr.employee"].search(domain + [("id", "=", self.employee.id)])

    def test_in_and_not_in(self):
        self.assertEqual(
            self._search([("current_employee_skill_ids", "in", self.held.ids)]),
            self.employee,
        )
        self.assertFalse(
            self._search([("current_employee_skill_ids", "in", self.lost.ids)])
        )
        self.assertFalse(
            self._search([("current_employee_skill_ids", "not in", self.held.ids)])
        )
        self.assertEqual(
            self._search([("current_employee_skill_ids", "not in", self.lost.ids)]),
            self.employee,
        )

    def test_any_and_ilike(self):
        self.assertEqual(
            self._search(
                [
                    (
                        "current_employee_skill_ids",
                        "any",
                        [("skill_id", "=", self.skill_piano.id)],
                    )
                ]
            ),
            self.employee,
        )
        self.assertEqual(
            self._search([("current_employee_skill_ids", "ilike", "Piano")]),
            self.employee,
        )
        self.assertFalse(
            self._search([("current_employee_skill_ids", "ilike", "Guitar")])
        )

    def test_an_unsupported_operator_fails_loudly(self):
        with self.assertRaises(NotImplementedError):
            self.env["hr.employee"]._search_current_individual_skill_ids("=", True)
