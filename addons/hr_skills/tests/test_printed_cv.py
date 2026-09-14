from datetime import date

from dateutil.relativedelta import relativedelta

from odoo.tests import tagged

from .common import SkillsCase


@tagged("post_install", "-at_install")
class TestPrintedCv(SkillsCase):
    """The CV prints what the employee holds, not everything ever recorded."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = date.today()
        cls.employee = cls.env["hr.employee"].create({"name": "Printed employee"})
        cls.env["hr.employee.skill"].create(
            [
                {
                    "employee_id": cls.employee.id,
                    "skill_id": cls.skill_piano.id,
                    "skill_level_id": cls.level_novice.id,
                    "skill_type_id": cls.skill_type.id,
                    "valid_from": cls.today - relativedelta(months=8),
                    "valid_to": cls.today - relativedelta(months=4),
                },
                {
                    "employee_id": cls.employee.id,
                    "skill_id": cls.skill_piano.id,
                    "skill_level_id": cls.level_expert.id,
                    "skill_type_id": cls.skill_type.id,
                    "valid_from": cls.today
                    - relativedelta(months=4)
                    + relativedelta(days=1),
                },
            ],
        )
        cls.env.flush_all()

    def _render(self):
        html, _kind = self.env["ir.actions.report"]._render_qweb_html(
            self.env.ref("hr_skills.action_report_employee_cv"),
            self.employee.ids,
            data={
                "color_primary": "#666666",
                "color_secondary": "#666666",
                "resume_type_education": self.env["hr.resume.line.type"],
                "skill_type_language": self.env["hr.skill.type"],
                "show_skills": True,
                "show_contact": True,
                "show_others": True,
            },
        )
        return html.decode() if isinstance(html, bytes) else html

    def test_a_versioned_skill_is_printed_once(self):
        # Two rows for one skill is the versioning engine's normal output: the
        # superseded level keeps its history and the current one carries on.
        # Printing both put the same skill on the CV twice, with two progress
        # bars at different levels and no level name to tell them apart.
        self.assertEqual(len(self._piano_rows()), 2)
        self.assertEqual(self._render().count("Piano"), 1)

    def test_a_skill_no_longer_held_is_not_printed(self):
        self.env["hr.employee.skill"].create(
            {
                "employee_id": self.employee.id,
                "skill_id": self.skill_guitar.id,
                "skill_level_id": self.level_novice.id,
                "skill_type_id": self.skill_type.id,
                "valid_from": self.today - relativedelta(months=8),
                "valid_to": self.today - relativedelta(months=4),
            },
        )
        self.env.flush_all()
        self.assertNotIn("Guitar", self._render())

    def test_two_sections_sharing_a_name_are_both_printed(self):
        first, second = self.env["hr.resume.line.type"].create(
            [{"name": "Tours", "sequence": 1}, {"name": "Tours", "sequence": 2}]
        )
        self.env["hr.resume.line"].create(
            [
                {
                    "employee_id": self.employee.id,
                    "name": "Europe",
                    "line_type_id": first.id,
                },
                {
                    "employee_id": self.employee.id,
                    "name": "Asia",
                    "line_type_id": second.id,
                },
            ]
        )
        self.env.flush_all()
        html = self._render()
        self.assertIn("Europe", html)
        self.assertIn("Asia", html)

    def test_a_lapsed_certification_is_not_printed_as_a_skill(self):
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
        self.env.flush_all()
        self.assertIn(
            self.certification, self.employee.current_employee_skill_ids.skill_id
        )
        self.assertNotIn("Conservatory", self._render())

    def _piano_rows(self):
        return self.employee.employee_skill_ids.filtered(
            lambda skill: skill.skill_id == self.skill_piano
        )
