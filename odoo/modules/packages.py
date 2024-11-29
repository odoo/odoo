# Part of Odoo. See LICENSE file for full copyright and licensing details.

""" Modules dependency graph. """

from __future__ import annotations

import logging
import typing

from odoo.tools import lazy_property, OrderedSet
from odoo.tools.sql import column_exists

from .module import get_manifest

if typing.TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from typing import Any, Literal
    from odoo.sql_db import BaseCursor

_logger = logging.getLogger(__name__)


# THE LOADING ORDER
#
# Dependency Graph:
#      +---------+
#      |  base   |
#      +---------+
#        ^
#        |
#        |
#      +---------+
#      | module1 | <-----+
#      +---------+       |
#        ^               |
#        |               |
#        |               |
#      +---------+     +---------+
#   +> | module2 |     | module3 |
#   |  +---------+     +---------+
#   |    ^               ^     ^
#   |    |               |     |
#   |    |               |     |
#   |  +---------+       |     |  +---------+
#   |  | module4 | ------+     +- | module5 |
#   |  +---------+                +---------+
#   |    ^
#   |    |
#   |    |
#   |  +---------+
#   +- | module6 |
#      +---------+
#
#
# We always load module base in the zeroth phase, because
# 1. base should always be the single drain of the dependency graph
# 2. we need to use models in the base to upgrade other modules
#
# If there is no module to update(init/upgrade)
# the loading order of modules in the same phase are sorted by the (depth, name)
# where depth is the longest distance from the module to the base module along the dependency graph.
# For example: the depth of module6 is 4 (path: module6 -> module4 -> module2 -> module1 -> base)
# As a result, the loading order is
# phase 0: base
# phase 1: module1 -> module2 -> module3 -> module4 -> module5 -> module6
#
# If there are some modules need update(init/upgrade)
# For example,
# 'installed' : base, module1, module2, module3, module4, module6
# 'to install': module5
# the updating order is
# phase 0: base
# phase 1: module1 -> module2 -> module3 -> module4 -> module6
# phase 2: module5
#
# In summary:
# phase 0: base
# phase odd: (modules: 1. don't need init; 2. all depends modules have been loaded or going to be loaded in this phase)
# phase even: (modules: 1. need init; 2. all depends modules have been loaded or going to be loaded in this phase)
#
#
# Corner case
# Sometimes the dependency may be changed for sake of upgrade
# For example
#      BEFORE UPGRADE                                       UPGRADING
#
#      +---------+                                          +---------+
#      |  base   |                                          |  base   |
#      +---------+                                          +---------+
#        ^   installed                                        ^    to upgrade
#        |                                                    |
#        |                                                    |
#      +---------+                                          +---------+
#      | module1 |                                          | module1 | <-----+
#      +---------+                                          +---------+       |
#        ^   installed                                        ^    to upgrade |
#        |                         ==>                        |               |
#        |                                                    |               |
#      +---------+                                          +---------+     +---------+
#      | module2 |                                          | module2 |     | module3 |
#      +---------+                                          +---------+     +---------+
#        ^   installed                                        ^    to upgrade ^    to install
#        |                                                    |               |
#        |                                                    |               |
#      +---------+                                          +---------+       |
#      | module4 |                                          | module4 | ------+
#      +---------+                                          +---------+
#            installed                                             to upgrade
#
# Because of the new dependency module4 -> module3
# The module3 will be marked 'to install' while upgrading, and module4 should be loaded after module3
# As a result, the updating order is
# phase 0: base
# phase 1: module1 -> module2
# phase 2: module3
# phase 3: module4


