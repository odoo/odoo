import ast
import os
import re
from contextlib import suppress
from pathlib import Path

import odoo.tests
from odoo.tools.misc import file_open, file_path

import odoo.addons

RE_FORBIDDEN_STATEMENTS = re.compile(r"test.*\.(only|debug)\(")

_DEDICATED_VIEW_SUITES = frozenset({"calendar", "form", "kanban", "list"})


def _misc_view_suites():
    root = Path(file_path("web/static/tests/views"))
    names = {
        entry.name.removesuffix(".test.js")
        for entry in root.iterdir()
        if entry.is_dir() or entry.name.endswith(".test.js")
    }
    return tuple(
        f"@web/views/{name}"
        for name in sorted(names)
        if name not in _DEDICATED_VIEW_SUITES
    )


MISC_VIEW_SUITES = _misc_view_suites()
MISC_SUITES = (
    "@web/boot",
    "@web/env",
    "@web/reactivity",
    "@web/t_custom_click",
    "@web/test_isolation",
    "@web/helpers",
    "@web/interactions",
    "@web/l10n",
    "@web/libs",
    "@web/mock_server",
    "@web/modules",
)
ALL_WEB_SUITE_PREFIXES = (
    "@web/core",
    "@web/components",
    "@web/ui",
    "@web/views/calendar",
    "@web/fields",
    "@web/views/form",
    "@web/views/kanban",
    "@web/views/list",
    *MISC_VIEW_SUITES,
    "@web/search",
    "@web/webclient",
    "@web/public",
    "@web/model",
    *MISC_SUITES,
)


def unit_test_error_checker(message):
    return "[HOOT]" not in message


def _get_filters(test_params):
    filters = []
    for sign, param in test_params:
        parts = param.split(",")
        for part in parts:
            part = part.strip()
            if not part:
                continue
            part_sign = sign
            if part.startswith("-"):
                part = part[1:]
                part_sign = "-" if sign == "+" else "+"
            filters.append((part_sign, part))
    return sorted(filters)


def suite_addon(suite):
    return suite.split("/", 1)[0].lstrip("@")


def runner_suite_prefixes(path):
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    constants = {}
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, ast.Tuple | ast.List)
        ):
            values = []
            for elt in node.value.elts:
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                    values.append(elt.value)
                elif isinstance(elt, ast.Starred) and isinstance(elt.value, ast.Name):
                    values.extend(constants.get(elt.value.id, ()))
            constants[node.targets[0].id] = tuple(values)
    prefixes = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "_run_hoot"
        ):
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    prefixes.add(arg.value)
                elif isinstance(arg, ast.Starred) and isinstance(arg.value, ast.Name):
                    prefixes.update(constants.get(arg.value.id, ()))
    return prefixes


RE_RUNNABLE_TEST = re.compile(r"\btest\s*\(|\btest\.tags\s*\(")


def has_runnable_tests(test_file):
    with suppress(OSError):
        return bool(RE_RUNNABLE_TEST.search(test_file.read_text(encoding="utf-8")))
    return False


def addons_bundling_unit_tests():
    bundled = {}
    for root in (Path(p) for p in odoo.addons.__path__):
        for manifest in root.glob("*/__manifest__.py"):
            addon = manifest.parent
            if "assets_unit_tests" not in manifest.read_text(encoding="utf-8"):
                continue
            tests_root = addon / "static" / "tests"
            suites = [
                f"@{addon.name}/"
                + test_file.relative_to(tests_root).as_posix()[: -len(".test.js")]
                for test_file in sorted(tests_root.rglob("*.test.js"))
                if has_runnable_tests(test_file)
            ]
            if suites:
                bundled.setdefault(addon.name, []).extend(suites)
    return bundled


def uncovered_unit_suites():
    prefixes = set()
    for root in (Path(p) for p in odoo.addons.__path__):
        for runner in root.glob("*/tests/test_js.py"):
            prefixes |= runner_suite_prefixes(runner)
    return [
        suite
        for suites in addons_bundling_unit_tests().values()
        for suite in suites
        if not any(suite == p or suite.startswith(p + "/") for p in prefixes)
    ]


def uncovered_suites_by_addon():
    by_addon = {}
    for suite in uncovered_unit_suites():
        by_addon.setdefault(suite_addon(suite), []).append(suite)
    return by_addon


RE_MOBILE_TAG = re.compile(r"""\.tags\([^)]*["']mobile["']""")


