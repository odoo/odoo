import json

from freezegun import freeze_time
from lxml import etree

from odoo.tests import tagged
from odoo.tools.view_ir import from_arch

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

    @freeze_time("2026-01-28")
    def test_the_client_reads_the_rewritten_view_not_only_the_arch(self):
        # get_view ships `ir` beside `arch` and the client reads `ir` first, so
        # an override that rewrites only the arch rewrites nothing the user sees.
        view = self._view(
            "list", """<list><field name="today_location_name"/></list>"""
        )
        result = self.env["hr.employee"].get_views([(view.id, "list")])["views"]["list"]
        self.assertIn("ir", result)
        ir = json.dumps(result["ir"])
        self.assertNotIn("today_location_name", ir)
        self.assertIn("wednesday_location_id", ir)

    @freeze_time("2026-01-28")
    def test_the_ir_is_the_one_the_arch_derives(self):
        for view_type, arch in (
            ("list", """<list><field name="today_location_name"/></list>"""),
            (
                "search",
                (
                    """<search><filter name="x" string="X" """
                    """context="{'group_by': 'today_location_name'}"/></search>"""
                ),
            ),
        ):
            view = self._view(view_type, arch)
            result = self.env["hr.employee"].get_views([(view.id, view_type)])
            payload = result["views"][view_type]
            from_the_arch = from_arch(etree.fromstring(payload["arch"])).to_dict()
            self.assertEqual(
                payload["ir"], from_the_arch, f"{view_type} ir disagrees with its arch"
            )
