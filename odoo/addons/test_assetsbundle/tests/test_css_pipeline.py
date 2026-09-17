import logging
import pathlib
import re
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from odoo.tests.common import BaseCase, TransactionCase
from odoo.tools import mute_logger
from odoo.tools.config import config

from .common import asset_file, make_bundle
from odoo.addons.base.models import assetsbundle as _ab
from odoo.addons.base.models.assetsbundle import (
    AssetError,
    AssetsBundle,
    CssPipeline,
    PreprocessedCSS,
    SassStylesheetAsset,
    ScssStylesheetAsset,
    StylesheetAsset,
    WebAsset,
    _rewrite_css_outside_strings,
    css_pipeline,
)
from odoo.addons.base.models.assetsbundle.common import (
    _SCSS_STATEMENT_SPANS,
    CompileError,
)

_logger = logging.getLogger(__name__)

FORBIDDEN = "../../secret"
NON_ASCII_SCSS = '.audit-charset{content:"→ flecha"}'
PLAIN_CSS = "body { margin-left: 1px; }"


def _fake_bundle(**overrides):
    defaults = {
        "name": "test.bundle",
        "stylesheets": [],
        "css_errors": [],
        "autoprefix": False,
        "rtl": False,
        "is_debug_assets": False,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _sanitized(source):
    bundle = _fake_bundle(name="test.spans")
    identity = SimpleNamespace(compile=lambda src: src, output_style="test")
    out = CssPipeline(bundle).compile_css(identity, source)
    return out, bundle.css_errors


class _MissRecordset:
    def __bool__(self):
        return False

    def __len__(self):
        return 0

    def check_singleton(self):
        raise ValueError("empty recordset")


class _MissAttachModel:
    def sudo(self):
        return self

    def _get_serve_attachment(self, url):
        return _MissRecordset()


class TestPreprocessCssErrorContract(BaseCase):
    def _pipeline(self, stylesheets):
        bundle = _fake_bundle(stylesheets=stylesheets)
        return CssPipeline(bundle), bundle

    def test_compile_failure_returns_empty_not_raw_source(self):
        scss = Mock(spec=ScssStylesheetAsset)
        scss.get_source.return_value = "$x: 1; a {}"
        scss.minify.return_value = "RAW_UNCOMPILED_SCSS"
        scss.errors = []
        self.assertIsInstance(scss, PreprocessedCSS)

        pipeline, bundle = self._pipeline([scss])

        def failing_compile_css(compiler, source):
            bundle.css_errors.append("Sass: something broke")
            return ""

        pipeline.compile_css = failing_compile_css

        result = pipeline.preprocess()
        self.assertEqual(result, "")
        self.assertEqual(bundle.css_errors, ["Sass: something broke"])

    def test_leaf_asset_error_still_ships_partial_bundle(self):
        plain = Mock(spec=StylesheetAsset)
        plain._content = None
        plain.errors = []

        def _minify():
            plain.errors.append("audit_missing.css does not exist.")
            return "body{color:red}"

        plain.minify.side_effect = _minify
        pipeline, bundle = self._pipeline([plain])

        result = pipeline.preprocess()
        self.assertEqual(result, "body{color:red}")
        self.assertIn("audit_missing.css does not exist.", bundle.css_errors)

    def test_clean_compile_returns_bundle(self):
        plain = Mock(spec=StylesheetAsset)
        plain.minify.return_value = "body{color:red}"
        plain.errors = []
        pipeline, bundle = self._pipeline([plain])

        result = pipeline.preprocess()
        self.assertEqual(result, "body{color:red}")
        self.assertEqual(bundle.css_errors, [])

    def test_no_stylesheets_short_circuits(self):
        pipeline, _ = self._pipeline([])
        self.assertEqual(pipeline.preprocess(), "")


class TestPreprocessLeafErrorRebuilt(BaseCase):
    _MISSING = "/web/static/src/audit_missing.scss"

    def _bundle_with_missing_scss(self, autoprefix=False, rtl=False):
        bundle = _fake_bundle(
            autoprefix=autoprefix,
            rtl=rtl,
            env={"ir.attachment": _MissAttachModel()},
        )
        asset = ScssStylesheetAsset(bundle, url=self._MISSING)
        bundle.stylesheets.append(asset)
        return bundle, asset

    def test_single_call_compile_failure_reports_leaf_once(self):
        bundle, _asset = self._bundle_with_missing_scss()
        pipeline = CssPipeline(bundle)

        def failing_compile(compiler, source):
            bundle.css_errors.append("Sass: build broke")
            return ""

        pipeline.compile_css = failing_compile

        self.assertEqual(pipeline.preprocess(), "")
        leaf_msg = f"Could not find {self._MISSING}"
        self.assertEqual(bundle.css_errors.count(leaf_msg), 1)
        self.assertIn("Sass: build broke", bundle.css_errors)

    def test_rerun_does_not_accumulate_leaf_errors(self):
        bundle, asset = self._bundle_with_missing_scss()
        pipeline = CssPipeline(bundle)
        pipeline.compile_css = lambda compiler, source: source

        leaf_msg = f"Could not find {self._MISSING}"
        for _ in range(3):
            pipeline.preprocess()
            self.assertEqual(bundle.css_errors.count(leaf_msg), 1)
        self.assertEqual(asset.errors.count(leaf_msg), 1)


class TestPreprocessCssAtRulesIdempotent(BaseCase):
    _COMPILED = '@charset "UTF-8";\n/*! odoo-split:abc123 */\nh1{color:red}'

    def _pipeline(self, rtl=False):
        scss = Mock(spec=ScssStylesheetAsset)
        scss.id = "abc123"
        scss.get_source.return_value = "/*! odoo-split:abc123 */\nh1{}"
        scss.minify.return_value = "h1{color:red}"
        scss.errors = []
        bundle = _fake_bundle(stylesheets=[scss], rtl=rtl)
        pipeline = CssPipeline(bundle)
        pipeline.compile_css = lambda compiler, source: self._COMPILED
        pipeline.convert_css_to_rtl = lambda source: source
        return pipeline, bundle

    def test_source_list_untouched_atrules_in_render_list(self):
        pipeline, bundle = self._pipeline()
        out1 = pipeline.preprocess()
        self.assertEqual(len(bundle.stylesheets), 1, "source list must not be mutated")
        self.assertEqual(
            len(pipeline._rendered_assets), 2, "@at-rules prepended to the render list"
        )
        self.assertEqual(out1.count("@charset"), 1)

    def test_rerun_does_not_stack_at_rules(self):
        pipeline, bundle = self._pipeline()
        pipeline.preprocess()
        out2 = pipeline.preprocess()
        self.assertEqual(
            len(bundle.stylesheets), 1, "re-run must not mutate the source"
        )
        self.assertEqual(
            len(pipeline._rendered_assets), 2, "render list rebuilt, not stacked"
        )
        self.assertEqual(out2.count("@charset"), 1, "@charset must not be duplicated")

    def test_rerun_idempotent_under_rtl(self):
        pipeline, bundle = self._pipeline(rtl=True)
        pipeline.preprocess()
        pipeline.preprocess()
        out3 = pipeline.preprocess()
        self.assertEqual(len(bundle.stylesheets), 1)
        self.assertEqual(len(pipeline._rendered_assets), 2)
        self.assertEqual(out3.count("@charset"), 1)


class TestRtlAfterCompileFailure(BaseCase):
    def _pipeline(self, compile_ok):
        scss = Mock(spec=ScssStylesheetAsset)
        scss.id = "abc123"
        scss.get_source.return_value = "/*! odoo-split:abc123 */\n.a{color:$x}"
        scss.minify.return_value = ".a{color:red}"
        scss.errors = []
        plain = Mock(spec=StylesheetAsset)
        plain.id = "def456"
        plain.get_source.return_value = "/*! odoo-split:def456 */\n.b{margin-left:1px}"
        plain.minify.return_value = ".b{margin-left:1px}"
        plain.errors = []
        bundle = _fake_bundle(stylesheets=[scss, plain], rtl=True)
        pipeline = CssPipeline(bundle)

        def compile_css(compiler, source):
            if compile_ok:
                return "/*! odoo-split:abc123 */\n.a{color:red}"
            bundle.css_errors.append("Sass: broke")
            return ""

        pipeline.compile_css = compile_css
        pipeline.convert_css_to_rtl = Mock(side_effect=lambda source: source)
        return pipeline, bundle

    def test_a_failed_compile_never_reaches_rtlcss(self):
        pipeline, bundle = self._pipeline(compile_ok=False)

        self.assertEqual(pipeline.preprocess(), "")

        pipeline.convert_css_to_rtl.assert_not_called()
        self.assertEqual(bundle.css_errors, ["Sass: broke"])

    def test_a_clean_compile_still_converts(self):
        pipeline, bundle = self._pipeline(compile_ok=True)

        out = pipeline.preprocess()

        pipeline.convert_css_to_rtl.assert_called_once()
        self.assertIn(".a{color:red}", out)
        self.assertIn(".b{margin-left:1px}", out)
        self.assertEqual(bundle.css_errors, [])


class TestStylesheetErrorInversion(BaseCase):
    class _StubBundle(AssetsBundle):
        def __init__(self):
            self.name = "test.stub"
            self.stylesheets = []
            self.css_errors = []
            self.rtl = False
            self.autoprefix = False
            self.is_debug_assets = False

    def test_asset_records_error_without_touching_bundle(self):
        class BareBundle:
            pass

        asset = StylesheetAsset(BareBundle(), url="/web/static/src/css/missing.css")
        with patch.object(WebAsset, "_get_content", side_effect=AssetError("boom")):
            out = asset._get_content()
        self.assertEqual(out, "")
        self.assertEqual(asset.errors, ["boom"])
        self.assertFalse(hasattr(asset.bundle, "css_errors"))

    def test_bundle_harvests_asset_errors(self):
        bundle = self._StubBundle()
        good = StylesheetAsset(bundle, inline=".ok{color:red}")
        bad1 = StylesheetAsset(bundle, url="/web/static/src/css/x1.css")
        bad2 = StylesheetAsset(bundle, url="/web/static/src/css/x2.css")
        bundle.stylesheets = [good, bad1, bad2]

        def fake_fetch(self):
            raise AssetError(f"missing {self.url}")

        with patch.object(WebAsset, "_get_content", fake_fetch):
            result = bundle.preprocess_css()

        self.assertIn(".ok{color:red}", result)
        self.assertEqual(good.errors, [])
        self.assertEqual(
            bundle.css_errors,
            [
                "missing /web/static/src/css/x1.css",
                "missing /web/static/src/css/x2.css",
            ],
        )

    def test_preprocess_css_does_not_double_report_on_rerun(self):
        bundle = self._StubBundle()
        bad = StylesheetAsset(bundle, url="/web/static/src/css/x.css")
        bundle.stylesheets = [bad]

        def fake_fetch(self):
            raise AssetError("missing x.css")

        with patch.object(WebAsset, "_get_content", fake_fetch):
            bundle.preprocess_css()
            bundle.preprocess_css()

        self.assertEqual(bundle.css_errors, ["missing x.css"])


class TestCssVersionStability(TransactionCase):
    def test_source_list_untouched_by_preprocess(self):
        files = [
            asset_file("/test_assetsbundle/static/src/x.scss", "h1 { color: red; }")
        ]
        with patch.object(
            ScssStylesheetAsset,
            "compile",
            lambda self, source: '@charset "UTF-8";\n' + source,
        ):
            bundle = AssetsBundle(
                "test_assetsbundle.cssver", files, env=self.env, js=False
            )
            version_before = bundle.get_version("css")
            bundle.preprocess_css()
            self.assertEqual(len(bundle.stylesheets), 1)
            self.assertEqual(len(bundle._css._rendered_assets), 2)
            self.assertEqual(bundle.get_version("css"), version_before)

    def test_version_independent_of_call_order(self):
        files = [
            asset_file("/test_assetsbundle/static/src/x.scss", "h1 { color: red; }")
        ]
        with patch.object(
            ScssStylesheetAsset,
            "compile",
            lambda self, source: '@charset "UTF-8";\n' + source,
        ):
            bundle_a = AssetsBundle(
                "test_assetsbundle.cssorder", files, env=self.env, js=False
            )
            version_first = bundle_a.get_version("css")

            bundle_b = AssetsBundle(
                "test_assetsbundle.cssorder", files, env=self.env, js=False
            )
            bundle_b.preprocess_css()
            self.assertEqual(len(bundle_b.stylesheets), 1, "source list not mutated")
            self.assertEqual(
                bundle_b.get_version("css"),
                version_first,
                "preprocess_css must not change the advertised version",
            )


class TestDeterministicSplitMarker(TransactionCase):
    SPEC = [
        asset_file("/m/a.scss", "$c: red; .a{color:$c}"),
        asset_file("/m/b.scss", ".b{color:blue}"),
    ]

    def _source(self, **kw):
        bundle = AssetsBundle("test.audit.split", self.SPEC, env=self.env, **kw)
        return "\n".join(a.get_source() for a in bundle.stylesheets)

    def test_two_bundles_over_the_same_files_compile_the_same_bytes(self):
        self.assertEqual(self._source(), self._source())

    def test_markers_are_unique_within_a_bundle(self):
        bundle = AssetsBundle("test.audit.split", self.SPEC, env=self.env)
        ids = [a.id for a in bundle.stylesheets]
        self.assertEqual(len(set(ids)), len(ids))
        self.assertEqual(ids, ["0000", "0001"])

    def test_identical_content_still_gets_distinct_markers(self):
        same = [
            asset_file("/m/x.scss", ".x{color:red}"),
            asset_file("/m/y.scss", ".x{color:red}"),
        ]
        bundle = AssetsBundle("test.audit.dup", same, env=self.env)
        self.assertEqual(len({a.id for a in bundle.stylesheets}), 2)

    def test_the_direction_and_prefix_variants_share_one_compile_input(self):
        variants = [
            self._source(),
            self._source(rtl=True),
            self._source(autoprefix=True),
            self._source(rtl=True, autoprefix=True),
        ]
        self.assertEqual(len(set(variants)), 1)


class TestCompileMemoContract(TransactionCase):
    def setUp(self):
        super().setUp()
        CssPipeline._compiled_cache.clear()
        self.addCleanup(CssPipeline._compiled_cache.clear)

    def test_an_identical_source_is_compiled_once(self):
        calls = []

        def compiler(source):
            calls.append(source)
            return "compiled{}"

        asset = SimpleNamespace(compile=compiler, output_style="compressed")
        pipeline = CssPipeline(_fake_bundle())
        for _ in range(3):
            pipeline.compile_css(asset, "a{}")
        self.assertEqual(len(calls), 1)

    def test_a_failure_is_not_retained(self):
        attempts = []

        def flaky(source):
            attempts.append(source)
            if len(attempts) == 1:
                raise CompileError("transient")
            return "recovered{}"

        with self.assertRaises(CompileError):
            CssPipeline._memoized_transform(("t",), "a{}", flaky)
        self.assertEqual(
            CssPipeline._memoized_transform(("t",), "a{}", flaky), "recovered{}"
        )
        self.assertEqual(len(attempts), 2)

    def test_distinct_keys_do_not_collide(self):
        out = [
            CssPipeline._memoized_transform(("one",), "a{}", lambda s: "first"),
            CssPipeline._memoized_transform(("two",), "a{}", lambda s: "second"),
        ]
        self.assertEqual(out, ["first", "second"])

    def test_dev_mode_bypasses_the_memo(self):
        calls = []

        def transform(source):
            calls.append(source)
            return "compiled{}"

        with patch.dict(config._runtime_options, {"dev_mode": ["xml"]}):
            for _ in range(3):
                CssPipeline._memoized_transform(("t",), "a{}", transform)
        self.assertEqual(len(calls), 3)
        self.assertFalse(CssPipeline._compiled_cache)


class TestCompiledCacheConcurrency(BaseCase):
    def setUp(self):
        super().setUp()
        CssPipeline._compiled_cache.clear()
        self.addCleanup(CssPipeline._compiled_cache.clear)
        patcher = patch.object(css_pipeline, "config", {"dev_mode": []})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_parallel_access_never_raises_and_stays_bounded(self):
        failures = []
        sources = [f"src-{i}" for i in range(CssPipeline._COMPILED_CACHE_SIZE * 3)]

        def worker(offset):
            try:
                for n in range(400):
                    source = sources[(offset + n) % len(sources)]
                    result = CssPipeline._memoized_transform(
                        ("audit",), source, str.upper
                    )
                    if result != source.upper():
                        failures.append(f"{source} -> {result}")
            except Exception as exc:
                failures.append(repr(exc))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertFalse(failures)
        self.assertLessEqual(
            len(CssPipeline._compiled_cache), CssPipeline._COMPILED_CACHE_SIZE
        )

    def test_a_raising_transform_is_not_cached(self):
        def boom(_source):
            raise RuntimeError("compile failed")

        with self.assertRaises(RuntimeError):
            CssPipeline._memoized_transform(("audit",), "transient", boom)
        self.assertFalse(CssPipeline._compiled_cache)


class _SleepyCSS(PreprocessedCSS):
    _COMPILE_TIMEOUT_S = 1

    def get_command(self):
        return ["sleep", "30"]


class TestPreprocessorTimeout(TransactionCase):
    def test_compile_times_out(self):
        bundle = AssetsBundle("test_assetsbundle.timeout", [], env=self.env)
        asset = _SleepyCSS(bundle, url="/test_assetsbundle/static/src/x.scss")
        with self.assertRaises(CompileError) as cm:
            asset.compile("a { color: red; }")
        self.assertIn("timed out", str(cm.exception))


class TestForInlineCompile(TransactionCase):
    def test_compiles_standalone_scss(self):
        asset = ScssStylesheetAsset.for_inline_compile("// preview")
        css = asset.compile("$c: red;\nbody { color: $c; }")
        self.assertIn("body{color:red}", css)

    def test_no_content_error_survives_missing_bundle(self):
        with self.assertRaisesRegex(ValueError, "<no bundle>"):
            WebAsset(None)


class TestSassBackendParity(BaseCase):
    def test_cli_command_disables_the_charset_marker(self):
        asset = ScssStylesheetAsset.for_inline_compile()
        self.assertIn("--no-charset", asset.get_command())

    def test_cli_and_embedded_agree_on_non_ascii_output(self):
        asset = ScssStylesheetAsset.for_inline_compile()
        embedded = asset.compile(NON_ASCII_SCSS)
        cli = super(ScssStylesheetAsset, asset).compile(NON_ASCII_SCSS)
        self.assertEqual(cli.strip(), embedded.strip())

    def test_no_charset_marker_reaches_the_bundle(self):
        asset = ScssStylesheetAsset.for_inline_compile()
        cli = super(ScssStylesheetAsset, asset).compile(NON_ASCII_SCSS)
        self.assertNotIn("﻿", cli, "a mid-stylesheet BOM eats the next rule")
        self.assertNotIn("@charset", cli)


class TestEmbeddedSassFallbackWarning(BaseCase):
    def test_warns_once_then_debug(self):
        with patch.object(ScssStylesheetAsset, "_embedded_fallback_warned", False):
            with self.assertLogs(
                "odoo.addons.base.models.assetsbundle", "WARNING"
            ) as cm:
                ScssStylesheetAsset._warn_embedded_fallback(RuntimeError("boom"))
            self.assertEqual(sum("markedly slower" in m for m in cm.output), 1)
            with self.assertLogs(
                "odoo.addons.base.models.assetsbundle", "DEBUG"
            ) as cm2:
                ScssStylesheetAsset._warn_embedded_fallback(RuntimeError("boom"))
            self.assertEqual(sum("markedly slower" in m for m in cm2.output), 0)


class TestCompileCssImportSanitizeUnit(BaseCase):
    _sanitize = staticmethod(_sanitized)

    def test_single_media_query_preserved(self):
        out, errs = self._sanitize('@import "foo" screen;')
        self.assertEqual(out, '@import "foo" screen;')
        self.assertFalse(errs)

    def test_complex_media_query_preserved(self):
        out, _ = self._sanitize('@import "foo" screen and (min-width: 600px);')
        self.assertEqual(out, '@import "foo" screen and (min-width: 600px);')

    def test_distinct_media_keeps_both(self):
        out, _ = self._sanitize('@import "foo" screen;\n@import "foo" print;')
        self.assertEqual(out, '@import "foo" screen;\n@import "foo" print;')

    def test_duplicate_with_media_removed_without_orphan(self):
        out, _ = self._sanitize('@import "foo" screen;\n@import "foo" screen;')
        self.assertEqual(out, '@import "foo" screen;')

    def test_exact_duplicate_deduped(self):
        out, _ = self._sanitize('@import "foo";\n@import "foo";')
        self.assertEqual(out, '@import "foo";')

    def test_bare_legit_import_kept(self):
        out, errs = self._sanitize('@import "lib/partial";')
        self.assertEqual(out, '@import "lib/partial";')
        self.assertFalse(errs)

    def test_forbidden_local_import_with_media_leaves_no_orphan(self):
        with self.assertLogs("odoo.addons.base.models.assetsbundle", "WARNING"):
            out, errs = self._sanitize('@import "./x.scss" screen;')
        self.assertEqual(out, "")
        self.assertTrue(errs)

    def test_repeated_forbidden_import_reported_once(self):
        with self.assertLogs("odoo.addons.base.models.assetsbundle", "WARNING") as cm:
            out, errs = self._sanitize(
                '@import "./a.scss";\n@import "./a.scss";\n@import "./a.scss";'
            )
        self.assertEqual(out, "")
        self.assertEqual(len(errs), 1, "one forbidden statement => one error")
        self.assertEqual(
            sum("forbidden" in m for m in cm.output), 1, "and one server warning"
        )

    def test_distinct_forbidden_imports_each_reported(self):
        with self.assertLogs("odoo.addons.base.models.assetsbundle", "WARNING"):
            _out, errs = self._sanitize('@import "./a.scss";\n@import "./b.scss";')
        self.assertEqual(len(errs), 2)

    @staticmethod
    def _code_imports(out):
        return [ln for ln in out.splitlines() if ln.strip().startswith("@import")]

    def test_line_commented_import_does_not_poison_dedup(self):
        out, errs = self._sanitize(
            '// @import "mixins";\n.a{}\n@import "mixins";\n.b{}'
        )
        self.assertEqual(self._code_imports(out), ['@import "mixins";'])
        self.assertFalse(errs)

    def test_forbidden_import_in_line_comment_ignored(self):
        out, errs = self._sanitize('// @import "theme/foo.scss";\n.a{}')
        self.assertFalse(errs)
        self.assertIn('// @import "theme/foo.scss";', out)

    def test_forbidden_import_in_block_comment_ignored(self):
        out, errs = self._sanitize('/* @import "theme/foo.scss"; */\n.a{}')
        self.assertFalse(errs)
        self.assertIn('/* @import "theme/foo.scss"; */', out)

    def test_import_inside_string_value_left_intact(self):
        out, errs = self._sanitize('.c::before{content:"@import bad"}\n@import "ok";')
        self.assertIn('content:"@import bad"', out)
        self.assertEqual(self._code_imports(out), ['@import "ok";'])
        self.assertFalse(errs)

    def test_real_forbidden_import_still_caught(self):
        with self.assertLogs("odoo.addons.base.models.assetsbundle", "WARNING"):
            out, errs = self._sanitize('@import "./evil.scss";\n.a{}')
        self.assertTrue(errs)
        self.assertNotIn("evil", out)

    def test_compile_css_dedups_repeated_library_import(self):
        out, errors = self._sanitize(
            '@import "bootstrap/scss/functions";\n'
            ".a { color: red; }\n"
            '@import "bootstrap/scss/functions";'
        )
        self.assertEqual(
            errors,
            [],
            "a repeated library @import must not be flagged as an error",
        )
        self.assertEqual(
            out.count('@import "bootstrap/scss/functions"'),
            1,
            "the duplicate @import should be dropped, keeping the first",
        )

    def test_compile_css_blocks_whitespace_padded_local_import(self):
        with mute_logger("odoo.addons.base.models.assetsbundle"):
            out, errors = self._sanitize('@import  "./secret.css";')
        self.assertTrue(
            errors,
            "a whitespace-padded local @import must be rejected",
        )
        self.assertNotIn("secret", out, "the local @import must be stripped")


class TestImportSanitizerSpans(BaseCase):
    def test_protocol_relative_url_does_not_hide_later_import(self):
        out, errors = _sanitized(
            f'.a{{background:url(//cdn.x/y.png)}} @import "{FORBIDDEN}";'
        )
        self.assertTrue(errors, "the local import must still be rejected")
        self.assertNotIn(FORBIDDEN, out)
        self.assertIn("url(//cdn.x/y.png)", out, "the href itself is untouched")

    def test_absolute_url_does_not_hide_later_import(self):
        out, errors = _sanitized(
            f'.a{{background:url(https://cdn.x/y.png)}} @import "{FORBIDDEN}";'
        )
        self.assertTrue(errors)
        self.assertNotIn(FORBIDDEN, out)

    def test_real_line_comment_still_ends_at_newline(self):
        out, errors = _sanitized(f'// note\n@import "{FORBIDDEN}";')
        self.assertTrue(errors, "a comment protects its own line, not the next")
        self.assertIn("// note", out)

    def test_import_inside_block_comment_is_untouched(self):
        source = f'/* @import "{FORBIDDEN}"; */ @import "bootstrap";'
        out, errors = _sanitized(source)
        self.assertFalse(errors)
        self.assertEqual(out, source)

    def test_import_inside_string_is_untouched(self):
        source = f'$s: "@import \'{FORBIDDEN}\';";\n@import "bootstrap";'
        out, errors = _sanitized(source)
        self.assertFalse(errors)
        self.assertEqual(out, source)

    def test_media_aware_dedup_survives_the_rewrite(self):
        out, _ = _sanitized('@import "foo" screen;\n@import "foo" screen;')
        self.assertEqual(out, '@import "foo" screen;')
        out, _ = _sanitized('@import "foo" screen;\n@import "foo" print;')
        self.assertEqual(out, '@import "foo" screen;\n@import "foo" print;')


class TestEmptyUrlIsLeftAlone(BaseCase):
    def test_an_empty_url_is_not_rewritten_to_a_directory(self):
        asset = StylesheetAsset(
            _fake_bundle(), url="/mod/static/src/css/a.css", inline="x"
        )
        with patch.object(
            WebAsset, "_get_content", return_value=".a{background:url()}"
        ):
            out = asset._get_content()
        self.assertEqual(out, ".a{background:url()}")

    def test_a_relative_url_still_resolves(self):
        asset = StylesheetAsset(
            _fake_bundle(), url="/mod/static/src/css/a.css", inline="x"
        )
        with patch.object(
            WebAsset, "_get_content", return_value=".a{background:url(../img/x.png)}"
        ):
            out = asset._get_content()
        self.assertEqual(out, ".a{background:url(/mod/static/src/img/x.png)}")


class TestAutoprefixImportStringBoundary(BaseCase):
    def test_autoprefix_rewrites_real_declaration(self):
        out = CssPipeline._autoprefix_css("a{appearance:none}")
        self.assertIn("-webkit-appearance:none", out)
        self.assertIn("-moz-appearance:none", out)

    def test_autoprefix_skips_string_literal(self):
        out = CssPipeline._autoprefix_css('.x{content:" appearance: auto"}')
        self.assertNotIn("-webkit-appearance", out)
        self.assertIn('" appearance: auto"', out)

    def test_import_hoist_matches_real_rule(self):
        self.assertEqual(
            CssPipeline.rx_css_import.findall('@import "a.css";\nbody{}'),
            ['@import "a.css";'],
        )

    def test_import_hoist_skips_string_literal(self):
        collected = []

        def take(match):
            collected.append(match.group(0))
            return ""

        out = _rewrite_css_outside_strings(
            CssPipeline.rx_css_import, take, '.x{content:"@import url(evil);"}'
        )
        self.assertEqual(collected, [])
        self.assertEqual(out, '.x{content:"@import url(evil);"}')

    def test_hoist_import_rules_extracts_only_real_rules(self):
        pipeline = CssPipeline(_fake_bundle(name="b"))
        rules, remainder = pipeline.hoist_import_rules(
            '@import "a.css";\n.x{content:"@import url(evil);"}\nbody{}'
        )
        self.assertEqual(rules, ['@import "a.css";'])
        self.assertIn('content:"@import url(evil);"', remainder)
        self.assertNotIn('@import "a.css"', remainder)


class TestAutoprefixDeclarationBoundary(BaseCase):
    def test_consecutive_declarations_are_both_prefixed(self):
        out = CssPipeline._autoprefix_css(".b{appearance:auto;appearance:textfield}")
        self.assertIn("-webkit-appearance:auto", out)
        self.assertIn("-webkit-appearance:textfield", out)

    def test_a_bare_newline_is_a_declaration_boundary(self):
        out = CssPipeline._autoprefix_css(".a{\nappearance:none}")
        self.assertIn("-webkit-appearance:none", out)

    def test_indented_output_still_prefixed(self):
        out = CssPipeline._autoprefix_css(".a {\n  appearance: none;\n}")
        self.assertIn("-webkit-appearance:none", out)
        self.assertIn("-moz-appearance:none", out)

    def test_compressed_output_is_unchanged(self):
        self.assertEqual(
            CssPipeline._autoprefix_css(".a{appearance:none}"),
            ".a{-webkit-appearance:none;-moz-appearance:none;appearance:none}",
        )

    def test_important_is_carried_to_every_prefix(self):
        out = CssPipeline._autoprefix_css(".a{appearance:none !important;}")
        self.assertEqual(out.count("!important"), 3)

    def test_non_declarations_are_left_alone(self):
        for source in (
            ".appearance:hover{color:red}",
            "[appearance]{color:red}",
            ".a{--my-appearance:none}",
            '.a{content:"appearance:none"}',
        ):
            self.assertEqual(CssPipeline._autoprefix_css(source), source, source)

    def test_a_hand_written_prefix_is_not_re_prefixed_in_place(self):
        out = CssPipeline._autoprefix_css(".a{-webkit-appearance:none;appearance:none}")
        self.assertNotIn("-webkit--webkit", out)
        self.assertNotIn("--webkit", out)


class TestPlainCssAutoprefix(TransactionCase):
    PLAIN_CSS = ".audit-g10-plain { appearance: none; }"

    def _bundle(self, debug=False):
        return AssetsBundle(
            "test_assetsbundle.audit_g10_prefix",
            [asset_file("/test/audit_g10_prefix.css", self.PLAIN_CSS)],
            env=self.env,
            js=False,
            autoprefix=True,
            debug_assets=debug,
        )

    def test_plain_css_prefixed_in_production(self):
        content = self._bundle().css().raw.decode()
        self.assertIn(
            "-webkit-appearance:none;-moz-appearance:none;appearance:none", content
        )

    def test_plain_css_prefixed_in_debug(self):
        content = self._bundle(debug=True).css().raw.decode()
        self.assertIn("-webkit-appearance:none", content)

    def test_mixed_bundle_scss_not_double_prefixed(self):
        files = [
            asset_file("/test/audit_g10_mix.scss", ".mix-scss { appearance: none; }"),
            asset_file("/test/audit_g10_mix.css", ".mix-css { appearance: none; }"),
        ]
        bundle = AssetsBundle(
            "test_assetsbundle.audit_g10_mix",
            files,
            env=self.env,
            js=False,
            autoprefix=True,
        )
        content = bundle.css().raw.decode()
        self.assertRegex(
            content,
            r"\.mix-scss\{-webkit-appearance:none;"
            r"-moz-appearance:none;appearance:none\}",
        )
        self.assertRegex(
            content,
            r"\.mix-css\{-webkit-appearance:none;"
            r"-moz-appearance:none;appearance:none[;}]",
        )


class TestProtectedSpanDispatch(BaseCase):
    def test_url_span_reaches_repl_never(self):
        seen = []

        def repl(match):
            seen.append(match.group(0))
            return "REWRITTEN"

        out = _rewrite_css_outside_strings(
            re.compile(r"(cdn\.x)"),
            repl,
            ".a{background:url(//cdn.x/y.png)}",
            _SCSS_STATEMENT_SPANS,
        )
        self.assertEqual(seen, [], "a url(...) span is opaque, not code")
        self.assertEqual(out, ".a{background:url(//cdn.x/y.png)}")

    def test_code_outside_the_span_is_still_rewritten(self):
        out = _rewrite_css_outside_strings(
            re.compile(r"(cdn\.x)"),
            lambda m: "REWRITTEN",
            ".cdn.x{background:url(//cdn.x/y.png)}",
            _SCSS_STATEMENT_SPANS,
        )
        self.assertEqual(out, ".REWRITTEN{background:url(//cdn.x/y.png)}")

    def test_target_groups_are_readable_by_name(self):
        out = _rewrite_css_outside_strings(
            StylesheetAsset.rx_url,
            lambda m: f"url({m.group('q')}X/{m.group('body')}{m.group('q')})",
            "a{background:url('img/x.png')}",
        )
        self.assertEqual(out, "a{background:url('X/img/x.png'))}")


class TestUrlFragmentReferences(BaseCase):
    WEB_DIR = "/mod/static/src/css"

    def _rewritten(self, css):
        import posixpath

        def repl(match):
            q, body = match.group("q"), match.group("body")
            if not body:
                return f"url({q}{self.WEB_DIR}/{q}"
            return f"url({q}{posixpath.normpath(f'{self.WEB_DIR}/{body}')}{q}"

        return _rewrite_css_outside_strings(
            StylesheetAsset.rx_url, repl, css, StylesheetAsset._SOURCE_TOKEN_RE
        )

    def test_fragment_reference_is_left_alone(self):
        for css in (
            ".a{mask:url(#alttext-manager-mask)}",
            ".a{clip-path:url(#clip)}",
            ".a{behavior:url(#default#VML)}",
        ):
            self.assertEqual(self._rewritten(css), css, css)

    def test_interpolated_leading_segment_is_still_rewritten(self):
        self.assertEqual(
            self._rewritten('@font-face{src:url("#{$lato-font-path}/Lato-Reg.eot")}'),
            '@font-face{src:url("/mod/static/src/css/#{$lato-font-path}/Lato-Reg.eot")}',
        )
        self.assertEqual(
            self._rewritten('.a{background:url("#{$p}/#{$f}/#{$f}.woff")}'),
            '.a{background:url("/mod/static/src/css/#{$p}/#{$f}/#{$f}.woff")}',
        )

    def test_str_function_interpolation_is_left_alone(self):
        for css in (
            "a{background:url(\"#{str-slice(o-website-value('body-image'), 2)}\")}",
            "a{background:url(\"#{str-replace(str-slice($s, 1, -2), 'a', 'b')}\")}",
        ):
            self.assertEqual(self._rewritten(css), css, css)

    def test_relative_paths_are_still_rewritten(self):
        self.assertEqual(
            self._rewritten(".a{background:url(img/x.png)}"),
            ".a{background:url(/mod/static/src/css/img/x.png)}",
        )
        self.assertEqual(
            self._rewritten('.a{background:url("img/x.png")}'),
            '.a{background:url("/mod/static/src/css/img/x.png")}',
        )

    def test_absolute_and_data_urls_are_still_skipped(self):
        for css in (
            ".a{background:url(https://x/y.png)}",
            ".a{background:url(/abs/y.png)}",
            ".a{background:url(data:image/gif;base64,AA)}",
        ):
            self.assertEqual(self._rewritten(css), css, css)

    def test_stylesheet_url_rewrite_is_os_independent(self):
        from odoo.addons.base.models import assetsbundle
        from odoo.addons.base.models.assetsbundle import StylesheetAsset, WebAsset

        bundle = _fake_bundle()
        sample = (
            '@import "theme.css";\n'
            ".a { background: url(images/logo.png); }\n"
            ".b { background: url(../img/sprite.png); }\n"
        )
        asset = StylesheetAsset(bundle, url="/web/static/src/css/foo.css")

        with (
            patch.object(WebAsset, "_get_content", lambda self: sample),
            patch.object(assetsbundle.assets, "Path", pathlib.PureWindowsPath),
        ):
            out = asset._get_content()

        self.assertNotIn("\\", out, "rewritten URLs must never contain backslashes")
        self.assertIn(
            '@import "/web/static/src/css/theme.css"',
            out,
            "relative @import must be prefixed with the asset's posix dir",
        )
        self.assertIn(
            "url(/web/static/src/css/images/logo.png)",
            out,
            "relative url() must be prefixed with the asset's posix dir",
        )
        self.assertIn(
            "url(/web/static/src/img/sprite.png)",
            out,
            "a ../ in url() must collapse against the posix dir",
        )


class TestUrlRewriteStringBoundary(BaseCase):
    rx = StylesheetAsset.rx_url

    def _rewrite(self, css):
        def repl(match):
            q = match.group("q")
            return f"url({q}REW/{match.group('body')}{q}"

        return _rewrite_css_outside_strings(self.rx, repl, css)

    def test_real_url_is_rewritten(self):
        self.assertIn("REW/", self._rewrite("a{background:url(x.png)}"))

    def test_quoted_real_url_is_rewritten(self):
        self.assertIn('url("REW/x', self._rewrite('a{background:url("x.png")}'))

    def test_multi_url_src_list_all_rewritten(self):
        out = self._rewrite(
            'src:url("./l/a.eot?#iefix") format("embedded-opentype"),'
            'url("./l/a.woff") format("woff"),'
            "url('./l/a.ttf') format('truetype');"
        )
        self.assertEqual(out.count("REW/"), 3, out)
        self.assertIn('format("woff")', out)
        self.assertIn("format('truetype')", out)

    def test_quoted_url_with_space_is_left_untouched(self):
        out = self._rewrite('a{background:url("x y.png")}')
        self.assertNotIn("REW/", out)
        self.assertIn('url("x y.png")', out)

    def test_consecutive_imports_all_rewritten(self):

        def repl(match):
            q = match.group("q")
            return f"@import {q}REW/{match.group('path')}{q}"

        out = _rewrite_css_outside_strings(
            StylesheetAsset.rx_import,
            repl,
            '@import "a.css"; @import "b.css";',
        )
        self.assertEqual(out.count("REW/"), 2, out)

    def test_url_inside_string_value_is_skipped(self):
        out = self._rewrite('a{content:"hello url(x.png) y"}')
        self.assertNotIn("REW/", out)
        self.assertIn('"hello url(x.png) y"', out)

    def test_raw_regex_remains_permissive(self):
        self.assertEqual(len(self.rx.findall('a{content:"hello url(x.png) y"}')), 1)


class TestRewriteScannerDotallScope(BaseCase):
    def test_dot_in_target_does_not_span_newlines(self):
        hits = []
        _rewrite_css_outside_strings(
            re.compile(r"X.Y"), lambda m: hits.append(m.group(0)) or "H", "X\nY"
        )
        self.assertEqual(hits, [], "target's '.' must not gain DOTALL")

    def test_target_with_explicit_dotall_is_respected(self):
        hits = []
        _rewrite_css_outside_strings(
            re.compile(r"X.Y", re.DOTALL),
            lambda m: hits.append(m.group(0)) or "H",
            "X\nY",
        )
        self.assertEqual(hits, ["X\nY"])

    def test_multiline_comment_still_protected(self):
        out = _rewrite_css_outside_strings(
            StylesheetAsset.rx_url, lambda m: "U", "a/*\n c \n*/ url(z)"
        )
        self.assertIn("/*\n c \n*/", out)
        self.assertIn("U", out)


class TestPlainCssMinifyStringHandling(BaseCase):
    @staticmethod
    def _min(css):
        return StylesheetAsset._minify_css_body(css)

    def test_double_space_inside_string_is_preserved(self):
        self.assertEqual(self._min('x { content: "a  b"; }'), 'x{content: "a  b";}')

    def test_braces_inside_string_are_preserved(self):
        self.assertEqual(self._min('x { content: "{ }"; }'), 'x{content: "{ }";}')

    def test_comment_sequence_inside_string_is_preserved(self):
        out = self._min('x { content: "/* not a comment */"; }')
        self.assertIn('"/* not a comment */"', out)

    def test_single_quoted_string_is_preserved(self):
        self.assertEqual(self._min("x { content: '  y  '; }"), "x{content: '  y  ';}")

    def test_escaped_quote_does_not_end_the_string(self):
        out = self._min(r'x { content: "a\"  b"; }')
        self.assertIn(r'"a\"  b"', out)

    def test_ordinary_comment_is_still_stripped(self):
        out = self._min("a { color: red; } /* drop me */ b { color: blue; }")
        self.assertNotIn("drop me", out)
        self.assertEqual(out, "a{color: red;}b{color: blue;}")

    def test_legal_comment_is_kept_verbatim(self):
        out = self._min("/*!  License  */\n.a {\n  color: red;\n}")
        self.assertIn("/*!  License  */", out)
        self.assertIn(".a{color: red;}", out)

    def test_minification_still_applies_outside_strings(self):
        out = self._min("a   {\n  color :  red ;\n}\n\n  b{}")
        self.assertNotIn("  ", out)
        self.assertEqual(out, "a{color : red ;}b{}")

    def test_css_minify_preserves_legal_comments(self):
        asset = StylesheetAsset(
            _fake_bundle(),
            inline="/*! (c) Audit Corp */\n/* strip me */\nbody { color: red; }",
        )
        out = asset.minify()
        self.assertIn("/*! (c) Audit Corp */", out)
        self.assertNotIn("strip me", out)


class TestCssCommentIsATokenSeparator(BaseCase):
    def test_at_rule_keeps_its_media_query(self):
        self.assertEqual(
            StylesheetAsset._minify_css_body("@media/*c*/screen{a{b:c}}"),
            "@media screen{a{b:c}}",
        )

    def test_dimensions_do_not_fuse(self):
        self.assertEqual(
            StylesheetAsset._minify_css_body("a{margin:1px/*c*/2px}"),
            "a{margin:1px 2px}",
        )

    def test_a_compound_selector_stays_compound(self):
        self.assertEqual(
            StylesheetAsset._minify_css_body(".a/*x*/.b{color:red}"),
            ".a.b{color:red}",
        )

    def test_punctuation_neighbours_take_no_separator(self):
        self.assertEqual(
            StylesheetAsset._minify_css_body("a{b:red/*c*/!important}"),
            "a{b:red!important}",
        )

    def test_legal_comments_and_strings_still_survive(self):
        self.assertEqual(
            StylesheetAsset._minify_css_body('/*! (c) me */\n.a{content:"/*x*/"}'),
            '/*! (c) me */ .a{content:"/*x*/"}',
        )


class TestMinifyNulGuard(BaseCase):
    def test_nul_digit_no_longer_crashes(self):
        out = StylesheetAsset._minify_css_body("a{}\x000\x00b{}")
        self.assertNotIn("\x00", out)
        self.assertIn("a{}", out)
        self.assertIn("b{}", out)

    def test_strip_does_not_disturb_normal_minification(self):
        self.assertIn('"x   y"', StylesheetAsset._minify_css_body('a{content:"x   y"}'))
        out = StylesheetAsset._minify_css_body(
            "/*! keep */ a{color:red} /* drop */ b{}"
        )
        self.assertIn("/*! keep */", out)
        self.assertNotIn("drop", out)


class TestMinifySourceMapStringAware(BaseCase):
    @staticmethod
    def _min(css):
        return StylesheetAsset._minify_css_body(css)

    def test_real_sourcemap_link_is_stripped(self):
        out = self._min("a{color:red}\n/*# sourceMappingURL=app.css.map */")
        self.assertNotIn("sourceMappingURL", out)
        self.assertIn("a{color:red}", out)

    def test_sourcemap_text_inside_string_is_preserved(self):
        out = self._min('a::before{content:"/*# sourceMappingURL=x */ keep"}')
        self.assertIn('"/*# sourceMappingURL=x */ keep"', out)


class TestScssMinifySkipsRegex(TransactionCase):
    def test_debug_scss_content_untouched(self):
        bundle = AssetsBundle(
            "test_assetsbundle.scssmin", [], env=self.env, debug_assets=True
        )
        asset = ScssStylesheetAsset(bundle, inline='x { content: "a  b"; }')
        self.assertIn('"a  b"', asset.minify())


class TestDebugCssMinifySkipsRegex(BaseCase):
    def _minify(self, *, debug):
        bundle = _fake_bundle(is_debug_assets=debug)
        return StylesheetAsset(bundle, inline="body {  color:   red ; }").minify()

    def test_debug_leaves_content_unminified(self):
        self.assertIn("  color", self._minify(debug=True))

    def test_production_minifies(self):
        out = self._minify(debug=False)
        self.assertNotIn("  color", out)
        self.assertIn("body{", out)


class TestVendoredCssMinifyCorpus(BaseCase):
    @staticmethod
    def _legacy_minify(content):
        content = re.sub(r"/\*# sourceMappingURL=.*", "", content)
        content = re.sub(r"/\*(?!!).*?\*/", "", content, flags=re.DOTALL)
        content = re.sub(r"\s+", " ", content)
        return re.sub(r" *([{}]) *", r"\1", content)

    @staticmethod
    def _mask(css):
        css = re.sub(r"/\*!.*?\*/", "<C>", css, flags=re.DOTALL)
        css = re.sub(r'"(?:[^"\\]|\\.)*"', "<S>", css)
        return re.sub(r"'(?:[^'\\]|\\.)*'", "<S>", css)

    def _shipped_css_files(self):
        from odoo.modules.module import get_module_path

        base_path = get_module_path("base")
        seen = set()
        for path in Path(base_path).rglob("*.css"):
            if path.name.endswith(".min.css") or path in seen:
                continue
            seen.add(path)
            yield path

    def test_minify_is_semantically_identical_to_legacy_on_shipped_css(self):
        checked = differed = 0
        for path in self._shipped_css_files():
            try:
                src = path.read_text(encoding="utf-8")
            except OSError, UnicodeDecodeError:
                continue
            new = StylesheetAsset._minify_css_body(src)
            legacy = self._legacy_minify(src)
            self.assertEqual(
                self._mask(new),
                self._mask(legacy),
                f"string-aware minify drifted structurally on {path}",
            )
            checked += 1
            differed += new != legacy
        self.assertGreater(checked, 0, "no shipped .css files were found to check")
        _logger.info(
            "vendored-css minify corpus: %d files checked, %d changed (string/"
            "legal-comment only)",
            checked,
            differed,
        )


class TestCssErrorBanner(BaseCase):
    H = CssPipeline._CSS_ERROR_HEADER

    def test_message_is_escaped_for_a_css_string_literal(self):
        out = CssPipeline._render_css_error_banner(['boom "x" *\n y'], "")
        self.assertIn(r"\"x\"", out)
        self.assertIn(r"\A", out)
        self.assertIn(r"\*", out)
        self.assertIn("A css error occurred", out)

    def test_previous_good_css_is_carried_over(self):
        out = CssPipeline._render_css_error_banner(["e"], ".keep{color:red}")
        self.assertTrue(out.startswith(".keep{color:red}"))
        self.assertIn(self.H, out)

    def test_banner_does_not_stack_across_repeated_errors(self):
        first = CssPipeline._render_css_error_banner(["err_one"], ".keep{}")
        second = CssPipeline._render_css_error_banner(["err_two"], first)
        self.assertEqual(second.count(self.H), 1, "exactly one banner survives")
        self.assertIn(".keep{}", second)
        self.assertIn("err_two", second)
        self.assertNotIn("err_one", second)

    def test_multiple_errors_are_joined_into_one_message(self):
        out = CssPipeline._render_css_error_banner(["a", "b"], "")
        self.assertIn(r"a\Ab", out)


class TestCssErrorBannerBackslashEscape(BaseCase):
    def test_backslash_is_escaped_not_interpreted(self):
        banner = CssPipeline._render_css_error_banner([r"C:\foo broke"], "")
        content_line = next(ln for ln in banner.splitlines() if "C:" in ln)
        self.assertIn(r"C:\\foo", content_line)

    def test_quote_escape_stays_single_backslash(self):
        banner = CssPipeline._render_css_error_banner(['say "hi"'], "")
        content_line = next(ln for ln in banner.splitlines() if "say" in ln)
        self.assertIn(r"say \"hi\"", content_line)
        self.assertNotIn(r"\\\"", content_line)


class TestAuditRtlSilentDegradation(TransactionCase):
    def test_missing_rtlcss_returns_ltr_silently(self):
        bundle = AssetsBundle(
            "test_assetsbundle.audit_rtl",
            [asset_file("/test_assetsbundle/static/src/css/audit_rtl.css", PLAIN_CSS)],
            env=self.env,
            js=False,
            rtl=True,
        )
        with patch(
            "odoo.addons.base.models.assetsbundle.css_pipeline._is_rtlcss_available",
            return_value=False,
        ):
            out = bundle._css.convert_css_to_rtl(PLAIN_CSS)
        self.assertEqual(out, PLAIN_CSS)
        self.assertFalse(bundle.css_errors)


class TestRunRtlcssEmptyOutputGuard(BaseCase):
    def _run(self, source, fake_out):
        bundle = _fake_bundle(name="t.b")
        pipe = CssPipeline(bundle)
        CssPipeline._compiled_cache.clear()
        with (
            patch.object(_ab.css_pipeline, "_is_rtlcss_available", return_value=True),
            patch.object(_ab.css_pipeline, "_rtlcss_bin", return_value="rtlcss"),
            patch.object(
                _ab.css_pipeline, "_rtlcss_config_path", return_value="/x.json"
            ),
            patch.object(_ab.css_pipeline, "_run_cli_pipe", return_value=fake_out),
        ):
            result = pipe.convert_css_to_rtl(source)
        return result, bundle.css_errors

    def test_whitespace_only_output_surfaces_error(self):
        result, errors = self._run("body{color:red}", "  \n")
        self.assertEqual(result, "")
        self.assertTrue(errors, "a swallowed-to-whitespace payload must banner")

    def test_empty_output_surfaces_error(self):
        result, errors = self._run("body{color:red}", "")
        self.assertEqual(result, "")
        self.assertTrue(errors)

    def test_normal_output_passes_through(self):
        result, errors = self._run("body{color:red}", "body{color:red}")
        self.assertEqual(result, "body{color:red}")
        self.assertFalse(errors)

    def test_whitespace_only_source_is_not_a_false_positive(self):
        _result, errors = self._run("   \n  ", "")
        self.assertFalse(errors, "empty output for an empty payload is fine")


class TestRtlOutputIsActuallyFlipped(TransactionCase):
    def test_directional_properties_flip(self):
        bundle = AssetsBundle(
            "test_assetsbundle.audit_rtl_resolution",
            [
                asset_file(
                    "/test/audit_rtl.css", ".box{padding-left:10px;margin-right:5px}"
                )
            ],
            env=self.env,
            js=False,
            rtl=True,
        )
        out = bundle.css().raw.decode()
        self.assertFalse(bundle.css_errors, f"css_errors: {bundle.css_errors}")
        self.assertIn("padding-right", out)
        self.assertNotIn("padding-left", out)
        self.assertIn("margin-left", out)
        self.assertNotIn("margin-right", re.sub(r"/\*.*?\*/", "", out, flags=re.DOTALL))


class TestAssetExtensionTable(TransactionCase):
    def test_extension_tables_match_the_constants(self):
        from odoo.tools.assets.constants import (
            SCRIPT_EXTENSIONS,
            STYLE_EXTENSIONS,
            TEMPLATE_EXTENSIONS,
        )

        self.assertEqual(set(STYLE_EXTENSIONS), set(AssetsBundle._STYLESHEET_TYPES))
        self.assertEqual(set(SCRIPT_EXTENSIONS), set(AssetsBundle._SCRIPT_TYPES))
        self.assertEqual(set(TEMPLATE_EXTENSIONS), set(AssetsBundle._TEMPLATE_TYPES))

    def test_query_string_does_not_hide_the_extension(self):
        bundle = AssetsBundle(
            "test.query_ext",
            [
                asset_file("/m/static/src/a.css?v=2", "a{}"),
                asset_file("/m/static/src/b.js#frag", "//b"),
            ],
            env=self.env,
        )
        self.assertEqual(len(bundle.stylesheets), 1)
        self.assertEqual(len(bundle.javascripts) + len(bundle.native_modules), 1)

    def test_sass_file_builds_a_sass_asset(self):
        bundle = AssetsBundle(
            "test.sass_ext",
            [asset_file("/mod/static/src/a.sass", ".x\n  color: red\n")],
            env=self.env,
        )
        self.assertEqual(len(bundle.stylesheets), 1)
        self.assertIsInstance(bundle.stylesheets[0], SassStylesheetAsset)

    def test_sass_cli_selects_the_indented_syntax(self):
        scss = ScssStylesheetAsset(None, inline="// x")
        sass = SassStylesheetAsset(None, inline="// x")
        self.assertEqual(scss._sass_syntax, "scss")
        self.assertEqual(sass._sass_syntax, "indented")
        self.assertIn("--no-indented", scss.get_command())
        self.assertIn("--indented", sass.get_command())
        self.assertNotIn("--no-indented", sass.get_command())

    def test_sass_bundle_compiles_end_to_end(self):
        bundle = AssetsBundle(
            "test.sass_compile",
            [asset_file("/mod/static/src/a.sass", ".audit-sass\n  color: red\n")],
            env=self.env,
        )
        css = bundle.preprocess_css()
        self.assertFalse(bundle.css_errors, bundle.css_errors)
        self.assertIn(".audit-sass", css)
        self.assertIn("color:red", css.replace(" ", ""))

    def test_sass_compiles_the_same_on_the_cli_fallback(self):
        from odoo.tools import sass_embedded

        source = ".audit-sass\n  color: red\n  &:hover\n    color: blue\n"
        spec = [asset_file("/mod/static/src/a.sass", source)]

        embedded = AssetsBundle("test.sass_emb", spec, env=self.env).preprocess_css()
        with patch.object(
            sass_embedded,
            "get_sass_compiler",
            side_effect=sass_embedded.SassProtocolError("forced"),
        ):
            cli = AssetsBundle("test.sass_cli", spec, env=self.env).preprocess_css()

        self.assertIn(".audit-sass:hover", embedded)
        self.assertEqual(embedded.strip(), cli.strip())

    def test_a_bug_in_the_embedded_path_is_not_hidden_behind_the_cli(self):
        from odoo.tools import sass_embedded

        spec = [asset_file("/mod/static/src/a.scss", ".x{color:red}")]
        bundle = AssetsBundle("test.sass_bug", spec, env=self.env)
        with (
            patch.object(
                sass_embedded, "get_sass_compiler", side_effect=TypeError("bug")
            ),
            self.assertRaises(TypeError),
        ):
            bundle.preprocess_css()

    def test_mixed_dialects_degrade_instead_of_raising(self):
        bundle = AssetsBundle(
            "test.sass_mixed",
            [
                asset_file("/mod/static/src/a.sass", ".x\n  color: red\n"),
                asset_file("/mod/static/src/b.scss", ".y{color:blue}"),
            ],
            env=self.env,
        )
        self.assertEqual(bundle.preprocess_css(), "")
        self.assertTrue(bundle.css_errors)
        self.assertIn("dialects", bundle.css_errors[0])


class TestUrlExtensionCaseFolding(TransactionCase):
    def test_uppercase_member_survives_ir_asset_resolution(self):
        self.env["ir.attachment"].create(
            {
                "name": "upper ext css",
                "mimetype": "text/css",
                "type": "binary",
                "url": "test_assetsbundle/audit_upper.CSS",
                "raw": b".audit_upper{color:red}",
            }
        )
        self.env["ir.asset"].create(
            {
                "name": "audit upper",
                "bundle": "test_assetsbundle.audit_upper",
                "path": "test_assetsbundle/audit_upper.CSS",
            }
        )
        with mute_logger("odoo.addons.base.models.ir_asset"):
            bundle = self.env["ir.qweb"]._get_asset_bundle(
                "test_assetsbundle.audit_upper"
            )
        self.assertEqual(
            len(bundle.stylesheets),
            1,
            "an upper-case member reached the bundle and was dropped",
        )
        self.assertIn(".audit_upper", bundle.preprocess_css())

    def test_uppercase_extensions_are_classified(self):
        bundle = AssetsBundle(
            "test_assetsbundle.audit_case",
            [
                asset_file("/test/audit_case.CSS", ".audit-case{color:red}"),
                asset_file("/test/audit_case.JS", "window.auditCase = 1;"),
                asset_file(
                    "/test/audit_case.XML", "<templates><t t-name='a.b'/></templates>"
                ),
            ],
            env=self.env,
        )
        self.assertEqual(len(bundle.stylesheets), 1)
        self.assertEqual(len(bundle.javascripts) + len(bundle.native_modules), 1)
        self.assertEqual(len(bundle.templates), 1)

    def test_query_string_and_case_combined(self):
        self.assertEqual(AssetsBundle._url_extension("/a/b.SCSS?v=2#x"), "scss")


class TestSourceDialectTokenizers(BaseCase):
    def _rewritten(self, source, token_re):
        bodies = []

        def _collect(match):
            bodies.append(match.group("body"))
            return match.group(0)

        _rewrite_css_outside_strings(StylesheetAsset.rx_url, _collect, source, token_re)
        return bodies

    def test_scss_line_comment_apostrophe_keeps_later_urls(self):
        source = "// Lato's matrix\n@font-face { src: url('./lato/a.woff'); }"
        self.assertEqual(
            self._rewritten(source, ScssStylesheetAsset._SOURCE_TOKEN_RE),
            ["./lato/a.woff"],
        )

    def test_scss_line_comment_body_is_opaque(self):
        source = "// see url('./x.woff')\n.a { background: url('./y.png'); }"
        self.assertEqual(
            self._rewritten(source, ScssStylesheetAsset._SOURCE_TOKEN_RE),
            ["./y.png"],
        )

    def test_scss_protocol_relative_url_is_not_a_comment(self):
        source = ".a { src: url(//cdn/a.woff) format('woff'),"
        source += " url('./b.woff') format('woff'); }"
        self.assertEqual(
            self._rewritten(source, ScssStylesheetAsset._SOURCE_TOKEN_RE),
            ["./b.woff"],
        )

    def test_plain_css_keeps_double_slash_as_text(self):
        source = ".a { background: url('https://x/y.png'); src: url('./z.woff'); }"
        self.assertEqual(
            self._rewritten(source, StylesheetAsset._SOURCE_TOKEN_RE),
            ["./z.woff"],
        )

    def test_scss_asset_selects_the_scss_tokenizer(self):
        self.assertIsNot(
            ScssStylesheetAsset._SOURCE_TOKEN_RE,
            StylesheetAsset._SOURCE_TOKEN_RE,
            "SCSS sources must not be scanned with the plain-CSS tokenizer",
        )


class TestCssCompileErrorReporting(TransactionCase):
    BROKEN_SCSS = ".rule1 ()){\n    color: black;\n}\n"

    def _bundle(self, *files, **kw):
        return make_bundle(self, "test_assetsbundle.csserr", *files, js=False, **kw)

    def test_a_sass_error_is_reported_not_raised(self):
        bundle = self._bundle(("/m/static/src/broken.scss", self.BROKEN_SCSS))
        with mute_logger("odoo.addons.base.models.assetsbundle"):
            out = bundle.preprocess_css()

        self.assertEqual(out, "", "a bundle that failed to compile serves nothing")
        self.assertTrue(bundle.css_errors)

    def test_the_error_names_the_bundle_and_its_members(self):
        bundle = self._bundle(
            ("/m/static/src/broken.scss", self.BROKEN_SCSS),
            ("/m/static/src/fine.scss", ".ok{color:red}"),
        )
        with mute_logger("odoo.addons.base.models.assetsbundle"):
            bundle.preprocess_css()

        (error,) = bundle.css_errors
        self.assertIn("test_assetsbundle.csserr", error)
        self.assertIn("/m/static/src/broken.scss", error)
        self.assertIn(
            "/m/static/src/fine.scss",
            error,
            "every member is listed: the compiler saw the concatenation, so "
            "the line it complains about is not necessarily in the broken file",
        )

    def test_the_error_points_at_the_file_that_failed(self):
        bundle = self._bundle(
            ("/m/static/src/fine.scss", ".ok{color:red}"),
            ("/m/static/src/broken.scss", self.BROKEN_SCSS),
        )
        with mute_logger("odoo.addons.base.models.assetsbundle"):
            bundle.preprocess_css()

        (error,) = bundle.css_errors
        self.assertIn(
            "/m/static/src/broken.scss line",
            error,
            "the member list narrows the search to the bundle; the compiler's "
            "own line number is against the concatenation, so it has to be "
            "resolved back to a file before it means anything",
        )

    def test_the_located_line_is_numbered_within_its_own_file(self):
        bundle = self._bundle(
            ("/m/static/src/first.scss", ".a{color:red}"),
            ("/m/static/src/second.scss", ".b{color:blue}\n.c{color:green}"),
        )
        pipeline = bundle._css
        source = "\n".join(asset.get_source() for asset in bundle.stylesheets)
        # 1 marker, 2 .a, 3 marker, 4 .b, 5 .c
        located = pipeline._locate_source_line(source, 5)

        self.assertIn("/m/static/src/second.scss line 2", located)
        self.assertIn(".c{color:green}", located)

    def test_a_line_outside_the_source_locates_nothing(self):
        pipeline = CssPipeline(_fake_bundle(name="b"))
        self.assertEqual(pipeline._locate_source_line("a\nb\n", 99), "")

    def test_a_protocol_slash_inside_a_string_is_not_a_comment(self):
        """`//` inside a quoted url() is data, not the start of a comment.

        A comment stripper that is not string-aware truncates the line at the
        protocol, and the whole bundle then stops compiling for a reason that
        names no file. This shape has reached production once already.
        """
        svg = "<svg xmlns='http://www.w3.org/2000/svg'/>"
        bundle = self._bundle(
            (
                "/m/static/src/dataurl.scss",
                f'.a{{background:url("data:image/svg+xml;utf8,{svg}")}}',
            )
        )
        out = bundle.preprocess_css()

        self.assertFalse(bundle.css_errors, bundle.css_errors)
        self.assertIn("www.w3.org/2000/svg", out)

    def test_the_error_reaches_the_banner(self):
        bundle = self._bundle(("/m/static/src/broken.scss", self.BROKEN_SCSS))
        with mute_logger("odoo.addons.base.models.assetsbundle"):
            banner = bundle.css().raw.decode()

        self.assertIn(CssPipeline._CSS_ERROR_HEADER, banner)
        self.assertIn("test_assetsbundle.csserr", banner)

    def test_sass_load_path_noise_is_trimmed(self):
        pipeline = CssPipeline(_fake_bundle(name="b"))
        formatted = pipeline._format_compiler_error(
            "Error: bad\n  Use --trace for backtrace.\nLoad paths\n  /a\n  /b\n"
        )
        self.assertNotIn("Load paths", formatted)
        self.assertNotIn("Use --trace", formatted)
        self.assertIn("Error: bad", formatted)

    def test_a_desynchronised_split_marker_is_loud(self):
        bundle = self._bundle(("/m/static/src/a.scss", ".a{color:red}"))
        pipeline = bundle._css
        pipeline.compile_css = lambda compiler, source: (
            "/*! odoo-split:ffff */\n.a{color:red}"
        )
        with self.assertRaisesRegex(RuntimeError, "out of sync"):
            pipeline.preprocess()


class TestRtlcssProbeFailures(BaseCase):
    def setUp(self):
        super().setUp()
        _ab.css_pipeline._is_rtlcss_available.cache_clear()
        self.addCleanup(_ab.css_pipeline._is_rtlcss_available.cache_clear)

    def test_a_missing_binary_disables_rtl(self):
        with (
            patch.object(
                _ab.css_pipeline, "Popen", side_effect=OSError("no such file")
            ),
            self.assertLogs("odoo.addons.base.models.assetsbundle", "WARNING") as log,
        ):
            self.assertFalse(_ab.css_pipeline._is_rtlcss_available())
        self.assertIn("rtlcss is required", "\n".join(log.output))

    def test_a_hanging_probe_is_killed_and_disables_rtl(self):
        import subprocess

        probe = Mock()
        probe.communicate.side_effect = [
            subprocess.TimeoutExpired("rtlcss", 10),
            (b"", b""),
        ]
        with (
            patch.object(_ab.css_pipeline, "Popen", return_value=probe),
            self.assertLogs("odoo.addons.base.models.assetsbundle", "WARNING") as log,
        ):
            self.assertFalse(_ab.css_pipeline._is_rtlcss_available())
        probe.kill.assert_called_once()
        self.assertIn("probe timed out", "\n".join(log.output))

    def test_a_nonzero_probe_disables_rtl(self):
        probe = Mock()
        probe.communicate.return_value = (b"", b"")
        probe.returncode = 127
        with (
            patch.object(_ab.css_pipeline, "Popen", return_value=probe),
            self.assertLogs("odoo.addons.base.models.assetsbundle", "WARNING") as log,
        ):
            self.assertFalse(_ab.css_pipeline._is_rtlcss_available())
        self.assertIn("exited with 127", "\n".join(log.output))

    def test_a_working_probe_enables_rtl(self):
        probe = Mock()
        probe.communicate.return_value = (b"4.1.0", b"")
        probe.returncode = 0
        with patch.object(_ab.css_pipeline, "Popen", return_value=probe):
            self.assertTrue(_ab.css_pipeline._is_rtlcss_available())
