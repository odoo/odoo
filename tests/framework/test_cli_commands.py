import logging
import sys
import zipfile
from pathlib import Path
from unittest import mock

import pytest

import odoo.cli
from odoo.cli import command as cli_command
from odoo.cli.command import Command, commands, get_single_database
from odoo.cli.deploy import Deploy
from odoo.cli.obfuscate import DEFAULT_FIELDS, _get_fields_selected, _parse_field_spec
from odoo.cli.populate import _prepare_factors_by_model_name
from odoo.cli.scaffold import Template, _str_to_pascal_case, _str_to_snake_case
from odoo.cli.start import _derive_addons_paths, _has_arg, _is_path_arg

import odoo.addons


class _Recorder:
    def __init__(self):
        self.messages = []

    def __call__(self, message):
        self.messages.append(message)
        raise SystemExit(2)


def _define(name, module="odoo.cli", run=None, **attrs):
    body = {"__module__": f"{module}.{name}", **attrs}
    if "declared_name" in attrs:
        body["name"] = body.pop("declared_name")
    if run is not None:
        body["run"] = run
    return type(name.capitalize(), (Command,), body)


@pytest.fixture
def registry_snapshot():
    before = dict(commands)
    yield commands
    commands.clear()
    commands.update(before)


class TestCommandRegistration:
    def test_a_subclass_registers_under_its_lowercased_class_name(
        self, registry_snapshot
    ):
        cls = _define("probe", run=lambda self, args: None)
        assert registry_snapshot["probe"] is cls
        assert cls.name == "probe"

    def test_register_false_keeps_the_class_out_of_the_table(self, registry_snapshot):
        class Hidden(Command, register=False):
            def run(self, args):
                pass

        assert "hidden" not in registry_snapshot
        assert Hidden.name is None

    def test_a_name_that_is_not_a_module_name_is_rejected(self, registry_snapshot):
        with pytest.raises(ValueError, match="must match Module name"):
            _define("probe", declared_name="other", run=lambda s, a: None)

    def test_an_invalid_name_is_rejected(self, registry_snapshot):
        with pytest.raises(ValueError, match="must match"):
            _define("Bad-Name", run=lambda s, a: None)

    def test_a_subclass_without_run_is_rejected(self, registry_snapshot):
        with pytest.raises(TypeError, match="must override"):
            _define("probe")

    def test_a_second_registration_wins_with_a_warning(self, registry_snapshot, caplog):
        first = _define("probe", run=lambda s, a: None)
        with caplog.at_level(logging.WARNING, logger="odoo.cli.command"):
            second = _define("probe", module="odoo.addons.x.cli", run=lambda s, a: 1)
        assert registry_snapshot["probe"] is second
        assert registry_snapshot["probe"] is not first
        assert "redefined" in caplog.text


class TestGetSingleDatabase:
    def test_none_is_an_error_unless_allowed(self):
        recorder = _Recorder()
        with pytest.raises(SystemExit):
            get_single_database([], error_handler=recorder)
        assert "No database specified" in recorder.messages[0]
        assert get_single_database([], allow_none=True, error_handler=recorder) is None

    def test_several_databases_are_an_error(self):
        recorder = _Recorder()
        with pytest.raises(SystemExit):
            get_single_database(["a", "b"], error_handler=recorder)
        assert "Multiple databases" in recorder.messages[0]

    @pytest.mark.parametrize("name", ["postgres", "template0", "template1"])
    def test_maintenance_databases_are_refused(self, name):
        recorder = _Recorder()
        with pytest.raises(SystemExit):
            get_single_database([name], error_handler=recorder)
        assert name in recorder.messages[0]

    def test_one_ordinary_database_is_returned(self):
        assert get_single_database(["shop"]) == "shop"


class TestAddonCommandDiscovery:
    @staticmethod
    def _addon_with_command(root, addon, command, body):
        cli_dir = root / addon / "cli"
        cli_dir.mkdir(parents=True)
        (root / addon / "__init__.py").write_text("")
        (root / addon / "__manifest__.py").write_text("{'name': 'x'}")
        (cli_dir / f"{command}.py").write_text(body)

    def test_the_first_addons_path_defining_a_command_keeps_it(
        self, tmp_path, registry_snapshot, caplog
    ):
        first, second = tmp_path / "first", tmp_path / "second"
        for root, tag in ((first, "first"), (second, "second")):
            self._addon_with_command(
                root,
                f"mod_{tag}",
                "probe",
                "from odoo.cli import Command\n"
                "class Probe(Command):\n"
                f"    TAG = {tag!r}\n"
                "    def run(self, args):\n"
                "        pass\n",
            )
        with (
            mock.patch.object(odoo.addons, "__path__", [str(first), str(second)]),
            mock.patch.object(cli_command, "initialize_sys_path"),
            caplog.at_level(logging.WARNING, logger="odoo.cli.command"),
        ):
            cli_command.load_addons_commands("probe")
        loaded = registry_snapshot["probe"]
        assert loaded.TAG == "first", "addons_path order is priority"
        assert "shadows" in caplog.text
        assert str(first / "mod_first") in caplog.text.split("shadows")[0]

    def test_an_invalid_command_name_loads_nothing(self, registry_snapshot):
        with mock.patch.object(cli_command, "initialize_sys_path") as init:
            cli_command.load_addons_commands("Not-Valid")
        init.assert_not_called()


