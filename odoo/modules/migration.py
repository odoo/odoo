import inspect
import itertools
import logging
import re
import typing
from collections import defaultdict
from collections.abc import Iterator
from pathlib import Path

import odoo.upgrade
from odoo import release
from odoo.libs.parse_version import parse_version
from odoo.modules.module import load_script
from odoo.orm.runtime import Registry
from odoo.tools.misc import file_path

if typing.TYPE_CHECKING:
    from odoo.db import Cursor

    from . import module_graph

_logger = logging.getLogger(__name__)


# Reviewed 2026-03: pre-7.0 patterns (6.1, saas~) are intentionally kept — multi-version
# upgrade scripts and odoo.upgrade paths may contain historical version folders.
# The regex is compiled once; zero runtime cost.
VERSION_RE = re.compile(
    r"""^
        # Optional prefix with Odoo version
        ((
            6\.1|

            # "x.0" version, with x >= 6.
            [6-9]\.0|

            # multi digits "x.0" versions
            [1-9]\d+\.0|

            # x.saas~y, where x >= 7 and x <= 10
            (7|8|9|10)\.saas~[1-9]\d*|

            # saas~x.y, where x >= 11 and y between 1 and 9
            # FIXME handle version >= saas~100 (expected in year 2106)
            saas~(1[1-9]|[2-9]\d+)\.[1-9]
        )\.)?
        # After Odoo version we allow precisely 2 or 3 parts
        # note this will also allow 0.0.0 which has a special meaning
        \d+\.\d+(\.\d+)?
    $""",
    re.VERBOSE | re.ASCII,
)


class MigrationManager:
    """Manages the migration of modules.

    Migrations files must be python files containing a ``migrate(cr, installed_version)``
    function. These files must respect a directory tree structure: A 'migrations' folder
    which contains a folder by version. Version can be 'module' version or 'server.module'
    version (in this case, the files will only be processed by this version of the server).
    Python file names must start by ``pre-`` or ``post-`` and will be executed, respectively,
    before and after the module initialisation. ``end-`` scripts are run after all modules have
    been updated.

    A special folder named ``0.0.0`` can contain scripts that will be run on any version change.
    In `pre` stage, ``0.0.0`` scripts are run first, while in ``post`` and ``end``, they are run last.

    Example::

        <moduledir>
        `-- migrations
            |-- 1.0
            |   |-- pre-update_table_x.py
            |   |-- pre-update_table_y.py
            |   |-- post-create_plop_records.py
            |   |-- end-cleanup.py
            |   `-- README.txt                      # not processed
            |-- 9.0.1.1                             # processed only on a 9.0 server
            |   |-- pre-delete_table_z.py
            |   `-- post-clean-data.py
            |-- 0.0.0
            |   `-- end-invariants.py               # processed on all version update
            `-- foo.py                              # not processed
    """

    migrations: defaultdict[str, dict]

    def __init__(self, cr: Cursor, graph: module_graph.ModuleGraph):
        self.cr = cr
        self.graph = graph
        self.migrations = defaultdict(dict)
        self._get_files()

    def _get_files(self) -> None:
        def _get_upgrade_path(pkg: str) -> Iterator[str]:
            for path in odoo.upgrade.__path__:
                upgrade_path = Path(path, pkg)
                if upgrade_path.exists():
                    yield str(upgrade_path)

        def _verify_upgrade_version(path: str, version: str) -> bool:
            full_path = Path(path, version)
            if not full_path.is_dir():
                return False

            if version == "tests":
                return False

            if not VERSION_RE.match(version):
                _logger.warning("Invalid version for upgrade script %r", str(full_path))
                return False

            return True

        def get_scripts(path: str) -> dict[str, list[str]]:
            if not path:
                return {}
            p = Path(path)
            return {
                entry.name: [str(f) for f in (p / entry.name).glob("*.py")]
                for entry in p.iterdir()
                if _verify_upgrade_version(path, entry.name)
            }

        def check_path(path: str) -> str:
            try:
                return file_path(path)
            except FileNotFoundError:
                return ""

        for pkg in self.graph:
            if (
                pkg.load_state != "to upgrade"
                and pkg.name not in Registry(self.cr.dbname)._force_upgrade_scripts
            ):
                continue

            self.migrations[pkg.name] = {
                "module": get_scripts(check_path(pkg.name + "/migrations")),
                "module_upgrades": get_scripts(check_path(pkg.name + "/upgrades")),
            }

            scripts = defaultdict(list)
            for p in _get_upgrade_path(pkg.name):
                for v, s in get_scripts(p).items():
                    scripts[v].extend(s)
            self.migrations[pkg.name]["upgrade"] = scripts

    def migrate_module(
        self,
        pkg: module_graph.ModuleNode,
        stage: typing.Literal["pre", "post", "end"],
    ) -> None:
        assert stage in ("pre", "post", "end")
        stageformat = {
            "pre": "[>%s]",
            "post": "[%s>]",
            "end": "[$%s]",
        }
        if (
            pkg.load_state != "to upgrade"
            and pkg.name not in Registry(self.cr.dbname)._force_upgrade_scripts
        ):
            return

        def convert_version(version: str) -> str:
            if version == "0.0.0":
                return version
            if version.count(".") > 2:
                return version  # the version number already contains the server version, see VERSION_RE for details
            return f"{release.major_version}.{version}"

        def _get_migration_versions(pkg, stage: str) -> list[str]:
            versions = sorted(
                {
                    ver: None
                    for lv in self.migrations[pkg.name].values()
                    for ver, lf in lv.items()
                    if lf
                },
                key=lambda k: parse_version(convert_version(k)),
            )
            if "0.0.0" in versions:
                # reorder versions
                versions.remove("0.0.0")
                if stage == "pre":
                    versions.insert(0, "0.0.0")
                else:
                    versions.append("0.0.0")
            return versions

        def _get_migration_files(pkg, version, stage):
            """return a list of migration script files"""
            m = self.migrations[pkg.name]

            return sorted(
                (
                    f
                    for k in m
                    for f in m[k].get(version, [])
                    if Path(f).name.startswith(f"{stage}-")
                ),
                key=lambda f: Path(f).name,
            )

        installed_version = pkg.load_version or ""
        parsed_installed_version = parse_version(installed_version)
        current_version = parse_version(convert_version(pkg.manifest["version"]))

        def compare(version: str) -> bool:
            if version == "0.0.0" and parsed_installed_version < current_version:
                return True

            full_version = convert_version(version)
            majorless_version = version != full_version

            if majorless_version:
                # We should not re-execute major-less scripts when upgrading to new Odoo version
                # a module in `9.0.2.0` should not re-execute a `2.0` script when upgrading to `10.0.2.0`.
                # In which case we must compare just the module version
                return (
                    parsed_installed_version[2:]
                    < parse_version(full_version)[2:]
                    <= current_version[2:]
                )

            return (
                parsed_installed_version
                < parse_version(full_version)
                <= current_version
            )

        versions = _get_migration_versions(pkg, stage)
        for version in versions:
            if compare(version):
                for pyfile in _get_migration_files(pkg, version, stage):
                    exec_script(
                        self.cr,
                        installed_version,
                        pyfile,
                        pkg.name,
                        stage,
                        stageformat[stage] % version,
                    )


