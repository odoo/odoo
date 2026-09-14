from freezegun import freeze_time

from odoo.tests import tagged

from .common import HomeworkingCase


@tagged("post_install", "-at_install")
class TestGetViews(HomeworkingCase):
    def _view(self, view_type, arch):
        return self.env["ir.ui.view"].create(
            {"arch": arch, "model": "hr.employee", "type": view_type}
        )

    @freeze_time("2026-01-28")
    def test_the_marker_becomes_the_current_weekday_field(self):
        view = self._view(
            "list", """<list><field name="today_location_name"/></list>"""
        )
        result = self.env["hr.employee"].get_views([(view.id, "list")])
        self.assertEqual(
            result["views"]["list"]["arch"],
            """<list><field name="wednesday_location_id"/></list>""",
        )
        self.assertIn(
            "wednesday_location_id", result["models"]["hr.employee"]["fields"]
        )

    @freeze_time("2026-01-28")
    def test_the_marker_becomes_the_current_weekday_field_in_a_group_by(self):
        view = self._view(
            "search",
            """<search><filter name="x" string="X" """
            """context="{'group_by': 'today_location_name'}"/></search>""",
        )
        result = self.env["hr.employee"].get_views([(view.id, "search")])
        self.assertIn("wednesday_location_id", result["views"]["search"]["arch"])
        self.assertNotIn("today_location_name", result["views"]["search"]["arch"])

    @freeze_time("2026-01-28")
    def test_a_label_that_merely_contains_the_marker_is_left_alone(self):
        view = self._view(
            "list",
            """<list><field name="name" string="today_location_name_report"/></list>""",
        )
        result = self.env["hr.employee"].get_views([(view.id, "list")])
        self.assertIn("today_location_name_report", result["views"]["list"]["arch"])

    @freeze_time("2026-01-28")
    def test_another_field_is_not_rewritten(self):
        view = self._view("list", """<list><field name="work_location_name"/></list>""")
        result = self.env["hr.employee"].get_views([(view.id, "list")])
        self.assertEqual(
            result["views"]["list"]["arch"],
            """<list><field name="work_location_name"/></list>""",
        )
