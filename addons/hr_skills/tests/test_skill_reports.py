from datetime import date

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.tests import tagged
from odoo.tests.common import new_test_user

from .common import SkillsCase


@tagged("post_install", "-at_install")
class TestSkillReportScope(SkillsCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = date.today()
        cls.employee = cls.env["hr.employee"].create({"name": "Reported employee"})

    def test_a_skill_ending_in_the_future_is_still_current(self):
        self.env["hr.employee.skill"].create(
            {
                "employee_id": self.employee.id,
                "skill_id": self.skill_piano.id,
                "skill_level_id": self.level_expert.id,
                "skill_type_id": self.skill_type.id,
                "valid_from": self.today - relativedelta(months=1),
                "valid_to": self.today + relativedelta(months=1),
            },
        )
        self.env.flush_all()

        rows = self.env["hr.employee.skill.report"].search(
            [("employee_id", "=", self.employee.id)]
        )
        self.assertEqual(rows.skill_id, self.skill_piano)

    def test_an_expired_skill_is_not_current(self):
        self.env["hr.employee.skill"].create(
            {
                "employee_id": self.employee.id,
                "skill_id": self.skill_guitar.id,
                "skill_level_id": self.level_novice.id,
                "skill_type_id": self.skill_type.id,
                "valid_from": self.today - relativedelta(months=2),
                "valid_to": self.today - relativedelta(days=1),
            },
        )
        self.env.flush_all()

        rows = self.env["hr.employee.skill.report"].search(
            [("employee_id", "=", self.employee.id)]
        )
        self.assertFalse(rows)

    def test_a_skill_starting_later_is_not_current(self):
        self.env["hr.employee.skill"].create(
            {
                "employee_id": self.employee.id,
                "skill_id": self.skill_guitar.id,
                "skill_level_id": self.level_novice.id,
                "skill_type_id": self.skill_type.id,
                "valid_from": self.today + relativedelta(days=10),
            },
        )
        self.env.flush_all()

        rows = self.env["hr.employee.skill.report"].search(
            [("employee_id", "=", self.employee.id)]
        )
        self.assertFalse(rows)

    def test_the_report_hides_the_skills_of_an_archived_employee(self):
        self.env["hr.employee.skill"].create(
            {
                "employee_id": self.employee.id,
                "skill_id": self.skill_piano.id,
                "skill_level_id": self.level_expert.id,
                "skill_type_id": self.skill_type.id,
                "valid_from": self.today - relativedelta(months=1),
            },
        )
        self.employee.active = False
        self.env.flush_all()

        report = self.env["hr.employee.skill.report"]
        self.assertFalse(report.search([("employee_id", "=", self.employee.id)]))
        self.assertTrue(
            report.with_context(active_test=False).search(
                [("employee_id", "=", self.employee.id)]
            )
        )


@tagged("post_install", "-at_install")
class TestCertificationReportValidity(SkillsCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = date.today()
        cls.employee = cls.env["hr.employee"].create({"name": "Certified employee"})
        cls.env["hr.employee.skill"].create(
            {
                "employee_id": cls.employee.id,
                "skill_id": cls.certification.id,
                "skill_level_id": cls.level_certified.id,
                "skill_type_id": cls.certification_type.id,
                "valid_from": cls.today - relativedelta(days=1),
                "valid_to": cls.today + relativedelta(days=10),
            },
        )
        cls.env.flush_all()

    def _rows(self, employee, active):
        return self.env["hr.employee.certification.report"].search(
            [("employee_id", "=", employee.id), ("active", "=", active)],
        )

    def test_a_valid_certification_reads_active(self):
        self.assertTrue(self._rows(self.employee, True))
        self.assertFalse(self._rows(self.employee, False))

    def test_a_certification_that_ended_yesterday_reads_expired(self):
        lapsed = self.env["hr.employee"].create({"name": "Lapsed employee"})
        self.env["hr.employee.skill"].create(
            {
                "employee_id": lapsed.id,
                "skill_id": self.certification.id,
                "skill_level_id": self.level_certified.id,
                "skill_type_id": self.certification_type.id,
                "valid_from": self.today - relativedelta(months=2),
                "valid_to": self.today - relativedelta(days=1),
            },
        )
        self.env.flush_all()

        self.assertFalse(self._rows(lapsed, True))
        self.assertTrue(self._rows(lapsed, False))

    def test_the_view_reads_the_clock_rather_than_a_literal(self):
        self.env.cr.execute(
            "SELECT pg_get_viewdef('hr_employee_certification_report', true)"
        )
        definition = self.env.cr.fetchone()[0]
        self.assertIn("now()", definition)
        self.assertNotRegex(definition, r"'\d{4}-\d{2}-\d{2}'::date")

    def test_the_view_and_the_orm_agree_on_today(self):
        self.env.cr.execute("SELECT (now() AT TIME ZONE 'UTC')::date, CURRENT_DATE")
        view_today, session_today = self.env.cr.fetchone()
        self.assertEqual(view_today, fields.Date.today())
        del session_today


@tagged("post_install", "-at_install")
class TestCertificationReportAccess(SkillsCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = date.today()
        cls.their_department = cls.env["hr.department"].create({"name": "Strings"})
        cls.someone_else = cls.env["hr.employee"].create(
            {"name": "Somebody else", "department_id": cls.their_department.id},
        )
        cls.env["hr.employee.skill"].create(
            {
                "employee_id": cls.someone_else.id,
                "skill_id": cls.certification.id,
                "skill_level_id": cls.level_certified.id,
                "skill_type_id": cls.certification_type.id,
                "valid_from": cls.today - relativedelta(days=1),
            },
        )
        cls.onlooker = new_test_user(
            cls.env, login="skills.onlooker", groups="base.group_user"
        )
        cls.env["hr.employee"].create(
            {"name": "The onlooker", "user_id": cls.onlooker.id},
        )
        cls.env.flush_all()

    def test_the_report_is_scoped_like_its_sibling(self):
        """The certification report had no ir.rule at all; its two siblings do."""
        certifications = (
            self.env["hr.employee.certification.report"]
            .with_user(self.onlooker)
            .search([("employee_id", "=", self.someone_else.id)])
        )
        skills = (
            self.env["hr.employee.skill.report"]
            .with_user(self.onlooker)
            .search([("employee_id", "=", self.someone_else.id)])
        )
        self.assertEqual(
            len(certifications),
            len(skills),
            "the two reports must answer the same audience the same way",
        )

    def test_the_rule_scopes_the_report_and_not_the_data(self):
        """The same certifications stay readable through hr.employee.skill.

        This is deliberate -- `hr_skill_rule_employee` grants base.group_user
        read with domain [(1, '=', 1)], and hr.employee.certification_ids
        surfaces the same rows on the profile page. The report rules make the
        three report models consistent; they are not a confidentiality boundary,
        and treating them as one would be wrong.
        """
        rows = (
            self.env["hr.employee.skill"]
            .with_user(self.onlooker)
            .search([("employee_id", "=", self.someone_else.id)])
        )
        self.assertTrue(rows, "hr.employee.skill is world-readable by design")
        self.assertEqual(rows.skill_id, self.certification)

    def test_a_department_manager_can(self):
        manager_employee = self.env["hr.employee"].search(
            [("user_id", "=", self.onlooker.id)]
        )
        self.their_department.manager_id = manager_employee
        self.env.flush_all()
        self.env.invalidate_all()

        rows = (
            self.env["hr.employee.certification.report"]
            .with_user(self.onlooker)
            .search([("employee_id", "=", self.someone_else.id)])
        )
        self.assertTrue(rows)

    def test_a_line_manager_reads_all_three_reports(self):
        manager_employee = self.env["hr.employee"].search(
            [("user_id", "=", self.onlooker.id)]
        )
        self.someone_else.parent_id = manager_employee
        self.env["hr.employee.skill"].create(
            {
                "employee_id": self.someone_else.id,
                "skill_id": self.skill_piano.id,
                "skill_level_id": self.level_novice.id,
                "skill_type_id": self.skill_type.id,
                "valid_from": self.today - relativedelta(days=3),
            },
        )
        self.env.flush_all()
        self.env.invalidate_all()

        for model in (
            "hr.employee.certification.report",
            "hr.employee.skill.report",
            "hr.employee.skill.history.report",
        ):
            with self.subTest(model=model):
                self.assertTrue(
                    self.env[model]
                    .with_user(self.onlooker)
                    .search([("employee_id", "=", self.someone_else.id)])
                )

    def test_a_department_manager_reads_the_history(self):
        manager_employee = self.env["hr.employee"].search(
            [("user_id", "=", self.onlooker.id)]
        )
        self.their_department.manager_id = manager_employee
        self.env.flush_all()
        self.env.invalidate_all()

        self.assertTrue(
            self.env["hr.employee.skill.history.report"]
            .with_user(self.onlooker)
            .search([("employee_id", "=", self.someone_else.id)])
        )

    def test_the_report_does_not_cross_companies(self):
        """An HR user in one company must not see another company's rows."""
        other_company = self.env["res.company"].create({"name": "Other company"})
        elsewhere = self.env["hr.employee"].create(
            {"name": "Employee elsewhere", "company_id": other_company.id},
        )
        self.env["hr.employee.skill"].create(
            {
                "employee_id": elsewhere.id,
                "skill_id": self.certification.id,
                "skill_level_id": self.level_certified.id,
                "skill_type_id": self.certification_type.id,
                "valid_from": self.today - relativedelta(days=1),
            },
        )
        hr_user = new_test_user(
            self.env, login="skills.hr.onecompany", groups="hr.group_hr_user"
        )
        hr_user.write(
            {
                "company_ids": [(6, 0, [self.env.company.id])],
                "company_id": self.env.company.id,
            },
        )
        self.env.flush_all()

        rows = (
            self.env["hr.employee.certification.report"]
            .with_user(hr_user)
            .with_context(allowed_company_ids=[self.env.company.id])
            .search([("employee_id", "=", elsewhere.id)])
        )
        self.assertFalse(
            rows,
            "the certification report was the only one of the three report "
            "models with no multi-company rule",
        )

    def test_an_hr_user_can(self):
        hr_user = new_test_user(
            self.env, login="skills.hr.user", groups="hr.group_hr_user"
        )
        rows = (
            self.env["hr.employee.certification.report"]
            .with_user(hr_user)
            .search([("employee_id", "=", self.someone_else.id)])
        )
        self.assertTrue(rows)


@tagged("post_install", "-at_install")
class TestSkillHistoryReport(SkillsCase):
    def test_a_row_keeps_its_id_when_other_rows_appear(self):
        employee, other = self.env["hr.employee"].create(
            [{"name": "Stable employee"}, {"name": "Newcomer"}]
        )
        self.env["hr.employee.skill"].create(
            {
                "employee_id": employee.id,
                "skill_id": self.skill_piano.id,
                "skill_level_id": self.level_novice.id,
                "skill_type_id": self.skill_type.id,
                "valid_from": date(2025, 1, 1),
            },
        )
        self.env.flush_all()
        report = self.env["hr.employee.skill.history.report"]
        before = report.search([("employee_id", "=", employee.id)]).ids

        self.env["hr.employee.skill"].create(
            {
                "employee_id": other.id,
                "skill_id": self.skill_guitar.id,
                "skill_level_id": self.level_novice.id,
                "skill_type_id": self.skill_type.id,
                "valid_from": date(2024, 1, 1),
            },
        )
        self.env.flush_all()

        self.assertEqual(report.search([("employee_id", "=", employee.id)]).ids, before)
        self.assertEqual(len(report.browse(before).exists()), 1)

    def test_the_report_carries_department_and_company(self):
        department = self.env["hr.department"].create({"name": "Percussion"})
        employee = self.env["hr.employee"].create(
            {"name": "Historic employee", "department_id": department.id},
        )
        self.env["hr.employee.skill"].create(
            {
                "employee_id": employee.id,
                "skill_id": self.skill_piano.id,
                "skill_level_id": self.level_novice.id,
                "skill_type_id": self.skill_type.id,
                "valid_from": date.today() - relativedelta(months=1),
            },
        )
        self.env.flush_all()

        rows = self.env["hr.employee.skill.history.report"].search(
            [("department_id", "=", department.id)]
        )
        self.assertTrue(rows)
        self.assertEqual(rows.employee_id, employee)
        self.assertEqual(rows.company_id, employee.company_id)

    def test_the_department_action_opens_the_history_report(self):
        action = self.env.ref("hr_skills.action_hr_employee_skill_log_department")
        self.assertEqual(action.res_model, "hr.employee.skill.history.report")

        search_view = self.env.ref(
            "hr_skills.hr_employee_skill_history_report_view_search"
        )
        self.assertEqual(action.search_view_id, search_view)
        for filter_name in ("group_by_skill_type_id", "group_by_skill_id"):
            self.assertIn(f'name="{filter_name}"', search_view.arch)


@tagged("post_install", "-at_install")
class TestSkillDataMultiCompany(SkillsCase):
    """Skills and resume lines follow the employee's company.

    hr.employee has carried a multi-company rule for as long as it has existed;
    the rows hanging off it did not, so an HR user in one company could
    enumerate another company's skill and resume rows -- the employee behind
    them was already unreadable, but their existence and level were not.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = date.today()
        cls.other_company = cls.env["res.company"].create({"name": "Elsewhere"})
        cls.stranger = cls.env["hr.employee"].create(
            {"name": "Stranger", "company_id": cls.other_company.id},
        )
        cls.neighbour = cls.env["hr.employee"].create(
            {"name": "Neighbour", "company_id": cls.env.company.id},
        )
        for employee in (cls.stranger, cls.neighbour):
            cls.env["hr.employee.skill"].create(
                {
                    "employee_id": employee.id,
                    "skill_id": cls.skill_piano.id,
                    "skill_level_id": cls.level_novice.id,
                    "skill_type_id": cls.skill_type.id,
                    "valid_from": cls.today - relativedelta(days=5),
                },
            )
            cls.env["hr.resume.line"].create(
                {
                    "employee_id": employee.id,
                    "name": f"{employee.name} line",
                    "date_start": cls.today,
                },
            )
        cls.local_hr = new_test_user(
            cls.env, login="skills.local.hr", groups="hr.group_hr_user"
        )
        cls.local_hr.write(
            {
                "company_ids": [(6, 0, [cls.env.company.id])],
                "company_id": cls.env.company.id,
            },
        )
        cls.env.flush_all()

    def _visible(self, model, employee):
        return (
            self.env[model]
            .with_user(self.local_hr)
            .with_context(allowed_company_ids=[self.env.company.id])
            .search([("employee_id", "=", employee.id)])
        )

    def test_another_company_skills_are_not_enumerable(self):
        self.assertFalse(self._visible("hr.employee.skill", self.stranger))

    def test_another_company_resume_lines_are_not_enumerable(self):
        self.assertFalse(self._visible("hr.resume.line", self.stranger))

    def test_the_rule_leaves_the_user_own_company_alone(self):
        self.assertTrue(self._visible("hr.employee.skill", self.neighbour))
        self.assertTrue(self._visible("hr.resume.line", self.neighbour))

    def test_an_employee_still_reads_their_own_skills(self):
        user = new_test_user(
            self.env, login="skills.own.rows", groups="base.group_user"
        )
        user.write(
            {
                "company_ids": [(6, 0, [self.env.company.id])],
                "company_id": self.env.company.id,
            },
        )
        employee = self.env["hr.employee"].create(
            {
                "name": "Owns rows",
                "user_id": user.id,
                "company_id": self.env.company.id,
            },
        )
        self.env["hr.employee.skill"].create(
            {
                "employee_id": employee.id,
                "skill_id": self.skill_guitar.id,
                "skill_level_id": self.level_novice.id,
                "skill_type_id": self.skill_type.id,
                "valid_from": self.today,
            },
        )
        self.env.flush_all()

        rows = (
            self.env["hr.employee.skill"]
            .with_user(user)
            .search([("employee_id", "=", employee.id)])
        )
        self.assertTrue(rows)


@tagged("post_install", "-at_install")
class TestReportRowIdentity(SkillsCase):
    """A row of the skill or certification report *is* one hr.employee.skill
    row, so it carries that row's id. row_number() gave every read a fresh
    numbering, so the same row answered to a different id from one query to
    the next and nothing could be opened, followed or compared across reads."""

    def test_the_skill_report_row_is_the_skill_row(self):
        employee = self.env["hr.employee"].create({"name": "Identity employee"})
        row = self.env["hr.employee.skill"].create(
            {
                "employee_id": employee.id,
                "skill_id": self.skill_piano.id,
                "skill_level_id": self.level_expert.id,
                "skill_type_id": self.skill_type.id,
                "valid_from": date.today(),
            },
        )
        self.env.flush_all()
        report = self.env["hr.employee.skill.report"].browse(row.id)
        self.assertEqual(report.employee_id, employee)
        self.assertEqual(report.skill_id, self.skill_piano)

    def test_the_certification_report_row_is_the_certification_row(self):
        employee = self.env["hr.employee"].create({"name": "Identity holder"})
        row = self.env["hr.employee.skill"].create(
            {
                "employee_id": employee.id,
                "skill_id": self.certification.id,
                "skill_level_id": self.level_certified.id,
                "skill_type_id": self.certification_type.id,
                "valid_from": date.today(),
            },
        )
        self.env.flush_all()
        report = self.env["hr.employee.certification.report"].browse(row.id)
        self.assertEqual(report.employee_id, employee)
        self.assertTrue(report.active)
