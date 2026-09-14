import logging
import re
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from odoo import tools
from odoo.tests.common import BaseCase, TransactionCase
from odoo.tools.assets import esbuild_process
from odoo.tools.assets.esbuild import EsbuildCompiler, _get_esbuild_path
from odoo.tools.json import scriptsafe as json


class TestEsbuildFailClosed(TransactionCase):
    def _run(self, **config):
        from odoo.addons.base.models.ir_qweb_assets_esbuild import EsbuildBundleError

        qweb = self.env["ir.qweb"]
        patched = dict(tools.config._runtime_options)
        patched.update(config)
        with patch.dict(tools.config._runtime_options, patched, clear=False):
            return qweb._is_esbuild_fail_closed(), EsbuildBundleError

    def test_test_enable_fails_closed(self):
        fail_closed, _ = self._run(test_enable=True, dev_mode=[])
        self.assertTrue(fail_closed)

    def test_dev_assets_fails_closed(self):
        fail_closed, _ = self._run(test_enable=False, dev_mode=["assets"])
        self.assertTrue(fail_closed)

    def test_production_still_degrades(self):
        fail_closed, _ = self._run(test_enable=False, dev_mode=[])
        self.assertFalse(fail_closed)

    def test_unrelated_dev_mode_still_degrades(self):
        fail_closed, _ = self._run(test_enable=False, dev_mode=["xml", "reload"])
        self.assertFalse(fail_closed)

    def test_config_parameter_overrides_both_ways(self):
        param = self.env["ir.config_parameter"].sudo()
        param.set_param("web.esbuild.fail_closed", "0")
        fail_closed, _ = self._run(test_enable=True, dev_mode=["assets"])
        self.assertFalse(fail_closed, "explicit 0 must disable it under --test-enable")

        param.set_param("web.esbuild.fail_closed", "1")
        fail_closed, _ = self._run(test_enable=False, dev_mode=[])
        self.assertTrue(fail_closed, "explicit 1 must enable it on a plain server")


NATIVE_BUNDLE = "test_assetsbundle.native_esm"
NATIVE_DEP = "@test_assetsbundle/../tests/native_esm/dep"
NATIVE_ENTRY = "@test_assetsbundle/../tests/native_esm/entry"
NATIVE_REEXPORT = "@test_assetsbundle/../tests/native_esm/reexport"


@unittest.skipUnless(_get_esbuild_path(), "esbuild binary not available")
class TestEsbuildEndToEnd(TransactionCase):
    def _bundle(self):
        return self.env["ir.qweb"]._get_asset_bundle(
            NATIVE_BUNDLE, css=False, assets_params={}
        )

    def test_the_fixture_bundle_routes_to_native_modules(self):
        bundle = self._bundle()
        self.assertEqual(
            sorted(a.module_path for a in bundle.native_modules),
            [NATIVE_DEP, NATIVE_ENTRY, NATIVE_REEXPORT],
        )
        self.assertFalse(bundle.javascripts)

    def test_a_registered_bundle_compiles_and_resolves_its_imports(self):
        result = self._bundle().esbuild_native_bundle()

        self.assertTrue(result.code, "esbuild produced no output")
        self.assertNotRegex(
            result.code,
            r'(^|[;\s])import\s*[{"\']',
            "a bare import survived bundling, so a specifier went unresolved",
        )
        self.assertIn("41", result.code, "the imported constant must be inlined")

    def test_the_metafile_accounts_for_every_member(self):
        result = self._bundle().esbuild_native_bundle()

        self.assertTrue(result.metafile, "no metafile: the GC sidecar has no input")
        inputs = json.loads(result.metafile)["inputs"]
        for name in ("dep.js", "entry.js", "reexport.js"):
            self.assertTrue(
                any(name in path for path in inputs),
                f"{name} is a bundle member but absent from the metafile",
            )

    def test_two_compiles_of_the_same_sources_agree(self):
        first = self._bundle().esbuild_native_bundle()
        second = self._bundle().esbuild_native_bundle()
        self.assertEqual(first.code, second.code)


