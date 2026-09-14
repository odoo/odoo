import importlib.util
from datetime import date
from pathlib import Path

from odoo.tests import tagged

from .common import SkillsCase

MIGRATION = (
    Path(__file__).resolve().parents[1] / "migrations" / "1.3" / "post-migrate.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location(
        "hr_skills_post_migrate_1_3", MIGRATION
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@tagged("post_install", "-at_install")
class TestMigration13(SkillsCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.migration = _load_migration()
        cls.employee = cls.env["hr.employee"].create({"name": "Migrated employee"})
        cls.job = cls.env["hr.job"].create({"name": "Migrated job"})

    def _row(self, model, owner_field, owner, skill, level, skill_type, valid_from):
        return self.env[model].create(
            {
                owner_field: owner.id,
                "skill_id": skill.id,
                "skill_level_id": level.id,
                "skill_type_id": skill_type.id,
                "valid_from": valid_from,
                "valid_to": valid_from,
            }
        )

    def _force(self, rows, valid_from, valid_to):
        self.env.flush_all()
        self.env.cr.execute(
            f"UPDATE {rows._table} SET valid_from = %s, valid_to = %s WHERE id = ANY(%s)",
            (valid_from, valid_to, rows.ids),
        )
        self.env.invalidate_all()

    def test_stored_urls_become_web_addresses(self):
        line = self.env["hr.resume.line"].create(
            {"employee_id": self.employee.id, "name": "Course"}
        )
        for stored, expected in (
            ("javascript:alert(1)", "http://javascript:alert(1)"),
            ("coursera.org/learn", "http://coursera.org/learn"),
            ("https://www.edx.org/x", "https://www.edx.org/x"),
        ):
            with self.subTest(stored=stored):
                self.env.cr.execute(
                    "UPDATE hr_resume_line SET external_url = %s WHERE id = %s",
                    (stored, line.id),
                )
                self.migration._normalize_resume_urls(self.env.cr)
                self.env.invalidate_all()
                self.assertEqual(line.external_url, expected)

    def test_overlapping_rows_end_before_their_successor(self):
        earlier, later, same_start = (
            self._row(
                "hr.employee.skill",
                "employee_id",
                self.employee,
                self.skill_piano,
                level,
                self.skill_type,
                date(2020, 1, day),
            )
            for level, day in (
                (self.level_novice, 1),
                (self.level_expert, 2),
                (self.level_novice, 3),
            )
        )
        self._force(earlier, date(2025, 1, 1), None)
        self._force(later, date(2025, 3, 1), None)
        self._force(same_start, date(2025, 3, 1), date(2025, 6, 1))

        repaired = self.migration._repair_overlapping_rows(self.env)

        self.assertEqual(earlier.valid_to, date(2025, 2, 28))
        self.assertFalse(later.exists())
        self.assertEqual(
            (same_start.valid_from, same_start.valid_to),
            (date(2025, 3, 1), date(2025, 6, 1)),
        )
        self.assertEqual(
            repaired["hr.employee.skill"], (sorted(earlier.ids), sorted(later.ids))
        )

    def test_overlapping_certifications_are_left_where_the_model_allows_them(self):
        first, renewal = (
            self._row(
                "hr.employee.skill",
                "employee_id",
                self.employee,
                self.certification,
                self.level_certified,
                self.certification_type,
                date(2020, 1, day),
            )
            for day in (1, 2)
        )
        job_first, job_second = (
            self._row(
                "hr.job.skill",
                "job_id",
                self.job,
                self.certification,
                self.level_certified,
                self.certification_type,
                date(2020, 1, day),
            )
            for day in (1, 2)
        )
        self._force(first, date(2025, 1, 1), date(2025, 12, 31))
        self._force(renewal, date(2025, 6, 1), None)
        self._force(job_first, date(2025, 1, 1), None)
        self._force(job_second, date(2025, 6, 1), None)

        self.migration._repair_overlapping_rows(self.env)

        self.assertEqual(first.valid_to, date(2025, 12, 31))
        self.assertEqual(job_first.valid_to, date(2025, 5, 31))

    def test_the_report_rules_are_rewritten_from_the_data_file(self):
        rules = self.env["ir.rule"].browse(
            [
                self.env.ref(f"hr_skills.{xmlid}").id
                for xmlid in self.migration.RULES_REWRITTEN
            ]
        )
        expected = {rule: (rule.name, rule.domain_force) for rule in rules}
        rules.write({"name": "Stale", "domain_force": "[(0, '=', 1)]"})

        self.migration._rewrite_rules(self.env)

        for rule, values in expected.items():
            self.assertEqual((rule.name, rule.domain_force), values)
        self.assertIn(
            "child_of",
            self.env.ref("hr_skills.hr_employee_skill_report_manager").domain_force,
        )

    def test_open_certification_reminders_are_linked_by_their_summary(self):
        employee = self.env["hr.employee"].create({"name": "Reminded"})
        reminder, stranger = employee.activity_schedule(
            act_type_xmlid="hr_skills.mail_activity_data_upload_certification",
            summary="Conservatory: Certified",
        ) | employee.activity_schedule(
            act_type_xmlid="hr_skills.mail_activity_data_upload_certification",
            summary="Something else",
        )
        self.migration._link_certification_reminders(self.env)
        self.assertEqual(
            (reminder.certification_skill_id, reminder.certification_skill_level_id),
            (self.certification, self.level_certified),
        )
        self.assertFalse(stranger.certification_skill_id)