# Reviewed 2026-03: _cr/_version variants are kept for backward compatibility
# with existing migration scripts.  Zero cost, removing would break silently.
VALID_MIGRATE_PARAMS = list(
    itertools.product(
        ["cr", "_cr"],
        ["version", "_version"],
    )
)


def exec_script(
    cr: Cursor,
    installed_version: str,
    pyfile: str,
    addon: str,
    stage: str,
    version: str | None = None,
) -> None:
    """Execute a single migration script file."""
    version = version or installed_version
    p = Path(pyfile)
    if p.suffix.lower() != ".py":
        return
    try:
        mod = load_script(pyfile, p.stem)
    except ImportError as e:
        raise ImportError(
            f"module {addon}: Unable to load {stage}-migration file {pyfile}"
        ) from e

    if not hasattr(mod, "migrate"):
        raise AttributeError(
            f'module {addon}: Each {stage}-migration file must have a'
            f' "migrate(cr, installed_version)" function, not found in {pyfile}'
        )

    try:
        sig = inspect.signature(mod.migrate)
    except TypeError as e:
        raise TypeError(
            f"module {addon}: `migrate` needs to be a function, got {mod.migrate!r}"
        ) from e

    if not (
        tuple(sig.parameters.keys()) in VALID_MIGRATE_PARAMS
        and all(
            param.kind in (param.POSITIONAL_ONLY, param.POSITIONAL_OR_KEYWORD)
            for param in sig.parameters.values()
        )
    ):
        raise TypeError(
            f"module {addon}: `migrate`'s signature should be `(cr, version)`,"
            f" {mod.migrate} is {sig}"
        )

    _logger.info("module %s: Running migration %s %s", addon, version, mod.__name__)
    mod.migrate(cr, installed_version)
