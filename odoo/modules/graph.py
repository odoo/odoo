# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

""" Modules dependency graph. """

import logging
from typing import Set, Dict, Tuple, Iterable, Iterator

import odoo
import odoo.tools as tools

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
# Since the Odoo update module by module(not perfect but successful solution), we sacrifice some determinacy of
# overriding order while installing modules to avoid raising errors.
# For example,
# 'installed' : base, module1, module2, module3, module4, module6
# 'to install': module5
# module6 extends modelA with an extra field1 = fields.Char(required=True, default='value')
# If the loading order is base -> module1 -> module2 -> module3 -> module4 -> module5 -> module6
# While loading and installing module5, module6 hasn't been loaded. If module5 imports a new record for modelA as data
# while installing, field1 won't be populated to the database and violates the not-null constraint
# So we load those non-'to install' modules at first if possible and then those 'to install' modules in the next phase
# As a result, the updating order is
# phase 0: base
# phase 1: module1 -> module2 -> module3 -> module4 -> module6
# phase 2: module5
#
# In summary:
# phase 0: base
# phase odd: (modules: 1. don't need init; 2. all depends modules have been loaded or going to be loaded in this phase)
# phase even: (models: 1. need init; 2. all depends modules have been loaded or going to be loaded in this phase)
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


class lazy_recursive_property(tools.lazy_property):
    """
    a non-thread-safe lazy recursive property
    """

    def __get__(self, obj, cls):
        if obj is None:
            return self
        _visited = f'_{self.fget.__name__}_visited'
        if getattr(obj, _visited, False):
            raise RecursionError
        setattr(obj, _visited, True)
        value = self.fget(obj)
        delattr(obj, _visited)
        setattr(obj, self.fget.__name__, value)
        return value


class Package:
    """
    Python package for the Odoo module with the same name
    """
    def __init__(self, name: str, package_graph: 'PackageGraph') -> None:
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
        self.package_graph = package_graph

    @lazy_recursive_property
    def depth(self) -> int:
        """ Return the longest distance from self to module 'base' along dependencies. """
        return max(package.depth for package in self.depends) + 1 if self.depends else 0

    @lazy_recursive_property
    def phase(self) -> int:
        if not self.package_graph._update_module:
            return 1 if self.depends else 0
        return max(
            package.phase + 1 if (package.state == 'to install') ^ (self.state == 'to install') or package.name == 'base'
            else package.phase for package in self.depends
        ) if self.depends else 0

    @property
    def loading_order(self) -> Tuple[int, str]:
        return self.depth, self.name

    @property
    def updating_order(self) -> Tuple[int, int, str]:
        return self.phase, self.depth, self.name

    def demo_installable(self) -> bool:
        return all(p.dbdemo for p in self.depends)


class PackageGraph:
    """
    Sorted Python packages for Odoo modules with the same names ordered by (package.phase, package.depth, package.name)
    """

    def __init__(self, cr, update_module=False) -> None:
        self._packages: Dict[str, Package] = {}
        self._cr = cr
        self._update_module = update_module
        self._sort_key = (lambda package: package.updating_order) \
            if update_module else (lambda package: package.loading_order)

    def __contains__(self, name: str) -> bool:
        return name in self._packages

    def __getitem__(self, name: str) -> Package:
        return self._packages[name]

    def __iter__(self) -> Iterator[Package]:
        return iter(sorted(self._packages.values(), key=self._sort_key))

    def __reversed__(self) -> Iterator[Package]:
        return iter(sorted(self._packages.values(), key=self._sort_key, reverse=True))

    def __len__(self) -> int:
        return len(self._packages)

    @property
    def is_loading_order_sorted(self) -> bool:
        return max(p.phase for p in self._packages.values()) <= 1 if self._update_module else True

    def add(self, names: Iterable[str]) -> None:
        for name in names:
            package = self._packages[name] = Package(name, self)
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
            if state == 'uninstallable':
                self._remove(name, 'not_installable')
            if not self._update_module and state == ['to install', 'uninstalled']:
                self._remove(name, 'not_installed')
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
        'not_installed': (_logger.info, 'not installed or some depends are not installed, skipped'),
        'missing_depends': (_logger.info, 'some depends are not loaded, skipped'),
    }
