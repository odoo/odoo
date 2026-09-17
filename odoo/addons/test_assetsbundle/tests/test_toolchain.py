import errno
import pathlib
from pathlib import Path
from unittest.mock import patch

import odoo
from odoo.tests.common import BaseCase

from odoo.addons.base.models.assetsbundle.common import (
    CompileError,
    _pipeline_fingerprint,
    _pipeline_sources,
    _run_cli_pipe,
)
from odoo.addons.base.models.assetsbundle.css_pipeline import _rtlcss_bin


class TestRtlcssResolution(BaseCase):
    def test_resolves_to_an_existing_executable(self):
        binary = _rtlcss_bin()
        self.assertTrue(
            Path(binary).is_absolute() and Path(binary).exists(),
            f"rtlcss resolved to {binary!r}, which does not exist; RTL bundles "
            f"would be served as LTR and every skipUnless(_is_rtlcss_available()) "
            f"suite would report success without running",
        )

    def test_rtlcss_binary_resolution_shared_between_probe_and_run(self):
        from odoo.addons.base.models import assetsbundle

        self.addCleanup(assetsbundle.css_pipeline._rtlcss_bin.cache_clear)

        assetsbundle.css_pipeline._rtlcss_bin.cache_clear()
        with (
            patch.object(assetsbundle.css_pipeline.os, "name", "nt"),
            patch.object(
                assetsbundle.css_pipeline.misc,
                "get_executable_path",
                return_value="C:/npm/rtlcss.cmd",
            ) as find,
        ):
            self.assertEqual(
                assetsbundle.css_pipeline._rtlcss_bin(), "C:/npm/rtlcss.cmd"
            )
            find.assert_called_once_with("rtlcss.cmd")

        assetsbundle.css_pipeline._rtlcss_bin.cache_clear()
        with (
            patch.object(assetsbundle.css_pipeline.os, "name", "posix"),
            patch.object(
                assetsbundle.css_pipeline.misc,
                "get_executable_path",
                return_value="/usr/bin/rtlcss",
            ),
        ):
            self.assertEqual(assetsbundle.css_pipeline._rtlcss_bin(), "/usr/bin/rtlcss")

    def test_rtlcss_binary_falls_back_to_node_modules(self):
        from odoo.addons.base.models import assetsbundle

        self.addCleanup(assetsbundle.css_pipeline._rtlcss_bin.cache_clear)
        assetsbundle.css_pipeline._rtlcss_bin.cache_clear()

        node_bin = str(
            pathlib.Path(odoo.__path__[0]).parent / "node_modules" / ".bin" / "rtlcss"
        )
        with (
            patch.object(assetsbundle.css_pipeline.os, "name", "posix"),
            patch.object(
                assetsbundle.css_pipeline.misc,
                "get_executable_path",
                side_effect=OSError(errno.ENOENT, "not found"),
            ),
            patch.object(
                assetsbundle.css_pipeline.shutil, "which", return_value=node_bin
            ) as which,
        ):
            self.assertEqual(assetsbundle.css_pipeline._rtlcss_bin(), node_bin)
        self.assertEqual(which.call_args.args, ("rtlcss",))
        self.assertTrue(which.call_args.kwargs["path"].endswith("node_modules/.bin"))


class TestNodeToolchainManifest(BaseCase):
    @staticmethod
    def _manifests():
        import json

        import odoo

        root = Path(odoo.__path__[0]).parent
        return (
            json.loads((root / "package.json").read_text()),
            json.loads((root / "package-lock.json").read_text()),
        )

    def test_rtlcss_is_declared(self):
        manifest, _ = self._manifests()
        self.assertIn("rtlcss", manifest["devDependencies"])

    def test_every_declared_dependency_is_locked(self):
        manifest, lock = self._manifests()
        declared = manifest["devDependencies"]
        packages = lock["packages"]
        locked_root = packages[""].get("devDependencies", {})
        self.assertEqual(
            declared,
            locked_root,
            "package.json and package-lock.json disagree; `npm ci` refuses to "
            "install. Regenerate with `npm install --package-lock-only`.",
        )
        for name in declared:
            self.assertIn(
                f"node_modules/{name}",
                packages,
                f"{name} is declared and root-locked but has no resolved entry",
            )


