import os
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from odoo.tools import sass_embedded
from odoo.tools.sass_embedded import (
    SassEmbeddedCompiler,
    SassNotFoundError,
    SassProtocolError,
    _find_sass_path,
    _supports_embedded,
    get_sass_path,
)


class TestSupportsEmbedded(unittest.TestCase):
    def _run(self, returncode: int = 0, stdout: bytes = b"") -> MagicMock:
        proc = MagicMock()
        proc.returncode = returncode
        proc.stdout = stdout
        return proc

    def test_native_dart_sass_returns_true(self) -> None:
        with patch("subprocess.run", return_value=self._run(0, b"")):
            self.assertTrue(_supports_embedded("/usr/bin/sass"))

    def test_pure_js_sass_returns_false(self) -> None:
        with patch(
            "subprocess.run",
            return_value=self._run(
                1, b"sass --embedded is unavailable in pure JS mode"
            ),
        ):
            self.assertFalse(_supports_embedded("/usr/bin/sass"))

    def test_wrong_platform_binary_returns_false(self) -> None:
        with patch("subprocess.run", return_value=self._run(127, b"")):
            self.assertFalse(
                _supports_embedded("/opt/sass-embedded-linux-musl/dart-sass/sass")
            )

    def test_zero_exit_with_marker_returns_false(self) -> None:
        with patch(
            "subprocess.run",
            return_value=self._run(
                0, b"sass --embedded is unavailable in pure JS mode"
            ),
        ):
            self.assertFalse(_supports_embedded("/usr/bin/sass"))

    def test_nonzero_exit_without_marker_returns_false(self) -> None:
        with patch("subprocess.run", return_value=self._run(1, b"some other failure")):
            self.assertFalse(_supports_embedded("/usr/bin/sass"))

    def test_oserror_returns_false(self) -> None:
        with patch("subprocess.run", side_effect=OSError("not executable")):
            self.assertFalse(_supports_embedded("/nonexistent/sass"))

    def test_subprocess_error_returns_false(self) -> None:
        with patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="sass", timeout=10),
        ):
            self.assertFalse(_supports_embedded("/usr/bin/sass"))


class TestFindSass(unittest.TestCase):
    def test_skips_unverified_system_sass_falls_back_to_node_modules_cli(
        self,
    ) -> None:
        with (
            patch("shutil.which") as which_mock,
            patch("pathlib.Path.glob", return_value=iter([])),
            patch("odoo.tools.sass_embedded._supports_embedded", return_value=False),
        ):
            which_mock.side_effect = [
                "/usr/bin/sass",
                "/app/node_modules/.bin/sass",
            ]
            result = _find_sass_path()
        self.assertEqual(result, "/app/node_modules/.bin/sass")

    def test_returns_first_verified_embedded_candidate(self) -> None:
        with (
            patch("shutil.which", return_value="/usr/bin/sass"),
            patch("pathlib.Path.glob", return_value=iter([])),
            patch("odoo.tools.sass_embedded._supports_embedded", return_value=True),
        ):
            result = _find_sass_path()
        self.assertEqual(result, "/usr/bin/sass")

    def test_no_system_sass_and_no_bundled_binary_returns_none(self) -> None:
        with (
            patch("shutil.which", return_value=None),
            patch("pathlib.Path.glob", return_value=iter([])),
        ):
            result = _find_sass_path()
        self.assertIsNone(result)


class TestRestartDoesNotLeakPipes(unittest.TestCase):
    @staticmethod
    def _fd_count() -> int:
        return len(list(Path(f"/proc/{os.getpid()}/fd").iterdir()))

    def setUp(self):
        if not Path("/proc/self/fd").is_dir():
            self.skipTest("needs /proc to count descriptors")
        if get_sass_path() is None:
            raise SassNotFoundError("sass is a required dependency of this fork")

    @staticmethod
    def _kill_running(compiler: SassEmbeddedCompiler) -> None:
        process = compiler._process
        assert process is not None
        process.kill()
        process.wait()

    def test_the_descriptor_count_is_flat_across_restarts(self):
        compiler = SassEmbeddedCompiler()
        self.addCleanup(compiler.close)
        compiler._start()
        first = compiler._process
        assert first is not None
        steady = self._fd_count()

        for _ in range(3):
            self._kill_running(compiler)
            compiler._start()
            self.assertEqual(self._fd_count(), steady)

        for pipe in (first.stdin, first.stdout):
            assert pipe is not None
            self.assertTrue(pipe.closed)

    def test_a_compile_still_works_after_the_process_died(self):
        compiler = SassEmbeddedCompiler()
        self.addCleanup(compiler.close)
        self.assertIn("color: red", compiler.compile_string("a { b { color: red } }"))
        self._kill_running(compiler)
        self.assertIn("color: blue", compiler.compile_string("p { color: blue }"))


class TestUndecodablePacketIsAProtocolError(unittest.TestCase):
    def test_garbage_from_the_subprocess_is_named_as_transport(self):
        compiler = SassEmbeddedCompiler()
        self.addCleanup(compiler.close)
        with (
            patch.object(compiler, "_start"),
            patch.object(compiler, "_send_packet"),
            patch.object(compiler, "_recv_packet", return_value=(1, b"\xff\xff\xff")),
            self.assertRaises(SassProtocolError),
        ):
            compiler.compile_string("a { color: red }")


