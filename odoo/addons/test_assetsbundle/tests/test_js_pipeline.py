import re
from types import SimpleNamespace
from unittest.mock import patch

from odoo.tests.common import BaseCase, TransactionCase
from odoo.tools import config
from odoo.tools.assets.esm_graph import _MODULE_SYNTAX_RE
from odoo.tools.assets.esm_registry import esm_registry
from odoo.tools.assets.js_scan import rjsmin_misreads
from odoo.tools.json import scriptsafe as json

from .common import asset_file, make_bundle
from odoo.addons.base.models.assetsbundle import (
    AssetsBundle,
    JavascriptAsset,
    is_odoo_module,
)
from odoo.addons.base.models.assetsbundle.js_pipeline import (
    JsPipeline,
    ModuleSyntaxInLegacyBundleError,
)

MODULE_JS = 'import { x } from "@web/core/registry";\nexport const y = x;\n'
PLAIN_JS = "(function () {\n    var x = 1;\n    window.testX = x;\n})();\n"
TEMPLATE_XML = "<templates><t t-name='audit.g10.tpl'><div>x</div></t></templates>"
UNTERMINATED_JS = "window.auditG10 = window.auditG10Src\n"

_B64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"


def _vlq_decode_mappings(mappings):
    out = []
    gen_line = 0
    src_idx = 0
    orig_line0 = 0
    for field in mappings.split(";"):
        gen_line += 1
        for seg in field.split(","):
            if not seg:
                continue
            vals = []
            shift = acc = 0
            for ch in seg:
                d = _B64.index(ch)
                acc += (d & 31) << shift
                if d & 32:
                    shift += 5
                else:
                    vals.append((acc >> 1) * (-1 if acc & 1 else 1))
                    acc = shift = 0
            if len(vals) >= 4:
                src_idx += vals[1]
                orig_line0 += vals[2]
                out.append((gen_line, src_idx, orig_line0 + 1))
    return out


class TestModuleSyntaxGuard(TransactionCase):
    BUNDLE = "test_assetsbundle.legacy_guard"

    def _legacy_bundle(self, name=None):
        return make_bundle(
            self,
            name or self.BUNDLE,
            ("/test_assetsbundle/static/src/mod.js", MODULE_JS),
            ("/test_assetsbundle/static/src/plain.js", PLAIN_JS),
        )

    def test_module_file_stops_the_build_when_someone_can_read_it(self):
        bundle = self._legacy_bundle()
        self.assertNotIn(self.BUNDLE, esm_registry().bundles)
        self.assertEqual(len(bundle.javascripts), 2)
        with (
            self.assertLogs("odoo.assets.bundle", level="ERROR") as cm,
            self.assertRaises(ModuleSyntaxInLegacyBundleError) as raised,
        ):
            bundle.js()
        self.assertIn("module_syntax_in_legacy_bundle", "\n".join(cm.output))
        self.assertIn("declare the bundle under the 'esm' key", str(raised.exception))

    def test_module_file_is_stubbed_and_excluded_in_production(self):
        with config.patch(test_enable=False, dev_mode=[]):
            self.assertFalse(JsPipeline._is_asset_error_fatal())
            bundle = self._legacy_bundle(f"{self.BUNDLE}_prod")
            with self.assertLogs("odoo.assets.bundle", level="ERROR") as cm:
                attachment = bundle.js()
        self.assertIn("module_syntax_in_legacy_bundle", "\n".join(cm.output))
        content = attachment.raw.decode()
        self.assertIn("console.error(", content)
        self.assertNotIn("import { x }", content)
        self.assertIn("window.testX", content)

    def test_plain_src_file_is_not_stubbed(self):
        bundle = AssetsBundle(
            f"{self.BUNDLE}_plain",
            [asset_file("/test_assetsbundle/static/src/plain.js", PLAIN_JS)],
            env=self.env,
        )
        content = bundle.js().raw.decode()
        self.assertIn("window.testX", content)
        self.assertNotIn("console.error(", content)

    def test_ignore_header_opts_out(self):
        ignored = "// @odoo-module ignore\n" + PLAIN_JS
        bundle = AssetsBundle(
            f"{self.BUNDLE}_ignore",
            [asset_file("/test_assetsbundle/static/src/ignored.js", ignored)],
            env=self.env,
        )
        content = bundle.js().raw.decode()
        self.assertIn("window.testX", content)
        self.assertNotIn("console.error(", content)

    def test_esm_bundle_routes_module_to_native(self):
        bundle = AssetsBundle(
            "web.assets_web",
            [asset_file("/web/static/src/fake_mod.js", MODULE_JS)],
            env=self.env,
        )
        self.assertEqual(len(bundle.native_modules), 1)
        self.assertEqual(len(bundle.javascripts), 0)

    def test_syntax_regex_ignores_dynamic_import(self):
        self.assertFalse(_MODULE_SYNTAX_RE.search('import("/web/x.js").then();'))
        self.assertTrue(_MODULE_SYNTAX_RE.search('import { a } from "@web/x";'))
        self.assertTrue(_MODULE_SYNTAX_RE.search('import "side-effect";'))
        self.assertTrue(_MODULE_SYNTAX_RE.search("export default class {}"))

    def test_is_odoo_module_empty_url(self):
        self.assertFalse(is_odoo_module("", PLAIN_JS))
        self.assertTrue(is_odoo_module("", "// @odoo-module\n" + MODULE_JS))

    def test_block_comment_export_is_not_stubbed(self):
        commented = "/*\nexport const x = 1;\nimport { a } from 'b';\n*/\n" + PLAIN_JS
        bundle = AssetsBundle(
            f"{self.BUNDLE}_blockcomment",
            [asset_file("/test_assetsbundle/static/src/commented.js", commented)],
            env=self.env,
        )
        content = bundle.js().raw.decode()
        self.assertIn("window.testX", content)
        self.assertNotIn("console.error(", content)

    def test_template_literal_export_is_not_stubbed(self):
        templated = "var s = `\nexport default thing\n`;\n" + PLAIN_JS
        bundle = AssetsBundle(
            f"{self.BUNDLE}_template",
            [asset_file("/test_assetsbundle/static/src/templated.js", templated)],
            env=self.env,
        )
        content = bundle.js().raw.decode()
        self.assertIn("window.testX", content)
        self.assertNotIn("console.error(", content)

    def test_module_syntax_outside_comment_still_stubbed(self):
        mixed = "/*\nexport const decoy = 1;\n*/\n" + MODULE_JS
        with config.patch(test_enable=False, dev_mode=[]):
            bundle = AssetsBundle(
                f"{self.BUNDLE}_mixed",
                [asset_file("/test_assetsbundle/static/src/mixed.js", mixed)],
                env=self.env,
            )
            with self.assertLogs("odoo.assets.bundle", level="ERROR"):
                content = bundle.js().raw.decode()
        self.assertIn("console.error(", content)


