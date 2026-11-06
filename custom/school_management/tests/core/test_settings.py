import uuid
from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestUniversitySettings(TransactionCase):
    def setUp(self):
        super().setUp()
        self.AcademicYear = self.env["university.academic.year"].sudo()
        self.Semester = self.env["university.semester"].sudo()

    def _create_year(self, name, date_start="2035-09-01", date_end="2036-06-30"):
        unique_name = f"{name} {uuid.uuid4().hex[:6]}"
        return self.AcademicYear.create(
            {
                "name": unique_name,
                "date_start": date_start,
                "date_end": date_end,
            }
        )

    def _create_semester(self, year, name="Semester 1", date_start="2035-09-01", date_end="2036-01-31"):
        return self.Semester.create(
            {
                "name": name,
                "academic_year_id": year.id,
                "semester_type": "semester_1",
                "date_start": fields.Date.to_date(date_start),
                "date_end": fields.Date.to_date(date_end),
            }
        )

    def _create_settings(self, vals):
        Settings = self.env["res.config.settings"]
        default_vals = Settings.default_get(list(Settings.fields_get().keys()))
        if "default_picking_policy" in Settings._fields and not default_vals.get("default_picking_policy"):
            default_vals["default_picking_policy"] = "direct"
        default_vals.update(vals)
        return Settings.create(default_vals)

    def test_saving_settings_syncs_current_academic_year(self):
        previous_year = self._create_year("2035-2036", "2035-09-01", "2036-06-30")
        self.AcademicYear.search([("current", "=", True)]).write({"current": False})
        previous_year.current = True
        selected_year = self._create_year("2036-2037", "2036-09-01", "2037-06-30")
        semester = self._create_semester(selected_year, date_start="2036-09-01", date_end="2037-01-31")

        settings = self._create_settings(
            {
                "current_academic_year_id": selected_year.id,
                "current_semester_id": semester.id,
            }
        )
        settings.execute()

        self.assertFalse(previous_year.current)
        self.assertTrue(selected_year.current)
        self.assertEqual(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("school_management.current_academic_year_id"),
            str(selected_year.id),
        )
        self.assertEqual(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("school_management.current_semester_id"),
            str(semester.id),
        )

    def test_settings_reject_semester_from_another_year(self):
        year_a = self._create_year("2037-2038", "2037-09-01", "2038-06-30")
        year_b = self._create_year("2038-2039", "2038-09-01", "2039-06-30")
        semester_b = self._create_semester(year_b, date_start="2038-09-01", date_end="2039-01-31")

        with self.assertRaises(ValidationError):
            self._create_settings(
                {
                    "current_academic_year_id": year_a.id,
                    "current_semester_id": semester_b.id,
                }
            )

    def test_settings_menu_is_system_admin_only(self):
        menu = self.env.ref("school_management.menu_university_settings")
        self.assertIn(self.env.ref("base.group_system"), menu.group_ids)
        self.assertNotIn(
            self.env.ref("school_management.group_school_admin"), menu.group_ids
        )
