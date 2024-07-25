#!/usr/bin/env python3
import argparse
import sys

import os.path
from importlib.machinery import SourceFileLoader
from pathlib import Path
from typing import Iterator
from types import ModuleType

from . import Command

"""
Script method is add into the /upgrade/code directory.
Every script should be in a file corresponding to his upgrade version (script for the )

"""

AVAILABLE_EXT = ('py', 'js', 'css', 'scss', 'xml', 'csv')


class FileAccessor:
    addon: Path
    path: Path
    content: str

    def __init__(self, path: Path, addon: Path) -> None:
        self.path = path
        self.addon = addon
        self._content = None
        self.dirty = False

    @property
    def content(self):
        if self._content is None:
            with self.path.open("r") as f:
                self._content = f.read()
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
            str(path): FileAccessor(path, addon)
            for addon_path in addons_path
            for addon in Path(addon_path).iterdir()
            for path in addon.glob(glob)
            if path.is_file() and path.name.rsplit('.')[-1] in AVAILABLE_EXT
        }

    def __iter__(self) -> Iterator[FileAccessor]:
        return iter(self._files.values())

    def get_file(self, path):
        return self._files.get(str(path))

    def print_progress(self, current, total):
        if sys.stdout.isatty():
            print(f'\033[F{round(current / total * 100)}%')  # noqa: T201


def get_version(value: str) -> tuple[int | str, ...]:
    return tuple(int(x) if x.isnumeric() else x for x in value.split('.'))


def get_upgrade_code_scripts(from_version: tuple[int, ...], to_version: tuple[int, ...]) -> list[tuple[str, ModuleType]]:
    modules: list[tuple[str, ModuleType]] = []
    script_paths = list(Path(__file__).parent.parent.glob('upgrade_code/*.py'))
    script_paths.sort(key=str)
    for script_path in script_paths:
        version = get_version(script_path.name.split('-', 1)[0])
        if from_version <= version <= to_version:
            module = SourceFileLoader(script_path.name, str(script_path)).load_module()
            modules.append((script_path.name, module))
    return modules


def migrate(
        from_version: tuple[int, ...],
        to_version: tuple[int, ...],
        addons_path: list[str],
        glob: str,
        test: bool = False):

    modules = get_upgrade_code_scripts(from_version, to_version)
    file_manager = FileManager(addons_path, glob)
    for (name, module) in modules:
        print(f'update script: {name}\n')  # noqa: T201
        module.upgrade(file_manager)

    for file in file_manager:
        if file.dirty:
            print('updated: ', file.path)  # noqa: T201
            if not test:
                with file.path.open("w") as f:
                    f.write(file.content)


class UpgradeCode(Command):
    name = 'upgrade_code'

    def run(self, cmdargs):
        odoo = Path(__file__).parent.parent.parent
        to_version = SourceFileLoader('release', str(next(odoo.glob('odoo/release.py')))).load_module().version_info
        from_version = (to_version[0] if to_version[1] else to_version[0] - 1,)
        addons_path = [
            str(next(odoo.glob('odoo/addons'))),
            str(next(odoo.glob('addons'))),
        ]

        parser = argparse.ArgumentParser()
        parser.add_argument('--addons-path', default=','.join(addons_path),
            help="[str] comma separated string representing the odoo addons path")
        parser.add_argument('-g', '--glob', default='**/*',
            help="[str] glob filter to apply changes")
        parser.add_argument('--from', default='.'.join(map(str, from_version)),
            help="[typle[int, ...]] odoo version")
        parser.add_argument('--to', default='.'.join(map(str, to_version)),
            help="[typle[int, ...]] odoo version")
        parser.add_argument(
            '-t', '--test', action='store_true', default=False,
            help="Test the script and display the number of files impacted without making the modification"
        )

        args = vars(parser.parse_args(cmdargs))
        args['addons_path'] = tuple(os.path.abspath(os.path.expanduser(path)) for path in args['addons_path'].split(','))
        args['from'] = get_version(args['from'])
        args['to'] = get_version(args['to'])

        migrate(args['from'], args['to'], args['addons_path'], args['glob'], args['test'])
