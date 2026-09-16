import collections
import configparser
import contextlib
import functools
import io
import logging
import optparse  # noqa: TID251  the whole CLI is built on optparse; the ban guards NEW uses
import os
import sys
import tempfile
import warnings
from collections.abc import Callable, Iterator
from os.path import expandvars, normcase
from pathlib import Path
from typing import TYPE_CHECKING, Any

import odoo
from odoo import release
from odoo.db.settings import PoolSettings
from odoo.db.settings import provide as _provide_pool_settings
from odoo.libs.debug_log import DebugLog
from odoo.libs.filesystem import appdirs
from odoo.libs.func import classproperty
from odoo.libs.password import CryptContext

if TYPE_CHECKING:
    from collections.abc import Generator

crypt_context = CryptContext(
    schemes=["pbkdf2_sha512", "plaintext"],
    deprecated=["plaintext"],
    pbkdf2_sha512__rounds=600_000,
)

_dangerous_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

optparse._ = str  # type: ignore[attr-defined]

ALL_DEV_MODE = ["access", "assets", "qweb", "reload", "xml"]
_MODULE_MAP_OPTIONS = frozenset({"init", "update"})
DEFAULT_SERVER_WIDE_MODULES = ["base", "rpc", "web"]
REQUIRED_SERVER_WIDE_MODULES = ["base", "web"]


class _Empty:
    def __repr__(self) -> str:
        return ""


EMPTY = _Empty()


class _OdooOption(optparse.Option):
    config: Any = None

    TYPES = (
        "int",
        "float",
        "string",
        "choice",
        "bool",
        "path",
        "comma",
        "addons_path",
        "upgrade_path",
        "pre_upgrade_scripts",
        "without_demo",
        "smtp_ssl",
    )

    @classproperty
    def TYPE_CHECKER(self):
        checkers = {
            "int": lambda _option, _opt, value: int(value),
            "float": lambda _option, _opt, value: float(value),
            "string": lambda _option, _opt, value: str(value),
            "choice": optparse.check_choice,
            "bool": self.config._parse_bool,
            "path": self.config._parse_path,
            "comma": self.config._parse_comma,
            "addons_path": self.config._parse_addons_path,
            "upgrade_path": self.config._parse_upgrade_path,
            "pre_upgrade_scripts": self.config._parse_scripts,
            "smtp_ssl": self.config._check_smtp_ssl,
        }
        return {
            **{name: _accept_none(check) for name, check in checkers.items()},
            "without_demo": self.config._parse_without_demo,
        }

    @classproperty
    def TYPE_FORMATTER(self):
        return {
            "int": self.config._format_string,
            "float": self.config._format_string,
            "string": self.config._format_string,
            "choice": self.config._format_string,
            "bool": self.config._format_string,
            "path": self.config._format_string,
            "comma": self.config._format_list,
            "addons_path": self.config._format_list,
            "upgrade_path": self.config._format_list,
            "pre_upgrade_scripts": self.config._format_list,
            "smtp_ssl": self.config._format_string,
            "without_demo": self.config._format_without_demo,
        }

    def __init__(self, *opts: str, **attrs: Any) -> None:
        self.my_default = attrs.pop("my_default", None)
        self.cli_loadable = attrs.pop("cli_loadable", True)
        env_name = attrs.pop("env_name", None)
        self.env_name = env_name or ""
        self.file_loadable = attrs.pop("file_loadable", True)
        self.file_exportable = attrs.pop("file_exportable", self.file_loadable)
        self.nargs_ = attrs.get("nargs")
        if self.nargs_ == "?":
            const = attrs.pop("const", None)
            attrs["nargs"] = 1
        attrs.setdefault("metavar", attrs.get("type", "string").upper())
        super().__init__(*opts, **attrs)
        if "default" in attrs:
            self.config._log(
                logging.WARNING,
                "please use my_default= instead of default= with option %s",
                self,
            )
        if self.file_exportable and not self.file_loadable:
            e = (
                f"it makes no sense that the option {self} can be exported "
                "to the config file but not loaded from the config file"
            )
            raise ValueError(e)
        is_new_option = False
        if self.dest and self.dest not in self.config.options_index:
            self.config.options_index[self.dest] = self
            is_new_option = True
        if self.nargs_ == "?":
            self.const = const
            for opt in self._short_opts + self._long_opts:
                self.config.optional_options[opt] = self
        if env_name is None and is_new_option and self.file_loadable:
            self.env_name = "ODOO_" + (self.dest or "").upper()
        elif env_name and not is_new_option:
            raise ValueError(
                f"cannot set env_name to an option that is not indexed: {self}"
            )

    def __str__(self) -> str:
        out = []
        if self.cli_loadable:
            out.append(super().__str__())
        if self.file_loadable and self.dest:
            out.append(self.dest)
        return "/".join(out)


class _FileOnlyOption(_OdooOption):
    def __init__(self, **attrs: Any) -> None:
        super().__init__(**attrs, cli_loadable=False, help=optparse.SUPPRESS_HELP)

    def _check_opt_strings(self, opts):
        if opts:
            msg = "No option can be supplied"
            raise TypeError(msg)
        return []

    def _set_opt_strings(self, opts):
        return


class _PosixOnlyOption(_OdooOption):
    def __init__(self, *opts: str, **attrs: Any) -> None:
        if os.name != "posix":
            attrs["help"] = optparse.SUPPRESS_HELP
            attrs["cli_loadable"] = False
            attrs["env_name"] = ""
            attrs["file_loadable"] = False
            attrs["file_exportable"] = False
        super().__init__(*opts, **attrs)


class _Unset:
    __slots__ = ()

    def __repr__(self) -> str:
        return "None"


UNSET = _Unset()
SMTP_SSL_MODES = ("starttls_strict", "starttls", "ssl_strict", "ssl")
# an empty value is "unset" in the config file; these types have no empty literal
_TYPES_WITHOUT_AN_EMPTY_VALUE = frozenset(
    {"int", "float", "bool", "choice", "smtp_ssl", "without_demo"}
)


