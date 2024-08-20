# Part of Odoo. See LICENSE file for full copyright and licensing details.

""" Modules dependency graph. """
from __future__ import annotations

import functools
import itertools
import logging
import typing

import odoo.tools as tools

from .module import get_manifest

if typing.TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from odoo.sql_db import BaseCursor

_logger = logging.getLogger(__name__)


@functools.lru_cache(maxsize=1)
def _ignored_modules(cr: BaseCursor) -> list[str]:
    result = ['studio_customization']
    if tools.sql.column_exists(cr, 'ir_module_module', 'imported'):
        cr.execute('SELECT name FROM ir_module_module WHERE imported')
        result += [m[0] for m in cr.fetchall()]
    return result


class Graph(dict[str, 'Node']):
    """ Modules dependency graph.

    The graph is a mapping from module name to Nodes.

    """

    def add_node(self, name: str, info: dict) -> Node:
        max_depth, father = 0, None
        for d in info['depends']:
            n = self.get(d) or Node(d, self, None)  # lazy creation, do not use default value for get()
            if n.depth >= max_depth:
                father = n
                max_depth = n.depth
        if father:
            return father.add_child(name, info)
        else:
            return Node(name, self, info)

    def update_from_db(self, cr: BaseCursor):
        if not len(self):
            return
        # update the graph with values from the database (if exist)
        ## First, we set the default values for each package in graph
        additional_data = {key: {'id': 0, 'state': 'uninstalled', 'dbdemo': False, 'installed_version': None} for key in self.keys()}
        ## Then we get the values from the database
        cr.execute('SELECT name, id, state, demo AS dbdemo, latest_version AS installed_version'
                   '  FROM ir_module_module'
                   ' WHERE name IN %s',(tuple(additional_data),)
                   )

        ## and we update the default values with values from the database
        additional_data.update((x['name'], x) for x in cr.dictfetchall())

        for package in self.values():
            for k, v in additional_data[package.name].items():
                setattr(package, k, v)

    def add_module(self, cr: BaseCursor, module: str, force: list[str] | None = None):
        self.add_modules(cr, [module], force)

    def add_modules(self, cr: BaseCursor, module_list: list[str], force: list[str] | None = None):
        if force is None:
            force = []
        packages = []
        len_graph = len(self)
        for module in module_list:
            info = get_manifest(module)
            if info and info['installable']:
                packages.append((module, info)) # TODO directly a dict, like in get_modules_with_version
            elif module not in _ignored_modules(cr):
                _logger.warning('module %s: not installable, skipped', module)

        dependencies = {p: info['depends'] for p, info in packages}
        current: set[str] = {p for p, _info in packages}
        later: set[str] = set()

        while packages and current > later:
            package, info = packages[0]
            deps = info['depends']

            # if all dependencies of 'package' are already in the graph, add 'package' in the graph
            if all(dep in self for dep in deps):
                if not package in current:
                    packages.pop(0)
                    continue
                later.clear()
                current.remove(package)
                node = self.add_node(package, info)
                for kind in ('init', 'demo', 'update'):
                    if package in tools.config[kind] or 'all' in tools.config[kind] or kind in force:
                        setattr(node, kind, True)
            else:
                later.add(package)
                packages.append((package, info))
            packages.pop(0)

        self.update_from_db(cr)

        for package in later:
            unmet_deps = [p for p in dependencies[package] if p not in self]
            _logger.info('module %s: Unmet dependencies: %s', package, ', '.join(unmet_deps))

        return len(self) - len_graph

    def packages(self) -> Iterator[Node]:
        level = 0
        done = set(self.keys())
        while done:
            level_modules = sorted((name, module) for name, module in self.items() if module.depth==level)
            for name, module in level_modules:
                done.remove(name)
                yield module
            level += 1

    def __str__(self) -> str:
        return '\n'.join(str(n) for n in self.packages() if n.depth == 0)


class Node:
    """ One module in the modules dependency graph.

    Node acts as a per-module singleton. A node is constructed via
    Graph.add_module() or Graph.add_modules(). Some of its fields are from
    ir_module_module (set by Graph.update_from_db()).

    """
    id: int = 0
    state: str = 'uninstalled'
    installed_version: str | None = None
    dbdemo: bool = False

    def __new__(cls, name: str, graph: Graph, info):
        if name in graph:
            inst = graph[name]
        else:
            inst = object.__new__(cls)
            graph[name] = inst
        return inst

    def __init__(self, name: str, graph: Graph, info: dict | None):
        self.name = name
        self.graph = graph
        self.info: dict = info or typing.cast(dict, getattr(self, 'info', {}))
        if not hasattr(self, 'children'):
            self.children: list[Node] = []
        if not hasattr(self, 'depth'):
            self.depth: int = 0

    @property
    def data(self):
        return self.info

    def add_child(self, name: str, info: dict | None) -> Node:
        node = Node(name, self.graph, info)
        node.depth = self.depth + 1
        if node not in self.children:
            self.children.append(node)
        for attr in ('init', 'update', 'demo'):
            if hasattr(self, attr):
                setattr(node, attr, True)
        self.children.sort(key=lambda x: x.name)
        return node

    def __setattr__(self, name, value):
        super().__setattr__(name, value)
        if name in ('init', 'update', 'demo'):
            tools.config[name][self.name] = 1
            for child in self.children:
                setattr(child, name, value)
        if name == 'depth':
            for child in self.children:
                setattr(child, name, value + 1)

    def __iter__(self):
        return itertools.chain(
            self.children,
            itertools.chain.from_iterable(self.children)
        )

    def __str__(self):
        return self._pprint()

    def _pprint(self, depth: int = 0):
        s = '%s\n' % self.name
        for c in self.children:
            s += '%s`-> %s' % ('   ' * depth, c._pprint(depth+1))
        return s

    def should_have_demo(self) -> bool:
        return (hasattr(self, 'demo') or (self.dbdemo and self.state != 'installed')) and all(p.dbdemo for p in self.parents)  # type: ignore

    @property
    def parents(self) -> Iterable[Node]:
        if self.depth == 0:
            return []

        return (
            node for node in self.graph.values()
            if node.depth < self.depth
            if self in node.children
        )
