from pathlib import Path

import odoo.tests
from odoo.tools.misc import file_path

import odoo.addons.web.tests.test_js as web_test_js

ALL_POS_SUITE_PREFIXES = ("@point_of_sale/unit",)


@odoo.tests.tagged("post_install", "-at_install", "point_of_sale_js")
class PointOfSaleSuite(web_test_js.HOOTCommon):
    @odoo.tests.no_retry
    def test_point_of_sale_unit(self):
        self._run_hoot("@point_of_sale/unit", preset="desktop", timeout=900)

    @odoo.tests.no_retry
    def test_point_of_sale_backend_mobile(self):
        self._run_hoot("@point_of_sale/unit/backend", preset="mobile")

    def test_suite_filters_cover_every_test_file(self):
        tests_root = Path(file_path("point_of_sale/static/tests"))
        uncovered = []
        for test_file in sorted((tests_root / "unit").rglob("*.test.js")):
            rel = test_file.relative_to(tests_root).as_posix()
            suite = "@point_of_sale/" + rel[: -len(".test.js")]
            if not any(
                suite == prefix or suite.startswith(prefix + "/")
                for prefix in ALL_POS_SUITE_PREFIXES
            ):
                uncovered.append(suite)
        self.assertFalse(
            uncovered,
            "point_of_sale unit test files selected by no CI suite filter (they "
            "will never run):\n- " + "\n- ".join(uncovered),
        )
