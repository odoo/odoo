from pathlib import Path

import odoo.tests
from odoo.tools.misc import file_path

import odoo.addons.web.tests.test_js as web_test_js

VIEW_SUITES = (
    "@document/views",
    "@document/activity_view",
    "@document/kanban_view",
    "@document/list_view",
    "@document/multi_view",
    "@document/search_model",
    "@document/search_panel",
    "@document/select_all",
    "@document/draggable_drop_rules",
)
PDF_SUITES = (
    "@document/pdf_manager",
    "@document/pdf_page_store",
)
MISC_SUITES = (
    "@document/activity_menu_patch",
    "@document/chatter_visible_storage",
    "@document/cog_menu_pin_actions",
    "@document/details_panel",
    "@document/document_systray_activity_menu",
    "@document/document_to_restore",
    "@document/error_dialog_patch",
    "@document/log_access",
    "@document/manage_versions",
    "@document/model_mixin",
    "@document/notifications_systray",
    "@document/operation",
    "@document/preview_lifecycle",
    "@document/thumbnail_service",
)
ALL_DOCUMENTS_SUITE_PREFIXES = (*VIEW_SUITES, *PDF_SUITES, *MISC_SUITES)

KNOWN_FAILURES = ()


@odoo.tests.tagged("post_install", "-at_install", "documents_js")
class DocumentsSuite(web_test_js.HOOTCommon):
    def _excluding_known_failures(self, *prefixes):
        return "".join(
            f"&id=-{self._generate_hash(name)}"
            for name in KNOWN_FAILURES
            if any(name.startswith(prefix + "/") for prefix in prefixes)
        )

    @odoo.tests.no_retry
    def test_views(self):
        self._run_hoot(
            *VIEW_SUITES,
            preset="desktop",
            timeout=900,
            extra=self._excluding_known_failures(*VIEW_SUITES),
        )

    @odoo.tests.no_retry
    def test_pdf(self):
        self._run_hoot(*PDF_SUITES, preset="desktop")

    @odoo.tests.no_retry
    def test_misc(self):
        self._run_hoot(
            *MISC_SUITES,
            preset="desktop",
            timeout=900,
            extra=self._excluding_known_failures(*MISC_SUITES),
        )

    def test_known_failures_are_still_named_correctly(self):
        tests_root = Path(file_path("document/static/tests"))
        suites = {
            "@document/" + p.relative_to(tests_root).as_posix()[: -len(".test.js")]
            for p in tests_root.rglob("*.test.js")
        }
        for name in KNOWN_FAILURES:
            self.assertTrue(
                any(name.startswith(suite + "/") for suite in suites),
                f"KNOWN_FAILURES entry names no existing test file: {name}",
            )

    def test_suite_filters_cover_every_test_file(self):
        tests_root = Path(file_path("document/static/tests"))
        uncovered = []
        for test_file in sorted(tests_root.rglob("*.test.js")):
            rel = test_file.relative_to(tests_root).as_posix()
            suite = "@document/" + rel[: -len(".test.js")]
            if not any(
                suite == prefix or suite.startswith(prefix + "/")
                for prefix in ALL_DOCUMENTS_SUITE_PREFIXES
            ):
                uncovered.append(suite)
        self.assertFalse(
            uncovered,
            "Documents test files selected by no CI suite filter (they will "
            "never run):\n- " + "\n- ".join(uncovered),
        )
