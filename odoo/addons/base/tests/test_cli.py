import contextlib
import copy
import os
import re
import subprocess as sp
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from odoo.cli.command import (
    commands,
    load_addons_commands,
    load_internal_commands,
    prepare_bootstrap_parser,
)
from odoo.db import SYSTEM_DBS
from odoo.tests import BaseCase
from odoo.tools import config, file_path

_CONFIG_LAYERS = (
    "_default_options",
    "_file_options",
    "_env_options",
    "_cli_options",
    "_override_options",
    "_runtime_options",
)


@contextlib.contextmanager
def isolated_config():
    saved = {name: copy.deepcopy(getattr(config, name)) for name in _CONFIG_LAYERS}
    try:
        yield
    finally:
        for name, layer in saved.items():
            getattr(config, name).clear()
            getattr(config, name).update(layer)


class TestCommand(BaseCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.odoo_bin = Path(__file__).parents[4].resolve() / "odoo-bin"
        addons_path = config.format("addons_path", config["addons_path"])
        cls.run_args = (
            sys.executable,
            cls.odoo_bin,
            f"--addons-path={addons_path}",
        )

    def run_command(self, *args, check=True, capture_output=True, text=True, **kwargs):
        return sp.run(
            [*self.run_args, *args],
            capture_output=capture_output,
            check=check,
            text=text,
            **kwargs,
        )

    def popen_command(self, *args, capture_output=True, text=True, **kwargs):
        if capture_output:
            kwargs["stdout"] = kwargs["stderr"] = sp.PIPE
        return sp.Popen([*self.run_args, *args], text=text, **kwargs)

    def test_help_text(self):
        load_internal_commands()
        load_addons_commands()
        for name, cmd in commands.items():
            help_text = cmd.description or cmd.__doc__
            self.assertTrue(
                help_text,
                msg=(
                    f"Command {name} has no help text: set `description` on the "
                    f"class. A docstring will not do -- the prose strip removes "
                    f"it and `odoo-bin help` goes blank."
                ),
            )
            first_line = help_text.strip().partition("\n")[0].strip()
            self.assertTrue(
                first_line,
                msg=(
                    f"Command {name}'s help text starts with a blank line; "
                    f"`odoo-bin help` lists the first line and would show "
                    f"nothing"
                ),
            )
            self.assertLessEqual(
                len(first_line),
                120,
                msg=(
                    f"Command {name}'s first help line is {len(first_line)} "
                    f"characters; `odoo-bin help` puts it on one line"
                ),
            )

    def test_unknown_command(self):
        for name in ("bonbon", "café"):
            with self.subTest(name):
                command_output = self.run_command(name, check=False).stderr.strip()
                self.assertEqual(
                    command_output,
                    f"Unknown command '{name}'.\nUse 'odoo-bin --help' to see the list of available commands.",
                )

    def test_help(self):
        expected = {
            "cloc",
            "db",
            "deploy",
            "help",
            "i18n",
            "module",
            "neutralize",
            "obfuscate",
            "populate",
            "scaffold",
            "server",
            "shell",
            "start",
        }
        for option in ("help", "-h", "--help"):
            with self.subTest(option=option):
                actual = set()
                for line in self.run_command(option).stdout.splitlines():
                    if line.startswith("   ") and (
                        result := re.search(r"    (\w+)\s+(\w.*)$", line)
                    ):
                        actual.add(result.groups()[0])
                self.assertGreaterEqual(
                    actual,
                    expected,
                    msg="Help is not showing required commands",
                )

    def test_help_covers_all_cli_modules(self):
        from pathlib import Path

        cli_dir = Path(__file__).parents[3] / "cli"
        declared = set()
        for py in cli_dir.glob("*.py"):
            if py.stem.startswith("_"):
                continue
            if re.search(r"class\s+\w+\(Command\)", py.read_text()):
                declared.add(py.stem)

        actual = set()
        for line in self.run_command("--help").stdout.splitlines():
            if line.startswith("   ") and (
                result := re.search(r"    (\w+)\s+(\w.*)$", line)
            ):
                actual.add(result.groups()[0])
        missing = declared - actual
        self.assertFalse(
            missing,
            msg=f"cli/ modules missing from `odoo-bin help`: {sorted(missing)}",
        )

    def test_help_subcommand(self):
        load_internal_commands()
        for name in commands:
            with self.subTest(command=name):
                self.run_command(name, "--help", timeout=10)

    def test_i18n_loadlang_requires_language(self):
        proc = self.run_command(
            "i18n",
            "loadlang",
            "-d",
            "no_such_db",
            check=False,
        )
        self.assertNotEqual(proc.returncode, 0)
        msg = proc.stderr.lower()
        self.assertTrue(
            "required" in msg or "-l" in msg or "--languages" in msg,
            msg=f"stderr did not mention the missing -l flag: {proc.stderr!r}",
        )

    def test_scaffold_help_tolerant_of_missing_templates(self):
        import contextlib
        import io

        from odoo.cli import scaffold as scaffold_mod

        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "no_such_templates"
            cwd = Path.cwd()
            os.chdir(tmp)
            buf = io.StringIO()
            try:
                with mock.patch.object(
                    scaffold_mod,
                    "_get_template_path",
                    missing.joinpath,
                ):
                    with self.assertRaises(SystemExit) as ctx:
                        with contextlib.redirect_stdout(buf):
                            scaffold_mod.Scaffold().run(["--help"])
            finally:
                os.chdir(cwd)
        self.assertIn(ctx.exception.code, (0, None), msg="--help must exit 0")
        self.assertIn("usage:", buf.getvalue())

    def test_scaffold_invalid_template_is_usage_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = self.run_command(
                "scaffold", "-t", "bogus_template", "mymod", tmp, check=False
            )
        self.assertEqual(proc.returncode, 2, msg=proc.stderr)
        self.assertIn("usage:", proc.stderr)
        self.assertIn("not a valid module template", proc.stderr)

    def test_scaffold_renders_default_template(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = self.run_command("scaffold", "MyModule", tmp)
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)

            mod = Path(tmp) / "my_module"
            self.assertTrue(
                mod.is_dir(), msg=f"scaffold produced {list(Path(tmp).iterdir())}"
            )

            rendered = sorted(
                p.relative_to(mod).as_posix() for p in mod.rglob("*") if p.is_file()
            )
            self.assertNotIn(
                ".template", " ".join(rendered), msg=f"unstripped suffix in {rendered}"
            )
            self.assertIn("__manifest__.py", rendered)

            manifest = (mod / "__manifest__.py").read_text()
            self.assertIn("'name': \"MyModule\"", manifest)

            acl = (mod / "security" / "ir.model.access.csv").read_text()
            self.assertIn(
                "access_my_module_my_module,my_module.my_module,"
                "model_my_module_my_module,base.group_user,1,1,1,1",
                acl,
            )

            demo = (mod / "demo" / "demo.xml").read_text()
            self.assertIn('<record id="object4" model="my_module.my_module">', demo)
            self.assertIn('<field name="value">40</field>', demo)

            for rel in rendered:
                with self.subTest(file=rel):
                    body = (mod / rel).read_text()
                    self.assertNotIn("{{", body)
                    self.assertNotIn("{%", body)

    def test_scaffold_renders_templated_filenames(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = self.run_command("scaffold", "-t", "l10n_payroll", "mexico-mx", tmp)
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)
            mod = Path(tmp) / "l10n_mx_hr_payroll"
            self.assertTrue(
                mod.is_dir(), msg=f"scaffold produced {list(Path(tmp).iterdir())}"
            )
            self.assertTrue(
                (mod / "data" / "l10n_mx_hr_payroll_demo.xml").is_file(),
                msg=f"filename not rendered: "
                f"{sorted(p.name for p in (mod / 'data').iterdir())}",
            )

    def test_db_load_validates_before_drop(self):
        from odoo.cli import db as dbmod

        calls = []
        with tempfile.NamedTemporaryFile(suffix=".sql") as tmp:
            tmp.write(b"not a zip")
            tmp.flush()
            ns = mock.Mock(
                database="mydb", dump_file=tmp.name, force=True, neutralize=False
            )
            with (
                mock.patch.object(dbmod, "exp_db_exist", lambda db: True),
                mock.patch.object(
                    dbmod, "drop_database", lambda db: calls.append("drop") or True
                ),
                mock.patch.object(
                    dbmod, "restore_db", lambda **kw: calls.append("restore")
                ),
            ):
                with self.assertRaises(SystemExit):
                    dbmod.Db().load(ns)
        self.assertEqual(calls, [], msg=f"target dropped before validation: {calls}")

    def test_db_load_force_drops_after_validation(self):
        import zipfile as zipfile_mod

        from odoo.cli import db as dbmod

        calls = []
        with tempfile.NamedTemporaryFile(suffix=".zip") as tmp:
            with zipfile_mod.ZipFile(tmp, "w") as z:
                z.writestr("dump.sql", "fake")
            tmp.flush()
            ns = mock.Mock(
                database="mydb", dump_file=tmp.name, force=True, neutralize=False
            )
            with (
                mock.patch.object(dbmod, "exp_db_exist", lambda db: True),
                mock.patch.object(
                    dbmod, "drop_database", lambda db: calls.append("drop") or True
                ),
                mock.patch.object(
                    dbmod, "restore_db", lambda **kw: calls.append("restore")
                ),
            ):
                dbmod.Db().load(ns)
        self.assertEqual(calls, ["drop", "restore"])

    def test_db_duplicate_checks_source_before_drop(self):
        from odoo.cli import db as dbmod

        calls = []
        ns = mock.Mock(source="missing_src", target="tgt", force=True, neutralize=False)
        with (
            mock.patch.object(dbmod, "exp_db_exist", lambda db: db != "missing_src"),
            mock.patch.object(
                dbmod, "drop_database", lambda db: calls.append("drop") or True
            ),
            mock.patch.object(
                dbmod,
                "duplicate_database",
                lambda *a, **k: calls.append("duplicate"),
            ),
        ):
            with self.assertRaises(SystemExit) as ctx:
                dbmod.Db().duplicate(ns)
        self.assertEqual(calls, [])
        self.assertIn("missing_src", str(ctx.exception.code))

    def test_db_drop_calls_drop_database_not_exp_drop(self):
        from odoo.cli import db as dbmod

        with mock.patch.object(dbmod, "drop_database", return_value=True) as drop_mock:
            dbmod.Db().drop(mock.Mock(database="mydb"))
        drop_mock.assert_called_once_with("mydb")

    def test_db_drop_reports_missing_database(self):
        from odoo.cli import db as dbmod

        with mock.patch.object(dbmod, "drop_database", return_value=False):
            with self.assertRaises(SystemExit) as ctx:
                dbmod.Db().drop(mock.Mock(database="missing"))
        self.assertIn("missing", str(ctx.exception.code))

    def test_db_connection_flag_map_covers_all_flags(self):
        from odoo.cli import db as dbmod

        dest_flags = dbmod.Db._get_connection_flags_by_dest()
        for flags in dbmod.Db._CONNECTION_FLAGS:
            long_flag = flags[-1]
            dest = long_flag.lstrip("-").replace("-", "_")
            self.assertIn(dest, dest_flags)
            self.assertEqual(dest_flags[dest], long_flag)

    def test_obfuscate_select_fields(self):
        import argparse

        from odoo.cli.obfuscate import DEFAULT_FIELDS, _get_fields_selected

        base = {
            "fields": None,
            "file": None,
            "exclude": None,
            "allfields": False,
            "no_default_fields": False,
        }

        def ns(**kw):
            return argparse.Namespace(**{**base, **kw})

        self.assertEqual(_get_fields_selected(ns()), list(DEFAULT_FIELDS))
        self.assertEqual(
            _get_fields_selected(ns(fields="t.c")),
            list(DEFAULT_FIELDS) + [("t", "c")],
            msg="--fields appends to the built-in list",
        )
        self.assertEqual(
            _get_fields_selected(ns(fields="t.c", no_default_fields=True)),
            [("t", "c")],
            msg="--no-default-fields restricts to the manual selection",
        )
        excluded = _get_fields_selected(ns(exclude="res_partner.name"))
        self.assertNotIn(("res_partner", "name"), excluded)
        self.assertEqual(len(excluded), len(DEFAULT_FIELDS) - 1)
        self.assertEqual(
            _get_fields_selected(ns(fields="t.c", allfields=True)),
            list(DEFAULT_FIELDS),
            msg="--allfields ignores manual selection (expanded later)",
        )
        with self.assertRaises(ValueError):
            _get_fields_selected(ns(fields="no_dot_here"))

    def test_populate_model_factors(self):
        from odoo.cli.populate import _prepare_factors_by_model_name

        errors = []
        self.assertEqual(
            _prepare_factors_by_model_name("1,2,3,4", "a,b", errors.append),
            {"a": 1, "b": 2},
        )
        self.assertEqual(
            _prepare_factors_by_model_name("7", "a,b,c", errors.append),
            {"a": 7, "b": 7, "c": 7},
        )
        self.assertFalse(errors)
        _prepare_factors_by_model_name("x", "a", errors.append)
        self.assertTrue(errors and "--factors" in errors[0])

    def test_deploy_requests_have_timeouts(self):
        from odoo.cli.deploy import Deploy

        deploy = Deploy()
        deploy.session = mock.MagicMock()
        deploy.session.post.return_value = mock.MagicMock(status_code=200, text="ok")
        with tempfile.NamedTemporaryFile(suffix=".zip") as tmp:
            deploy.login_upload_module(
                module_file=tmp.name,
                url="http://localhost:8069",
                login="admin",
                password="admin",
                db="",
            )
        self.assertIsNotNone(deploy.session.get.call_args.kwargs.get("timeout"))
        self.assertIsNotNone(deploy.session.post.call_args.kwargs.get("timeout"))

    def test_deploy_reports_the_server_reason_on_a_refused_upload(self):
        from odoo.cli.deploy import Deploy

        deploy = Deploy()
        deploy.session = mock.MagicMock()
        deploy.session.post.return_value = mock.MagicMock(
            ok=False, status_code=403, reason="FORBIDDEN", text="Access Denied\n"
        )
        with (
            tempfile.NamedTemporaryFile(suffix=".zip") as tmp,
            self.assertRaises(Exception) as caught,
        ):
            deploy.login_upload_module(
                module_file=tmp.name,
                url="http://localhost:8069",
                login="admin",
                password="wrong",
                db="",
            )
        self.assertIn("403 FORBIDDEN", str(caught.exception))
        self.assertIn("Access Denied", str(caught.exception))

    def test_module_install_skips_modules_already_installed(self):
        from types import SimpleNamespace

        from odoo.cli.module import Module

        class Records(list):
            def filtered(self, predicate):
                return Records(record for record in self if predicate(record))

            def mapped(self, field):
                return [getattr(record, field) for record in self]

            def __sub__(self, other):
                return Records(record for record in self if record not in other)

        records = Records(
            SimpleNamespace(name=name, state=state)
            for name, state in (
                ("base", "installed"),
                ("web", "installed"),
                ("foo", "uninstalled"),
                ("bar", "to install"),
            )
        )
        already, to_install = Module._split_installed(records)
        self.assertEqual(already.mapped("name"), ["base", "web"])
        self.assertEqual(to_install.mapped("name"), ["foo", "bar"])

    def test_deploy_zip_compressed_and_pruned(self):
        import zipfile as zipfile_mod

        from odoo.cli.deploy import Deploy

        with tempfile.TemporaryDirectory() as tmp:
            mod = Path(tmp) / "mymod"
            (mod / "node_modules" / "pkg").mkdir(parents=True)
            (mod / "node_modules" / "pkg" / "index.js").write_text("x" * 4096)
            (mod / "__manifest__.py").write_text("{'name': 'mymod'}\n" * 64)
            zpath = Deploy().zip_module(mod)
            try:
                with zipfile_mod.ZipFile(zpath) as z:
                    infos = {i.filename: i for i in z.infolist()}
            finally:
                Path(zpath).unlink()
        self.assertFalse(
            [n for n in infos if "node_modules" in n],
            msg=f"excluded tree leaked into zip: {list(infos)}",
        )
        manifest = next(i for n, i in infos.items() if n.endswith("__manifest__.py"))
        self.assertEqual(manifest.compress_type, zipfile_mod.ZIP_DEFLATED)

    def test_deploy_zip_keeps_file_named_like_excluded_dir(self):
        import zipfile as zipfile_mod

        from odoo.cli.deploy import Deploy

        with tempfile.TemporaryDirectory() as tmp:
            mod = Path(tmp) / "mymod"
            mod.mkdir()
            (mod / "__manifest__.py").write_text("{'name': 'mymod'}\n")
            (mod / "build").write_text("legit content")
            (mod / "node_modules").mkdir()
            (mod / "node_modules" / "junk.js").write_text("junk")
            zpath = Deploy().zip_module(mod)
            try:
                with zipfile_mod.ZipFile(zpath) as z:
                    names = {n.split("/", 1)[1] for n in z.namelist()}
            finally:
                Path(zpath).unlink()
        self.assertIn("build", names, msg="file named like an excluded dir was dropped")
        self.assertNotIn(
            "node_modules/junk.js", names, msg="excluded dir tree leaked into zip"
        )

    def test_start_explicit_path_wins_over_venv(self):
        from odoo.cli import start as start_mod

        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp) / "proj"
            (proj / "mymodule").mkdir(parents=True)
            (proj / "mymodule" / "__manifest__.py").write_text("{'name': 'x'}\n")
            captured = {}
            cwd = Path.cwd()
            os.chdir(proj)
            try:
                with (
                    mock.patch.object(
                        start_mod,
                        "run_server",
                        lambda cmdargs: captured.update(args=list(cmdargs)),
                    ),
                    mock.patch.dict(os.environ, {"VIRTUAL_ENV": tmp}),
                    isolated_config(),
                ):
                    start_mod.Start().run(["-p", ".", "-d", "mydb"])
            finally:
                os.chdir(cwd)
            flags = [a for a in captured["args"] if a.startswith("--addons-path=")]
            self.assertEqual(len(flags), 1, msg=f"args: {captured['args']}")
            paths = flags[0].removeprefix("--addons-path=").split(",")
            self.assertIn(str(proj.resolve()), paths)
            self.assertNotIn(tmp, paths, msg="venv path overrode explicit -p .")

    def test_db_init_accepts_config_after_subcommand(self):
        proc = self.run_command(
            "db",
            "init",
            "nonexistent_db",
            "-c",
            "/nonexistent/path.conf",
            check=False,
        )
        self.assertNotIn("unrecognized arguments", proc.stderr)

    def test_db_connection_flags_before_subcommand_survive(self):
        from odoo.cli import db as dbmod

        captured = {}

        def fake_parse_config(args, **kwargs):
            captured["config_args"] = list(args)

        with (
            mock.patch.object(dbmod.config, "parse_config", fake_parse_config),
            mock.patch.object(dbmod, "report_configuration", lambda: None),
            mock.patch.object(dbmod.Db, "drop", lambda self, args: None),
        ):
            dbmod.Db().run(
                ["-c", "/tmp/before.conf", "--db_host", "prodhost", "drop", "mydb"]
            )

        config_args = captured.get("config_args", [])
        self.assertIn("/tmp/before.conf", config_args, msg=f"-c lost: {config_args}")
        self.assertIn("prodhost", config_args, msg=f"--db_host lost: {config_args}")

    def test_deploy_db_omitted_does_not_crash(self):
        from odoo.cli.deploy import Deploy

        deploy = Deploy()
        deploy.session = mock.MagicMock()
        deploy.session.post.return_value = mock.MagicMock(status_code=200, text="ok")
        with tempfile.NamedTemporaryFile(suffix=".zip") as tmp:
            try:
                deploy.login_upload_module(
                    module_file=tmp.name,
                    url="http://localhost:8069",
                    login="admin",
                    password="admin",
                    db=None,
                )
            except TypeError as exc:
                self.fail(f"login_upload_module crashed on db=None: {exc}")
        self.assertTrue(deploy.session.get.called)

    def test_bootstrap_parser_rejects_abbreviation(self):
        parser = prepare_bootstrap_parser()
        ns, rest = parser.parse_known_args(["server", "--addons=/y"])
        self.assertIsNone(ns.addons_path)
        self.assertIn("--addons=/y", rest)
        ns2, _ = parser.parse_known_args(["server", "--addons-path=/y"])
        self.assertEqual(ns2.addons_path, "/y")

    def test_discovery_survives_broken_addon_cli(self):
        from odoo.cli import command as cmd

        import odoo.addons

        with tempfile.TemporaryDirectory() as tmp:
            cli_dir = Path(tmp) / "brokenmod" / "cli"
            cli_dir.mkdir(parents=True)
            (cli_dir / "brokencmd.py").write_text(
                "from odoo.cli import Command\n"
                "class Brokencmd(Command)\n"
                "    def run(self, args): pass\n"
            )
            with (
                mock.patch.object(odoo.addons, "__path__", [tmp]),
                mock.patch.object(cmd, "initialize_sys_path", lambda: None),
            ):
                try:
                    load_addons_commands()
                except SyntaxError:
                    self.fail("a broken addon cli file broke command discovery")
            self.assertNotIn("brokencmd", commands)

    def test_deploy_local_host_detection(self):
        from odoo.cli.deploy import _LOCAL_HOSTS

        self.assertIn("localhost", _LOCAL_HOSTS)
        self.assertIn("127.0.0.1", _LOCAL_HOSTS)
        self.assertIn("0.0.0.0", _LOCAL_HOSTS)
        self.assertIn("::1", _LOCAL_HOSTS)
        self.assertNotIn("localhost.evil.com", _LOCAL_HOSTS)
        self.assertNotIn("127.0.0.1.evil.com", _LOCAL_HOSTS)

    def test_deploy_excluded_paths(self):
        from odoo.cli.deploy import (
            EXCLUDED_DIR_NAMES,
            EXCLUDED_FILE_NAMES,
            EXCLUDED_SUFFIXES,
        )

        for name in (
            ".git",
            ".hg",
            "__pycache__",
            "node_modules",
            ".idea",
            ".vscode",
            "dist",
            "build",
        ):
            self.assertIn(name, EXCLUDED_DIR_NAMES)
        for ext in (".pyc", ".pyo", ".swp", ".bak"):
            self.assertIn(ext, EXCLUDED_SUFFIXES)
        self.assertIn(".DS_Store", EXCLUDED_FILE_NAMES)

    def test_start_db_filter_escapes_regex(self):
        src = (Path(__file__).parents[3] / "cli/start.py").read_text()
        self.assertIn(
            "re.escape(db_name)",
            src,
            msg="--db-filter built without re.escape — regex meta-chars in "
            "db names would let unrelated databases through.",
        )

    def test_db_filter_database_constrains_permissive_dbfilter(self):
        from odoo.http import filter_dbs_served

        dbs = ["alpha", "beta", "prod", "test_db"]
        with config.patch(dbfilter=".*", db_name=["test_db"]):
            self.assertEqual(filter_dbs_served(dbs, host="localhost"), ["test_db"])
        with config.patch(dbfilter="^al", db_name=[]):
            self.assertEqual(filter_dbs_served(dbs, host="localhost"), ["alpha"])
        with config.patch(dbfilter="", db_name=["beta", "alpha"]):
            self.assertEqual(
                filter_dbs_served(dbs, host="localhost"), ["alpha", "beta"]
            )
        with config.patch(dbfilter="^(alpha|prod)$", db_name=["prod", "beta"]):
            self.assertEqual(filter_dbs_served(dbs, host="localhost"), ["prod"])

    def test_db_filter_strips_system_databases(self):
        from odoo.http import filter_dbs_served

        dbs = ["postgres", "template0", "template1", config["db_template"], "mydb"]
        for options in (
            {"dbfilter": "", "db_name": []},
            {"dbfilter": ".*", "db_name": []},
            {"dbfilter": "", "db_name": ["postgres", "mydb"]},
            {"dbfilter": ".*", "db_name": ["template1", "mydb"]},
        ):
            with config.patch(**options):
                self.assertEqual(
                    filter_dbs_served(dbs, host="localhost"),
                    ["mydb"],
                    msg=f"system dbs not stripped with {options}",
                )

    def test_registry_refuses_system_databases(self):
        from odoo.modules.registry import Registry

        for name in ("postgres", "template0", "template1", config["db_template"]):
            with self.assertRaises(ValueError, msg=f"Registry({name!r}) allowed"):
                Registry(name)

    def test_obfuscate_excludes_ir_tables_via_starts_with(self):
        src = (Path(__file__).parents[3] / "cli/obfuscate.py").read_text()
        non_comment = "\n".join(line.split("#", 1)[0] for line in src.splitlines())
        self.assertIn("starts_with(table_name, 'ir_')", non_comment)
        self.assertNotIn("LIKE 'ir_%'", non_comment)

    def test_obfuscate_catalog_reads_base_tables_only(self):
        from odoo.cli.obfuscate import Obfuscate

        self.assertIn("table_type = 'BASE TABLE'", Obfuscate._CATALOG_COLUMNS)
        self.assertIn("information_schema.tables", Obfuscate._CATALOG_COLUMNS)

    def test_dotted_command_name_no_traceback(self):
        for name in ("db.init", "x.y", ".", ".."):
            with self.subTest(name=name):
                proc = self.run_command(name, check=False)
                self.assertIn("Unknown command", proc.stderr)
                self.assertNotIn("Traceback", proc.stderr)

    def test_start_merges_bootstrap_addons_path(self):
        import odoo.cli
        from odoo.cli import start as start_mod

        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp) / "proj"
            (proj / "mymodule").mkdir(parents=True)
            (proj / "mymodule" / "__manifest__.py").write_text("{'name': 'x'}\n")
            captured = {}
            with (
                mock.patch.object(
                    start_mod,
                    "run_server",
                    lambda cmdargs: captured.update(args=list(cmdargs)),
                ),
                mock.patch.object(odoo.cli, "BOOTSTRAP_ADDONS_PATH", "/custom/addons"),
                isolated_config(),
            ):
                start_mod.Start().run(["--path", str(proj), "-d", "mydb"])
            flags = [a for a in captured["args"] if a.startswith("--addons-path=")]
            self.assertEqual(len(flags), 1, msg=f"args: {captured['args']}")
            paths = flags[0].removeprefix("--addons-path=").split(",")
            self.assertEqual(
                paths[0], "/custom/addons", msg="user-supplied paths must come first"
            )
            self.assertIn(str(proj.resolve()), paths)

    def test_start_filters_concatenated_path_flag(self):
        from odoo.cli import start as start_mod

        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp) / "proj"
            (proj / "mymodule").mkdir(parents=True)
            (proj / "mymodule" / "__manifest__.py").write_text("{'name': 'x'}\n")
            captured = {}
            with (
                mock.patch.object(
                    start_mod,
                    "run_server",
                    lambda cmdargs: captured.update(args=list(cmdargs)),
                ),
                isolated_config(),
            ):
                start_mod.Start().run([f"-p{proj}", "-d", "mydb"])
            leaked = [
                a
                for a in captured["args"]
                if a.startswith("-p") and not a.startswith("--")
            ]
            self.assertFalse(leaked, msg=f"args: {captured['args']}")

    def test_deploy_zip_skips_symlinks(self):
        import zipfile

        from odoo.cli.deploy import Deploy

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            (tmp_path / "secret.txt").write_text("TOPSECRET")
            mod = tmp_path / "mymod"
            mod.mkdir()
            (mod / "__manifest__.py").write_text("{'name': 'mymod'}\n")
            (mod / "leak.txt").symlink_to(tmp_path / "secret.txt")
            zpath = Deploy().zip_module(mod)
            try:
                with zipfile.ZipFile(zpath) as z:
                    names = z.namelist()
            finally:
                Path(zpath).unlink()
            self.assertTrue(any(n.endswith("__manifest__.py") for n in names))
            self.assertFalse(
                any(n.endswith("leak.txt") for n in names),
                msg=f"symlink leaked into zip: {names}",
            )

    def test_command_register_optout(self):
        from odoo.cli.command import Command, commands

        before = dict(commands)
        helper = type("HelperBase", (Command,), {}, register=False)
        self.assertEqual(commands, before, msg="opt-out base must not register")
        self.assertIsNone(helper.name)
        with self.assertRaises(ValueError):
            type("Concrete", (helper,), {"run": lambda self, args: None})
        self.assertEqual(commands, before)

    def test_db_helpers_live_on_databasecommand_not_base(self):
        from odoo.cli.command import Command, DatabaseCommand

        for meth in (
            "add_config_arguments",
            "bootstrap_config",
            "get_configured_database",
        ):
            self.assertIn(
                meth,
                vars(DatabaseCommand),
                msg=f"{meth} must be defined on DatabaseCommand",
            )
            self.assertNotIn(
                meth,
                vars(Command),
                msg=f"{meth} must not be defined on the base Command",
            )

    def test_obfuscate_update_has_where_guard(self):
        from odoo.cli.obfuscate import Obfuscate

        for unobfuscate, marker in (
            (False, "IS NOT NULL AND NOT pg_temp.odoo_cyph_marked"),
            (True, "WHERE pg_temp.odoo_cyph_marked"),
        ):
            with self.subTest(unobfuscate=unobfuscate):
                ob = Obfuscate()
                ob.cr = mock.MagicMock()
                ob.cr.rowcount = 1
                ob.cr.fetchone.return_value = ("varchar",)
                ob._update_table_values(
                    "res_partner", ["name"], "pwd", unobfuscate=unobfuscate
                )
                update_sql = ob.cr.execute.call_args[0][0].code
                self.assertIn("UPDATE", update_sql)
                self.assertIn("WHERE", update_sql)
                self.assertIn(marker, update_sql)

    def test_obfuscate_prefetches_field_kinds(self):
        from odoo.cli.obfuscate import Obfuscate

        ob = Obfuscate()
        executed = []

        class FakeCur:
            def execute(self, query, params=None):
                executed.append(params)

            def fetchall(self):
                return [
                    ("res_partner", "name", "varchar", None),
                    ("res_partner", "email", "varchar", None),
                    ("res_partner", "extra", "jsonb", None),
                    ("res_partner", "active", "bool", None),
                    ("res_partner", "ref", "varchar", 8),
                ]

        ob.cr = FakeCur()
        ob._load_field_catalog({"res_partner"})
        self.assertEqual(len(executed), 1, msg="prefetch must be a single query")
        self.assertEqual(
            executed[0], [["res_partner"]], msg="tables passed via ANY(%s)"
        )

        before = len(executed)
        self.assertEqual(ob._get_field_kind("res_partner", "name"), "string")
        self.assertEqual(ob._get_field_kind("res_partner", "extra"), "json")
        self.assertIsNone(
            ob._get_field_kind("res_partner", "active"), msg="non-text type"
        )
        self.assertIsNone(
            ob._get_field_kind("res_partner", "ghost"), msg="absent column"
        )
        self.assertEqual(
            len(executed),
            before,
            msg="_get_field_kind issued a catalog query despite the prefetch",
        )
        self.assertEqual(
            ob._field_widths,
            {("res_partner", "ref"): 8},
            msg="the same catalog read must carry the declared column widths",
        )

    @unittest.skipIf(os.name != "posix", "`os.openpty` only available on POSIX systems")
    def test_shell(self):

        main, child = os.openpty()

        shell = self.popen_command(
            "shell",
            "--shell-interface=python",
            "--shell-file",
            file_path("base/tests/shell_file.txt"),
            stdin=main,
            close_fds=True,
        )
        os.close(main)
        with os.fdopen(child, "w", encoding="utf-8") as stdin_file:
            stdin_file.write("print(message)\nexit()\n")
        with shell:
            self.assertFalse(shell.wait(), "exited with a non 0 code")

            lines = [
                line
                for line in shell.stdout.read().splitlines()
                if line.startswith(">>>")
            ]
            self.assertEqual(lines, [">>> Hello from Python!", ">>> "])

    def test_databasecommand_preserves_bootstrap_addons_path(self):
        from odoo.tools.config import configmanager

        with tempfile.TemporaryDirectory() as ad, tempfile.TemporaryDirectory() as dd:
            module = Path(ad) / "mymodule"
            module.mkdir()
            (module / "__init__.py").write_text("")
            (module / "__manifest__.py").write_text("{'name': 'mymodule'}\n")

            cfg = configmanager()
            cfg._parse_config([f"--addons-path={ad}", f"--data-dir={dd}"])
            first_addons = list(cfg["addons_path"])
            first_data_dir = cfg["data_dir"]
            self.assertIn(ad, first_addons)

            cfg._parse_config(["-d", "somedb"])
            second_addons = list(cfg["addons_path"])
            second_data_dir = cfg["data_dir"]

            self.assertIn(
                ad,
                second_addons,
                msg="addons_path lost on the second config parse: "
                "`module install --addons-path=X` would find no modules",
            )
            self.assertNotEqual(
                second_data_dir,
                first_data_dir,
                msg="data_dir unexpectedly persisted; the control no longer "
                "isolates addons_path's special preservation",
            )

    def test_build_config_args_forwards_only_connection_flags(self):
        from odoo.cli.command import prepare_config_args

        self.assertEqual(
            prepare_config_args("cfg", "db"),
            ["--no-http", "-c", "cfg", "-d", "db"],
        )
        self.assertNotIn("--addons-path", prepare_config_args("cfg", "db"))
        self.assertIn(
            "--workers=4",
            prepare_config_args(None, None, extra_args=["--workers=4"]),
        )

    def test_db_refuses_system_databases(self):
        from odoo.cli import db as dbmod

        cmd = dbmod.Db()
        protected = ["postgres", "template0", "template1", config["db_template"]]
        with (
            mock.patch.object(dbmod, "exp_db_exist", return_value=True),
            mock.patch.object(dbmod, "drop_database") as drop_mock,
            mock.patch.object(dbmod, "exp_create_database") as create_mock,
            mock.patch.object(dbmod, "rename_database") as rename_mock,
            mock.patch.object(dbmod, "duplicate_database") as duplicate_mock,
        ):
            for name in protected:
                with self.assertRaises(SystemExit, msg=f"drop {name} not refused"):
                    cmd.drop(mock.Mock(database=name))
                with self.assertRaises(SystemExit, msg=f"init {name} not refused"):
                    cmd.init(mock.Mock(database=name, force=True))
                with self.assertRaises(SystemExit, msg=f"rename from {name}"):
                    cmd.rename(mock.Mock(source=name, target="tgt", force=True))
                with self.assertRaises(SystemExit, msg=f"duplicate onto {name}"):
                    cmd.duplicate(mock.Mock(source="src", target=name, force=True))
            for name in ("postgres", "template0", "template1"):
                with self.assertRaises(SystemExit, msg=f"dump {name} not refused"):
                    cmd.dump(mock.Mock(database=name))
        drop_mock.assert_not_called()
        create_mock.assert_not_called()
        rename_mock.assert_not_called()
        duplicate_mock.assert_not_called()

    def test_db_dump_allows_the_template(self):
        from odoo.cli import db as dbmod

        if config["db_template"] in SYSTEM_DBS:
            self.skipTest("db_template is itself a system database here")
        with (
            mock.patch.object(dbmod, "exp_db_exist", return_value=True),
            mock.patch.object(dbmod, "dump_db") as dump_mock,
        ):
            dbmod.Db().dump(
                mock.Mock(
                    database=config["db_template"],
                    dump_path="-",
                    dump_format="zip",
                    filestore=True,
                )
            )
        dump_mock.assert_called_once()

    def _assert_start_hands_db_name_to_the_server(self, db_name):
        from odoo.cli import start as startmod

        with tempfile.TemporaryDirectory() as tmp:
            proj = Path(tmp) / db_name
            proj.mkdir()
            captured = {}
            with (
                mock.patch.object(
                    startmod,
                    "run_server",
                    lambda cmdargs: captured.update(args=list(cmdargs)),
                ),
                isolated_config(),
            ):
                startmod.Start().run(["-p", str(proj)])
        args = captured["args"]
        self.assertEqual(
            args[args.index("-d") + 1],
            db_name,
            msg=f"start did not hand the resolved name to the server: {args}",
        )

    def test_start_hands_protected_names_to_the_servers_guard(self):
        for db_name in (*SYSTEM_DBS, config["db_template"]):
            with self.subTest(db_name=db_name):
                self._assert_start_hands_db_name_to_the_server(db_name)

    def test_start_marks_base_for_install_via_the_server(self):
        from odoo.cli import server as server_mod

        with (
            mock.patch.object(config, "parse_config"),
            mock.patch.object(server_mod, "check_db_user_not_postgres"),
            mock.patch.object(server_mod, "report_configuration"),
            mock.patch.object(server_mod, "write_pid_file"),
            mock.patch.object(server_mod.db, "_create_empty_database"),
            mock.patch.object(server_mod.server, "start", return_value=0),
            mock.patch.dict(config._runtime_options, {"init": {}}, clear=False),
            isolated_config(),
        ):
            config._runtime_options["db_name"] = ["freshdb"]
            with self.assertRaises(SystemExit):
                server_mod.run_server([])
            self.assertEqual(
                config["init"],
                {"base": True},
                msg="a freshly created database was not marked for bootstrap",
            )

    def test_start_rejects_a_path_that_is_not_a_directory(self):
        from odoo.cli import start as startmod

        with (
            mock.patch.object(startmod, "run_server") as run_server_mock,
            self.assertRaises(SystemExit) as ctx,
            isolated_config(),
        ):
            startmod.Start().run(["-p", "8070"])
        run_server_mock.assert_not_called()
        self.assertEqual(ctx.exception.code, 2)

    def test_start_prefers_the_configured_db_name_over_the_directory(self):
        from odoo.cli import start as startmod

        with tempfile.TemporaryDirectory() as tmp:
            conf = Path(tmp) / "start.conf"
            conf.write_text("[options]\ndb_name = configured_db\n")
            proj = Path(tmp) / "named_after_the_directory"
            proj.mkdir()
            captured = {}
            with (
                mock.patch.object(
                    startmod,
                    "run_server",
                    lambda cmdargs: captured.update(args=list(cmdargs)),
                ),
                isolated_config(),
            ):
                startmod.Start().run(["-p", str(proj), "-c", str(conf)])
        args = captured["args"]
        self.assertEqual(args[args.index("-d") + 1], "configured_db", msg=str(args))
        self.assertIn("--db-filter=^configured_db$", args)

    def test_db_list_prints_databases(self):
        import contextlib
        import io

        from odoo.cli import db as dbmod

        out = io.StringIO()
        with (
            mock.patch.object(dbmod, "list_dbs", return_value=["alpha", "beta"]) as m,
            contextlib.redirect_stdout(out),
        ):
            dbmod.Db().list_databases(mock.Mock())
        m.assert_called_once_with(force=True)
        self.assertEqual(out.getvalue(), "alpha\nbeta\n")

    def test_db_connection_flags_have_help(self):
        import argparse

        from odoo.cli import db as dbmod

        declared = {flags[-1] for flags in dbmod.Db._CONNECTION_FLAGS}
        self.assertEqual(set(dbmod.Db._CONNECTION_HELP), declared)
        parser = argparse.ArgumentParser(prog="db")
        dbmod.Db._add_connection_flags(parser)
        registered = {
            a.option_strings[-1]: a.help
            for a in parser._actions
            if a.option_strings and a.dest != "help"
        }
        for long_flag in declared:
            self.assertEqual(
                registered.get(long_flag),
                dbmod.Db._CONNECTION_HELP[long_flag],
                msg=f"{long_flag} registered without its help text",
            )

    def test_deploy_zip_skips_junk_file_names(self):
        import zipfile as zipfile_mod

        from odoo.cli.deploy import Deploy

        with tempfile.TemporaryDirectory() as tmp:
            mod = Path(tmp) / "mymod"
            mod.mkdir()
            (mod / "__manifest__.py").write_text("{'name': 'mymod'}\n")
            (mod / ".DS_Store").write_bytes(b"\x00junk")
            (mod / "Thumbs.db").write_bytes(b"\x00junk")
            zpath = Deploy().zip_module(mod)
            try:
                with zipfile_mod.ZipFile(zpath) as z:
                    names = {n.split("/", 1)[1] for n in z.namelist()}
            finally:
                Path(zpath).unlink()
        self.assertNotIn(".DS_Store", names)
        self.assertNotIn("Thumbs.db", names)
        self.assertIn("__manifest__.py", names)

    def test_populate_rejects_nonpositive_factors(self):
        from odoo.cli.populate import _prepare_factors_by_model_name

        for factors in ("0", "-1", "3,0"):
            errors = []
            _prepare_factors_by_model_name(factors, "a,b", errors.append)
            self.assertTrue(
                errors and ">= 1" in errors[0],
                msg=f"factors {factors!r} not rejected: {errors}",
            )

    def test_help_falls_back_to_description(self):
        import contextlib
        import io

        from odoo.cli import help as helpmod

        class NoDocstring:
            __doc__ = None
            description = "From description\nsecond line ignored"

        out = io.StringIO()
        with (
            mock.patch.object(helpmod, "load_internal_commands"),
            mock.patch.object(helpmod, "load_addons_commands"),
            mock.patch.dict(helpmod.commands, {"nodoc": NoDocstring}, clear=True),
            contextlib.redirect_stdout(out),
        ):
            helpmod.Help().run([])
        self.assertIn("From description", out.getvalue())
        self.assertNotIn("second line", out.getvalue())

    def test_shell_repl_availability_probe(self):
        import importlib.util

        from odoo.cli.shell import Shell

        self.assertTrue(Shell._is_repl_installed("python"))
        self.assertEqual(
            set(Shell._REPL_MODULES),
            set(Shell.supported_shells) - {"python"},
        )
        with mock.patch.object(importlib.util, "find_spec", return_value=None):
            self.assertFalse(Shell._is_repl_installed("ipython"))

    def test_cloc_counts_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "thing.py").write_text("x = 1\ny = 2\n")
            proc = self.run_command("cloc", "-v", "-p", tmp)
        self.assertIn(Path(tmp).name, proc.stdout)
        self.assertIn("thing.py", proc.stdout)
        help_proc = self.run_command("cloc", "--help")
        self.assertIn("--config", help_proc.stdout)
        self.assertIn("--data-dir", help_proc.stdout)

    def test_get_single_database_refuses_system_databases(self):
        from odoo.cli.command import get_single_database

        for name in ("postgres", "template0", "template1", config["db_template"]):
            errors = []
            self.assertIsNone(get_single_database([name], error_handler=errors.append))
            self.assertTrue(
                errors and "system or template" in errors[0],
                msg=f"{name!r} not refused: {errors}",
            )
        errors = []
        self.assertEqual(
            get_single_database(["mydb"], error_handler=errors.append), "mydb"
        )
        self.assertFalse(errors)

    def test_server_refuses_system_database(self):
        proc = self.run_command(
            "server",
            "-d",
            "postgres",
            "--no-http",
            "--stop-after-init",
            check=False,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("system or template database", proc.stderr)

    def test_db_dump_removes_partial_file_on_failure(self):
        from odoo.cli import db as dbmod

        with tempfile.TemporaryDirectory() as tmp:
            dump_path = Path(tmp) / "out.zip"
            ns = mock.Mock(
                database="mydb",
                dump_path=str(dump_path),
                dump_format="zip",
                filestore=True,
            )
            with (
                mock.patch.object(dbmod, "exp_db_exist", return_value=True),
                mock.patch.object(
                    dbmod, "dump_db", side_effect=RuntimeError("disk full")
                ),
                self.assertRaises(RuntimeError),
            ):
                dbmod.Db().dump(ns)
            self.assertFalse(dump_path.exists(), msg="partial dump file left behind")

    def test_module_zip_path_requires_real_zip(self):
        import zipfile as zipfile_mod

        from odoo.cli.module import Module

        cmd = Module()
        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp) / "fake.zip"
            fake.write_text("not a zip at all")
            real = Path(tmp) / "real.zip"
            with zipfile_mod.ZipFile(real, "w") as z:
                z.writestr("mod/__manifest__.py", "{}")
            self.assertIsNone(cmd._get_zip_path(str(fake)))
            self.assertEqual(cmd._get_zip_path(str(real)), real.resolve())

    def test_subcommand_config_flags_work_in_both_positions(self):
        from odoo.cli.i18n import I18n
        from odoo.cli.module import Module

        for args in (
            ["-c", "cfg", "-d", "mydb", "install", "mymod"],
            ["install", "-c", "cfg", "-d", "mydb", "mymod"],
        ):
            ns = Module().parser.parse_args(args)
            self.assertEqual((ns.config, ns.db_name), ("cfg", "mydb"), msg=str(args))

        for args in (
            ["-c", "cfg", "-d", "mydb", "export", "base"],
            ["export", "-c", "cfg", "-d", "mydb", "base"],
        ):
            ns = I18n().parser.parse_args(args)
            self.assertEqual((ns.config, ns.db_name), ("cfg", "mydb"), msg=str(args))

    def test_i18n_import_force_overwrite_flag(self):
        from odoo.cli.i18n import I18n

        ns = I18n().parser.parse_args(
            ["import", "-l", "es_MX", "--force-overwrite", "f.po"]
        )
        self.assertTrue(ns.force_overwrite)
        ns = I18n().parser.parse_args(["import", "-l", "es_MX", "f.po"])
        self.assertFalse(ns.force_overwrite)
        self.assertFalse(ns.overwrite)

    def test_module_subcommands_exit_nonzero_when_nothing_resolved(self):
        from odoo.cli.module import Module

        cmd = Module()
        for sub, method in (
            ("install", cmd._install_modules),
            ("uninstall", cmd._uninstall_modules),
            ("upgrade", cmd._upgrade_modules),
        ):
            with self.subTest(sub=sub):
                env = mock.MagicMock()
                empty = mock.MagicMock()
                empty.__bool__.return_value = False
                empty.mapped.return_value = []
                empty.filtered.return_value = empty
                env.__getitem__.return_value.search.return_value = empty
                ns = mock.Mock(db_name="db", modules=["no_such_module"], outdated=False)
                with (
                    mock.patch("odoo.cli.module.open_environment") as env_ctx,
                    self.assertRaises(SystemExit) as ctx,
                ):
                    env_ctx.return_value.__enter__.return_value = env
                    method(ns)
                self.assertNotEqual(ctx.exception.code, 0)

    def test_database_commands_forward_server_options(self):
        from odoo.cli.module import Module

        parsed, unknown = Module().parse_args(
            ["-d", "db", "install", "base", "--log-level=warn"]
        )
        self.assertEqual(parsed.modules, ["base"])
        self.assertEqual(unknown, ["--log-level=warn"])

    def test_bootstrap_swallows_addons_path_before_any_command_sees_it(self):
        from odoo.cli.db import Db

        parser = prepare_bootstrap_parser()
        for argv in (
            ["db", "init", "foo", "--addons-path=/x"],
            ["db", "--addons-path=/x", "list"],
        ):
            with self.subTest(argv=argv):
                bootstrap, rest = parser.parse_known_args(argv)
                self.assertIsNotNone(bootstrap.addons_path)
                self.assertNotIn("--addons-path", " ".join(rest))
        self.assertNotIn(
            "addons_path",
            Db._get_connection_flags_by_dest(),
            msg="db re-declares a flag the bootstrap parser always eats first",
        )

    def test_obfuscate_probes_capacity_rather_than_the_declared_width(self):
        from odoo.cli.obfuscate import Obfuscate

        ob = Obfuscate()
        projections = {"roomy": 180, "snug": 180, "code": 103}

        class FakeCur:
            def __init__(self):
                self.last = None

            def execute(self, query, params=None):
                code = getattr(query, "code", query)
                self.last = next(
                    (name for name in projections if f'"{name}"' in code), None
                )

            def fetchall(self):
                return [
                    ("t", "roomy", "varchar", 400),
                    ("t", "snug", "varchar", 150),
                    ("t", "wide_open", "text", None),
                ]

            def fetchone(self):
                return (projections[self.last],)

        ob.cr = FakeCur()
        ob._load_field_catalog({"t"})
        fields = [("t", "roomy"), ("t", "snug"), ("t", "wide_open")]
        self.assertEqual(
            ob._get_fields_unfittable(fields, "pw"),
            [(("t", "snug"), 150, 180)],
            msg="only the column that actually cannot hold the ciphertext",
        )

    def test_obfuscate_refuses_a_field_the_user_named_and_cannot_encrypt(self):
        from odoo.cli.obfuscate import Obfuscate

        ob = Obfuscate()
        fields = [("t", "snug"), ("t", "other")]
        with mock.patch.object(
            Obfuscate,
            "_get_fields_unfittable",
            return_value=[(("t", "snug"), 150, 180)],
        ):
            with self.assertRaises(SystemExit) as ctx:
                ob._exclude_fields_unfittable(fields, "pw", {("t", "snug")})
            self.assertIn("cannot hold ciphertext", str(ctx.exception.code))
            self.assertEqual(
                ob._exclude_fields_unfittable(fields, "pw", set()),
                [("t", "other")],
                msg="a built-in default entry is skipped, not fatal",
            )

    def test_obfuscate_reports_user_named_fields_apart_from_the_defaults(self):
        from odoo.cli.obfuscate import Obfuscate

        opt = mock.Mock(fields="typo.column", file=None)
        self.assertEqual(
            Obfuscate._get_fields_requested_explicitly(opt), {("typo", "column")}
        )
        opt = mock.Mock(fields=None, file=None)
        self.assertEqual(Obfuscate._get_fields_requested_explicitly(opt), set())

    def test_commands_declare_their_arguments_on_construction(self):
        load_internal_commands()
        expected = {
            "cloc": "--path",
            "db": "--db_host",
            "deploy": "--login",
            "i18n": "-c",
            "module": "-d",
            "neutralize": "--stdout",
            "obfuscate": "--pwd",
            "populate": "--factors",
            "scaffold": "--template",
            "shell": "--shell-interface",
            "start": "--path",
        }
        for name, flag in expected.items():
            with self.subTest(name=name):
                strings = {
                    option
                    for action in commands[name]().parser._actions
                    for option in action.option_strings
                }
                self.assertIn(flag, strings)

    def test_help_renders_one_commands_own_help(self):
        proc = self.run_command("help", "db", check=False)
        self.assertIn("usage:", proc.stdout)
        self.assertIn("duplicate", proc.stdout)
        self.assertNotIn("Available commands:", proc.stdout)
        proc = self.run_command("help", "nosuchcommand", check=False)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("Unknown command", proc.stderr)

    def test_maintenance_db_rule_has_one_spelling(self):
        from odoo.cli.command import (
            MAINTENANCE_DB_MESSAGE,
            check_db_not_maintenance,
        )

        with self.assertRaises(SystemExit) as ctx:
            check_db_not_maintenance("postgres")
        self.assertEqual(
            str(ctx.exception.code),
            MAINTENANCE_DB_MESSAGE.format(db_name="postgres"),
        )
        check_db_not_maintenance("a_perfectly_ordinary_database")

    def test_shell_tolerates_a_stdin_without_a_fileno(self):
        from odoo.cli.shell import Shell

        class NoFileno:
            def fileno(self):
                raise ValueError("I/O operation on closed file")

        for stdin in (None, NoFileno()):
            with mock.patch.object(sys, "stdin", stdin):
                self.assertFalse(Shell._is_stdin_a_tty())

    def test_obfuscate_json_transform_only_touches_string_values(self):
        from odoo.cli.obfuscate import Obfuscate

        ob = Obfuscate()
        executed = []

        class FakeCur:
            def execute(self, query, params=None):
                executed.append(getattr(query, "code", query))

            def fetchall(self):
                return [("en_US",)]

            def fetchone(self):
                return (0,)

        ob.cr = FakeCur()
        ob._field_kinds = {("t", "val"): "json"}
        ob._field_widths = {}
        ob._update_table_values("t", ["val"], "pw")
        update = executed[-1]
        self.assertIn("jsonb_typeof", update)
        self.assertIn("= 'string'", update)
        self.assertIn("jsonb_typeof(\"val\") = 'object'", update)

    def test_obfuscate_json_key_probe_skips_non_object_rows(self):
        from odoo.cli.obfuscate import Obfuscate

        ob = Obfuscate()
        executed = []

        class FakeCur:
            def execute(self, query, params=None):
                executed.append(getattr(query, "code", query))

            def fetchone(self):
                return (2,)

            def fetchall(self):
                return [("en_US",)]

        ob.cr = FakeCur()
        with self.assertLogs("odoo.cli.obfuscate", level="WARNING") as logs:
            self.assertEqual(ob._get_keys_in_jsonb_column("t", "val"), ["en_US"])
        self.assertIn("not an object", logs.output[0])
        self.assertIn("<> 'object'", executed[0], msg="the non-object count")
        self.assertIn("= 'object'", executed[1], msg="the guarded key probe")

    def test_db_load_validates_the_name_before_downloading(self):
        from odoo.cli import db as dbmod

        ns = mock.Mock(
            database="bad name!", dump_file="http://example.invalid/d.zip", force=False
        )
        with (
            mock.patch.object(dbmod.requests, "get") as get_mock,
            self.assertRaises(SystemExit) as ctx,
        ):
            dbmod.Db().load(ns)
        get_mock.assert_not_called()
        self.assertIn("bad name!", str(ctx.exception.code))

    def test_every_builtin_template_scaffolds_a_loadable_module(self):
        import ast
        import csv as csv_mod

        from lxml import etree

        from odoo.cli.scaffold import Template, _get_template_path

        names = sorted(d.name for d in _get_template_path().iterdir() if d.is_dir())
        self.assertTrue(names, msg="no built-in templates found")

        argument = {"l10n_payroll": "mexico-mx"}
        for name in names:
            with self.subTest(template=name), tempfile.TemporaryDirectory() as tmp:
                template = Template(name)
                given = argument.get(name, "scaffold_probe")
                params = template.parse_params(given)
                modname = template.get_module_name(given, params)
                template.render_to_directory(modname, Path(tmp), params=params)
                module = Path(tmp) / modname

                manifest_path = module / "__manifest__.py"
                self.assertTrue(manifest_path.is_file(), msg=f"{name}: no manifest")
                manifest = ast.literal_eval(manifest_path.read_text(encoding="utf-8"))
                self.assertIsInstance(manifest, dict)
                self.assertIn(
                    "license",
                    manifest,
                    msg=f"{name}: no license key; every load warns about it",
                )

                for py in module.rglob("*.py"):
                    try:
                        ast.parse(py.read_text(encoding="utf-8"))
                    except SyntaxError as exc:
                        self.fail(f"{name} rendered unparseable Python in {py}: {exc}")

                declared = [*manifest.get("data", []), *manifest.get("demo", [])]
                self.assertTrue(
                    declared, msg=f"{name}: manifest declares no data at all"
                )
                for relative in declared:
                    path = module / relative
                    self.assertTrue(
                        path.is_file(),
                        msg=f"{name}: manifest lists {relative}, which was not rendered",
                    )
                    body = path.read_text(encoding="utf-8")
                    if path.suffix == ".xml":
                        try:
                            etree.fromstring(body.encode())
                        except etree.XMLSyntaxError as exc:
                            self.fail(
                                f"{name}: {relative} is not loadable XML ({exc}); "
                                "a module declaring it fails to install"
                            )
                    elif path.suffix == ".csv":
                        rows = list(csv_mod.reader(body.splitlines()))
                        self.assertTrue(
                            rows and rows[0], msg=f"{name}: {relative} empty"
                        )

    def test_scaffold_naming_conventions_agree(self):
        from odoo.cli.scaffold import (
            DEFAULT_NAMING,
            NAMING_CONVENTIONS,
            Template,
            _get_template_path,
        )

        samples = {"l10n_payroll": "mexico-mx"}
        for template_id, convention in NAMING_CONVENTIONS.items():
            with self.subTest(template=template_id):
                given = samples[template_id]
                params = convention.parse_params(given)
                modname = convention.get_module_name(given, params)
                self.assertTrue(modname and not modname.startswith("_"), msg=modname)
                self.assertEqual(
                    Template(template_id).get_module_name(given, params),
                    modname,
                    msg="Template disagrees with its own convention",
                )

        self.assertEqual(DEFAULT_NAMING.parse_params("MyThing"), {"name": "MyThing"})
        self.assertEqual(
            DEFAULT_NAMING.get_module_name("MyThing", {"name": "MyThing"}), "my_thing"
        )

        for directory in _get_template_path().iterdir():
            if directory.is_dir():
                with self.subTest(template=directory.name):
                    given = samples.get(directory.name, "probe")
                    template = Template(directory.name)
                    params = template.parse_params(given)
                    self.assertIn("name", params)
                    self.assertTrue(template.get_module_name(given, params))

    def test_db_dump_refuses_an_unwritable_destination_before_dumping(self):
        from odoo.cli import db as dbmod

        with tempfile.TemporaryDirectory() as tmp:
            ns = mock.Mock(
                database="whatever",
                dump_path=str(Path(tmp) / "no" / "such" / "dir" / "x.zip"),
                dump_format="zip",
                filestore=True,
            )
            with (
                mock.patch.object(dbmod, "exp_db_exist", return_value=True),
                mock.patch.object(dbmod, "dump_db") as dump_mock,
                self.assertRaises(SystemExit) as ctx,
            ):
                dbmod.Db().dump(ns)
            dump_mock.assert_not_called()
            self.assertIn("is not a directory", str(ctx.exception.code))

    def test_i18n_export_does_not_mutate_the_parsed_namespace(self):
        from odoo.cli.i18n import I18n

        cmd = I18n()
        parsed = cmd.parser.parse_args(["export", "base", "-l", "pot", "-l", "es_MX"])
        before = list(parsed.languages)
        with mock.patch(
            "odoo.cli.i18n.open_environment", side_effect=RuntimeError("stop")
        ):
            with self.assertRaises((RuntimeError, SystemExit)):
                cmd._export_translations(parsed)
        self.assertEqual(parsed.languages, before)
