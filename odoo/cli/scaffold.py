import argparse
import dataclasses
import functools
import os
import re
import sys
from collections.abc import Callable, Generator
from pathlib import Path
from typing import TYPE_CHECKING, Any

from odoo.libs.debug_log import DebugLog

from . import Command

if TYPE_CHECKING:
    from jinja2 import Environment
else:
    Environment = Any

_debug = DebugLog(__name__)

_MODNAME_RE = re.compile(r"^[a-z_][a-z0-9_]*$")


class Scaffold(Command):
    description = "Generates an Odoo module skeleton."

    def __init__(self) -> None:
        super().__init__()
        try:
            templates = sorted(
                d.name for d in _get_template_path().iterdir() if d.is_dir()
            )
        except OSError:
            _debug.logic("cli.scaffold.templates_unavailable")
            templates = []
        self.epilog = (
            f"Built-in templates available are: {', '.join(templates)}"
            if templates
            else "No built-in templates found (templates/ directory missing)."
        )
        parser = self.parser
        parser.add_argument(
            "-t",
            "--template",
            type=Template,
            default="default",
            help="Use a custom module template, can be a template name or the"
            " path to a module template (default: %(default)s)",
        )
        parser.add_argument("name", help="Name of the module to create")
        parser.add_argument(
            "dest",
            default=".",
            nargs="?",
            help="Directory to create the module in (default: %(default)s)",
        )
        parser.add_argument(
            "--force",
            "-f",
            action="store_true",
            help="Overwrite an existing module directory instead of refusing",
        )

    def run(self, cmdargs: list[str]) -> None:
        parser = self.parser
        args = parser.parse_args(args=cmdargs)

        try:
            params = args.template.parse_params(args.name)
            modname = args.template.get_module_name(args.name, params)
        except ValueError as err:
            _debug.logic("cli.scaffold.name_rejected", name=args.name)
            parser.error(str(err))
        dest = _get_or_create_directory(args.dest)
        if (dest / modname).exists():
            if not args.force:
                _debug.logic("cli.scaffold.rejected", module=modname, reason="exists")
                parser.error(
                    f"{dest / modname} already exists; pass --force to overwrite it"
                )
            _debug.logic("cli.scaffold.overwrite", module=modname, dest=str(dest))
        _debug.pipeline(
            "cli.scaffold.render",
            template=str(args.template),
            module=modname,
            dest=str(dest),
            force=args.force,
            params=len(params),
        )
        with _debug.perf(
            "cli.scaffold.render", template=str(args.template), module=modname
        ):
            args.template.render_to_directory(modname, dest, params=params)
        _debug.lifecycle(
            "cli.scaffold.module_created", module=modname, path=str(dest / modname)
        )


def _get_template_path(*parts: str) -> Path:
    base = Path(__file__).resolve().parent / "templates"
    return base / Path(*parts) if parts else base


def _str_to_snake_case(s: str) -> str:
    s = re.sub(r"(?<=[A-Z])([A-Z][a-z])", r" \1", s)
    s = re.sub(r"(?<=[a-z0-9])([A-Z])", r" \1", s)
    return "_".join(s.lower().split())


def _str_to_pascal_case(s: str) -> str:
    return "".join(ss.capitalize() for ss in re.sub(r"[_\s]+", " ", s).split())


def _get_or_create_directory(p: str) -> Path:
    expanded = Path(os.path.expandvars(p)).expanduser().resolve()
    if not expanded.exists():
        expanded.mkdir(parents=True)
        _debug.lifecycle("cli.scaffold.directory_created", path=str(expanded))
    if not expanded.is_dir():
        _debug.logic("cli.scaffold.rejected", path=str(expanded), reason="not_dir")
        sys.exit(f"{p} is not a directory")
    return expanded


@functools.cache
def _get_jinja_env() -> Environment:
    try:
        import jinja2
    except ImportError:
        _debug.logic("cli.scaffold.rejected", reason="jinja2_missing")
        sys.exit(
            "odoo-bin scaffold needs Jinja2, which is not installed.\n"
            "    pip install Jinja2      (or: pip install 'odoo[scaffold]')"
        )
    # autoescape stays off: the templates render Python, XML and CSV source
    # for a module skeleton, never HTML served to a browser.
    env = jinja2.Environment()  # noqa: S701  see the two lines above
    env.filters["snake"] = _str_to_snake_case
    env.filters["pascal"] = _str_to_pascal_case
    _debug.lifecycle("cli.scaffold.jinja_env_built", filters=2)
    return env


