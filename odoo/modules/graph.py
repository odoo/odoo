# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

""" Modules dependency graph. """

import logging
from typing import Set, Dict, Iterable, Iterator

import odoo
import odoo.tools as tools

_logger = logging.getLogger(__name__)


class Package:
    """
    Python package for the Odoo module with the same name
    """
    def __init__(self, name: str) -> None:
        # manifest data
        self.name = name
        self.manifest = odoo.modules.module.get_manifest(name) or {}

        # ir_module_module data             # column_name
        self.id = None                      # id
        self.state = 'uninstalled'          # state
        self.dbdemo = False                 # demo
        self.installed_version = None       # latest_version

        # info for upgrade
        self.load_state = None               # the state when loaded to packages
        self.load_version = None             # the version when loaded to packages

        # dependency
        self.depends: Set[Package] = set()
        self._depth_loop = False            # detects dependency loops

    @tools.lazy_property
    def depth(self) -> int:
        """ Return the longest distance from self to module 'base' along dependencies. """
        if self._depth_loop:
            raise RecursionError
        self._depth_loop = True
        depth = max(package.depth for package in self.depends) + 1 if self.depends else 0
        self._depth_loop = False
        return depth

    def demo_installable(self) -> bool:
        return all(p.dbdemo for p in self.depends)


class PackageGraph:
    """
    Sorted Python packages for Odoo modules with the same names ordered by (package.depth, package.name)
    """

    def __init__(self, cr) -> None:
        self._packages: Dict[str, Package] = {}
        self._cr = cr

    def __contains__(self, name: str) -> bool:
        return name in self._packages

    def __getitem__(self, name: str) -> Package:
        return self._packages[name]

    def __iter__(self) -> Iterator[Package]:
        return iter(sorted(self._packages.values(), key=lambda package: (package.depth, package.name)))

    def __len__(self) -> int:
        return len(self._packages)

    def __bool__(self) -> bool:
        return bool(self._packages)

    def add(self, names: Iterable[str]) -> None:
        for name in names:
            package = self._packages[name] = Package(name)
            if not package.manifest.get('installable'):
                message = None if name == 'studio_customization' else 'not_installable'
                self._remove(name, message)

        self._update_depends(names)
        self._check_depth(names)
        self._update_from_database(names)

    def _update_depends(self, names: Iterable[str]) -> None:
        for name in names:
            package = self._packages.get(name)
            if package is not None:
                try:
                    package.depends = set(self._packages[dep] for dep in package.manifest['depends'])
                except KeyError:
                    self._remove(name, 'missing_depends')

    def _check_depth(self, names: Iterable[str]) -> None:
        for name in names:
            package = self._packages.get(name)
            try:
                package and package.depth
            except RecursionError:
                self._remove(name, 'depends_loop')

    def _update_from_database(self, names: Iterable[str]) -> None:
        names = tuple(name for name in names if name in self._packages)
        if not names:
            return
        # update packages with values from the database (if exist)
        query = '''
            SELECT name, id, state, demo, latest_version AS installed_version
            FROM ir_module_module
            WHERE name IN %s
        '''
        self._cr.execute(query, [names])
        for name, id_, state, demo, installed_version in self._cr.fetchall():
            package = self._packages[name]
            package.id = id_
            package.state = state
            package.dbdemo = demo
            package.installed_version = installed_version
            package.load_version = installed_version
            package.load_state = state

    def _remove(self, name: str, reason: str = None) -> None:
        package = self._packages.pop(name, None)
        if package is not None:
            if reason:
                logger, message = self._REMOVE_MESSAGES.get(reason, (_logger.debug, reason))
                logger('module %s: %s', name, message)
            for other, other_package in list(self._packages.items()):
                if package in other_package.depends:
                    self._remove(other, reason)

    _REMOVE_MESSAGES = {
        'depends_loop': (_logger.warning, 'in a dependency loop, skipped'),
        'not_installable': (_logger.warning, 'not installable, skipped'),
        'missing_depends': (_logger.info, 'some depends are not loaded, skipped'),
    }
