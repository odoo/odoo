import os
import subprocess
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from odoo.tools.sass_embedded import (
    SassEmbeddedCompiler,
    SassNotFoundError,
    SassProtocolError,
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
            result = get_sass_path()
        self.assertEqual(result, "/app/node_modules/.bin/sass")

    def test_returns_first_verified_embedded_candidate(self) -> None:
        with (
            patch("shutil.which", return_value="/usr/bin/sass"),
            patch("pathlib.Path.glob", return_value=iter([])),
            patch("odoo.tools.sass_embedded._supports_embedded", return_value=True),
        ):
            result = get_sass_path()
        self.assertEqual(result, "/usr/bin/sass")

    def test_no_system_sass_and_no_bundled_binary_returns_none(self) -> None:
        with (
            patch("shutil.which", return_value=None),
            patch("pathlib.Path.glob", return_value=iter([])),
        ):
            result = get_sass_path()
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()


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
