import os
import pathlib
import tempfile
import unittest
from unittest import mock

from odoo.tools import config
from odoo.tools import subprocess as tools_subprocess
from odoo.tools.config import configmanager
from odoo.tools.subprocess import (
    get_executable_path,
    get_pg_tool_path,
    stripped_sys_argv,
)


def strip(argv, *extra):
    with mock.patch.object(tools_subprocess.sys, "argv", argv):
        return stripped_sys_argv(*extra)


def parsed(args):
    # a private manager: parsing into the global one would leave `-d db` behind
    # for every later test, and `--save` would write the user's rc file
    manager = configmanager()
    with mock.patch.object(configmanager, "save"):
        return vars(manager._parse_config(args))


class TestStrippedSysArgv(unittest.TestCase):
    def test_program_name_is_kept(self):
        self.assertEqual(strip(["odoo-bin"]), ["odoo-bin"])

    def test_unrelated_options_are_kept(self):
        argv = ["odoo-bin", "-c", "odoo.conf", "-d", "mydb", "--http-port=8069"]
        self.assertEqual(strip(argv), argv)

    def test_separate_value_form_drops_both_entries(self):
        self.assertEqual(
            strip(["odoo-bin", "-d", "db", "-u", "base"]), ["odoo-bin", "-d", "db"]
        )

    def test_attached_short_form(self):
        self.assertEqual(
            strip(["odoo-bin", "-ubase", "-d", "db"]), ["odoo-bin", "-d", "db"]
        )

    def test_long_form_with_separate_value(self):
        self.assertEqual(
            strip(["odoo-bin", "--update", "base", "-d", "db"]),
            ["odoo-bin", "-d", "db"],
        )

    def test_long_form_with_equals(self):
        self.assertEqual(
            strip(["odoo-bin", "--update=base", "-d", "db"]), ["odoo-bin", "-d", "db"]
        )

    def test_init_is_stripped(self):
        self.assertEqual(
            strip(["odoo-bin", "-i", "sale", "-d", "db"]), ["odoo-bin", "-d", "db"]
        )

    def test_save_is_stripped(self):
        self.assertEqual(
            strip(["odoo-bin", "-s", "-d", "db"]), ["odoo-bin", "-d", "db"]
        )

    def test_i18n_overwrite_is_stripped(self):
        self.assertEqual(
            strip(["odoo-bin", "--i18n-overwrite", "-d", "db"]),
            ["odoo-bin", "-d", "db"],
        )

    def test_extra_option_can_be_stripped(self):
        self.assertEqual(
            strip(["odoo-bin", "-d", "db", "--test-enable"], "--test-enable"),
            ["odoo-bin", "-d", "db"],
        )

    def test_unknown_option_to_strip_is_rejected(self):
        with self.assertRaises(ValueError):
            strip(["odoo-bin"], "--no-such-option")

    def test_several_stripped_options_at_once(self):
        self.assertEqual(
            strip(["odoo-bin", "-d", "db", "-i", "sale", "-u", "base", "-s"]),
            ["odoo-bin", "-d", "db"],
        )

    def test_a_database_named_like_a_module_is_not_confused(self):
        self.assertEqual(strip(["odoo-bin", "-d", "base"]), ["odoo-bin", "-d", "base"])

    def test_an_abbreviated_long_option_is_stripped(self):
        self.assertEqual(
            strip(["odoo-bin", "--upd", "web", "--ini=sale", "-d", "db"]),
            ["odoo-bin", "-d", "db"],
        )

    def test_an_abbreviated_flag_is_stripped_and_the_next_option_kept(self):
        self.assertEqual(
            strip(["odoo-bin", "-u", "web", "--i18n-over", "-d", "db"]),
            ["odoo-bin", "-d", "db"],
        )

    def test_a_value_starting_with_a_dash_belongs_to_its_option(self):
        argv = ["odoo-bin", "--test-tags", "-standard,/web", "-d", "db"]
        self.assertEqual(strip(argv), argv)
        argv = ["odoo-bin", "-d", "-staging", "--http-port", "8070"]
        self.assertEqual(strip(argv), argv)

    def test_a_short_cluster_keeps_its_other_options(self):
        self.assertEqual(strip(["odoo-bin", "-sd", "db"]), ["odoo-bin", "-d", "db"])
        self.assertEqual(strip(["odoo-bin", "-sddb"]), ["odoo-bin", "-ddb"])
        self.assertEqual(
            strip(["odoo-bin", "-su", "web", "-d", "db"]), ["odoo-bin", "-d", "db"]
        )

    def test_an_optional_value_option_does_not_swallow_the_next_option(self):
        argv = ["odoo-bin", "--without-demo", "-d", "db"]
        self.assertEqual(strip(argv), argv)
        argv = ["odoo-bin", "--without-demo", "False", "-d", "db"]
        self.assertEqual(strip(argv), argv)

    def test_reinit_does_not_survive_a_reload(self):
        self.assertEqual(
            strip(["odoo-bin", "-d", "db", "--reinit", "web", "--dev", "reload"]),
            ["odoo-bin", "-d", "db", "--dev", "reload"],
        )

    def test_a_retired_option_is_read_the_way_the_parser_reads_it(self):
        # the parser drops `--limit-memory-hard 5` before it reads the rest, so
        # the stripped argv must parse to what the original parsed to
        argv = [
            "odoo-bin",
            "--without-d",
            "--limit-memory-hard",
            "5",
            "--save",
            "-d",
            "db",
        ]
        self.assertEqual(parsed(strip(argv)[1:]), parsed(argv[1:]))

    def test_everything_after_a_double_dash_is_positional(self):
        self.assertEqual(
            strip(["odoo-bin", "-d", "db", "--", "-u", "x"]),
            ["odoo-bin", "-d", "db", "--", "-u", "x"],
        )

    def test_the_stripped_argv_parses_back(self):
        for argv in (
            ["odoo-bin", "--test-tags", "-standard,/web", "-d", "db"],
            ["odoo-bin", "-u", "web", "--i18n-over", "-d", "db"],
            ["odoo-bin", "-sd", "db"],
        ):
            with self.subTest(argv=argv):
                options, rest = config.parser.parse_args(strip(argv)[1:])
                self.assertEqual(rest, [])
                self.assertEqual(options.db_name, ["db"])
                self.assertIsNone(options.update)
                self.assertIsNone(options.save)


class TestToolLookup(unittest.TestCase):
    def test_find_in_path_finds_a_real_executable(self):
        self.assertTrue(get_executable_path("sh").endswith("sh"))

    def test_find_in_path_raises_for_a_missing_executable(self):
        with self.assertRaises(OSError):
            get_executable_path("odoo-no-such-binary-xyz")

    def test_a_directory_named_like_the_command_is_not_the_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            (pathlib.Path(tmp) / "odoo-dir-not-a-binary").mkdir()
            with (
                mock.patch.dict(os.environ, {"PATH": tmp}),
                self.assertRaises(FileNotFoundError),
            ):
                get_executable_path("odoo-dir-not-a-binary")

    def test_find_pg_tool_raises_filenotfound(self):
        with self.assertRaises(FileNotFoundError):
            get_pg_tool_path("pg_no_such_tool_xyz")


if __name__ == "__main__":
    unittest.main()
