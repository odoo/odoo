#!/usr/bin/env python3
"""
Rewrite the entire source code using the scripts found at
/odoo/upgrade_code

Each script is named {version}-{name}.py and exposes an upgrade function
that takes a single argument, the file_manager, and returns nothing.

The file_manager acts as a list of files, files have 3 attributes:
* path: the pathlib.Path where the file is on the file system;
* addon: the odoo addon in which the file is;
* content: the re-writtable content of the file (lazy).

There are additional utilities on the file_manager, such as:
* print_progress(current, total)

Example:

    def upgrade(file_manager):
        files = [f for f in file_manager if f.path.suffix == '.py']
        for fileno, file in enumerate(files, start=1):
            file.content = file.content.replace(..., ...)
            file_manager.print_progress(fileno, len(files))

The command line offers a way to select and run those scripts.

Please note that all the scripts are doing a best-effort a migrating the
source code, they only help do the heavy-lifting, they are not silver
bullets.
"""

import argparse
import sys

from importlib.machinery import SourceFileLoader
from pathlib import Path
from types import ModuleType
from typing import Iterator

ROOT = Path(__file__).parent.parent

try:
    import odoo.addons
    from . import Command
    from odoo import release
    from odoo.modules import initialize_sys_path
    from odoo.tools import config, parse_version
except ImportError:
    # Assume the script is directy executed (by opposition to be
    # executed via odoo-bin), happily release/parse_version are
    # standalone so we can hack our way there without importing odoo
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / 'tools'))
    import release
    from parse_version import parse_version
    class Command:
        pass
    config = {'addons_path': ''}
    initialize_sys_path = None


UPGRADE = ROOT / 'upgrade_code'
AVAILABLE_EXT = ('.py', '.js', '.css', '.scss', '.xml', '.csv')


class FileAccessor:
    addon: Path
    path: Path
    content: str

    def __init__(self, path: Path, addon_path: Path) -> None:
        self.path = path
        self.addon = addon_path / path.relative_to(addon_path).parts[0]
        self._content = None
        self.dirty = False

    @property
    def content(self):
        if self._content is None:
            self._content = self.path.read_text()
        return self._content

    @content.setter
    def content(self, value):
        if self._content != value:
            self._content = value
            self.dirty = True


class FileManager:
    addons_path: list[str]
    glob: str

    def __init__(self, addons_path: list[str], glob: str = '**/*') -> None:
        self.addons_path = addons_path
        self.glob = glob
        self._files = {
            str(path): FileAccessor(path, Path(addon_path))
            for addon_path in addons_path
            for path in Path(addon_path).glob(glob)
            if '__pycache__' not in path.parts
            if path.suffix in AVAILABLE_EXT
            if path.is_file()
        }

    def __iter__(self) -> Iterator[FileAccessor]:
        return iter(self._files.values())

    def __len__(self):
        return len(self._files)

    def get_file(self, path):
        return self._files.get(str(path))

    if sys.stdout.isatty():
        def print_progress(self, current, total=None):
            total = total or len(self) or 1
            print(f'{current / total:>4.0%}', end='\r', file=sys.stderr)  # noqa: T201
    else:
        def print_progress(self, current, total=None):
            pass


def get_upgrade_code_scripts(from_version: tuple[int, ...], to_version: tuple[int, ...]) -> list[tuple[str, ModuleType]]:
    modules: list[tuple[str, ModuleType]] = []
    for script_path in sorted(UPGRADE.glob('*.py')):
        version = parse_version(script_path.name.partition('-')[0])
        if from_version <= version <= to_version:
            module = SourceFileLoader(script_path.name, str(script_path)).load_module()
            modules.append((script_path.name, module))
    return modules


def migrate(
    addons_path: list[str],
    glob: str,
    from_version: tuple[int, ...] | None = None,
    to_version: tuple[int, ...] | None = None,
    script: str | None = None,
    dry_run: bool = False,
):
    if script:
        script_path = next(UPGRADE.glob(f'*{script.removesuffix(".py")}*.py'), None)
        if not script_path:
            raise FileNotFoundError(script)
        script_path.relative_to(UPGRADE)  # safeguard, prevent going up
        module = SourceFileLoader(script_path.name, str(script_path)).load_module()
        modules = [(script_path.name, module)]
    else:
        modules = get_upgrade_code_scripts(from_version, to_version)

    file_manager = FileManager(addons_path, glob)
    for (name, module) in modules:
        file_manager.print_progress(0)  # 0%
        module.upgrade(file_manager)
        file_manager.print_progress(len(file_manager))  # 100%

    for file in file_manager:
        if file.dirty:
            print(file.path)  # noqa: T201
            if not dry_run:
                with file.path.open("w") as f:
                    f.write(file.content)

    return any(file.dirty for file in file_manager)


class UpgradeCode(Command):
    """ Rewrite the entire source code using the scripts found at /odoo/upgrade_code """
    name = 'upgrade_code'
    prog_name = Path(sys.argv[0]).name

    def __init__(self):
        self.parser = argparse.ArgumentParser(
            prog=(
                f"{self.prog_name} [--addons-path=PATH,...] {self.name}"
                if initialize_sys_path else
                self.prog_name
            ),
            description=__doc__.replace('/odoo/upgrade_code', str(UPGRADE)),
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        group = self.parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            '--script',
            metavar='NAME',
            help="run this single script")
        group.add_argument(
            '--from',
            dest='from_version',
            type=parse_version,
            metavar='VERSION',
            help="run all scripts starting from this version, inclusive")
        self.parser.add_argument(
            '--to',
            dest='to_version',
            type=parse_version,
            default=parse_version(release.version),
            metavar='VERSION',
            help=f"run all scripts until this version, inclusive (default: {release.version})")
        self.parser.add_argument(
            '--glob',
            default='**/*',
            help="select the files to rewrite (default: %(default)s)")
        self.parser.add_argument(
            '--dry-run',
            action='store_true',
            help="list the files that would be re-written, but rewrite none")
        self.parser.add_argument(
            '--addons-path',
            default=config['addons_path'],
            metavar='PATH,...',
            help="specify additional addons paths (separated by commas)",
        )

    def run(self, cmdargs):
        options = self.parser.parse_args(cmdargs)
        if initialize_sys_path:
            config['addons_path'] = options.addons_path
            initialize_sys_path()
            options.addons_path = odoo.addons.__path__
        else:
            options.addons_path = [p for p in options.addons_path.split(',') if p]
        if not options.addons_path:
            self.parser.error("--addons-path is required when used standalone")
        is_dirty = migrate(**vars(options))
        sys.exit(int(is_dirty))


if __name__ == '__main__':
    UpgradeCode().run(sys.argv[1:])
