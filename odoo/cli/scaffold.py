import os
import re
import sys
from pathlib import Path

import jinja2

from . import Command


class Scaffold(Command):
    """Generates an Odoo module skeleton."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.epilog = f"Built-in templates available are: {
            ', '.join(d.name for d in _builtins_dir().iterdir() if d.name != 'base')
        }"

    def run(self, cmdargs):
        # TODO: bash completion file
        parser = self.parser
        parser.add_argument(
            "-t",
            "--template",
            type=Template,
            default=Template("default"),
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

        if not cmdargs:
            sys.exit(parser.print_help())
        args = parser.parse_args(args=cmdargs)

        if args.template.id == "l10n_payroll":
            name_split = args.name.split("-")
            params = {"name": name_split[0], "code": name_split[1]}
        else:
            params = {"name": args.name}

        args.template.render_to(
            snake(args.name),
            directory(args.dest, create=True),
            params=params,
        )


def _builtins_dir(*parts):
    """Return the path to the built-in templates directory."""
    base = Path(__file__).resolve().parent / "templates"
    return base / Path(*parts) if parts else base


def snake(s):
    """Convert ``s`` to snake_case.

    Inserts underscores before uppercase letters preceded by a
    non-uppercase letter, then lowercases and joins on whitespace.
    """
    s = re.sub(r"(?<=[^A-Z])\B([A-Z])", r" \1", s)
    return "_".join(s.lower().split())


def pascal(s):
    """Convert ``s`` to PascalCase."""
    return "".join(ss.capitalize() for ss in re.sub(r"[_\s]+", " ", s).split())


def directory(p, create=False):
    """Resolve and validate a directory path.

    Args:
        p: Directory path (supports ~ and $VAR expansion).
        create: If True, create the directory if it doesn't exist.
    """
    expanded = Path(os.path.expandvars(p)).expanduser().resolve()
    if create and not expanded.exists():
        expanded.mkdir(parents=True)
    if not expanded.is_dir():
        sys.exit(f"{p} is not a directory")
    return expanded


_env = jinja2.Environment()  # noqa: S701 — generates .py/.xml code templates, not HTML
_env.filters["snake"] = snake
_env.filters["pascal"] = pascal


class Template:
    """A module template that can be rendered into a new Odoo module."""

    def __init__(self, identifier):
        # TODO: archives (zipfile, tarfile)
        self.id = identifier
        # is identifier a builtin?
        self.path = _builtins_dir(identifier)
        if self.path.is_dir():
            return
        # is identifier a directory?
        self.path = Path(identifier)
        if self.path.is_dir():
            return
        sys.exit(f"{identifier} is not a valid module template")

    def __str__(self):
        return self.id

    def files(self):
        """List the (local) path and content of all files in the template."""
        for dirpath, _, filenames in self.path.walk():
            for f in filenames:
                filepath = dirpath / f
                yield filepath, filepath.read_bytes()

    def render_to(self, modname, directory, params=None):
        """Render this module template to ``directory`` with the provided
        rendering parameters.
        """
        for path, content in self.files():
            rendered = Path(_env.from_string(str(path)).render(params))
            local = rendered.relative_to(self.path)
            # strip .template extension
            ext = rendered.suffix
            if ext == ".template":
                local = local.with_suffix("")
            if self.id == "l10n_payroll":
                modname = f"l10n_{params['code']}_hr_payroll"
            dest = Path(directory) / modname / local
            dest.parent.mkdir(parents=True, exist_ok=True)

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
                    _env.from_string(content.decode("utf-8")).stream(params or {}).dump(
                        f, encoding="utf-8"
                    )
                    f.write(b"\n")