class Package:
    """
    Python package for the Odoo module with the same name
    """
    def __init__(self, name: str, package_graph: PackageGraph) -> None:
        # manifest data
        self.name:str = name
        self.manifest :dict = get_manifest(name) or {}

        # ir_module_module data                     # column_name
        self.id :int = 0                            # id
        self.state :str = 'uninstalled'             # state
        self.dbdemo :bool = False                   # demo
        self.installed_version :str | None = None   # latest_version

        # info for upgrade
        self.load_state :str = 'uninstalled'        # the state when loaded to packages
        self.load_version :str | None = None        # the version when loaded to packages

        # dependency
        self.depends: OrderedSet[Package] = OrderedSet()
        self.package_graph :PackageGraph = package_graph

    @lazy_property
    def depth(self) -> int:
        """ Return the longest distance from self to module 'base' along dependencies. """
        return max(package.depth for package in self.depends) + 1 if self.depends else 0

    @lazy_property
    def phase(self) -> int:
        if self.name == 'base':
            return 0

        if self.package_graph.mode == 'load':
            return 1

        def not_in_the_same_phase(package: Package, dependency: Package) -> bool:
            return (package.state == 'to install') ^ (dependency.state == 'to install') or dependency.name == 'base'

        return max(
            dependency.phase + 1 if not_in_the_same_phase(self, dependency) else dependency.phase
            for dependency in self.depends
        )

    @property
    def loading_sort_key(self) -> tuple[int, str]:
        return self.depth, self.name

    @property
    def updating_sort_key(self) -> tuple[int, int, str]:
        return self.phase, self.depth, self.name

    def demo_installable(self) -> bool:
        return all(p.dbdemo for p in self.depends)


class PackageGraph:
    """
    Sorted Python packages for Odoo modules with the same names ordered by (package.phase, package.depth, package.name)
    """

    def __init__(self, cr: BaseCursor, mode: Literal['load', 'update'] = 'load') -> None:
        self.mode :Literal['load', 'update'] = mode
        self._packages: dict[str, Package] = {}
        self._cr :BaseCursor = cr
        self._sort_key = (lambda package: package.updating_sort_key) \
            if mode == 'update' else (lambda package: package.loading_sort_key)

    def __contains__(self, name: str) -> bool:
        return name in self._packages

    def __getitem__(self, name: str) -> Package:
        return self._packages[name]

    def __iter__(self) -> Iterator[Package]:
        return iter(sorted(self._packages.values(), key=self._sort_key))

    def __len__(self) -> int:
        return len(self._packages)
    
    def add(self, names: list[str]) -> None:
        for name in names:
            package = self._packages[name] = Package(name, self)
            if not package.manifest.get('installable'):
                message = None if name in self._imported_modules else 'not_installable'
                self._remove(name, message)

        self._update_depends(names)
        self._update_depth(names)
        self._update_from_database(names)

    @lazy_property
    def _imported_modules(self) -> OrderedSet[str]:
        result = ['studio_customization']
        if column_exists(self._cr, 'ir_module_module', 'imported'):
            self._cr.execute('SELECT name FROM ir_module_module WHERE imported')
            result += [m[0] for m in self._cr.fetchall()]
        return OrderedSet(result)

    def _update_depends(self, names: Iterable[str]) -> None:
        for name in names:
            if package := self._packages.get(name):
                try:
                    package.depends = OrderedSet(self._packages[dep] for dep in package.manifest['depends'])
                except KeyError:
                    self._remove(name, 'missing_depends')

    def _update_depth(self, names: Iterable[str]) -> None:
        for name in names:
            if package := self._packages.get(name):
                try:
                    package.depth
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
            if state == 'uninstallable':
                self._remove(name, 'not_installable')
                continue
            if self.mode == 'load' and state in ['to install', 'uninstalled']:
                self._remove(name, 'not_installed')
                continue
            if name not in self._packages:
                # has been recursively removed for sake of not_installable or not_installed
                continue
            package = self._packages[name]
            package.id = id_
            package.state = state
            package.dbdemo = demo
            package.installed_version = installed_version
            package.load_version = installed_version
            package.load_state = state

    def _remove(self, name: str, reason: str | None = None) -> None:
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
        'not_installed': (_logger.info, 'not installed or some depends are not installed, skipped'),
        'missing_depends': (_logger.info, 'some depends are not loaded, skipped'),
    }