class TestPipelineFingerprint(BaseCase):
    def _covered_files(self):
        covered = []
        for source in _pipeline_sources():
            if source.is_dir():
                covered.extend(source.glob("*.py"))
            elif source.is_file():
                covered.append(source)
        return covered

    def test_rtlcss_config_is_covered(self):
        self.assertIn("rtlcss.json", {p.name for p in self._covered_files()})

    def test_content_addressed_inputs_are_not_covered(self):
        self.assertNotIn(
            "esm_lexer_worker.mjs", {p.name for p in self._covered_files()}
        )

    def test_every_declared_source_still_resolves(self):
        missing = [s for s in _pipeline_sources() if not (s.is_dir() or s.is_file())]
        self.assertFalse(
            missing,
            "a declared source resolving to nothing is skipped silently, so "
            "changes to it never invalidate a cached bundle",
        )

    def _assert_edit_moves_digest(self, target):
        before = _pipeline_fingerprint()
        real_read = type(target).read_bytes

        def _mutated(self):
            data = real_read(self)
            return data + b"\n/* pretend edit */\n" if self == target else data

        _pipeline_fingerprint.cache_clear()
        try:
            with patch.object(type(target), "read_bytes", _mutated):
                after = _pipeline_fingerprint()
        finally:
            _pipeline_fingerprint.cache_clear()
        self.assertNotEqual(before, after, f"editing {target.name} did not invalidate")

    def test_editing_the_rtlcss_config_moves_the_digest(self):
        config = next(p for p in self._covered_files() if p.name == "rtlcss.json")
        self._assert_edit_moves_digest(config)

    def test_editing_a_covered_python_source_moves_the_digest(self):
        esbuild = next(p for p in self._covered_files() if p.name == "esbuild.py")
        self._assert_edit_moves_digest(esbuild)

    def test_the_compiler_layer_is_covered(self):
        covered = {p.name for p in self._covered_files()}
        for name in ("esbuild.py", "esm_graph.py", "sass_embedded.py", "bundle.py"):
            self.assertIn(name, covered)

    def test_an_unresolvable_package_degrades_instead_of_crashing(self):
        from odoo import release

        from odoo.addons.base.models.assetsbundle import common

        _pipeline_fingerprint.cache_clear()
        try:
            with patch.object(common.odoo.tools, "__file__", None):
                self.assertEqual(_pipeline_sources(), ())
                self.assertEqual(_pipeline_fingerprint(), release.version)
        finally:
            _pipeline_fingerprint.cache_clear()