class TestMainDispatch:
    @pytest.fixture(autouse=True)
    def _restore_globals(self):
        saved = (odoo.cli.COMMAND, odoo.cli.BOOTSTRAP_ADDONS_PATH, list(sys.argv))
        yield
        odoo.cli.COMMAND, odoo.cli.BOOTSTRAP_ADDONS_PATH = saved[0], saved[1]
        sys.argv[:] = saved[2]

    def _run(self, argv):
        ran = []

        class Fake:
            def run(self, args):
                ran.append(args)

        resolved = []

        def get(name):
            resolved.append(name)
            return Fake

        sys.argv[:] = ["odoo-bin", *argv]
        with mock.patch.object(cli_command, "get_cli_command", side_effect=get):
            cli_command.main()
        return resolved, ran

    def test_a_positional_word_names_the_command(self):
        resolved, ran = self._run(["shell", "-d", "db"])
        assert resolved == ["shell"]
        assert ran == [["-d", "db"]]
        assert odoo.cli.COMMAND == "shell"

    def test_no_command_means_server(self):
        resolved, ran = self._run(["-d", "db", "--http-port=1"])
        assert resolved == ["server"]
        assert ran == [["-d", "db", "--http-port=1"]]

    @pytest.mark.parametrize("flag", ["-h", "--help"])
    def test_a_help_flag_first_means_help(self, flag):
        resolved, ran = self._run([flag])
        assert resolved == ["help"]
        assert ran == [[]]

    def test_the_bootstrap_addons_path_is_split_off_and_remembered(self):
        with mock.patch.object(cli_command.config, "_parse_config") as parse:
            _resolved, ran = self._run(["--addons-path=/a,/b", "shell"])
        parse.assert_called_once_with(["--addons-path=/a,/b"])
        assert odoo.cli.BOOTSTRAP_ADDONS_PATH == "/a,/b"
        assert ran == [[]]

    def test_an_unknown_command_exits_with_a_hint(self):
        sys.argv[:] = ["odoo-bin", "nonesuch"]
        with (
            mock.patch.object(cli_command, "get_cli_command", return_value=None),
            pytest.raises(SystemExit) as info,
        ):
            cli_command.main()
        assert "Unknown command 'nonesuch'" in str(info.value)


class TestPrepareConfigArgs:
    def test_the_shape_is_stable(self):
        assert cli_command.prepare_config_args() == ["--no-http"]
        assert cli_command.prepare_config_args(
            "c.conf", "db", no_http=False, extra_args=["-u", "base"]
        ) == ["-c", "c.conf", "-d", "db", "-u", "base"]


class TestStartArgumentSplit:
    @pytest.mark.parametrize(
        ("args", "expected"),
        [
            (["-p", "mods", "-d", "db"], [True, True, False, False]),
            (["--path=mods", "--http-port=1"], [True, False]),
            (["--path", "mods"], [True, True]),
            (["-pmods"], [True]),
            (["--pidfile=x", "-d", "db"], [False, False, False]),
        ],
    )
    def test_path_arguments_are_recognised_with_their_values(self, args, expected):
        assert [_is_path_arg(i, args) for i in range(len(args))] == expected

    def test_has_arg_matches_both_spellings(self):
        assert _has_arg(["--db-filter=^x$"], "--db-filter")
        assert _has_arg(["--db-filter", "^x$"], "--db-filter")
        assert not _has_arg(["--db-filter-x"], "--db-filter")


class TestStartAddonsPaths:
    def test_the_project_joins_the_configured_paths_instead_of_replacing_them(self):
        paths = _derive_addons_paths(
            Path("/proj"), bootstrap=None, configured=["/core", "/enterprise"]
        )
        assert paths == ["/proj", "/core", "/enterprise"]

    def test_bootstrap_paths_lead_and_duplicates_collapse(self):
        paths = _derive_addons_paths(
            Path("/proj"), bootstrap="/a,,/proj", configured=["/a", "/core"]
        )
        assert paths == ["/a", "/proj", "/core"]