def _suite_test_files(suite):
    addon, _, rel = suite.lstrip("@").partition("/")
    with suppress(FileNotFoundError):
        tests_root = Path(file_path(f"{addon}/static/tests"))
        target = tests_root / rel if rel else tests_root
        if target.is_dir():
            return sorted(target.rglob("*.test.js"))
        leaf = target.with_name(target.name + ".test.js")
        if leaf.is_file():
            return [leaf]
    return []


def _mobile_suites_under(prefixes):
    suites = []
    for prefix in prefixes:
        addon = prefix.lstrip("@").partition("/")[0]
        tests_root = Path(file_path(f"{addon}/static/tests"))
        for test_file in _suite_test_files(prefix):
            with suppress(OSError):
                if RE_MOBILE_TAG.search(test_file.read_text(encoding="utf-8")):
                    rel = test_file.relative_to(tests_root).as_posix()
                    suites.append(f"@{addon}/" + rel[: -len(".test.js")])
    return suites


@odoo.tests.tagged("post_install", "-at_install", "web_js")
class HOOTCommon(odoo.tests.HttpCase):
    def setUp(self):
        super().setUp()
        self.hoot_filters = self.get_hoot_filters()

    def _generate_hash(self, test_string):
        hash_val = 0
        units = test_string.encode("utf-16-le")
        for i in range(0, len(units), 2):
            hash_val = (hash_val << 5) - hash_val + (units[i] | units[i + 1] << 8)
            hash_val &= 0xFFFFFFFF
        return f"{hash_val:08x}"

    def get_hoot_filters(self):
        filters = _get_filters(self._test_params)
        id_params = ""
        for sign, f in filters:
            h = self._generate_hash(f)
            if sign == "-":
                h = f"-{h}"
            id_params += f"&id={h}"
        return id_params

    def test_generate_hoot_hash(self):
        self.assertEqual(self._generate_hash("@web/core"), "e39ce9ba")
        self.assertEqual(self._generate_hash("@web/core/autocomplete"), "69a6561d")
        self.assertEqual(
            self._generate_hash("@web/core/autocomplete/open dropdown on input"),
            "ee565d54",
        )
        self.assertEqual(
            self._generate_hash("@web/services/hotkey_service/hotkeys evil \U0001f479"),
            "25490ab8",
        )

    def test_get_hoot_filter(self):
        self._test_params = []
        self.assertEqual(self.get_hoot_filters(), "")
        expected = "&id=e39ce9ba&id=-69a6561d"
        self._test_params = [("+", "@web/core,-@web/core/autocomplete")]
        self.assertEqual(self.get_hoot_filters(), expected)
        self._test_params = [
            ("+", "@web/core"),
            ("-", "@web/core/autocomplete"),
        ]
        self.assertEqual(self.get_hoot_filters(), expected)
        self._test_params = [("+", "-@web/core/autocomplete,-@web/core/autocomplete2")]
        self.assertEqual(self.get_hoot_filters(), "&id=-69a6561d&id=-cb246db5")
        self._test_params = [("-", "-@web/core/autocomplete,-@web/core/autocomplete2")]
        self.assertEqual(self.get_hoot_filters(), "&id=69a6561d&id=cb246db5")

    @staticmethod
    def _get_module_scope_param(suite_names):
        addons = {name.partition("/")[0].removeprefix("@") for name in suite_names}
        if len(addons) != 1:
            return ""
        addon = addons.pop()
        return f"&module_scope={addon}" if addon else ""

    def test_filtered_module_scope(self):
        self._test_params = [("+", "@web/ui/dialog,@web/ui/popover")]
        self.assertEqual(self._filtered_module_scope_param(), "&module_scope=web")
        self._test_params = [("+", "@web/ui/dialog"), ("-", "@web/ui/dialog/x")]
        self.assertEqual(self._filtered_module_scope_param(), "&module_scope=web")
        self._test_params = [("+", "@web/ui,@mail/core")]
        self.assertEqual(self._filtered_module_scope_param(), "")
        self._test_params = [("-", "@web/ui/dialog")]
        self.assertEqual(self._filtered_module_scope_param(), "")

    def _filtered_module_scope_param(self):
        # a filtered run narrows the bundle like the lane it filters would:
        # on a database with point_of_sale installed an unscoped page loads
        # the POS app's global patches over web's own suites
        selected = [f for sign, f in _get_filters(self._test_params) if sign == "+"]
        return self._get_module_scope_param(selected) if selected else ""

    def _run_hoot(self, *suite_names, preset, timeout=600, tag="", extra=""):
        if self.hoot_filters:
            id_filters = self.hoot_filters
            scope_param = self._filtered_module_scope_param()
        else:
            id_filters = "".join(f"&id={self._generate_hash(n)}" for n in suite_names)
            scope_param = self._get_module_scope_param(suite_names)
        tag_param = f"&tag={tag}" if tag else ""
        # the browser's makeLogger namespaces, relayed by --log-handler <this module>:DEBUG
        log_param = f"&log={spec}" if (spec := os.environ.get("ODOO_HOOT_LOG")) else ""
        self.browser_js(
            f"/web/tests?headless&loglevel=2&preset={preset}&timeout=15000{id_filters}{tag_param}{scope_param}{log_param}{extra}",
            "",
            "",
            login="admin",
            timeout=timeout,
            success_signal="[HOOT] Test suite succeeded",
            error_checker=unit_test_error_checker,
        )