@dataclasses.dataclass(frozen=True)
class NamingConvention:
    parse_params: Callable[[str], dict[str, str]]
    get_module_name: Callable[[str, dict[str, str]], str]


def _parse_country_name_and_code(name: str) -> dict[str, str]:
    if "-" not in name:
        raise ValueError(
            "l10n_payroll template requires a name of the form "
            f"'<country>-<code>' (e.g. 'mexico-mx'); got {name!r}"
        )
    country, _, code = name.partition("-")
    return {"name": country, "code": code}


DEFAULT_NAMING = NamingConvention(
    parse_params=lambda name: {"name": name},
    get_module_name=lambda name, params: _str_to_snake_case(name),
)

NAMING_CONVENTIONS = {
    "l10n_payroll": NamingConvention(
        parse_params=_parse_country_name_and_code,
        get_module_name=lambda name, params: f"l10n_{params['code']}_hr_payroll",
    ),
}


class Template:
    def __init__(self, identifier: str) -> None:
        self.id = identifier
        self.path = _get_template_path(identifier)
        if self.path.is_dir():
            _debug.logic(
                "cli.scaffold.template_resolved", id=identifier, source="builtin"
            )
            return
        self.path = Path(identifier)
        if self.path.is_dir():
            _debug.logic("cli.scaffold.template_resolved", id=identifier, source="path")
            return
        _debug.logic("cli.scaffold.template_resolved", id=identifier, source=None)
        raise argparse.ArgumentTypeError(
            f"{identifier!r} is not a valid module template"
        )

    def __str__(self) -> str:
        return self.id

    def _read_files(self) -> Generator[tuple[Path, bytes]]:
        for dirpath, _, filenames in self.path.walk():
            for f in filenames:
                filepath = dirpath / f
                yield filepath, filepath.read_bytes()

    def parse_params(self, name: str) -> dict[str, str]:
        convention = NAMING_CONVENTIONS.get(self.id, DEFAULT_NAMING)
        _debug.logic(
            "cli.scaffold.naming_convention",
            template=self.id,
            convention="default" if convention is DEFAULT_NAMING else self.id,
        )
        return convention.parse_params(name)

    def get_module_name(self, name: str, params: dict[str, str]) -> str:
        convention = NAMING_CONVENTIONS.get(self.id, DEFAULT_NAMING)
        modname = convention.get_module_name(name, params)
        if not _MODNAME_RE.match(modname):
            _debug.logic(
                "cli.scaffold.name_rejected",
                name=name,
                module=modname,
                reason="pattern",
            )
            msg = (
                f"{modname!r} is not a valid module name: expected "
                f"{_MODNAME_RE.pattern!r} (name given: {name!r})"
            )
            raise ValueError(msg)
        return modname

    def render_to_directory(
        self, modname: str, directory: Path, params: dict[str, str] | None = None
    ) -> None:
        env = _get_jinja_env()
        files = 0  # debuglog
        templated = 0  # debuglog
        copied_bytes = 0  # debuglog
        for path, content in self._read_files():
            copied_bytes += len(content)  # debuglog
            rendered = Path(env.from_string(str(path)).render(params))
            local = rendered.relative_to(self.path)
            ext = rendered.suffix
            if ext == ".template":
                local = local.with_suffix("")
            dest = Path(directory) / modname / local
            dest.parent.mkdir(parents=True, exist_ok=True)
            files += 1  # debuglog

            with dest.open("wb") as f:
                if ext not in (
                    ".py",
                    ".xml",
                    ".csv",
                    ".js",
                    ".rst",
                    ".html",
                    ".template",
                ):
                    f.write(content)
                else:
                    env.from_string(content.decode("utf-8")).stream(params or {}).dump(
                        f, encoding="utf-8"
                    )
                    f.write(b"\n")
                    templated += 1  # debuglog
        _debug.pipeline(
            "cli.scaffold.rendered",
            module=modname,
            template=self.id,
            files=files,
            templated=templated,
            source_bytes=copied_bytes,
        )
