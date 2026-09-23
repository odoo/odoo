import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from odoo.tools.config import (
    ALL_DEV_MODE,
    DEFAULT_SERVER_WIDE_MODULES,
    configmanager,
)


class _Case(unittest.TestCase):
    def setUp(self):
        patcher = patch.dict("os.environ", {}, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.tmp = Path(tempfile.mkdtemp())

    def conf(self, text):
        path = self.tmp / "odoo.conf"
        path.write_text("[options]\n" + text)
        return str(path)

    def parse(self, argv=(), env=None, deprecations=False):
        config = configmanager()
        os.environ.update(env or {})
        with contextlib.redirect_stderr(io.StringIO()):
            config._parse_config(list(argv))
            if deprecations:
                config._warn_deprecated_options()
        return config


class TestDeprecatedAliasIsComparedAsTyped(_Case):
    def test_an_alias_equal_to_its_new_option_is_not_a_conflict(self):
        path = self.conf("import_image_maxbytes = 5\nimport_file_maxbytes = 5\n")
        config = self.parse(["-c", path], deprecations=True)
        self.assertEqual(config["import_file_maxbytes"], 5)

    def test_an_alias_equal_to_the_default_is_left_alone(self):
        path = self.conf("import_image_maxbytes = 10485760\nimport_file_maxbytes = 7\n")
        config = self.parse(["-c", path], deprecations=True)
        self.assertEqual(config["import_file_maxbytes"], 7)

    def test_an_alias_alone_still_sets_the_new_option(self):
        config = self.parse(
            ["-c", self.conf("import_image_maxbytes = 9\n")], deprecations=True
        )
        self.assertEqual(config["import_file_maxbytes"], 9)

    def test_two_different_values_still_conflict(self):
        path = self.conf("import_image_maxbytes = 5\nimport_file_maxbytes = 6\n")
        with self.assertRaises(SystemExit):
            self.parse(["-c", path], deprecations=True)


class TestAnEmptyValueIsUnset(_Case):
    def test_an_empty_environment_variable_is_ignored(self):
        config = self.parse(env={"PGPORT": "", "PGSSLMODE": "", "ODOO_DATA_DIR": ""})
        self.assertIsNone(config["db_port"])
        self.assertEqual(config["db_sslmode"], "prefer")
        self.assertEqual(config["data_dir"], config._default_options["data_dir"])
        self.assertTrue(Path(config.filestore("db")).is_absolute())

    def test_a_set_environment_variable_still_applies(self):
        config = self.parse(env={"PGPORT": "5433"})
        self.assertEqual(config["db_port"], 5433)

    def test_an_empty_data_dir_in_the_file_keeps_the_default(self):
        config = self.parse(["-c", self.conf("data_dir =\n")])
        self.assertTrue(config["data_dir"])
        self.assertEqual(config["data_dir"], config._default_options["data_dir"])

    def test_an_empty_geoip_or_screenshots_path_still_switches_it_off(self):
        from_file = self.parse(["-c", self.conf("geoip_city_db =\nscreenshots =\n")])
        from_env = self.parse(env={"ODOO_GEOIP_CITY_DB": ""})
        self.assertEqual(from_file["geoip_city_db"], "")
        self.assertEqual(from_file["screenshots"], "")
        self.assertEqual(from_env["geoip_city_db"], "")

    def test_an_empty_path_without_a_default_still_reads_empty(self):
        config = self.parse(["-c", self.conf("pidfile =\n")])
        self.assertEqual(config["pidfile"], "")


class TestTheReplicaPasswordIsNeverACommandLineOption(_Case):
    def test_the_command_line_refuses_it(self):
        with self.assertRaises(SystemExit):
            self.parse(["--db_replica_password=s3cret"])

    def test_it_is_not_advertised(self):
        self.assertNotIn("db_replica_password", configmanager().parser.format_help())

    def test_the_file_and_the_environment_still_set_it(self):
        path = self.conf("db_replica_password = from-file\n")
        self.assertEqual(self.parse(["-c", path])["db_replica_password"], "from-file")
        config = self.parse(env={"PGPASSWORD_REPLICA": "from-env"})
        self.assertEqual(config["db_replica_password"], "from-env")


class TestEveryLayerWriteMovesTheGeneration(_Case):
    def test_an_in_place_union_moves_it(self):
        config = configmanager()
        before = config.generation
        config._override_options |= {"http_port": 1234}
        self.assertGreater(config.generation, before)
        self.assertEqual(config["http_port"], 1234)

    def test_the_module_maps_cannot_be_edited_in_place(self):
        config = self.parse(["-i", "sale", "-u", "web", "-d", "db"])
        with self.assertRaises(NotImplementedError):
            config["init"]["base"] = True
        with self.assertRaises(NotImplementedError):
            config["update"]["base"] = True
        before = config.generation
        config["init"] = {**config["init"], "base": True}
        self.assertGreater(config.generation, before)
        self.assertEqual(dict(config["init"]), {"sale": True, "base": True})
        with self.assertRaises(NotImplementedError):
            config["init"]["other"] = True


class TestModuleConstantsAreNotLiveDefaults(_Case):
    def test_a_default_list_is_not_the_module_constant(self):
        config = self.parse()
        self.assertIsNot(config["server_wide_modules"], DEFAULT_SERVER_WIDE_MODULES)
        config["server_wide_modules"].append("x")
        self.assertNotIn("x", DEFAULT_SERVER_WIDE_MODULES)
        self.assertNotIn("x", configmanager()["server_wide_modules"])

    def test_dev_mode_all_expands(self):
        config = self.parse(["--dev", "all"])
        for mode in ALL_DEV_MODE:
            self.assertIn(mode, config["dev_mode"])


class TestRetiredOptions(_Case):
    RETIRED = ("csv_internal_sep", "reportgz", "limit_memory_hard")

    def test_they_are_not_options_any_more(self):
        config = configmanager()
        for name in (*self.RETIRED, "limit_memory_hard_gevent"):
            self.assertNotIn(name, config.options_index)

    def test_a_file_carrying_them_still_loads(self):
        path = self.conf(
            "csv_internal_sep = @\nreportgz = True\nlimit_memory_hard = 1\n"
            "limit_memory_hard_gevent = 2\nhttp_port = 9999\n"
        )
        config = self.parse(["-c", path])
        self.assertEqual(config["http_port"], 9999)
        for name in self.RETIRED:
            self.assertNotIn(name, config._file_options)

    def test_the_command_line_still_accepts_them(self):
        config = self.parse(
            ["--limit-memory-hard", "1", "--limit-memory-hard-gevent=2", "-p", "9"]
        )
        self.assertEqual(config["http_port"], 9)


class TestSaveFailuresAreReported(_Case):
    def test_save_raises_instead_of_printing(self):
        config = configmanager()
        config["config"] = str(self.tmp / "missing-dir" / "odoo.conf")
        (self.tmp / "missing-dir").write_text("a file where a directory must be")
        with self.assertRaises(OSError):
            config.save()

    def test_dash_s_exits_non_zero_when_the_file_cannot_be_written(self):
        blocker = self.tmp / "blocker"
        blocker.write_text("")
        with self.assertRaises(SystemExit) as caught:
            self.parse(["-s", "-c", str(blocker / "odoo.conf")])
        self.assertNotEqual(caught.exception.code, 0)


class TestTypeTablesAreBuiltOnce(unittest.TestCase):
    def test_the_checker_and_formatter_are_the_same_object_on_every_read(self):
        option_class = configmanager().parser.option_class
        self.assertIs(option_class.TYPE_CHECKER, option_class.TYPE_CHECKER)
        self.assertIs(option_class.TYPE_FORMATTER, option_class.TYPE_FORMATTER)

    def test_each_manager_binds_its_own(self):
        first, second = configmanager(), configmanager()
        self.assertIsNot(
            first.parser.option_class.TYPE_CHECKER,
            second.parser.option_class.TYPE_CHECKER,
        )
        self.assertEqual(first.parse("http_port", "8070"), 8070)
        self.assertEqual(first.format("addons_path", ["/a", "/b"]), "/a,/b")


class TestAnUnreadableAddonsDirectoryIsAnOptionError(_Case):
    def setUp(self):
        super().setUp()
        self.locked = self.tmp / "locked"
        (self.locked / "child").mkdir(parents=True)
        self.locked.chmod(0)
        self.addCleanup(self.locked.chmod, 0o700)

    def test_on_the_command_line(self):
        with self.assertRaises(SystemExit) as caught:
            self.parse(["--addons-path", str(self.locked)])
        self.assertEqual(caught.exception.code, 2)

    def test_in_the_environment_the_manager_still_builds(self):
        os.environ["ODOO_ADDONS_PATH"] = str(self.locked)
        config = configmanager()
        with self.assertRaises(ValueError) as caught:
            config._parse_config([])
        self.assertIn("ODOO_ADDONS_PATH", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