class TestToolchainParticipatesInBundleIdentity(BaseCase):
    def _fingerprint_with(self, versions):
        from odoo.addons.base.models.assetsbundle import common

        _pipeline_fingerprint.cache_clear()
        try:
            with patch.object(common, "_toolchain_versions", lambda: versions):
                return _pipeline_fingerprint.__wrapped__()
        finally:
            _pipeline_fingerprint.cache_clear()

    def test_every_output_affecting_tool_is_reported(self):
        from odoo.addons.base.models.assetsbundle.common import (
            _OUTPUT_AFFECTING_NPM_TOOLS,
            _toolchain_versions,
        )

        reported = _toolchain_versions()
        for name in _OUTPUT_AFFECTING_NPM_TOOLS:
            self.assertIn(f"{name}@", reported)
        for name in ("sass-embedded", "rtlcss", "esbuild"):
            self.assertIn(name, _OUTPUT_AFFECTING_NPM_TOOLS)

    def test_the_javascript_minifier_is_part_of_the_identity(self):
        from odoo.addons.base.models.assetsbundle.common import _toolchain_versions

        # rjsmin writes every min.js; an upgrade that changes its output must
        # move the version, or a cleared attachment table serves a new byte
        # stream under an old url
        self.assertRegex(_toolchain_versions(), r"rjsmin@\d+\.\d+")

    def test_the_sourcemap_generator_is_a_fingerprinted_source(self):
        from odoo.addons.base.models.assetsbundle.common import _pipeline_sources

        names = {source.name for source in _pipeline_sources()}
        self.assertIn("sourcemap_generator.py", names)

    def test_this_checkout_resolves_real_versions(self):
        from odoo.addons.base.models.assetsbundle.common import _toolchain_versions

        reported = _toolchain_versions()
        self.assertNotIn(
            "@absent",
            reported,
            f"{reported} -- a development checkout must have these installed; "
            f"run `npm install` in the repo root",
        )

    def test_a_compiler_upgrade_moves_the_digest(self):
        base = self._fingerprint_with(
            "sass-embedded@1.100.0;rtlcss@4.3.0;esbuild@0.25.0"
        )
        bumped = self._fingerprint_with(
            "sass-embedded@1.101.0;rtlcss@4.3.0;esbuild@0.25.0"
        )
        self.assertNotEqual(base, bumped, "a Dart Sass bump must invalidate bundles")

    def test_rtlcss_disappearing_moves_the_digest(self):
        present = self._fingerprint_with(
            "sass-embedded@1.100.0;rtlcss@4.3.0;esbuild@0.25.0"
        )
        absent = self._fingerprint_with(
            "sass-embedded@1.100.0;rtlcss@absent;esbuild@0.25.0"
        )
        self.assertNotEqual(
            present,
            absent,
            "without rtlcss an RTL bundle holds LTR rules (pinned by "
            "TestAuditRtlSilentDegradation); it must not share an identity with "
            "the same bundle built with it",
        )


class TestRunCliPipeFailures(BaseCase):
    def test_nonzero_exit_names_the_tool(self):
        with self.assertRaises(CompileError) as ctx:
            _run_cli_pipe(["false"], "", 10)
        message = str(ctx.exception)
        self.assertIn("'false'", message)
        self.assertIn("return code 1", message)

    def test_non_utf8_output_degrades_to_replacement(self):
        with self.assertRaises(CompileError) as ctx:
            _run_cli_pipe(["sh", "-c", "printf '\\377\\376 broken'; exit 3"], "", 10)
        message = str(ctx.exception)
        self.assertIn("'sh'", message)
        self.assertIn("broken", message)

    def test_non_utf8_success_output_degrades(self):
        out = _run_cli_pipe(["sh", "-c", "printf '\\377 ok'"], "", 10)
        self.assertIn("ok", out)


class TestFingerprintDegradation(BaseCase):
    def setUp(self):
        super().setUp()
        _pipeline_fingerprint.cache_clear()
        self.addCleanup(_pipeline_fingerprint.cache_clear)

    def test_a_source_that_resolves_to_nothing_warns(self):
        from odoo.addons.base.models.assetsbundle import common

        ghost = pathlib.Path("/nonexistent/asset_pipeline_source")
        with (
            patch.object(common, "_pipeline_sources", return_value=(ghost,)),
            self.assertLogs("odoo.addons.base.models.assetsbundle", "WARNING") as log,
        ):
            _pipeline_fingerprint()
        self.assertIn("does not exist", "\n".join(log.output))

    def test_an_unreadable_source_falls_back_to_the_release_version(self):
        from odoo import release

        from odoo.addons.base.models.assetsbundle import common

        target = next(
            p for s in _pipeline_sources() if s.is_dir() for p in s.glob("*.py")
        )
        with (
            patch.object(common, "_pipeline_sources", return_value=(target,)),
            patch.object(
                type(target), "read_bytes", side_effect=OSError("permission denied")
            ),
            self.assertLogs("odoo.addons.base.models.assetsbundle", "WARNING") as log,
        ):
            self.assertEqual(_pipeline_fingerprint(), release.version)
        self.assertIn("falling back to the release version", "\n".join(log.output))