class TestEsbuildFailurePath(TransactionCase):
    def setUp(self):
        super().setUp()
        circuit = self.env["ir.qweb"]._esbuild_circuit
        self.addCleanup(circuit.restore, circuit.snapshot())
        circuit.clear()

    def _run_with_broken_compiler(self, fail_closed):
        self.env["ir.config_parameter"].sudo().set_param(
            "web.esbuild.fail_closed", "1" if fail_closed else "0"
        )
        asset_bundle = self.env["ir.qweb"]._get_asset_bundle(
            NATIVE_BUNDLE, css=False, assets_params={}
        )
        # a by-source row another test saved through its own connection
        # would answer the compile before the broken compiler is asked
        with (
            patch.object(
                type(asset_bundle),
                "esbuild_native_bundle",
                side_effect=RuntimeError("esbuild exploded"),
            ),
            patch.object(
                type(self.env["ir.qweb"]),
                "_load_esbuild_result_by_source",
                return_value=None,
            ),
        ):
            return self.env["ir.qweb"]._compile_with_esbuild_locked(
                NATIVE_BUNDLE, asset_bundle, {}
            )

    def test_a_compile_failure_raises_when_fail_closed(self):
        from odoo.addons.base.models.ir_qweb_assets_esbuild import EsbuildBundleError

        with self.assertLogs("odoo.assets.fallback", level="WARNING"):
            with self.assertRaises(EsbuildBundleError) as caught:
                self._run_with_broken_compiler(fail_closed=True)
        self.assertIn(NATIVE_BUNDLE, str(caught.exception))
        self.assertIn("esbuild exploded", str(caught.exception))

    def test_a_compile_failure_degrades_when_not_fail_closed(self):
        with self.assertLogs("odoo.assets.fallback", level="WARNING"):
            result, _children = self._run_with_broken_compiler(fail_closed=False)
        self.assertEqual(result.code, "")
        self.assertIsNone(result.metafile)


class TestMinifyJsFailureModes(BaseCase):
    SOURCE = "const a = `A${`B  ${1}  C`}D`;\n"

    def test_no_binary_returns_none_and_says_so(self):
        from odoo.tools.assets import esbuild

        with (
            patch.object(esbuild, "_get_esbuild_path", return_value=None),
            self.assertLogs("odoo.assets.esbuild", level="WARNING") as logged,
        ):
            self.assertIsNone(esbuild.minify_js(self.SOURCE, label="probe.js"))
        self.assertIn("minify_no_binary", "\n".join(logged.output))

    def test_a_timeout_returns_none_and_says_so(self):
        import subprocess

        from odoo.tools.assets import esbuild

        with (
            patch.object(esbuild, "_get_esbuild_path", return_value="/bin/true"),
            patch.object(
                esbuild.subprocess,
                "run",
                side_effect=subprocess.TimeoutExpired("esbuild", 60),
            ),
            self.assertLogs("odoo.assets.esbuild", level="WARNING") as logged,
        ):
            self.assertIsNone(esbuild.minify_js(self.SOURCE, label="probe.js"))
        self.assertIn("minify_timeout", "\n".join(logged.output))

    def test_a_nonzero_exit_returns_none_and_surfaces_stderr(self):
        from odoo.tools.assets import esbuild

        with (
            patch.object(esbuild, "_get_esbuild_path", return_value="/bin/false"),
            self.assertLogs("odoo.assets.esbuild", level="WARNING") as logged,
        ):
            self.assertIsNone(esbuild.minify_js("this is not js {", label="bad.js"))
        joined = "\n".join(logged.output)
        self.assertIn("minify_failed", joined)
        self.assertIn("esbuild minify stderr for bad.js", joined)

    @unittest.skipUnless(_get_esbuild_path(), "esbuild binary not available")
    def test_the_success_path_really_minifies(self):
        from odoo.tools.assets import esbuild

        out = esbuild.minify_js("const a  =  1;\nconst b  =  2;\n", label="ok.js")
        self.assertIsNotNone(out)
        self.assertNotIn("  ", out)
        self.assertIn("const", out)