@odoo.tests.tagged("post_install", "-at_install", "web_js")
class WebSuite(HOOTCommon):
    @odoo.tests.no_retry
    def test_core(self):
        self._run_hoot("@web/core", preset="desktop", timeout=900)

    @odoo.tests.no_retry
    def test_components(self):
        self._run_hoot("@web/components", preset="desktop", timeout=900)

    @odoo.tests.no_retry
    def test_ui(self):
        self._run_hoot("@web/ui", preset="desktop")

    @odoo.tests.no_retry
    def test_calendar(self):
        self._run_hoot("@web/views/calendar", preset="desktop")

    @odoo.tests.no_retry
    def test_fields(self):
        self._run_hoot("@web/fields", preset="desktop", timeout=900)

    @odoo.tests.no_retry
    def test_form(self):
        self._run_hoot("@web/views/form", preset="desktop")

    @odoo.tests.no_retry
    def test_kanban(self):
        self._run_hoot("@web/views/kanban", preset="desktop")

    @odoo.tests.no_retry
    def test_list(self):
        self._run_hoot("@web/views/list", preset="desktop")

    @odoo.tests.no_retry
    def test_misc_views(self):
        self._run_hoot(*MISC_VIEW_SUITES, preset="desktop")

    @odoo.tests.no_retry
    def test_search(self):
        self._run_hoot("@web/search", preset="desktop")

    @odoo.tests.no_retry
    def test_webclient(self):
        self._run_hoot("@web/webclient", preset="desktop", timeout=900)

    @odoo.tests.no_retry
    def test_public(self):
        self._run_hoot("@web/public", preset="desktop")

    @odoo.tests.no_retry
    def test_html_editor(self):
        self._run_hoot("@html_editor", preset="desktop", timeout=900)

    @odoo.tests.no_retry
    def test_model(self):
        self._run_hoot("@web/model", preset="desktop")

    @odoo.tests.no_retry
    def test_misc(self):
        self._run_hoot(*MISC_SUITES, preset="desktop")

    @odoo.tests.no_retry
    def test_hoot(self):
        self.browser_js(
            f"/web/static/lib/hoot/tests/index.html?headless&loglevel=2{self.hoot_filters}",
            "",
            "",
            login="admin",
            timeout=1800,
            success_signal="[HOOT] Test suite succeeded",
            error_checker=unit_test_error_checker,
        )

    def test_check_suite(self):
        self._check_forbidden_statements("web.assets_unit_tests")

    def test_suite_filters_cover_every_test_file(self):
        tests_root = Path(file_path("web/static/tests"))
        uncovered = []
        for test_file in sorted(tests_root.rglob("*.test.js")):
            rel = test_file.relative_to(tests_root).as_posix()
            if rel.startswith(("_framework/", "tours/")):
                continue
            suite = "@web/" + rel[: -len(".test.js")]
            if not any(
                suite == prefix or suite.startswith(prefix + "/")
                for prefix in ALL_WEB_SUITE_PREFIXES
            ):
                uncovered.append(suite)
        self.assertFalse(
            uncovered,
            "Test files selected by no CI suite filter (they will never run):"
            "\n- " + "\n- ".join(uncovered),
        )

    def test_every_addon_unit_suite_is_selected_by_a_runner(self):
        from .test_js_addons import GENERATED_ADDONS, KNOWN_FAILING_ADDONS

        uncovered = uncovered_unit_suites()
        generated = GENERATED_ADDONS
        unowned = sorted(
            suite for suite in uncovered if suite_addon(suite) not in generated
        )
        self.assertFalse(
            unowned,
            "Unit test files selected by no runner and by no generated method "
            "(they will never run):\n- " + "\n- ".join(unowned),
        )

        covered_addons = set(addons_bundling_unit_tests()) - {
            suite_addon(s) for s in uncovered
        }
        self.assertFalse(
            generated & covered_addons,
            "These addons have their own runner; AddonSuite must not also "
            f"generate a method for them: {sorted(generated & covered_addons)}",
        )
        self.assertFalse(
            KNOWN_FAILING_ADDONS - generated,
            "These addons no longer bundle uncovered suites; remove them from "
            f"KNOWN_FAILING_ADDONS: {sorted(KNOWN_FAILING_ADDONS - generated)}",
        )

    @staticmethod
    def _suite_addon(suite):
        return suite_addon(suite)

    @staticmethod
    def _runner_suite_prefixes(path):
        return runner_suite_prefixes(path)

    def _uncovered_unit_suites(self):
        return uncovered_unit_suites()

    def _check_forbidden_statements(self, bundle):
        self.env.ref("web.layout").write(
            {
                "arch_db": '<t t-name="web.layout"><html><head><meta charset="utf-8"/><link/><script id="web.layout.odooscript"/><meta/><t t-esc="head"/></head><body><t t-out="0"/></body></html></t>'
            }
        )

        assets = self.env["ir.qweb"]._get_asset_content(bundle)[0]
        if len(assets) == 0:
            self.fail("No assets found in the given test bundle")

        for asset in assets:
            filename = asset["filename"]
            if not filename.endswith(".test.js"):
                continue
            with suppress(FileNotFoundError):
                with file_open(filename, "rb", filter_ext=(".js",)) as fp:
                    if RE_FORBIDDEN_STATEMENTS.search(fp.read().decode("utf-8")):
                        self.fail(
                            "`only()` or `debug()` used in file %r" % asset["url"]
                        )