class TestTemplateIifeAsiGuard(TransactionCase):
    def _bundle(self, name, debug=False):
        return make_bundle(
            self,
            name,
            ("/test/audit_g10_asi.js", UNTERMINATED_JS),
            ("/test/audit_g10_asi.xml", TEMPLATE_XML),
            css=False,
            debug_assets=debug,
        )

    def _assert_no_call_expression(self, content):
        code = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)
        self.assertIsNone(
            re.search(r"auditG10Src\s*\(", code),
            "the template IIFE forms a call expression with the last file",
        )

    def test_minified_bundle_defuses_asi(self):
        content = self._bundle("test_assetsbundle.audit_g10_asi_min").js().raw.decode()
        self.assertIn("(function()", content, "template IIFE missing")
        self.assertIn("window.auditG10=window.auditG10Src;", content)
        self._assert_no_call_expression(content)

    def test_debug_bundle_defuses_asi(self):
        content = (
            self._bundle("test_assetsbundle.audit_g10_asi_dbg", debug=True)
            .js()
            .raw.decode()
        )
        self.assertIn("(function()", content, "template IIFE missing")
        self.assertRegex(content, r"auditG10Src\s*;")
        self._assert_no_call_expression(content)


class TestJsContentPredicates(BaseCase):
    def _has_legacy_templates(self, templates, esm):
        fake = SimpleNamespace(templates=templates, _is_esm_bundle=esm)
        return AssetsBundle._has_legacy_templates.fget(fake)

    def _has_js_content(self, javascripts, legacy_templates):
        fake = SimpleNamespace(
            javascripts=javascripts, _has_legacy_templates=legacy_templates
        )
        return AssetsBundle.has_js_content.fget(fake)

    def test_legacy_templates_only_for_non_esm(self):
        self.assertTrue(self._has_legacy_templates(["t"], esm=False))
        self.assertFalse(self._has_legacy_templates(["t"], esm=True))
        self.assertFalse(self._has_legacy_templates([], esm=False))

    def test_has_js_content_combines_js_and_templates(self):
        self.assertTrue(self._has_js_content(["j"], False))
        self.assertTrue(self._has_js_content([], True))
        self.assertFalse(self._has_js_content([], False))


