import tempfile
import unittest
from pathlib import Path

from odoo.tools.config import configmanager


class _ConfigFileCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.config = configmanager()

    def write(self, name, text):
        path = self.tmp / name
        path.write_text(text)
        return path

    def load(self, path):
        self.config._load_file_options(str(path))
        return dict(self.config._file_options)


class TestUnreadableInputIsTolerated(_ConfigFileCase):
    def test_absent_file(self):
        self.assertEqual(self.load(self.tmp / "nope.conf"), {})

    def test_file_without_an_options_section(self):
        self.assertEqual(self.load(self.write("ns.conf", "[other]\nx = 1\n")), {})

    def test_unreadable_file(self):
        path = self.write("locked.conf", "[options]\nhttp_port = 1\n")
        path.chmod(0o000)
        try:
            self.assertEqual(self.load(path), {})
        finally:
            path.chmod(0o600)


class TestAnExplicitlyChosenFileIsLoud(_ConfigFileCase):
    def setUp(self):
        super().setUp()
        for source in self._explicit_sources():
            source.pop("config", None)
        self.path = self.write("locked.conf", "[options]\nhttp_port = 1\n")
        self.path.chmod(0o000)
        self.addCleanup(self.path.chmod, 0o600)

    def _explicit_sources(self):
        return (
            self.config._override_options,
            self.config._runtime_options,
            self.config._cli_options,
            self.config._env_options,
        )

    def check(self, source):
        source["config"] = str(self.path)
        with self.assertRaises(SystemExit):
            self.config._check_config_file_is_readable()

    def test_from_the_environment(self):
        self.check(self.config._env_options)

    def test_from_the_command_line(self):
        self.check(self.config._cli_options)

    def test_from_an_override(self):
        self.check(self.config._override_options)

    def test_the_default_path_stays_tolerated(self):
        self.config._default_options["config"] = str(self.path)
        self.config._check_config_file_is_readable()

    def test_a_readable_explicit_file_is_fine(self):
        readable = self.write("fine.conf", "[options]\nhttp_port = 1\n")
        self.config._env_options["config"] = str(readable)
        self.config._check_config_file_is_readable()

    def test_an_absent_explicit_file_is_also_loud(self):
        self.config._env_options["config"] = str(self.tmp / "nope.conf")
        with self.assertRaises(SystemExit):
            self.config._check_config_file_is_readable()

    def test_an_absent_explicit_file_is_tolerated_when_saving(self):
        self.config._env_options["config"] = str(self.tmp / "nope.conf")
        self.config._cli_options["save"] = True
        self.config._check_config_file_is_readable()


class TestParseFailuresAreLoud(_ConfigFileCase):
    def test_an_undecodable_file_raises_instead_of_a_bare_traceback(self):
        path = self.tmp / "binary.conf"
        path.write_bytes(b"[o\xa3ptions]\nhttp_port = 1\n")
        with self.assertRaises(SystemExit):
            self.load(path)

    def test_an_ordinary_file_still_loads(self):
        loaded = self.load(
            self.write("good.conf", "[options]\nhttp_port = 9999\ndb_name = probe\n")
        )
        self.assertEqual(loaded["http_port"], 9999)

    def test_a_bad_value_raises_and_names_the_option(self):
        path = self.write("bad.conf", "[options]\nhttp_port = not-a-number\n")
        with self.assertRaises(ValueError) as caught:
            self.load(path)
        self.assertIn("http_port", str(caught.exception))

    def test_an_unreadable_addons_dir_raises_instead_of_emptying_the_file(self):
        locked = self.tmp / "locked"
        locked.mkdir()
        (locked / "child").mkdir()
        locked.chmod(0o000)
        path = self.write(
            "perm.conf",
            f"[options]\naddons_path = {locked}\nhttp_port = 9999\ndb_name = probe\n",
        )
        try:
            with self.assertRaises(ValueError) as caught:
                self.load(path)
        finally:
            locked.chmod(0o700)
        message = str(caught.exception)
        self.assertIn("addons_path", message)
        self.assertIn(str(path), message, "the message must name the file")
        cause = caught.exception.__cause__
        assert cause is not None
        self.assertIsInstance(cause.__cause__, PermissionError)


if __name__ == "__main__":
    unittest.main()