class TestRunEsbuildFailureReporting(BaseCase):
    def test_a_nonzero_exit_dumps_the_entry_and_names_the_file(self):
        name = "test.failrep"
        self.addCleanup(esbuild_process.remove_stale_fail_dumps, name)

        with self.assertLogs("odoo.assets.esbuild", level="WARNING") as logged:
            with self.assertRaises(RuntimeError) as caught:
                esbuild_process.run_esbuild(
                    name,
                    ["sh", "-c", "echo 'boom' >&2; exit 3"],
                    30,
                    "// the entry that failed\n",
                    0.0,
                )

        self.assertIn("exit 3", str(caught.exception))
        self.assertIn("boom", str(caught.exception))
        joined = "\n".join(logged.output)
        self.assertIn("event=failed", joined)

        dump = re.search(r"entry=(\S+\.js)", joined)
        self.assertIsNotNone(dump, f"the entry dump was not named: {joined}")
        self.assertEqual(
            Path(dump.group(1)).read_text(encoding="utf-8"),
            "// the entry that failed\n",
        )

    def test_each_failure_purges_the_previous_dump_for_that_bundle(self):
        name = "test.purge"
        self.addCleanup(esbuild_process.remove_stale_fail_dumps, name)

        def fail_once(text):
            with self.assertLogs("odoo.assets.esbuild", level="WARNING") as logged:
                with self.assertRaises(RuntimeError):
                    esbuild_process.run_esbuild(
                        name, ["sh", "-c", "exit 1"], 30, text, 0.0
                    )
            return re.search(r"entry=(\S+\.js)", "\n".join(logged.output)).group(1)

        first = fail_once("// first\n")
        second = fail_once("// second\n")

        self.assertNotEqual(first, second)
        self.assertFalse(Path(first).exists(), "the previous dump must be purged")
        self.assertTrue(Path(second).exists())

    def test_a_timeout_is_reported_as_a_timeout(self):
        with self.assertLogs("odoo.assets.esbuild", level="ERROR") as logged:
            with self.assertRaises(RuntimeError) as caught:
                esbuild_process.run_esbuild(
                    "test.failrep", ["sleep", "5"], 1, "// slow\n", 0.0
                )
        self.assertIn("timed out after 1s", str(caught.exception))
        self.assertIn("event=timeout", "\n".join(logged.output))

    def test_a_clean_exit_says_nothing_and_writes_nothing(self):
        name = "test.quiet"
        esbuild_process.remove_stale_fail_dumps(name)
        with self.assertNoLogs("odoo.assets.esbuild", level="WARNING"):
            esbuild_process.run_esbuild(name, ["true"], 30, "// fine\n", 0.0)
        self.assertEqual(
            list(Path(tempfile.gettempdir()).glob("esbuild_fail_test.quiet_*.js")), []
        )


class _EntryMod:
    def __init__(self, module_path, url="", filename=None, raw_content=""):
        self.module_path = module_path
        self.url = url
        self._filename = filename
        self.raw_content = raw_content


class TestParentOwnedRelativeImports(BaseCase):
    def test_relative_import_reuses_the_parent_without_running_its_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "probe/static/src"
            other_root = Path(tmp) / "other/static/src"
            for addon_root, marker in ((root, "first"), (other_root, "second")):
                addon_root.mkdir(parents=True)
                tests = addon_root.parent / "tests"
                tests.mkdir()
                (tests / "marker.js").write_text(f"export const marker = '{marker}';")
            sources = {
                "shared": "globalThis.sharedExecutions++; export const token = {};",
                "entry": (
                    "export { token } from './shared.js';"
                    "import { marker as first } from '@probe/../tests/marker';"
                    "import { marker as second } from '@other/../tests/marker';"
                    "export const markers = [first, second];"
                ),
            }
            modules = []
            for name, content in sources.items():
                path = root / f"{name}.js"
                path.write_text(content)
                module = _EntryMod(
                    f"@probe/{name}",
                    f"/probe/static/src/{name}.js",
                    str(path),
                    content,
                )
                module.parsed_header = None
                modules.append(module)
            compiler = EsbuildCompiler(
                "test.parent_owned_relative",
                modules,
                [],
                standalone=True,
                addon_flags_provider=lambda _: (
                    [f"--alias:@probe={root}", f"--alias:@other={other_root}"],
                    [],
                ),
            )
            compiled = compiler.compile(
                secondary_parent_stubs={
                    "@probe/shared": "export const token = globalThis.parentToken;",
                    "@other/shared": "export const token = globalThis.parentToken;",
                }
            )
            probe = subprocess.run(
                ["node", "--input-type=module"],
                input=(
                    "globalThis.parentToken = {}; globalThis.sharedExecutions = 0;"
                    "const modules = {}; globalThis.odoo = {loader: {"
                    "registerNativeModules: values => Object.assign(modules, values)}};"
                    + compiled.code
                    + "\nconsole.log(JSON.stringify({"
                    "same: modules['@probe/entry'].token === globalThis.parentToken,"
                    "executions: globalThis.sharedExecutions,"
                    "registeredParent: '@probe/shared' in modules,"
                    "markers: modules['@probe/entry'].markers}));"
                ),
                capture_output=True,
                text=True,
                check=True,
                timeout=10,
            )
            observed = json.loads(probe.stdout)
            logging.getLogger(__name__).debug("Parent ownership probe: %s", observed)
            self.assertEqual(
                observed,
                {
                    "same": True,
                    "executions": 0,
                    "registeredParent": False,
                    "markers": ["first", "second"],
                },
            )

            self.assertEqual((root / "shared.js").read_text(), sources["shared"])