class TestRelativeImportsResolveBesideTheImporter(unittest.TestCase):
    def _tree(self, root: Path) -> tuple[Path, Path]:
        addons = root / "addons_x"
        scss = addons / "xaddon" / "static" / "src" / "scss"
        scss.mkdir(parents=True)
        (scss / "main.scss").write_text('@import "helper";\n.m { color: $c; }\n')
        (scss / "_helper.scss").write_text("$c: red;\n")
        boot = root / "boot"
        boot.mkdir()
        (boot / "_helper.scss").write_text("$c: blue;\n")
        return addons, boot

    def _compile(self, root: Path) -> str:
        from odoo.tools import files
        from odoo.tools.sass_embedded import OdooSassImporter

        if get_sass_path() is None:
            raise SassNotFoundError("sass is a required dependency of this fork")
        addons, boot = self._tree(root)
        token = files._temporary_paths.set((str(addons),))
        self.addCleanup(files._temporary_paths.reset, token)
        with SassEmbeddedCompiler() as compiler:
            return compiler.compile_string(
                '@import "xaddon/static/src/scss/main";',
                importers=[OdooSassImporter(str(boot))],
                load_paths=[str(boot), str(addons)],
            )

    def test_a_partial_beside_the_importer_wins_over_bootstrap(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIn("color: red", self._compile(Path(tmp)))

    def test_a_path_that_needs_url_encoding_still_resolves(self):
        with tempfile.TemporaryDirectory(prefix="sass probe ") as tmp:
            self.assertIn("color: red", self._compile(Path(tmp)))

    def test_canonical_urls_round_trip_through_load(self):
        from odoo.tools.sass_embedded import OdooSassImporter

        with tempfile.TemporaryDirectory(prefix="a b%") as tmp:
            partial = Path(tmp) / "_part.scss"
            partial.write_text("$x: 1;\n")
            importer = OdooSassImporter(tmp)
            url = importer.canonicalize(Path(tmp).as_uri() + "/part", False)
            self.assertEqual(url, partial.resolve().as_uri())
            self.assertEqual(importer.load(url), ("$x: 1;\n", "scss"))


class TestTheBinaryIsProbedOnce(unittest.TestCase):
    def setUp(self):
        patcher = patch.object(sass_embedded, "_sass_path", None)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_a_found_binary_is_remembered(self):
        with patch.object(
            sass_embedded, "_find_sass_path", return_value="/usr/bin/sass"
        ) as find:
            self.assertEqual(get_sass_path(), "/usr/bin/sass")
            self.assertEqual(get_sass_path(), "/usr/bin/sass")
        find.assert_called_once()

    def test_a_missing_binary_is_looked_for_again(self):
        with patch.object(
            sass_embedded, "_find_sass_path", side_effect=[None, "/usr/bin/sass"]
        ):
            self.assertIsNone(get_sass_path())
            self.assertEqual(get_sass_path(), "/usr/bin/sass")


class TestTheSingletonLifecycle(unittest.TestCase):
    def setUp(self):
        sass_embedded.close_sass_compiler()
        self.addCleanup(sass_embedded.close_sass_compiler)

    def test_exit_hooks_are_registered_once_across_recreations(self):
        with (
            patch.object(sass_embedded, "_exit_hooks_registered", False),
            patch.object(sass_embedded.atexit, "register") as register,
        ):
            for _ in range(3):
                sass_embedded.get_sass_compiler()
                sass_embedded.close_sass_compiler()
        register.assert_called_once()

    def test_closing_waits_for_a_compile_in_flight(self):
        class Slow(sass_embedded.SassImporter):
            def canonicalize(self, url, from_import):
                return "file:///slow.scss" if url == "slow" else None

            def load(self, canonical_url):
                time.sleep(0.5)
                return ("$c: red;", "scss")

        if get_sass_path() is None:
            raise SassNotFoundError("sass is a required dependency of this fork")
        sass_embedded.get_sass_compiler().compile_string(".warm { a: b }")
        result = {}

        def compile_slowly():
            try:
                result["css"] = sass_embedded.get_sass_compiler().compile_string(
                    '@import "slow"; .a { color: $c }', importers=[Slow()]
                )
            except Exception as exc:
                result["error"] = exc

        thread = threading.Thread(target=compile_slowly)
        thread.start()
        time.sleep(0.2)
        sass_embedded.close_sass_compiler()
        thread.join()
        self.assertNotIn("error", result)
        self.assertIn("color: red", result["css"])

    def test_a_forked_child_drops_the_parents_process_untouched(self):
        compiler = SassEmbeddedCompiler()
        proc = MagicMock()
        compiler._process = proc
        compiler._started = True
        compiler._lock.acquire()
        self.addCleanup(compiler._lock.release)
        with patch.object(sass_embedded, "_sass_compiler", compiler):
            sass_embedded._reset_after_fork()
            self.assertIsNone(sass_embedded._sass_compiler)
        proc.kill.assert_not_called()
        proc.wait.assert_not_called()
        proc.stdin.close.assert_called_once()
        self.assertIsNone(compiler._process)
        self.assertFalse(compiler._lock.locked())


if __name__ == "__main__":
    unittest.main()