def _accept_none(check: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(check)
    def checked(option: Any, opt: str, value: str) -> Any:
        if value == "None":
            return UNSET
        return check(option, opt, value)

    return checked


def _open_private(path: str, flags: int) -> int:
    return os.open(path, flags, 0o600)


def _deduplicate_loggers(loggers: list[str]) -> Generator[str]:
    seen: dict[str, str] = {}
    for spec in loggers:
        logger, sep, level = spec.rpartition(":")
        if not sep:
            raise ValueError(
                f"invalid log handler {spec!r}: expected MODULE:LEVEL "
                f"(an empty MODULE is the root logger, e.g. ':INFO')"
            )
        seen[logger] = level
    return (f"{logger}:{level}" for logger, level in seen.items())


# An option layer that bumps the manager's generation on every write, so a
# settings snapshot derived from the options is reusable until any layer
# changes -- through __setitem__, patch(), parse_config() or a test poking
# config.options[...] directly. Reads are dict's own.
class _CountingDict(dict[str, Any]):
    __slots__ = ("_bump",)

    def __init__(self, bump: Callable[[], None]) -> None:
        super().__init__()
        self._bump = bump

    # A copy is a plain dict: deep-copying a layer must not drag the manager
    # along through the bound bump, nor bump a half-built copy while its
    # items are being restored. What copies a layer wants its content.
    def __reduce__(self) -> tuple[Any, ...]:
        return (dict, (dict(self),))

    def __setitem__(self, key: str, value: Any) -> None:
        super().__setitem__(key, value)
        self._bump()

    def __delitem__(self, key: str) -> None:
        super().__delitem__(key)
        self._bump()

    def pop(self, *args: Any) -> Any:
        result = super().pop(*args)
        self._bump()
        return result

    def popitem(self) -> tuple[str, Any]:
        result = super().popitem()
        self._bump()
        return result

    def clear(self) -> None:
        super().clear()
        self._bump()

    def update(self, *args: Any, **kwargs: Any) -> None:
        super().update(*args, **kwargs)
        self._bump()

    def setdefault(self, key: str, default: Any = None) -> Any:
        result = super().setdefault(key, default)
        self._bump()
        return result


class configmanager:
    def __init__(self) -> None:
        self._generation = 0
        bump = self._bump_generation
        self._default_options: dict[str, Any] = _CountingDict(bump)
        self._file_options: dict[str, Any] = _CountingDict(bump)
        self._env_options: dict[str, Any] = _CountingDict(bump)
        self._cli_options: dict[str, Any] = _CountingDict(bump)
        self._override_options: dict[str, Any] = _CountingDict(bump)
        self._runtime_options: dict[str, Any] = _CountingDict(bump)
        self.options: collections.ChainMap[str, Any] = collections.ChainMap(
            self._override_options,
            self._runtime_options,
            self._cli_options,
            self._env_options,
            self._file_options,
            self._default_options,
        )

        self.options_index: dict[str, _OdooOption] = {}

        self.optional_options: dict[str, _OdooOption] = {}

        self.aliases: dict[str, str] = {
            "import_image_maxbytes": "import_file_maxbytes",
            "import_image_regex": "import_url_regex",
            "import_image_timeout": "import_file_timeout",
        }

        self.parser = self._prepare_cli_parser()
        self._load_default_options()

        try:
            with contextlib.redirect_stderr(io.StringIO()):
                self._parse_config()
        except SystemExit, ValueError:
            pass

    @property
    def rcfile(self) -> str:
        self._warn(
            "Since 19.0, use odoo.tools.config['config'] instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return self["config"]

    @rcfile.setter
    def rcfile(self, rcfile: str) -> None:
        self._warn(
            f"Since 19.0, use odoo.tools.config['config'] = {rcfile!r} instead",
            DeprecationWarning,
            stacklevel=2,
        )
        self._override_options["config"] = rcfile

    def _prepare_cli_parser(self) -> optparse.OptionParser:
        OdooOption = type("OdooOption", (_OdooOption,), {"config": self})
        FileOnlyOption = type("FileOnlyOption", (_FileOnlyOption, OdooOption), {})
        PosixOnlyOption = type("PosixOnlyOption", (_PosixOnlyOption, OdooOption), {})

        version = "%s %s" % (release.description, release.version)
        parser = optparse.OptionParser(version=version, option_class=OdooOption)

        self._add_file_only_options(parser, FileOnlyOption)

        self._add_common_options(parser, OdooOption, PosixOnlyOption)
        self._add_http_options(parser, OdooOption, PosixOnlyOption)
        self._add_web_interface_options(parser, OdooOption, PosixOnlyOption)
        self._add_testing_options(parser, OdooOption, PosixOnlyOption)
        self._add_logging_options(parser, OdooOption, PosixOnlyOption)
        self._add_smtp_options(parser, OdooOption, PosixOnlyOption)
        self._add_database_options(parser, OdooOption, PosixOnlyOption)
        self._add_i18n_options(parser, OdooOption, PosixOnlyOption)
        self._add_security_options(parser, OdooOption, PosixOnlyOption)
        self._add_advanced_options(parser, OdooOption, PosixOnlyOption)
        self._add_multiprocessing_options(parser, OdooOption, PosixOnlyOption)

        return parser

    def _add_file_only_registry_options(
        self, parser: optparse.OptionParser, FileOnlyOption: type
    ) -> None:
        parser.add_option(FileOnlyOption(dest="admin_passwd", my_default="admin"))
        parser.add_option(
            FileOnlyOption(
                dest="bin_path",
                type="path",
                my_default="",
                file_exportable=False,
            )
        )
        parser.add_option(FileOnlyOption(dest="csv_internal_sep", my_default=","))
        parser.add_option(
            FileOnlyOption(
                dest="default_productivity_apps",
                type="bool",
                my_default=False,
                file_exportable=False,
            )
        )
        parser.add_option(
            FileOnlyOption(
                dest="registry_lru_size",
                type="int",
                my_default=42,
                file_exportable=False,
            )
        )
        parser.add_option(
            FileOnlyOption(
                dest="registry_idle_timeout",
                type="int",
                my_default=0,
                file_exportable=False,
            )
        )

    def _add_file_only_transfer_options(
        self, parser: optparse.OptionParser, FileOnlyOption: type
    ) -> None:
        parser.add_option(
            FileOnlyOption(
                dest="import_file_maxbytes",
                type="int",
                my_default=10 * 1024 * 1024,
                file_exportable=False,
            )
        )
        parser.add_option(
            FileOnlyOption(
                dest="import_file_timeout",
                type="int",
                my_default=3,
                file_exportable=False,
            )
        )
        parser.add_option(
            FileOnlyOption(
                dest="import_url_regex",
                my_default=r"^(?:http|https)://",
                file_exportable=False,
            )
        )
        parser.add_option(
            FileOnlyOption(
                dest="proxy_access_token", my_default="", file_exportable=False
            )
        )
        parser.add_option(
            FileOnlyOption(
                dest="publisher_warranty_url",
                my_default="http://services.odoo.com/publisher-warranty/",
                file_exportable=False,
            )
        )
        parser.add_option(
            FileOnlyOption(dest="reportgz", action="store_true", my_default=False)
        )
        parser.add_option(
            FileOnlyOption(
                dest="websocket_keep_alive_timeout", type="int", my_default=3600
            )
        )
        parser.add_option(
            FileOnlyOption(dest="websocket_rate_limit_burst", type="int", my_default=10)
        )
        parser.add_option(
            FileOnlyOption(
                dest="websocket_rate_limit_delay", type="float", my_default=0.2
            )
        )

    def _add_file_only_options(
        self, parser: optparse.OptionParser, FileOnlyOption: type
    ) -> None:
        self._add_file_only_registry_options(parser, FileOnlyOption)
        self._add_file_only_transfer_options(parser, FileOnlyOption)

    def _add_common_options(
        self,
        parser: optparse.OptionParser,
        OdooOption: type,
        PosixOnlyOption: type,
    ) -> None:
        group = optparse.OptionGroup(parser, "Common options")
        self._add_config_and_module_options(group)
        self._add_import_and_process_options(group)
        self._add_path_and_load_options(group)
        parser.add_option_group(group)

    def _add_config_and_module_options(self, group: optparse.OptionGroup) -> None:
        group.add_option(
            "-c",
            "--config",
            dest="config",
            type="path",
            file_loadable=False,
            env_name="ODOO_RC",
            help="specify alternate config file",
        )
        group.add_option(
            "-s",
            "--save",
            action="store_true",
            dest="save",
            my_default=False,
            file_loadable=False,
            help="save configuration to ~/.odoorc",
        )
        group.add_option(
            "-i",
            "--init",
            dest="init",
            type="comma",
            metavar="MODULE,...",
            my_default=[],
            file_loadable=False,
            help="install one or more modules (comma-separated list), requires -d",
        )
        group.add_option(
            "-u",
            "--update",
            dest="update",
            type="comma",
            metavar="MODULE,...",
            my_default=[],
            file_loadable=False,
            help='update one or more modules (comma-separated list, use "all" for all modules). Requires -d.',
        )
        group.add_option(
            "--reload-unchanged-data-files",
            dest="skip_unchanged_data_files",
            action="store_false",
            my_default=True,
            help="During module upgrade, reconvert every data file even when "
            "its content is identical to the last successful load. By default "
            "unchanged files are skipped (their records are left as-is), based "
            "on checksums stored in ir_module_module.data_file_checksums; use "
            "this flag (or --reinit) to force a full re-assertion of the data. "
            "Caveat of the default: -u no longer repairs records manually "
            "deleted from the database when their data file is unchanged; use "
            "--reinit (or this flag) to restore them.",
        )
        group.add_option(
            "--upgrade-unchanged-modules",
            dest="skip_unchanged_modules",
            action="store_false",
            my_default=True,
            help="When the upgrade of a module cascades to its dependents "
            "(most notably -u base, which cascades to every installed "
            "module), also mark dependents whose directory content is "
            "identical to their last successful upgrade. By default such "
            "modules are skipped, based on the checksum stored in "
            "ir_module_module.content_checksum; explicitly listed modules "
            "(-u/--reinit) are always processed.",
        )

    def _add_import_and_process_options(self, group: optparse.OptionGroup) -> None:
        group.add_option(
            "--reinit",
            dest="reinit",
            type="comma",
            metavar="MODULE,...",
            my_default=[],
            file_loadable=False,
            help="reinitialize one or more modules (comma-separated list), requires -d",
        )
        group.add_option(
            "--with-demo",
            dest="with_demo",
            action="store_true",
            my_default=False,
            help="install demo data in new databases",
        )
        group.add_option(  # type: ignore[call-overload]
            "--without-demo",
            dest="with_demo",
            type="without_demo",
            metavar="BOOL",
            nargs="?",
            const=True,
            help="don't install demo data in new databases (default)",
        )
        group.add_option(
            "--skip-auto-install",
            dest="skip_auto_install",
            action="store_true",
            my_default=False,
            help="skip the automatic installation of modules marked as auto_install",
        )
        group.add_option(
            "-P",
            "--import-partial",
            dest="import_partial",
            type="path",
            my_default="",
            file_loadable=False,
            help="Use this for big data importation, if it crashes you will be able to continue at the current state. Provide a filename to store intermediate importation states.",
        )
        group.add_option(
            "--pidfile",
            dest="pidfile",
            type="path",
            my_default="",
            help="file where the server pid will be stored",
        )

    def _add_path_and_load_options(self, group: optparse.OptionGroup) -> None:
        group.add_option(
            "--addons-path",
            dest="addons_path",
            type="addons_path",
            metavar="PATH,...",
            my_default=[],
            help="specify additional addons paths (separated by commas).",
        )
        group.add_option(
            "--upgrade-path",
            dest="upgrade_path",
            type="upgrade_path",
            metavar="PATH,...",
            my_default=[],
            help="specify an additional upgrade path.",
        )
        group.add_option(
            "--pre-upgrade-scripts",
            dest="pre_upgrade_scripts",
            type="pre_upgrade_scripts",
            metavar="PATH,...",
            my_default=[],
            help="Run specific upgrade scripts before loading any module when -u is provided.",
        )
        group.add_option(
            "--load",
            dest="server_wide_modules",
            type="comma",
            metavar="MODULE,...",
            my_default=DEFAULT_SERVER_WIDE_MODULES,
            help="Comma-separated list of server-wide modules.",
        )
        group.add_option(
            "-D",
            "--data-dir",
            dest="data_dir",
            type="path",
            help="Directory where to store Odoo data",
        )

    def _add_http_options(
        self,
        parser: optparse.OptionParser,
        OdooOption: type,
        PosixOnlyOption: type,
    ) -> None:
        group = optparse.OptionGroup(parser, "HTTP Service Configuration")
        group.add_option(
            "--http-interface",
            dest="http_interface",
            my_default="0.0.0.0",
            help="Listen interface address for HTTP services.",
        )
        group.add_option(
            "-p",
            "--http-port",
            dest="http_port",
            my_default=8069,
            help="Listen port for the main HTTP service",
            type="int",
            metavar="PORT",
        )
        group.add_option(
            "--gevent-port",
            dest="gevent_port",
            my_default=8072,
            help="Listen port for the evented worker",
            type="int",
            metavar="PORT",
        )
        group.add_option(
            "--no-http",
            dest="http_enable",
            action="store_false",
            my_default=True,
            help="Disable the HTTP and Longpolling services entirely",
        )
        group.add_option(
            "--proxy-mode",
            dest="proxy_mode",
            action="store_true",
            my_default=False,
            help="Activate reverse proxy WSGI wrappers (headers rewriting) "
            "Only enable this when running behind a trusted web proxy!",
        )
        group.add_option(
            "--proxy-hops",
            dest="proxy_hops",
            type="int",
            my_default=1,
            help="How many trusted reverse proxies sit in front of this server "
            "(default 1). Only the last N entries of X-Forwarded-For, -Proto "
            "and -Host are believed, so a value larger than the real chain lets "
            "a client forge its own address. Requires --proxy-mode.",
        )
        group.add_option(
            "--x-sendfile",
            dest="x_sendfile",
            action="store_true",
            my_default=False,
            help="Activate X-Sendfile (apache) and X-Accel-Redirect (nginx) "
            "HTTP response header to delegate the delivery of large "
            "files (assets/attachments) to the web server.",
        )
        parser.add_option_group(group)

    def _add_web_interface_options(
        self,
        parser: optparse.OptionParser,
        OdooOption: type,
        PosixOnlyOption: type,
    ) -> None:
        group = optparse.OptionGroup(parser, "Web interface Configuration")
        group.add_option(
            "--db-filter",
            dest="dbfilter",
            my_default="",
            metavar="REGEXP",
            help="Regular expression for filtering available databases for the "
            "Web UI. The expression can use %d (domain) and %h (host) "
            "placeholders. Without a placeholder it also names the databases "
            "this process serves: cron and job sweeps and XML-RPC/JSON-RPC "
            "calls are refused for any other, as with --database.",
        )
        parser.add_option_group(group)

    def _add_testing_options(
        self,
        parser: optparse.OptionParser,
        OdooOption: type,
        PosixOnlyOption: type,
    ) -> None:
        group = optparse.OptionGroup(parser, "Testing Configuration")
        group.add_option(
            "--test-file",
            dest="test_file",
            type="path",
            my_default="",
            file_loadable=False,
            help="Launch a python test file.",
        )
        group.add_option(
            "--test-enable",
            dest="test_enable",
            action="store_true",
            file_loadable=False,
            help="Enable unit tests. Implies --stop-after-init",
        )
        group.add_option(
            "-t",
            "--test-tags",
            dest="test_tags",
            file_loadable=False,
            help="Comma-separated list of specs to filter which tests to execute. Enable unit tests if set. "
            "A filter spec has the format: [-][tag][/module][:class][.method][[params]] "
            "The '-' specifies if we want to include or exclude tests matching this spec. "
            "The tag will match tags added on a class with a @tagged decorator "
            "(all Test classes have 'standard' and 'at_install' tags "
            "until explicitly removed, see the decorator documentation). "
            "'*' will match all tags. "
            "If tag is omitted on include mode, its value is 'standard'. "
            "If tag is omitted on exclude mode, its value is '*'. "
            "The module, class, and method will respectively match the module name, test class name and test method name. "
            "Example: --test-tags :TestClass.test_func,/test_module,external "
            "It is also possible to provide parameters to a test method that supports them"
            "Example: --test-tags /web.test_js[mail]"
            "If negated, a test-tag with parameter will negate the parameter when passing it to the test"
            "Filtering and executing the tests happens twice: right "
            "after each module installation/update and at the end "
            "of the modules loading. At each stage tests are filtered "
            "by --test-tags specs and additionally by dynamic specs "
            "'at_install' and 'post_install' correspondingly. Implies --stop-after-init",
        )

        group.add_option(
            "--screencasts",
            dest="screencasts",
            type="path",
            my_default="",
            metavar="DIR",
            help="Screencasts will go in DIR/{db_name}/screencasts.",
        )
        temp_tests_dir = str(Path(tempfile.gettempdir(), "odoo_tests"))
        group.add_option(
            "--screenshots",
            dest="screenshots",
            type="path",
            my_default=temp_tests_dir,
            metavar="DIR",
            help="Screenshots will go in DIR/{db_name}/screenshots. Defaults to %s."
            % temp_tests_dir,
        )
        parser.add_option_group(group)

    def _add_logging_destination(self, group: optparse.OptionGroup) -> None:
        group.add_option(
            "--logfile",
            dest="logfile",
            type="path",
            my_default="",
            help="file where the server log will be stored",
        )
        group.add_option(
            "--syslog",
            action="store_true",
            dest="syslog",
            my_default=False,
            help="Send the log to the syslog server",
        )

    def _add_logging_handlers(self, group: optparse.OptionGroup) -> None:
        group.add_option(
            "--log-handler",
            action="append",
            type="comma",
            my_default=[":INFO"],
            metavar="MODULE:LEVEL",
            help="setup a handler at LEVEL for a given MODULE. An empty MODULE indicates the root logger. "
            'This option can be repeated. Example: "odoo.orm:DEBUG" or "odoo.service.http.access:WARNING" (default: ":INFO")',
        )
        group.add_option(
            "--log-web",
            action="append_const",
            dest="log_handler",
            const=("odoo.http:DEBUG",),
            help="shortcut for --log-handler=odoo.http:DEBUG",
        )
        group.add_option(
            "--log-sql",
            action="append_const",
            dest="log_handler",
            const=("odoo.db:DEBUG",),
            help="shortcut for --log-handler=odoo.db:DEBUG",
        )
        group.add_option(
            "--log-db", dest="log_db", help="Logging database", my_default=""
        )
        group.add_option(
            "--log-db-level",
            dest="log_db_level",
            my_default="warning",
            help="Logging database level",
        )
        group.add_option(
            "--log-config",
            dest="log_config",
            type="path",
            my_default="",
            help="JSON logging configuration file, in dictConfig format "
            "(https://docs.python.org/3/library/logging.config.html#logging-config-dictschema).",
        )
        levels = [
            "info",
            "debug_rpc",
            "warn",
            "test",
            "critical",
            "runbot",
            "debug_sql",
            "error",
            "debug",
            "debug_rpc_answer",
            "notset",
        ]
        group.add_option(
            "--log-level",
            dest="log_level",
            type="choice",
            choices=levels,
            my_default="info",
            help="specify the level of the logging. Accepted values: %s." % (levels,),
        )

    def _add_logging_options(
        self,
        parser: optparse.OptionParser,
        OdooOption: type,
        PosixOnlyOption: type,
    ) -> None:
        group = optparse.OptionGroup(parser, "Logging Configuration")
        self._add_logging_destination(group)
        self._add_logging_handlers(group)

        parser.add_option_group(group)

    def _add_smtp_envelope(self, group: optparse.OptionGroup) -> None:
        group.add_option(
            "--email-from",
            dest="email_from",
            my_default="",
            help="specify the SMTP email address for sending email",
        )
        group.add_option(
            "--from-filter",
            dest="from_filter",
            my_default="",
            help="specify for which email address the SMTP configuration can be used",
        )

    def _add_smtp_server(self, group: optparse.OptionGroup) -> None:
        group.add_option(
            "--smtp",
            dest="smtp_server",
            my_default="localhost",
            help="specify the SMTP server for sending email",
        )
        group.add_option(
            "--smtp-port",
            dest="smtp_port",
            my_default=25,
            help="specify the SMTP port",
            type="int",
        )
        group.add_option(  # type: ignore[call-overload]
            "--smtp-ssl",
            dest="smtp_ssl",
            type="smtp_ssl",
            metavar="MODE",
            nargs="?",
            const=True,
            my_default=False,
            help="encrypt SMTP connections; MODE is one of "
            + ", ".join(SMTP_SSL_MODES)
            + " or none. A bare --smtp-ssl (or True) means starttls_strict: "
            "STARTTLS with the server certificate validated",
        )

    def _add_smtp_credentials(self, group: optparse.OptionGroup) -> None:
        group.add_option(
            "--smtp-user",
            dest="smtp_user",
            my_default="",
            help="specify the SMTP username for sending email",
        )
        group.add_option(
            "--smtp-password",
            dest="smtp_password",
            my_default="",
            help="specify the SMTP password for sending email",
        )
        group.add_option(
            "--smtp-timeout",
            dest="smtp_timeout",
            my_default=60,
            help="specify the socket timeout, in seconds, for each SMTP command "
            "(0 disables the timeout)",
            type="int",
        )

    def _add_smtp_tls(self, group: optparse.OptionGroup) -> None:
        group.add_option(
            "--smtp-helo-name",
            dest="smtp_helo_name",
            my_default="",
            help="specify the hostname announced in the SMTP HELO/EHLO command; "
            "defaults to the machine's FQDN, which resolves to a bare IP literal "
            "on hosts without one and is rejected by strict MTAs",
        )
        group.add_option(
            "--smtp-ssl-certificate-filename",
            dest="smtp_ssl_certificate_filename",
            type="path",
            my_default="",
            help="specify the SSL certificate used for authentication",
        )
        group.add_option(
            "--smtp-ssl-private-key-filename",
            dest="smtp_ssl_private_key_filename",
            type="path",
            my_default="",
            help="specify the SSL private key used for authentication",
        )

    def _add_smtp_options(
        self,
        parser: optparse.OptionParser,
        OdooOption: type,
        PosixOnlyOption: type,
    ) -> None:
        group = optparse.OptionGroup(parser, "SMTP Configuration")
        self._add_smtp_envelope(group)
        self._add_smtp_server(group)
        self._add_smtp_credentials(group)
        self._add_smtp_tls(group)

        parser.add_option_group(group)

    def _add_database_options(
        self,
        parser: optparse.OptionParser,
        OdooOption: type,
        PosixOnlyOption: type,
    ) -> None:
        group = optparse.OptionGroup(parser, "Database related options")
        self._add_db_endpoint_options(group)
        self._add_db_replica_and_tls_options(group)
        self._add_db_pool_sizing_options(group)
        self._add_db_connection_lifecycle_options(group)
        self._add_db_session_and_health_options(group)
        parser.add_option_group(group)

    def _add_db_endpoint_options(self, group: optparse.OptionGroup) -> None:
        group.add_option(
            "-d",
            "--database",
            dest="db_name",
            type="comma",
            metavar="DATABASE,...",
            my_default=[],
            env_name="PGDATABASE",
            help="database(s) used when installing or updating modules.",
        )
        group.add_option(
            "-r",
            "--db_user",
            dest="db_user",
            my_default="",
            env_name="PGUSER",
            help="specify the database user name",
        )
        group.add_option(
            "-w",
            "--db_password",
            dest="db_password",
            my_default="",
            env_name="PGPASSWORD",
            help="specify the database password",
        )
        group.add_option(
            "--pg_path",
            dest="pg_path",
            type="path",
            my_default="",
            env_name="PGPATH",
            help="specify the pg executable path",
        )
        group.add_option(
            "--db_host",
            dest="db_host",
            my_default="",
            env_name="PGHOST",
            help="specify the database host",
        )
        group.add_option(
            "--db_replica_host",
            dest="db_replica_host",
            my_default=None,
            env_name="PGHOST_REPLICA",
            help="specify the replica host",
        )
        group.add_option(
            "--db_port",
            dest="db_port",
            my_default=None,
            env_name="PGPORT",
            help="specify the database port",
            type="int",
        )
        group.add_option(
            "--db_replica_port",
            dest="db_replica_port",
            my_default=None,
            env_name="PGPORT_REPLICA",
            help="specify the replica port",
            type="int",
        )

    def _add_db_replica_and_tls_options(self, group: optparse.OptionGroup) -> None:
        group.add_option(
            "--db_replica_max_lag",
            dest="db_replica_max_lag",
            type="float",
            my_default=0.0,
            env_name="ODOO_DB_REPLICA_MAX_LAG",
            help="seconds of apply lag above which read-only requests are sent "
            "to the primary instead of the replica. 0 (default) never checks, "
            "so a replica serves reads however far behind it is. The lag is "
            "sampled at most every max(1, value/4) seconds and the verdict "
            "cached, so an enabled ceiling costs one extra query per sample, "
            "not per request. Bounds apply lag only: WAL the standby has not "
            "received is indistinguishable from an idle primary without asking "
            "the primary, which would defeat the point of reading elsewhere",
        )
        group.add_option(
            "--db_replica_user",
            dest="db_replica_user",
            my_default=None,
            env_name="PGUSER_REPLICA",
            help="specify the replica database user, when it differs from the "
            "primary's. Empty (default) reuses db_user",
        )
        group.add_option(
            "--db_replica_password",
            dest="db_replica_password",
            my_default=None,
            env_name="PGPASSWORD_REPLICA",
            cli_loadable=False,
            help="specify the replica database password, when it differs from "
            "the primary's. Empty (default) reuses db_password",
        )
        group.add_option(
            "--db_sslmode",
            dest="db_sslmode",
            type="choice",
            my_default="prefer",
            env_name="PGSSLMODE",
            choices=[
                "disable",
                "allow",
                "prefer",
                "require",
                "verify-ca",
                "verify-full",
            ],
            help="specify the database ssl connection mode (see PostgreSQL documentation)",
        )
        group.add_option(
            "--db_replica_sslmode",
            dest="db_replica_sslmode",
            type="choice",
            my_default=None,
            env_name="PGSSLMODE_REPLICA",
            choices=[
                "disable",
                "allow",
                "prefer",
                "require",
                "verify-ca",
                "verify-full",
            ],
            help="specify the replica ssl connection mode, when it differs from "
            "the primary's. Empty (default) reuses db_sslmode",
        )
        group.add_option(
            "--db_app_name",
            dest="db_app_name",
            my_default="odoo-{pid}",
            env_name="PGAPPNAME",
            help="specify the application name in the database, {pid} is substituted by the process pid",
        )

    def _add_db_pool_sizing_options(self, group: optparse.OptionGroup) -> None:
        group.add_option(
            "--db_maxconn",
            dest="db_maxconn",
            type="int",
            my_default=64,
            help="specify the maximum number of physical connections this "
            "process holds against a PostgreSQL server: checked out at once "
            "through one budget, and idle ones across all its databases, which "
            "are trimmed on return past this ceiling. The read/write and "
            "read-only pools share one budget while they target the same server "
            "(no replica, test_enable, dev_mode=replica), and get one each once "
            "db_replica_host resolves elsewhere — so this is the number to size "
            "each server's max_connections against, multiplied by the worker "
            "count. See db_maxconn_replica to size the replica independently",
        )
        group.add_option(
            "--db_maxconn_replica",
            dest="db_maxconn_replica",
            type="int",
            my_default=None,
            env_name="ODOO_DB_MAXCONN_REPLICA",
            help="specify the maximum number of physical connections checked "
            "out at once against the read replica. Empty (default) gives it the "
            "same ceiling as db_maxconn. Ignored unless db_replica_host resolves "
            "to a different host/port than db_host: when the read-only pool "
            "targets the primary, both pools share that server's single budget",
        )
        group.add_option(
            "--db_maxconn_gevent",
            dest="db_maxconn_gevent",
            type="int",
            my_default=None,
            help="specify the maximum number of physical connections to PostgreSQL specifically for the evented worker",
        )
        group.add_option(
            "--db_minconn",
            dest="db_minconn",
            type="int",
            my_default=0,
            help="specify the minimum number of physical connections kept warm "
            "per-database (0 = open lazily on demand). Raise it on single-database "
            "OLTP deployments to remove first-request cold-start latency; keep 0 on "
            "multi-tenant hosts: the db_maxconn ceiling never trims a pool below "
            "it, so databases x db_minconn above db_maxconn holds that many",
        )
        group.add_option(
            "--db-template",
            dest="db_template",
            my_default="template0",
            env_name="PGDATABASE_TEMPLATE",
            help="specify a custom database template to create a new database",
        )

    def _add_db_connection_lifecycle_options(self, group: optparse.OptionGroup) -> None:
        group.add_option(
            "--db_borrow_timeout",
            dest="db_borrow_timeout",
            type="float",
            my_default=30.0,
            help="wall-clock seconds one connection checkout (borrow) may wait "
            "before failing, shared between the pool-semaphore wait and the "
            "PostgreSQL connect. Raise on high-latency links or saturated pools "
            "(default 30)",
        )
        group.add_option(
            "--db_conn_max_lifetime",
            dest="db_conn_max_lifetime",
            type="int",
            my_default=3600,
            help="seconds before a pooled physical connection is recycled, "
            "discarding its prepared-statement cache (default 3600 = 1h)",
        )
        group.add_option(
            "--db_conn_max_idle",
            dest="db_conn_max_idle",
            type="int",
            my_default=600,
            help="seconds an unused pooled connection is kept open before being "
            "closed (default 600 = 10min). The server-side idle_session_timeout "
            "each pooled connection gets is derived from this (1.5x, min 15min) "
            "so the server never kills a connection the pool still considers warm",
        )
        group.add_option(
            "--db_pool_reap_idle",
            dest="db_pool_reap_idle",
            type="float",
            my_default=300.0,
            env_name="ODOO_DB_POOL_REAP_IDLE",
            help="seconds a per-database pool may sit idle (nothing checked out) "
            "before it is reaped, freeing its worker threads on hosts that serve "
            "many databases over time. When below db_conn_max_idle (default 600) "
            "a quiet pool is reaped — discarding its still-warm idle connections "
            "— before they reach their own idle timeout, so the next access to "
            "that database pays a reconnect; raise to db_conn_max_idle or above "
            "to let connections idle out first. Single-database hosts are "
            "unaffected. 0 disables reaping (default 300)",
        )
        group.add_option(
            "--db_pool_workers",
            dest="db_pool_workers",
            type="int",
            my_default=1,
            env_name="ODOO_DB_POOL_WORKERS",
            help="psycopg maintenance worker threads per DATABASE pool. Each "
            "pool also runs one scheduler thread, so the thread cost of a "
            "database is this plus one — measured at the psycopg default of 3, "
            "40 databases in one process held 161 threads. The workers only run "
            "AddConnection and ReturnConnection tasks, which are already off the "
            "request path, so 1 is enough unless a single database sustains "
            "enough concurrent returns to queue behind one reset round trip "
            "(default 1)",
        )
        group.add_option(
            "--db_discard_on_return",
            dest="db_discard_on_return",
            type="bool",
            my_default=False,
            env_name="ODOO_DB_DISCARD_ON_RETURN",
            help="issue DISCARD ALL when a connection returns to the pool, fully "
            "isolating session state (temp tables, GUCs, LISTEN, advisory locks) "
            "between borrowers at the cost of the prepared-statement cache. Enable "
            "on multi-tenant hosts needing hard isolation (default off). Either way "
            "a session reset costs one round-trip per transaction (measured ~29us "
            "over a unix socket, ~25%% of a bare cursor open/query/commit/close "
            "cycle; one network RTT elsewhere) — the price of not leaking session "
            "state between borrowers",
        )

    def _add_db_session_and_health_options(self, group: optparse.OptionGroup) -> None:
        group.add_option(
            "--db_session_gucs",
            dest="db_session_gucs",
            my_default="jit=off,work_mem=16MB",
            env_name="ODOO_DB_SESSION_GUCS",
            help="comma-separated GUC=value pairs applied to every pooled "
            "connection via the libpq options string. A GUC already set by the "
            "operator (explicit options kwarg, URI ?options=, or PGOPTIONS) is "
            "left alone, so this sets defaults rather than overriding "
            "deployment choices. Values cannot contain a comma; set such GUCs "
            "through PGOPTIONS instead. Set empty to apply none",
        )
        group.add_option(
            "--db_leak_detection",
            dest="db_leak_detection",
            type="float",
            my_default=0.0,
            env_name="ODOO_DB_LEAK_DETECTION",
            help="seconds a connection may stay checked out before the pool "
            "logs it as a suspected leak. 0 (default) never warns. Which thread "
            "holds each connection and where it was borrowed are recorded "
            "either way — they cost less than the tracking itself and are what "
            "let a db_maxconn exhaustion name its culprits — so this sets only "
            "when to complain. Set to a few minutes where cursors are suspected "
            "of outliving their request",
        )
        group.add_option(
            "--db_healthcheck_grace",
            dest="db_healthcheck_grace",
            type="float",
            my_default=1.0,
            env_name="ODOO_DB_HEALTHCHECK_GRACE",
            help="seconds a pooled connection released this recently skips the "
            "liveness probe on the next borrow. The probe is a server round-trip "
            "on every checkout; a connection released moments ago was provably "
            "alive then. Raise on low-traffic multi-tenant hosts, where nearly "
            "every borrow pays it. A connection that died within the window is "
            "replaced when the transaction's first statement fails on it; a "
            "later statement in that transaction fails. 0 probes every borrow "
            "(default 1.0)",
        )
        group.add_option(
            "--db_idle_in_transaction_timeout",
            dest="db_idle_in_transaction_timeout",
            type="float",
            my_default=0.0,
            env_name="ODOO_DB_IDLE_IN_TRANSACTION_TIMEOUT",
            help="seconds a pooled connection may sit idle inside an open "
            "transaction before the server ends it "
            "(idle_in_transaction_session_timeout, set per connection at "
            "connect). A cursor forgotten inside a transaction holds locks, a "
            "budget permit and a backend until then; the leak detector only "
            "reports it. 0 (default) leaves the server setting in force",
        )
        group.add_option(
            "--db_replica_write_pin",
            dest="db_replica_write_pin",
            type="float",
            my_default=2.0,
            env_name="ODOO_DB_REPLICA_WRITE_PIN",
            help="seconds a session's read-only requests stay on the primary "
            "after one of its transactions wrote, so a client reads its own "
            "writes rather than a replica that has not applied them yet. Only "
            "transactions that assigned a transaction id count (a cheap "
            "server-side check at commit). 0 disables pinning (default 2.0)",
        )

    def _add_i18n_options(
        self,
        parser: optparse.OptionParser,
        OdooOption: type,
        PosixOnlyOption: type,
    ) -> None:
        group = optparse.OptionGroup(
            parser,
            "Internationalisation options",
            "Use these options to translate Odoo to another language. "
            "See i18n section of the user manual. Option '-d' is mandatory. "
            "Option '-l' is mandatory in case of importation",
        )
        group.add_option(
            "--load-language",
            dest="load_language",
            file_exportable=False,
            help="specifies the languages for the translations you want to be loaded",
        )
        group.add_option(
            "--i18n-overwrite",
            dest="overwrite_existing_translations",
            action="store_true",
            my_default=False,
            file_exportable=False,
            help="overwrites existing translation terms on updating a module.",
        )
        parser.add_option_group(group)

    def _add_security_options(
        self,
        parser: optparse.OptionParser,
        OdooOption: type,
        PosixOnlyOption: type,
    ) -> None:
        group = optparse.OptionGroup(parser, "Security-related options")
        group.add_option(
            "--no-database-list",
            action="store_false",
            dest="list_db",
            my_default=True,
            help="Disable the ability to obtain or view the list of databases. "
            "Also disable access to the database manager and selector, "
            "so be sure to set a proper --database parameter first",
        )
        parser.add_option_group(group)

    def _add_advanced_dev(self, group: optparse.OptionGroup) -> None:
        group.add_option(
            "--dev",
            dest="dev_mode",
            type="comma",
            metavar="FEATURE,...",
            my_default=[],
            file_exportable=False,
            env_name="ODOO_DEV",
            help="Enable developer features (comma-separated list, use   "
            '"all" for access,assets,reload,qweb,xml). Features:     '
            "- access: log the traceback of access errors           "
            "- assets: watch asset sources, drop the assets cache on "
            "  change (same live-reload as xml, but cached)         "
            "- qweb: log the compiled xml with qweb errors          "
            "- reload: restart server on change in the source code  "
            "- replica: simulate a deployment with readonly replica "
            "- werkzeug: open a html debugger on http request error "
            "- xml: read views from the source code, and not the db ",
        )
        group.add_option(
            "--stop-after-init",
            action="store_true",
            dest="stop_after_init",
            my_default=False,
            file_exportable=False,
            file_loadable=False,
            help="stop the server after its initialization",
        )

    def _add_advanced_limits(self, group: optparse.OptionGroup) -> None:
        group.add_option(
            "--osv-memory-count-limit",
            dest="osv_memory_count_limit",
            my_default=0,
            help="Force a limit on the maximum number of records kept in the virtual "
            "osv_memory tables. By default there is no limit.",
            type="int",
        )
        group.add_option(
            "--transient-age-limit",
            dest="transient_age_limit",
            my_default=1.0,
            help="Time limit (decimal value in hours) records created with a "
            "TransientModel (mostly wizard) are kept in the database. Default to 1 hour.",
            type="float",
        )

    def _add_advanced_workers(self, group: optparse.OptionGroup) -> None:
        group.add_option(
            "--max-cron-threads",
            dest="max_cron_threads",
            my_default=2,
            help="Maximum number of threads processing concurrently cron jobs (default 2).",
            type="int",
        )
        group.add_option(
            "--limit-time-worker-cron",
            dest="limit_time_worker_cron",
            my_default=0,
            help="Maximum time a cron thread/worker stays alive before it is restarted. "
            "Set to 0 to disable. (default: 0)",
            type="int",
        )
        group.add_option(
            "--limit-time-worker-job",
            dest="limit_time_worker_job",
            my_default=-1,
            help="Maximum time a job thread/worker stays alive before it is "
            "restarted. Set to 0 to disable, -1 to follow "
            "--limit-time-worker-cron. (default: -1)",
            type="int",
        )
        group.add_option(
            "--job-workers",
            dest="job_workers",
            my_default=1,
            help="Number of background job queue (ir.job) workers — processes in "
            "prefork mode, threads in threaded mode. Set to 0 to disable job "
            "processing on this instance. (default 1)",
            type="int",
        )

    def _add_advanced_locale(self, group: optparse.OptionGroup) -> None:
        group.add_option(
            "--unaccent",
            dest="unaccent",
            my_default=False,
            action="store_true",
            help="Try to enable the unaccent extension when creating new databases.",
        )
        group.add_option(
            "--geoip-city-db",
            "--geoip-db",
            dest="geoip_city_db",
            type="path",
            my_default="/usr/share/GeoIP/GeoLite2-City.mmdb",
            help="Absolute path to the GeoIP City database file.",
        )
        group.add_option(
            "--geoip-country-db",
            dest="geoip_country_db",
            type="path",
            my_default="/usr/share/GeoIP/GeoLite2-Country.mmdb",
            help="Absolute path to the GeoIP Country database file.",
        )
        group.add_option(
            "--http-session-store",
            dest="http_session_store",
            my_default="filesystem",
            metavar="BACKEND",
            help="Where HTTP sessions live: filesystem (default, under data_dir/"
            "sessions), postgres (the http_session table of --http-session-db, "
            "shared by every host), or memory (this process only).",
        )
        group.add_option(
            "--http-session-db",
            dest="http_session_db",
            my_default="",
            metavar="DBNAME",
            help="The database holding the http_session table when "
            "--http-session-store=postgres.",
        )

    def _add_advanced_options(
        self,
        parser: optparse.OptionParser,
        OdooOption: type,
        PosixOnlyOption: type,
    ) -> None:
        group = optparse.OptionGroup(parser, "Advanced options")
        self._add_advanced_dev(group)
        self._add_advanced_limits(group)
        self._add_advanced_workers(group)
        self._add_advanced_locale(group)

        parser.add_option_group(group)

    def _add_multiprocessing_memory(
        self, group: optparse.OptionGroup, PosixOnlyOption: type
    ) -> None:
        group.add_option(
            "--limit-memory-soft",
            dest="limit_memory_soft",
            my_default=2048 * 1024 * 1024,
            help="Maximum allowed virtual memory per worker (in bytes), when reached the worker be "
            "reset after the current request (default 2048MiB).",
            type="int",
        )
        group.add_option(
            PosixOnlyOption(
                "--limit-memory-soft-gevent",
                dest="limit_memory_soft_gevent",
                my_default=None,
                help="Maximum allowed virtual memory per evented worker (in bytes), when reached the worker will be "
                "reset after the current request. Defaults to `--limit-memory-soft`.",
                type="int",
            )
        )
        group.add_option(
            PosixOnlyOption(
                "--limit-memory-hard",
                dest="limit_memory_hard",
                my_default=2560 * 1024 * 1024,
                help="Deprecated/not enforced in-process (default 2560MiB): the "
                "in-process RLIMIT_AS was removed because the allocator/gevent "
                "reserve multi-GB of never-resident virtual space. Set the hard "
                "cap with a cgroup v2 limit on the systemd unit (MemoryMax= + "
                "MemorySwapMax=0) instead; see --limit-memory-soft for recycling.",
                type="int",
            )
        )
        group.add_option(
            PosixOnlyOption(
                "--limit-memory-hard-gevent",
                dest="limit_memory_hard_gevent",
                my_default=None,
                help="Deprecated/not enforced in-process (see --limit-memory-hard "
                "for the rationale and the cgroup v2 alternative). Defaults to "
                "`--limit-memory-hard`.",
                type="int",
            )
        )
        group.add_option(
            PosixOnlyOption(
                "--limit-time-cpu",
                dest="limit_time_cpu",
                my_default=60,
                help="Maximum allowed CPU time per request (default 60). "
                "Enforced by RLIMIT_CPU inside each prefork worker, so it has "
                "no effect with --workers=0: a threaded server bounds a request "
                "with --limit-time-real instead.",
                type="int",
            )
        )

    def _add_multiprocessing_time(
        self, group: optparse.OptionGroup, PosixOnlyOption: type
    ) -> None:
        group.add_option(
            "--limit-time-real",
            dest="limit_time_real",
            my_default=120,
            help="Maximum allowed Real time per request (default 120).",
            type="int",
        )
        group.add_option(
            "--limit-time-real-cron",
            dest="limit_time_real_cron",
            my_default=-1,
            help="Maximum allowed Real time per cron job. (default: --limit-time-real). "
            "Set to 0 for no limit. ",
            type="int",
        )
        group.add_option(
            "--limit-time-real-job",
            dest="limit_time_real_job",
            my_default=-1,
            help="Maximum allowed Real time per background job. Set to 0 for no "
            "limit, -1 to follow --limit-time-real-cron. (default: -1)",
            type="int",
        )
        group.add_option(
            PosixOnlyOption(
                "--limit-request",
                dest="limit_request",
                my_default=2**16,
                help="Maximum number of request to be processed per worker (default 65536).",
                type="int",
            )
        )

    def _add_multiprocessing_options(
        self,
        parser: optparse.OptionParser,
        OdooOption: type,
        PosixOnlyOption: type,
    ) -> None:
        group = optparse.OptionGroup(parser, "Multiprocessing options")
        group.add_option(
            PosixOnlyOption(
                "--workers",
                dest="workers",
                my_default=0,
                help="Specify the number of workers, 0 disable prefork mode.",
                type="int",
            )
        )
        self._add_multiprocessing_memory(group, PosixOnlyOption)
        self._add_multiprocessing_time(group, PosixOnlyOption)

        parser.add_option_group(group)

    def _load_default_options(self) -> None:
        self._default_options.clear()
        self._default_options.update(
            {
                option_name: option.my_default
                for option_name, option in self.options_index.items()
            }
        )

        self._default_options["data_dir"] = (
            appdirs.user_data_dir(release.product_name, release.author)
            if Path("~").expanduser().is_dir()
            else (
                appdirs.site_data_dir(release.product_name, release.author)
                if sys.platform in ["win32", "darwin"]
                else f"/var/lib/{release.product_name}"
            )
        )

        if os.name == "nt":
            rcfilepath = str(Path(str(Path(sys.argv[0]).resolve().parent), "odoo.conf"))
        elif Path(rcfilepath := str(Path("~/.odoorc").expanduser())).is_file():
            pass
        elif Path(
            rcfilepath := str(Path("~/.openerp_serverrc").expanduser())
        ).is_file():
            self._warn(
                "Since ages ago, the ~/.openerp_serverrc file has been replaced by ~/.odoorc",
                DeprecationWarning,
            )
        else:
            rcfilepath = "~/.odoorc"
        self._default_options["config"] = self._normalize(rcfilepath)
        _debug.lifecycle(
            "config.defaults_loaded",
            options=len(self._default_options),
            data_dir=self._default_options["data_dir"],
            rcfile=self._default_options["config"],
        )

    _log_entries: list[tuple[int, str, tuple, dict]] = []
    _warn_entries: list[tuple[str, tuple, dict]] = []

    @classmethod
    def _log(cls, loglevel: int, message: str, *args: Any, **kwargs: Any) -> None:
        cls._log_entries.append((loglevel, message, args, kwargs))

    @classmethod
    def _warn(cls, message: str, *args: Any, **kwargs: Any) -> None:
        cls._warn_entries.append((message, args, kwargs))

    @classmethod
    def _flush_log_and_warn_entries(cls) -> None:
        for loglevel, message, args, kwargs in cls._log_entries:
            _dangerous_logger.log(loglevel, message, *args, **kwargs)
        cls._log_entries.clear()
        cls._log = _dangerous_logger.log  # type: ignore[method-assign, assignment]

        for message, args, kwargs in cls._warn_entries:
            kwargs.setdefault("stacklevel", 1)
            warnings.warn(message, *args, **kwargs)
        cls._warn_entries.clear()
        cls._warn = warnings.warn  # type: ignore[method-assign, assignment]

    def parse_config(
        self,
        args: list[str] | None = None,
        *,
        setup_logging: bool | None = None,
    ) -> optparse.Values:
        from odoo import modules
        from odoo.logutils import init_logger

        opt = self._parse_config(args)
        if setup_logging is not False:
            init_logger()
            if setup_logging is None:
                warnings.warn(
                    "As of Odoo 18, it's recommended to specify whether"
                    " you want Odoo to setup its own logging (or want to"
                    " handle it yourself)",
                    category=PendingDeprecationWarning,
                    stacklevel=2,
                )
        self._warn_deprecated_options()
        self._flush_log_and_warn_entries()
        modules.module.initialize_sys_path()
        _debug.lifecycle(
            "config.parse_config",
            setup_logging=setup_logging,
            addons_path=len(self["addons_path"]),
            databases=self["db_name"],
            init=len(self["init"]),
            update=len(self["update"]),
            workers=self["workers"],
            test_enable=self["test_enable"],
        )
        return opt

    def _parse_config(self, args: list[str] | None = None) -> optparse.Values:
        args = list(args) if args else []
        for arg_no, arg in enumerate(args):
            if option := self.optional_options.get(arg):
                if arg_no == len(args) - 1 or args[arg_no + 1].startswith("-"):
                    args[arg_no] += "=" + self.format(option.dest or "", option.const)
                    self._log(logging.DEBUG, "changed %s for %s", arg, args[arg_no])
                    _debug.logic(
                        "config.optional_arg_defaulted", arg=arg, value=args[arg_no]
                    )

        opt, unknown_args = self.parser.parse_args(args)
        _debug.pipeline(
            "config.cli_parsed",
            args=len(args),
            unknown=len(unknown_args),
            save=bool(opt.save),
        )
        if unknown_args:
            self.parser.error(f"unrecognized parameters: {' '.join(unknown_args)}")

        if not opt.save and opt.config and not os.access(opt.config, os.R_OK):
            self.parser.error(
                f"the config file {opt.config!r} selected with -c/--config doesn't exist or is not readable, use -s/--save if you want to generate it"
            )

        for option_name in list(vars(opt).keys()):
            if not self.options_index[option_name].cli_loadable:
                _debug.logic("config.cli_option_dropped", option=option_name)
                delattr(opt, option_name)

        self._load_env_options()
        self._load_cli_options(opt)
        self._check_config_file_is_readable()
        self._load_file_options(self["config"])
        self._postprocess_options()
        _debug.lifecycle(
            "config.parsed",
            rcfile=self["config"],
            env_options=len(self._env_options),
            cli_options=len(self._cli_options),
            file_options=len(self._file_options),
            save=bool(opt.save),
        )

        if opt.save:
            self.save()

        return opt

    def _check_config_file_is_readable(self) -> None:
        if not any(
            "config" in source
            for source in (
                self._override_options,
                self._runtime_options,
                self._cli_options,
                self._env_options,
            )
        ):
            return
        rcfile = self["config"]
        if not rcfile or self["save"]:
            return
        if not Path(rcfile).exists():
            self.parser.error(f"the configuration file {rcfile!r} does not exist")
        if not os.access(rcfile, os.R_OK):
            self.parser.error(
                f"the configuration file {rcfile!r} exists but could not be "
                f"read; check its permissions"
            )

    def _load_env_options(self) -> None:
        self._env_options.clear()
        environ = os.environ
        for option_name, option in self.options_index.items():
            env_name = option.env_name
            if env_name and env_name in environ:
                try:
                    self._env_options[option_name] = self.parse(
                        option_name, environ[env_name]
                    )
                except (ValueError, optparse.OptionValueError) as exc:
                    raise ValueError(
                        f"Invalid value for environment variable {env_name} "
                        f"(option {option_name!r}): {exc}"
                    ) from exc
        if environ.get("OPENERP_SERVER"):
            self._warn(
                "Since ages ago, the OPENERP_SERVER environment variable has been replaced by ODOO_RC",
                DeprecationWarning,
            )
        _debug.lifecycle(
            "config.env_options_loaded",
            options=sorted(self._env_options),
            legacy_openerp_server="OPENERP_SERVER" in environ,
        )

    def _load_cli_options(self, opt: optparse.Values) -> None:
        addons_path = self._cli_options.pop("addons_path", None)
        self._cli_options.clear()
        if addons_path is not None:
            self._cli_options["addons_path"] = addons_path

        keys = [
            option_name
            for option_name, option in self.options_index.items()
            if option.cli_loadable
            if option.action != "append"
        ]

        for arg in keys:
            value = getattr(opt, arg, None)
            if value is None:
                continue
            self._cli_options[arg] = None if value is UNSET else value

        if opt.log_handler:
            self._cli_options["log_handler"] = [
                handler for comma in opt.log_handler for handler in comma
            ]
        _debug.lifecycle(
            "config.cli_options_loaded",
            options=sorted(self._cli_options),
            addons_path_kept=addons_path is not None,
        )

    def _postprocess_exclusive_options(self) -> None:
        if self.options["syslog"] and self.options["logfile"]:
            self.parser.error("the syslog and logfile options are exclusive")

        if self.options["overwrite_existing_translations"] and not self["update"]:
            self.parser.error(
                "the i18n-overwrite option cannot be used without the update option"
            )

        if len(self["db_name"]) > 1 and (self["init"] or self["update"]):
            self.parser.error(
                "Cannot use -i/--init or -u/--update with multiple databases in the -d/--database/db_name"
            )

    def _postprocess_server_wide_modules(self) -> None:
        if not self["server_wide_modules"]:
            self._runtime_options["server_wide_modules"] = DEFAULT_SERVER_WIDE_MODULES
        missing = [
            mod
            for mod in REQUIRED_SERVER_WIDE_MODULES
            if mod not in self["server_wide_modules"]
        ]
        if missing:
            for mod in missing:
                self._log(
                    logging.INFO,
                    "adding missing %r to %s",
                    mod,
                    self.options_index["server_wide_modules"],
                )
            self._runtime_options["server_wide_modules"] = (
                missing + self["server_wide_modules"]
            )
        _debug.logic(
            "config.server_wide_modules",
            modules=self["server_wide_modules"],
            defaulted="server_wide_modules" in self._runtime_options and not missing,
            added=missing,
        )

    def _postprocess_log_handler(self) -> None:
        try:
            self._runtime_options["log_handler"] = list(
                _deduplicate_loggers(
                    [
                        *self._default_options.get("log_handler", []),
                        *self._file_options.get("log_handler", []),
                        *self._env_options.get("log_handler", []),
                        *self._cli_options.get("log_handler", []),
                    ]
                )
            )
        except ValueError as exc:
            self.parser.error(str(exc))

    def _postprocess_init_update(self) -> None:
        init_modules = self["init"]
        if "all" in init_modules:
            self._warn(
                "the 'all' pseudo-module is only supported by --update (-u), not "
                "--init (-i); it has been ignored — list modules to install "
                "explicitly."
            )
            init_modules = [m for m in init_modules if m != "all"]
        self._runtime_options["init"] = dict.fromkeys(init_modules, True)
        self._runtime_options["update"] = (
            {"base": True}
            if "all" in self["update"]
            else dict.fromkeys(self["update"], True)
        )
        _debug.logic(
            "config.init_update",
            init=sorted(self._runtime_options["init"]),
            update=sorted(self._runtime_options["update"]),
            init_all_dropped="all" in self["init"],
            update_all="all" in self["update"],
        )

    def _postprocess_dev_mode(self) -> None:
        if self["db_replica_host"] == "":
            self._runtime_options["db_replica_host"] = None
            if "replica" not in self["dev_mode"]:
                self._warn(
                    (
                        "Since 19.0, an empty {replica_host} was the 18.0 "
                        "way to open a replica connection on the same "
                        "server as {db_host}, for development/testing "
                        "purpose, the feature now exists as {dev}=replica"
                    ).format(
                        replica_host=self.options_index["db_replica_host"],
                        db_host=self.options_index["db_host"],
                        dev=self.options_index["dev_mode"],
                    ),
                    DeprecationWarning,
                )
                self._runtime_options["dev_mode"] = self["dev_mode"] + ["replica"]
                _debug.logic("config.dev_mode.replica_inferred_from_empty_host")

        if "all" in self["dev_mode"]:
            self._runtime_options["dev_mode"] = self["dev_mode"] + ALL_DEV_MODE
        _debug.logic(
            "config.dev_mode",
            modes=self["dev_mode"],
            replica_host=self["db_replica_host"],
        )

    def _postprocess_test_file(self) -> None:
        test_file = self["test_file"]
        if not test_file:
            return
        if not Path(test_file).is_file():
            self._log(logging.WARNING, f"test file {test_file!r} cannot be found")
        elif not test_file.endswith(".py"):
            self._log(logging.WARNING, f"test file {test_file!r} is not a python file")
        else:
            self._log(logging.INFO, "Transforming --test-file into --test-tags")
            test_tags = [t for t in (self["test_tags"] or "").split(",") if t]
            test_tags.append(str(Path(self["test_file"]).resolve()))
            self._runtime_options["test_tags"] = ",".join(test_tags)
            self._runtime_options["test_enable"] = True
            _debug.logic("config.test_file_as_tag", file=test_file, tags=len(test_tags))

    def _postprocess_test_options(self) -> None:
        self._postprocess_test_file()
        if self["test_enable"] and not self["test_tags"]:
            self._runtime_options["test_tags"] = "+standard"
        self._runtime_options["test_enable"] = bool(self["test_tags"])
        if self._runtime_options["test_enable"]:
            self._runtime_options["stop_after_init"] = True
            if not self["db_name"]:
                self._log(
                    logging.WARNING,
                    "Empty %s, tests won't run",
                    self.options_index["db_name"],
                )
        _debug.logic(
            "config.test_options",
            enabled=self._runtime_options["test_enable"],
            tags=self["test_tags"],
            databases=len(self["db_name"]),
        )

    def _postprocess_options(self) -> None:
        self._runtime_options.clear()
        self._postprocess_exclusive_options()
        self._postprocess_server_wide_modules()
        self._postprocess_log_handler()
        self._postprocess_init_update()
        self._postprocess_dev_mode()
        self._postprocess_test_options()

    def _warn_deprecated_options(self) -> None:
        if self["http_enable"] and not self.http_socket_activation:
            for map_ in self.options.maps:
                if "http_interface" in map_:
                    if map_ is self._file_options and map_["http_interface"] == "":
                        del map_["http_interface"]
                    elif map_ is self._default_options:
                        self._log(
                            logging.WARNING,
                            "missing %s, using 0.0.0.0 by default, will change to 127.0.0.1 in 20.0",
                            self.options_index["http_interface"],
                        )
                    else:
                        break

        for old_option_name, new_option_name in self.aliases.items():
            for source_name, deprecated_value in self._get_sources(
                old_option_name
            ).items():
                if deprecated_value is EMPTY:
                    continue
                default_value = self._default_options[new_option_name]
                current_value = self[new_option_name]

                _debug.logic(
                    "config.deprecated_alias",
                    old=old_option_name,
                    new=new_option_name,
                    source=source_name,
                    redundant=deprecated_value in (current_value, default_value),
                    applied=current_value == default_value,
                )
                if deprecated_value in (current_value, default_value):
                    self._log(
                        logging.INFO,
                        f"The {old_option_name!r} option found in the "
                        f"{source_name} is a deprecated alias to "
                        f"{new_option_name!r}. The configuration value "
                        "is the same as the default value, it can "
                        "safely be removed.",
                    )
                elif current_value == default_value:
                    self._runtime_options[new_option_name] = self.parse(
                        new_option_name, deprecated_value
                    )
                    self._warn(
                        f"The {old_option_name!r} option found in the "
                        f"{source_name} is a deprecated alias to "
                        f"{new_option_name!r}, please use the latter.",
                        DeprecationWarning,
                    )
                else:
                    self.parser.error(
                        f"The two options {old_option_name!r} "
                        f"(found in the {source_name} but deprecated) "
                        f"and {new_option_name!r} are set to different "
                        "values. Please remove the first one and make "
                        "sure the second is correct."
                    )

    @classmethod
    def _is_addons_path(cls, path: str) -> bool:
        for modpath in Path(path).iterdir():

            def hasfile(filename, _mp=modpath):
                return Path(_mp, filename).is_file()

            if hasfile("__init__.py") and hasfile("__manifest__.py"):
                return True
        return False

    @classmethod
    def _parse_addons_path(
        cls, option: optparse.Option, opt: str, value: str
    ) -> list[str]:
        ad_paths = []
        for path in map(cls._normalize, cls._parse_comma(option, opt, value)):
            if any(ch in path for ch in "*?["):
                anchor = Path(path).anchor
                matches = sorted(
                    str(match)
                    for match in Path(anchor).glob(str(Path(path).relative_to(anchor)))
                    if match.is_dir() and cls._is_addons_path(str(match))
                )
                _debug.logic(
                    "config.addons_path.glob", pattern=path, matches=len(matches)
                )
                ad_paths.extend(matches)
                continue
            if not Path(path).is_dir():
                cls._log(
                    logging.WARNING,
                    "option %s, no such directory %r, skipped",
                    opt,
                    path,
                )
                _debug.logic("config.addons_path.skipped", path=path, reason="missing")
                continue
            if not cls._is_addons_path(path):
                cls._log(
                    logging.WARNING,
                    "option %s, invalid addons directory %r, skipped",
                    opt,
                    path,
                )
                _debug.logic(
                    "config.addons_path.skipped", path=path, reason="no_manifest"
                )
                continue
            ad_paths.append(path)

        _debug.pipeline("config.addons_path", option=opt, paths=ad_paths)
        return ad_paths

    @classmethod
    def _parse_upgrade_path(
        cls, option: optparse.Option, opt: str, value: str
    ) -> list[str]:
        upgrade_path = []
        for path in map(cls._normalize, cls._parse_comma(option, opt, value)):
            if not Path(path).is_dir():
                cls._log(
                    logging.WARNING,
                    "option %s, no such directory %r, skipped",
                    opt,
                    path,
                )
                _debug.logic("config.upgrade_path.skipped", path=path, reason="missing")
                continue
            if not cls._is_upgrades_path(path):
                cls._log(
                    logging.WARNING,
                    "option %s, invalid upgrade directory %r, skipped",
                    opt,
                    path,
                )
                _debug.logic(
                    "config.upgrade_path.skipped", path=path, reason="no_scripts"
                )
                continue
            if path not in upgrade_path:
                upgrade_path.append(path)
        _debug.pipeline("config.upgrade_path", option=opt, paths=upgrade_path)
        return upgrade_path

    @classmethod
    def _parse_scripts(cls, option: optparse.Option, opt: str, value: str) -> list[str]:
        pre_upgrade_scripts = []
        for path in map(cls._normalize, cls._parse_comma(option, opt, value)):
            if not Path(path).is_file():
                cls._log(
                    logging.WARNING,
                    "option %s, no such file %r, skipped",
                    opt,
                    path,
                )
                _debug.logic("config.scripts.skipped", path=path, reason="missing")
                continue
            if path not in pre_upgrade_scripts:
                pre_upgrade_scripts.append(path)
        _debug.pipeline("config.scripts", option=opt, scripts=pre_upgrade_scripts)
        return pre_upgrade_scripts

    @classmethod
    def _is_upgrades_path(cls, path: str) -> bool:
        module = "*"
        version = "*"
        return any(
            any(Path(path).glob(f"{module}/{version}/{prefix}-*.py"))
            for prefix in ["pre", "post", "end"]
        )

    @classmethod
    def _parse_bool(cls, option: optparse.Option | None, opt: str, value: str) -> bool:
        if value.lower() in ("1", "yes", "true", "on"):
            return True
        if value.lower() in ("0", "no", "false", "off"):
            return False
        raise optparse.OptionValueError(
            f"option {opt}: invalid boolean value: {value!r}"
        )

    @classmethod
    def _check_smtp_ssl(
        cls, option: optparse.Option | None, opt: str, value: str
    ) -> bool | str:
        if value in SMTP_SSL_MODES:
            return value
        if value == "none":
            return False
        try:
            return cls._parse_bool(option, opt, value)
        except optparse.OptionValueError:
            raise optparse.OptionValueError(
                f"option {opt}: invalid value: {value!r}; expected a boolean, "
                f"none or one of {', '.join(SMTP_SSL_MODES)}"
            ) from None

    @classmethod
    def _parse_comma(
        cls, option: optparse.Option | None, opt: str, value: str
    ) -> list[str]:
        return [v for s in value.split(",") if (v := s.strip())]

    @classmethod
    def _parse_path(cls, option: optparse.Option, opt: str, value: str) -> str:
        return cls._normalize(value)

    @classmethod
    def _parse_without_demo(
        cls, option: optparse.Option | None, opt: str, value: str
    ) -> bool:
        try:
            return not cls._parse_bool(option, opt, value)
        except optparse.OptionValueError:
            cls._log(
                logging.WARNING,
                "option %s: since 19.0, invalid boolean value: %r, assume %s",
                opt,
                value,
                value != "None",
            )
            _debug.logic(
                "config.without_demo.legacy_value", value=value, demo=value == "None"
            )
            return value == "None"

    def parse(self, option_name: str, value: str) -> Any:
        if not isinstance(value, str):
            e = f"can only cast strings: {value!r}"
            raise TypeError(e)
        option = self.options_index[option_name]
        option_class: Any = self.parser.option_class
        checkers = option_class.TYPE_CHECKER
        check_func: Callable[..., Any] = (
            checkers["bool"]
            if option.action in ("store_true", "store_false")
            else checkers[option.type]
        )
        parsed = check_func(option, option_name, value)
        return None if parsed is UNSET else parsed

    @classmethod
    def _format_string(cls, value: Any) -> str:
        return str(value)

    @classmethod
    def _format_list(cls, value: list[Any]) -> str:
        return ",".join(filter(bool, (str(elem).strip() for elem in value)))

    @classmethod
    def _format_without_demo(cls, value: Any) -> str:
        return str(bool(value))

    def format(self, option_name: str, value: Any) -> str:
        option = self.options_index[option_name]
        option_class: Any = self.parser.option_class
        if option.action in ("store_true", "store_false"):
            format_func = option_class.TYPE_FORMATTER["bool"]
        else:
            format_func = option_class.TYPE_FORMATTER[option.type]
        return format_func(value)

    def load(self) -> None:
        self._warn(
            "Since 19.0, use config._load_file_options instead",
            DeprecationWarning,
            stacklevel=2,
        )
        self._load_file_options(self["config"])

    def _load_file_options(self, rcfile: str) -> None:
        self._file_options.clear()
        p = configparser.RawConfigParser(inline_comment_prefixes=("#", ";"))
        try:
            p.read([rcfile])
        except configparser.Error as exc:
            self.parser.error(f"malformed configuration file {rcfile!r}: {exc}")
            return
        except (OSError, UnicodeDecodeError) as exc:
            self.parser.error(f"cannot read the configuration file {rcfile!r}: {exc}")
            return

        try:
            items = p.items("options")
        except configparser.NoSectionError:
            _debug.logic("config.file.no_options_section", rcfile=rcfile)
            return

        unknown = 0  # debuglog
        skipped = 0  # debuglog
        try:
            for name, value in items:
                if name == "without_demo":
                    name = "with_demo"
                    value = str(self._parse_without_demo(None, "without_demo", value))
                option = self.options_index.get(name)
                if not option:
                    if name not in self.aliases:
                        self._log(
                            logging.WARNING,
                            "unknown option %r in the config file at "
                            "%s, option stored as-is, without parsing",
                            name,
                            rcfile,
                        )
                        unknown += 1  # debuglog
                    self._file_options[name] = value
                    continue
                if not option.file_loadable:
                    _debug.logic(
                        "config.file.option_skipped", option=name, reason="cli_only"
                    )
                    skipped += 1  # debuglog
                    continue
                if value == "" and option.type in _TYPES_WITHOUT_AN_EMPTY_VALUE:
                    _debug.logic(
                        "config.file.option_skipped", option=name, reason="empty_unset"
                    )
                    skipped += 1  # debuglog
                    continue
                if (
                    value in ("False", "false")
                    and option.action not in ("store_true", "store_false", "callback")
                    and option.nargs_ != "?"
                ):
                    self._log(
                        logging.WARNING,
                        "option %s reads %r in the config file at %s but isn't a "
                        "boolean option, skip. %r was the pre-19.0 spelling of "
                        "'unset'; write %s with an empty value instead.",
                        name,
                        value,
                        rcfile,
                        value,
                        name,
                    )
                    _debug.logic(
                        "config.file.option_skipped",
                        option=name,
                        reason="legacy_false_unset",
                    )
                    skipped += 1  # debuglog
                    continue
                try:
                    self._file_options[name] = self.parse(name, value)
                except (ValueError, optparse.OptionValueError, OSError) as exc:
                    raise ValueError(
                        f"Invalid value for option {name!r} in the config file "
                        f"at {rcfile}: {exc}"
                    ) from exc
        except configparser.Error as exc:
            self.parser.error(f"malformed configuration file {rcfile!r}: {exc}")
        _debug.lifecycle(
            "config.file_options_loaded",
            rcfile=rcfile,
            options=len(self._file_options),
            unknown=unknown,
            skipped=skipped,
        )

    def save(self, keys: list[str] | None = None) -> None:
        p = configparser.RawConfigParser(inline_comment_prefixes=("#", ";"))
        rc_exists = Path(self["config"]).exists()
        if rc_exists:
            p.read([self["config"]])
        if not p.has_section("options"):
            p.add_section("options")
        for opt in sorted(self.options):
            option = self.options_index.get(opt)
            if keys is not None and opt not in keys:
                continue
            if opt == "version" or (option and not option.file_exportable):
                continue
            if option:
                p.set("options", opt, self.format(opt, self.options[opt]))
            else:
                p.set("options", opt, self.options[opt])
        _debug.lifecycle(
            "config.save",
            rcfile=self["config"],
            existed=rc_exists,
            options=len(p.options("options")),
            keys=None if keys is None else len(keys),
        )

        try:
            if not rc_exists and not Path(self["config"]).parent.exists():
                Path(str(Path(self["config"]).parent)).mkdir(0o700, parents=True)
            try:
                cfg_path = Path(self["config"])
                with open(
                    cfg_path, "w", encoding="utf-8", opener=_open_private
                ) as file:
                    os.fchmod(file.fileno(), 0o600)
                    p.write(file)
            except OSError as exc:
                sys.stderr.write(f"ERROR: couldn't write the config file: {exc}\n")

        except OSError as exc:
            sys.stderr.write(f"ERROR: couldn't create the config directory: {exc}\n")

    @property
    def generation(self) -> int:
        # A test that swaps `options` for a plain mapping (patch.object) writes
        # past the counting layers; while that lasts every read moves the
        # counter, so nothing may be memoised.
        options = self.options
        if not (
            isinstance(options, collections.ChainMap)
            and all(isinstance(layer, _CountingDict) for layer in options.maps)
        ):
            self._generation += 1
        return self._generation

    def _bump_generation(self) -> None:
        self._generation += 1

    def get(self, key: str, default: Any = None) -> Any:
        return self.options.get(key, default)

    def __setitem__(self, key: str, value: Any) -> None:
        if isinstance(value, str) and key in self.options_index:
            value = self.parse(key, value)
        if key in _MODULE_MAP_OPTIONS and isinstance(value, (list, tuple, set)):
            value = dict.fromkeys(value, True)
        self._override_options[key] = value
        _debug.lifecycle(
            "config.override_set", option=key, known=key in self.options_index
        )

    def __getitem__(self, key: str) -> Any:
        return self.options[key]

    def pop(self, key: str, *args: Any) -> Any:
        _debug.lifecycle(
            "config.override_popped", option=key, was_set=key in self._override_options
        )
        return self._override_options.pop(key, *args)

    @contextlib.contextmanager
    def patch(self, **values: Any) -> Iterator[None]:
        sentinel = object()
        previous = {key: self._override_options.get(key, sentinel) for key in values}
        self._override_options.update(values)
        _debug.lifecycle("config.patch.enter", options=sorted(values))
        try:
            yield
        finally:
            for key, value in previous.items():
                if value is sentinel:
                    self._override_options.pop(key, None)
                else:
                    self._override_options[key] = value
            _debug.lifecycle("config.patch.exit", options=sorted(values))

    @functools.cached_property
    def root_path(self):
        return self._normalize(str(Path(__file__).parent.parent))

    @property
    def addons_base_dir(self):
        return str(Path(self.root_path, "addons"))

    @property
    def addons_community_dir(self):
        return str(Path(self.root_path).parent / "addons")

    @property
    def addons_data_dir(self):
        add_dir = str(Path(self["data_dir"], "addons"))
        d = str(Path(add_dir, release.series))
        if not Path(d).exists():
            try:
                if not Path(add_dir).exists():
                    Path(add_dir).mkdir(0o700, parents=True)
                Path(d).mkdir(0o500, parents=True)
                _debug.lifecycle("config.addons_data_dir.created", path=d)
            except OSError:
                self._log(logging.DEBUG, "Failed to create addons data dir %s", d)
                _debug.logic("config.addons_data_dir.create_failed", path=d)
        return d

    def filestore(self, dbname: str) -> str:
        return str(Path(self["data_dir"], "filestore", dbname))

    def set_admin_password(self, new_password: str) -> None:
        self.options["admin_passwd"] = crypt_context.hash(new_password)

    def is_valid_admin_password(self, password: str) -> bool:
        stored_hash = self.options["admin_passwd"]
        if not stored_hash:
            _debug.logic("config.admin_password.unset")
            return False
        result, updated_hash = crypt_context.match_and_update(password, stored_hash)
        _debug.logic(
            "config.admin_password.checked",
            valid=bool(result),
            rehashed=bool(result and updated_hash),
        )
        if result:
            if updated_hash:
                self.options["admin_passwd"] = updated_hash
            return True
        return False

    @property
    def http_socket_activation(self):
        return (
            self["http_enable"]
            and os.getenv("LISTEN_FDS") == "1"
            and os.getenv("LISTEN_PID") == str(os.getpid())
        )

    @classmethod
    def _normalize(cls, path: str) -> str:
        if not path:
            return ""
        return normcase(str(Path(expandvars(path.strip())).expanduser().resolve()))

    def _get_sources(self, name: str) -> dict[str, Any]:
        return {
            **{
                f"source#{no}": source.get(name, EMPTY)
                for no, source in enumerate(self.options.maps[:-6])
            },
            "override": self._override_options.get(name, EMPTY),
            "runtime": self._runtime_options.get(name, EMPTY),
            "command line": self._cli_options.get(name, EMPTY),
            "environment variable": self._env_options.get(name, EMPTY),
            "configuration file": self._file_options.get(name, EMPTY),
            "hardcoded default": self._default_options.get(name, EMPTY),
        }


config = configmanager()


def _pool_settings() -> PoolSettings:
    return PoolSettings.from_config(config, evented=odoo.evented)


_provide_pool_settings(_pool_settings)