class TestNestedTemplateLiteralDetection(BaseCase):
    def test_nesting_is_detected(self):
        self.assertTrue(rjsmin_misreads("const a = `A${`B  ${1}  C`}D`;"))

    def test_a_plain_interpolated_literal_is_not_nesting(self):
        for source in (
            "const a = `x ${y} z`;",
            'const a = `x ${ obj["k}"] } y`;',
            "const a = `${ 1/2 } // not a comment`;",
            "const a = `line one\n   two`;",
            "const a = `esc \\` still one ${x}`;",
        ):
            self.assertFalse(rjsmin_misreads(source), source)

    def test_a_file_without_both_markers_short_circuits(self):
        self.assertFalse(rjsmin_misreads("const a = `plain`;"))
        self.assertFalse(rjsmin_misreads("const a = '${notatemplate}';"))

    def test_every_file_rjsmin_corrupts_is_flagged(self):
        must_flag = [
            "const a = `A${`B  ${1}  C`}D`;",
            "expect(`${a}`).toBe(`x  ${`y  z`}`);",
            "const s = `${cond ? `a  b` : `c  d`}`;",
            "f(`${g(`  h  `)}`);",
            "const t = `${x.map((v) => `  ${v}  `).join('')}`;",
            "const a = `${ f({}) + `n  o` }`;",
            "const a = `${ (()=>{})() + `n  o` }`;",
            "const a = `${ {k: 1}.k + `p  q` }`;",
            "const a = `${ x.map(({v}) => `  ${v}  `).join('') }`;",
        ]
        for source in must_flag:
            self.assertTrue(rjsmin_misreads(source), source)

    def test_a_brace_in_a_substitution_is_not_its_end(self):
        for source in (
            "const a = `${ f({b:1}) }`;",
            "const a = `${ {a:{b:2}} }` + `${ 1 }`;",
        ):
            self.assertFalse(rjsmin_misreads(source), source)

    def test_a_backtick_in_a_comment_or_string_does_not_hide_nesting(self):
        for source in (
            "// don't use ` here\nconst a = `${`n  o`}`;",
            'const c = "a ` b";\nconst a = `${`n  o`}`;',
            'const a = `${ "}" + `n  o` }`;',
        ):
            with self.subTest(source=source):
                self.assertTrue(rjsmin_misreads(source))

    def test_a_regex_after_a_keyword_rjsmin_does_not_know_is_flagged(self):
        for source in (
            "x = typeof /a  b/;",
            "function* g() { yield /a  b/; }",
            "async function f() { await /a  b/; }",
            "function* g() { yield /`/;\n}\nconst m = `a    b`;",
        ):
            with self.subTest(source=source):
                self.assertTrue(rjsmin_misreads(source))

    def test_a_regex_rjsmin_reads_as_one_is_left_to_it(self):
        for source in (
            "function f() { return /a  b/; }",
            "x = (/a  b/);",
            "x = y / 2 / z;",
            "// typeof /a  b/\nconst t = 1;",
            "const s = 'yield /a  b/';",
        ):
            with self.subTest(source=source):
                self.assertFalse(rjsmin_misreads(source))

    def test_rjsmin_really_does_break_what_is_flagged(self):
        from rjsmin import jsmin

        for source, intact in (
            ("const a = `A${`B  ${1}  C`}D`;", "B  ${1}  C"),
            ("const a = `${ f({}) + `n  o` }`;", "n  o"),
            ("const a = `${ (()=>{})() + `n  o` }`;", "n  o"),
            ("x = typeof /a  b/;", "a  b"),
            ("function* g() { yield /`/;\n}\nconst m = `a    b`;", "a    b"),
        ):
            with self.subTest(source=source):
                self.assertTrue(rjsmin_misreads(source))
                self.assertNotIn(intact, jsmin(source, keep_bang_comments=True))

    def test_the_minifier_takes_the_in_process_path(self):
        bundle = AssetsBundle(
            "test.audit.tpl",
            [asset_file("/m/a.js", "const a = `x ${y}   z`;\nconst b   =   1;")],
            env=None,
            css=False,
        )
        with patch(
            "odoo.addons.base.models.assetsbundle.assets.minify_js"
        ) as minify_js:
            out = bundle.javascripts[0].minify()
        minify_js.assert_not_called()
        self.assertIn("`x ${y}   z`", out)

    def test_the_minifier_still_escalates_on_nesting(self):
        bundle = AssetsBundle(
            "test.audit.tpl",
            [asset_file("/m/a.js", "const a = `A${`B  ${1}  C`}D`;")],
            env=None,
            css=False,
        )
        with patch(
            "odoo.addons.base.models.assetsbundle.assets.minify_js",
            return_value="MINIFIED",
        ) as minify_js:
            out = bundle.javascripts[0].minify()
        minify_js.assert_called_once()
        self.assertIn("MINIFIED", out)