class TestEsbuildEntryLines(BaseCase):
    ROOT = Path("/odoo")

    def _compiler(self, modules, **kw):
        return EsbuildCompiler("test.entry", modules, [], **kw)

    def test_a_standalone_bundle_publishes_its_modules_behind_a_guard(self):
        lines = self._compiler(
            [_EntryMod("@a/one", url="/a/static/src/one.js")], standalone=True
        )._esbuild_entry_lines(self.ROOT)

        self.assertEqual(
            lines[0], 'import * as __m0 from "./addons/a/static/src/one.js";'
        )
        self.assertEqual(
            lines[1], "if (globalThis.odoo?.loader?.registerNativeModules) {"
        )
        self.assertEqual(lines[-1], "}")
        self.assertIn('  "@a/one": __m0', lines)

    def test_a_rendered_bundle_publishes_unguarded(self):
        lines = self._compiler(
            [_EntryMod("@a/one", url="/a/static/src/one.js")]
        )._esbuild_entry_lines(self.ROOT)

        self.assertNotIn("if (globalThis.odoo?.loader?.registerNativeModules) {", lines)
        self.assertIn("odoo.loader.registerNativeModules({", lines)

    def test_owl_rides_along_only_when_a_standalone_bundle_uses_it(self):
        without = self._compiler(
            [_EntryMod("@a/one", url="/a/static/src/one.js")], standalone=True
        )._esbuild_entry_lines(self.ROOT)
        self.assertFalse(any("@odoo/owl" in line for line in without))

        with_owl = self._compiler(
            [
                _EntryMod(
                    "@a/one",
                    url="/a/static/src/one.js",
                    raw_content='import { Component } from "@odoo/owl";',
                )
            ],
            standalone=True,
        )._esbuild_entry_lines(self.ROOT)
        self.assertIn('import * as __owl from "@odoo/owl";', with_owl)

    def test_an_app_bundle_registers_every_member_with_the_loader(self):
        lines = self._compiler(
            [
                _EntryMod("@a/one", url="/a/static/src/one.js"),
                _EntryMod("@a/two", url="/a/static/src/two.js"),
            ]
        )._esbuild_entry_lines(self.ROOT)
        entry = "\n".join(lines)

        self.assertIn('import * as __owl from "@odoo/owl";', entry)
        self.assertIn("odoo.loader.registerNativeModules({", entry)
        self.assertIn('"@a/one": __m0', entry)
        self.assertIn('"@a/two": __m1', entry)
        self.assertIn('"@odoo/owl": __owl', entry)

    def test_a_real_file_is_addressed_by_its_path_on_disk(self):
        lines = self._compiler(
            [
                _EntryMod(
                    "@a/one",
                    url="/a/static/src/one.js",
                    filename="/odoo/addons/a/static/src/one.js",
                )
            ]
        )._esbuild_entry_lines(self.ROOT)

        self.assertIn('import * as __m0 from "./addons/a/static/src/one.js";', lines)

    def test_a_test_member_is_skipped_where_the_import_map_supplies_it(self):
        modules = [
            _EntryMod("@a/src", url="/a/static/src/src.js"),
            _EntryMod("@a/../tests/spec", url="/a/static/tests/spec.js"),
        ]
        entry = "\n".join(
            self._compiler(modules, skip_legacy_test_imports=True)._esbuild_entry_lines(
                self.ROOT
            )
        )

        self.assertIn('"@a/src"', entry)
        self.assertNotIn("tests/spec", entry)

    def test_the_same_member_is_kept_when_that_flag_is_off(self):
        modules = [_EntryMod("@a/../tests/spec", url="/a/static/tests/spec.js")]
        entry = "\n".join(self._compiler(modules)._esbuild_entry_lines(self.ROOT))
        self.assertIn("tests/spec", entry)

    def test_hoot_is_aliased_only_when_the_bundle_carries_it(self):
        without = "\n".join(
            self._compiler(
                [_EntryMod("@a/one", url="/a/static/src/one.js")]
            )._esbuild_entry_lines(self.ROOT)
        )
        self.assertNotIn("@odoo/hoot", without)

        with_hoot = "\n".join(
            self._compiler(
                [_EntryMod("@web/../lib/hoot/hoot", url="/web/static/lib/hoot/hoot.js")]
            )._esbuild_entry_lines(self.ROOT)
        )
        self.assertIn(
            'odoo.loader.modules.set("@odoo/hoot",'
            'odoo.loader.modules.get("@web/../lib/hoot/hoot"));',
            with_hoot,
        )

    def test_an_empty_bundle_still_registers_owl(self):
        entry = "\n".join(self._compiler([])._esbuild_entry_lines(self.ROOT))
        self.assertIn('"@odoo/owl": __owl', entry)