class TestPopulateFactors:
    def test_the_last_factor_propagates(self):
        assert _prepare_factors_by_model_name("2,3", "a,b,c", _Recorder()) == {
            "a": 2,
            "b": 3,
            "c": 3,
        }

    def test_extra_factors_are_dropped_with_a_warning(self, caplog):
        with caplog.at_level(logging.WARNING, logger="odoo.cli.populate"):
            result = _prepare_factors_by_model_name("2,3,4", "a", _Recorder())
        assert result == {"a": 2}
        assert "ignoring the extra factors" in caplog.text

    @pytest.mark.parametrize("factors", ["x", "0", "1,-1", ""])
    def test_non_positive_or_non_integer_factors_are_errors(self, factors):
        recorder = _Recorder()
        with pytest.raises(SystemExit):
            _prepare_factors_by_model_name(factors, "a", recorder)
        assert "--factors" in recorder.messages[0]


class TestObfuscateFieldSelection:
    @staticmethod
    def _opt(**kw):
        base = {
            "no_default_fields": False,
            "fields": None,
            "allfields": False,
            "file": None,
            "exclude": None,
        }
        base.update(kw)
        return mock.Mock(**base)

    def test_spec_parsing(self):
        assert _parse_field_spec(" res_partner.name ") == ("res_partner", "name")
        for bad in ("res_partner", "a.b.c", ".name", "table."):
            with pytest.raises(ValueError, match="Invalid field specification"):
                _parse_field_spec(bad)

    def test_defaults_plus_fields_minus_exclude(self):
        fields = _get_fields_selected(
            self._opt(fields="x.y,res_partner.name", exclude="res_partner.email")
        )
        assert ("x", "y") in fields
        assert ("res_partner", "email") not in fields
        assert fields.count(("res_partner", "name")) == 2, (
            "duplicates are the caller's to squash; selection is a plain concat"
        )

    def test_no_default_fields_starts_empty(self):
        assert _get_fields_selected(
            self._opt(no_default_fields=True, fields="a.b")
        ) == [("a", "b")]

    def test_allfields_ignores_the_explicit_selections(self, caplog):
        with caplog.at_level(logging.WARNING, logger="odoo.cli.obfuscate"):
            fields = _get_fields_selected(
                self._opt(allfields=True, fields="a.b", exclude="res_partner.name")
            )
        assert fields == list(DEFAULT_FIELDS)
        assert caplog.text.count("--allfields is set") == 2


class TestDeployZip:
    def test_excluded_directories_files_and_symlinks_stay_out(self, tmp_path):
        module = tmp_path / "my_module"
        (module / "models").mkdir(parents=True)
        (module / "__manifest__.py").write_text("{}")
        (module / "models" / "a.py").write_text("x = 1")
        (module / "models" / "a.pyc").write_bytes(b"\0")
        (module / ".DS_Store").write_bytes(b"\0")
        (module / "__pycache__").mkdir()
        (module / "__pycache__" / "a.cpython-314.pyc").write_bytes(b"\0")
        (module / "node_modules").mkdir()
        (module / "node_modules" / "x.js").write_text("")
        (module / "link.py").symlink_to(module / "models" / "a.py")

        archive = Deploy().zip_module(module)
        try:
            with zipfile.ZipFile(archive) as zf:
                names = sorted(zf.namelist())
        finally:
            Path(archive).unlink()
        assert names == ["my_module/__manifest__.py", "my_module/models/a.py"]

    def test_a_missing_directory_is_a_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            Deploy().zip_module(tmp_path / "absent")


class TestScaffoldNaming:
    @pytest.mark.parametrize(
        ("given", "snake"),
        [
            ("MyModule", "my_module"),
            ("HTTPServer", "http_server"),
            ("my module", "my_module"),
            ("already_snake", "already_snake"),
            ("version2Beta", "version2_beta"),
        ],
    )
    def test_snake_case(self, given, snake):
        assert _str_to_snake_case(given) == snake

    def test_pascal_case(self):
        assert _str_to_pascal_case("my_module name") == "MyModuleName"

    def test_the_default_template_snake_cases_the_module_name(self):
        template = Template("default")
        params = template.parse_params("My Module")
        assert template.get_module_name("My Module", params) == "my_module"

    def test_the_payroll_template_derives_the_module_from_the_country_code(self):
        template = Template("l10n_payroll")
        params = template.parse_params("mexico-mx")
        assert params == {"name": "mexico", "code": "mx"}
        assert template.get_module_name("mexico-mx", params) == "l10n_mx_hr_payroll"
        with pytest.raises(ValueError, match="<country>-<code>"):
            template.parse_params("mexico")

    def test_a_name_that_snake_cases_to_an_invalid_module_is_rejected(self):
        template = Template("default")
        with pytest.raises(ValueError, match="not a valid module name"):
            template.get_module_name("9lives", template.parse_params("9lives"))

    def test_an_unknown_template_is_an_argument_error(self):
        import argparse

        with pytest.raises(argparse.ArgumentTypeError):
            Template("nonesuch-template")