@odoo.tests.tagged("post_install", "-at_install", "web_js")
class MobileWebSuite(HOOTCommon):
    browser_size = "375x667"
    touch_enabled = True

    def _run_hoot(self, *suite_names, **kwargs):
        if not self.hoot_filters:
            suite_names = _mobile_suites_under(suite_names)
            if not suite_names:
                self.skipTest("no mobile-tagged test under these suites")
        super()._run_hoot(*suite_names, **kwargs)

    @odoo.tests.no_retry
    def test_core(self):
        self._run_hoot("@web/core", preset="mobile", tag="-headless", timeout=900)

    @odoo.tests.no_retry
    def test_components(self):
        self._run_hoot("@web/components", preset="mobile", tag="-headless", timeout=900)

    @odoo.tests.no_retry
    def test_ui(self):
        self._run_hoot("@web/ui", preset="mobile", tag="-headless")

    @odoo.tests.no_retry
    def test_calendar(self):
        self._run_hoot("@web/views/calendar", preset="mobile", tag="-headless")

    @odoo.tests.no_retry
    def test_fields(self):
        self._run_hoot("@web/fields", preset="mobile", tag="-headless", timeout=900)

    @odoo.tests.no_retry
    def test_form(self):
        self._run_hoot("@web/views/form", preset="mobile", tag="-headless")

    @odoo.tests.no_retry
    def test_kanban(self):
        self._run_hoot("@web/views/kanban", preset="mobile", tag="-headless")

    @odoo.tests.no_retry
    def test_list(self):
        self._run_hoot("@web/views/list", preset="mobile", tag="-headless")

    @odoo.tests.no_retry
    def test_misc_views(self):
        self._run_hoot(*MISC_VIEW_SUITES, preset="mobile", tag="-headless")

    @odoo.tests.no_retry
    def test_search(self):
        self._run_hoot("@web/search", preset="mobile", tag="-headless")

    @odoo.tests.no_retry
    def test_webclient(self):
        self._run_hoot("@web/webclient", preset="mobile", tag="-headless", timeout=900)

    @odoo.tests.no_retry
    def test_public(self):
        self._run_hoot("@web/public", preset="mobile", tag="-headless")

    @odoo.tests.no_retry
    def test_html_editor(self):
        self._run_hoot("@html_editor", preset="mobile", tag="-headless", timeout=900)

    @odoo.tests.no_retry
    def test_model(self):
        self._run_hoot("@web/model", preset="mobile", tag="-headless")

    @odoo.tests.no_retry
    def test_misc(self):
        self._run_hoot(*MISC_SUITES, preset="mobile", tag="-headless")