class TestBacktickMinifyGate(BaseCase):
    _TARGET = "odoo.addons.base.models.assetsbundle.assets.minify_js"

    def _routes_to_esbuild(self, code):
        asset = JavascriptAsset(SimpleNamespace(name="b"), inline=code)
        with patch(self._TARGET, return_value="ESB") as minify_js:
            asset.minify()
        return minify_js.called

    def test_no_backtick_uses_rjsmin(self):
        self.assertFalse(self._routes_to_esbuild("var x = 1;\n"))

    def test_backtick_without_interpolation_uses_rjsmin(self):
        self.assertFalse(self._routes_to_esbuild("var x = `a   b`;\n"))

    def test_nested_interpolation_uses_esbuild(self):
        self.assertTrue(self._routes_to_esbuild("var x = `${`a   b`}`;\n"))

    def test_rjsmin_path_preserves_top_level_literal(self):
        asset = JavascriptAsset(SimpleNamespace(name="b"), inline="var x = `a   b`;\n")
        self.assertIn("a   b", asset.minify())

    def test_js_header_line_count(self):
        asset = JavascriptAsset(
            SimpleNamespace(name="b"), url="/web/static/src/_probe.js", inline="x"
        )
        rendered = asset.with_header("SINGLE_LINE_BODY", minimal=False)
        self.assertEqual(rendered.count("\n"), JavascriptAsset._HEADER_LINE_COUNT)


class TestBacktickMinification(TransactionCase):
    BUNDLE = "test_assetsbundle.backtick"

    def test_backtick_file_is_minified(self):
        src = (
            "(function () {\n"
            "    var name = 'x';\n"
            "    window.testTpl = `hello   ${name}`;\n"
            "})();\n"
        )
        bundle = AssetsBundle(
            self.BUNDLE,
            [asset_file("/test_assetsbundle/static/src/tpl.js", src)],
            env=self.env,
        )
        content = bundle.js().raw.decode()
        self.assertIn("hello   ", content)
        self.assertIn("window.testTpl", content)
        self.assertNotIn("\n    var name", content)

    def test_nested_template_survives(self):
        src = "window.testNested = `outer ${`in  ner`} end`;\n"
        bundle = AssetsBundle(
            f"{self.BUNDLE}_nested",
            [asset_file("/test_assetsbundle/static/src/nested.js", src)],
            env=self.env,
        )
        content = bundle.js().raw.decode()
        self.assertIn("in  ner", content)

    def test_esbuild_failure_ships_unminified(self):
        src = "window.testRaw = `outer ${`in  ner`} end`;\nvar    spaced = 1;\n"
        with patch(
            "odoo.addons.base.models.assetsbundle.assets.minify_js", return_value=None
        ):
            bundle = AssetsBundle(
                f"{self.BUNDLE}_fallback",
                [asset_file("/test_assetsbundle/static/src/fallback.js", src)],
                env=self.env,
            )
            content = bundle.js().raw.decode()
        self.assertIn("var    spaced = 1;", content)


class TestJsSourceMapAccuracy(TransactionCase):
    def test_map_round_trips_to_source_lines(self):
        a = "const a1 = 1;\nconst a2 = 2;\nconst a3 = 3;\n"
        b = "const b1 = 10;\nconst b2 = 20;\n"
        files = [
            {"url": "/test/a.js", "filename": None, "content": a, "last_modified": 1.0},
            {"url": "/test/b.js", "filename": None, "content": b, "last_modified": 1.0},
        ]
        bundle = AssetsBundle(
            "test_assetsbundle.srcmap",
            files,
            env=self.env,
            css=False,
            js=True,
            debug_assets=True,
        )
        js_attachment = bundle.js()
        body_lines = js_attachment.raw.decode().split("\n")

        smap = bundle.get_attachments("js.map")
        self.assertTrue(smap, "a js.map sibling must be produced in debug mode")
        raw = smap.raw.decode()
        data = json.loads(raw.split("\n", 1)[1] if raw.startswith(")]}'") else raw)

        self.assertEqual(data["sources"], ["/test/a.js", "/test/b.js"])
        self.assertTrue(data["mappings"], "mappings must not be empty")

        src_lines = {0: a.split("\n"), 1: b.split("\n")}
        checked = 0
        for gen_line, src_idx, orig_line in _vlq_decode_mappings(data["mappings"]):
            lines = src_lines[src_idx]
            if orig_line < 2 or orig_line > len(lines):
                continue
            expected = lines[orig_line - 1]
            if not expected.strip():
                continue
            self.assertEqual(
                body_lines[gen_line - 1],
                expected,
                f"map claims bundle line {gen_line} == "
                f"{data['sources'][src_idx]}:{orig_line}",
            )
            checked += 1
        self.assertGreaterEqual(checked, 3, "expected several content-line mappings")
