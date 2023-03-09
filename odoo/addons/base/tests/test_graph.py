# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
import logging
from unittest.mock import patch
from typing import Iterable, List, Dict

from odoo.tests.common import BaseCase, TransactionCase
from odoo.modules.graph import PackageGraph
from odoo.modules.module import _DEFAULT_MANIFEST
from odoo.tools import mute_logger

_logger = logging.getLogger(__name__)

class TestGraph(BaseCase):
    @mute_logger('odoo.modules.graph')
    def _test_graph_order(
            self,
            dependency: Dict[str, List[str]],
            modules_list: Iterable[Iterable[str]],
            expected: List[str]
    ) -> None:
        """
        Test the order of the modules that need to be loaded

        :param dependency: A dictionary of module dependency: {module_a: [module_b, module_c]}
        :param modules_list: [['module_a', 'module_b'], ['module_c'], ...]
            module_a and module_b will be added in the first round
            module_c will be added in the second round
            ...
        :param expected: expected graph order
        """
        manifests = {
            name: {**_DEFAULT_MANIFEST.copy(), **{'depends': depends}}
            for name, depends in dependency.items()
        }
        with patch('odoo.modules.graph.PackageGraph._update_from_database'), \
                patch('odoo.modules.module.get_manifest', lambda name: manifests.get(name, {})):
            graph = PackageGraph(None)
            graph_legacy = GraphLegacy()

            for modules in modules_list:
                graph.add(modules)
                graph_legacy.add_modules(None, modules)

            names = list(p.name for p in graph)
            names_legacy = list(p.name for p in graph_legacy)

            self.assertListEqual(names, expected)
            self.assertListEqual(names_legacy, expected)

    def test_graph_order_1(self):
        dependency = {
            'base': [],
            'module1': ['base'],
            'module2': ['module1'],
            'module3': ['module1'],
            'module4': ['module2', 'module3'],
            'module5': ['module2', 'module4'],
        }
        # modules are in random order
        self._test_graph_order(
            dependency,
            [['base'], ['module3', 'module4', 'module1', 'module5', 'module2']],
            ['base', 'module1', 'module2', 'module3', 'module4', 'module5']
        )
        # module 5's depends is missing
        self._test_graph_order(
            dependency,
            [['base'], ['module1', 'module2', 'module3', 'module5']],
            ['base', 'module1', 'module2', 'module3']
        )
        # module 6's manifest is missing
        self._test_graph_order(
            dependency,
            [['base'], ['module1', 'module2', 'module3', 'module4', 'module5', 'module6']],
            ['base', 'module1', 'module2', 'module3', 'module4', 'module5']
        )
        # three adding rounds
        self._test_graph_order(
            dependency,
            [['base'], ['module1', 'module2', 'module3'], ['module4', 'module5']],
            ['base', 'module1', 'module2', 'module3', 'module4', 'module5']
        )

    def test_graph_order_2(self):
        dependency = {
            'base': [],
            'module1': ['base'],
            'module2': ['module1'],
            'module3': ['module1'],
            'module4': ['module3'],
            'module5': ['module2'],
        }
        # module4 and module5 have the same depth but don't have shared depends
        # they should be ordered by name
        self._test_graph_order(
            dependency,
            [['base'], ['module3', 'module4', 'module1', 'module5', 'module2']],
            ['base', 'module1', 'module2', 'module3', 'module4', 'module5']
        )

    def test_graph_order_3(self):
        dependency = {
            'base': [],
            'module1': ['base'],
            'module2': ['module1'],
            # depends loop
            'module3': ['module1', 'module5'],
            'module4': ['module2', 'module3'],
            'module5': ['module2', 'module4'],
        }
        self._test_graph_order(
            dependency,
            [['base'], ['module3', 'module4', 'module1', 'module5', 'module2']],
            ['base', 'module1', 'module2']
        )


# test doesn't work because the order depends on the state which should not be 'uninstalled'
# class TestGraphAll(TransactionCase):
#     @mute_logger('odoo.modules.graph')
#     def test_graph_order_all(self):
#         self.env['ir.module.module'].update_list()
#         modules = self.env['ir.module.module'].search([]).mapped('name')
#         for module in modules:  # cache manifest for fair performance comparison
#             odoo.modules.module.get_manifest(module)
#
#         graph = PackageGraph(self.cr)
#         graph_legacy = GraphLegacy()
#
#         time0 = time.time()
#         graph.add(modules)
#         names = list(p.name for p in graph)
#         time1 = time.time()
#
#         time0_legacy = time.time()
#         graph_legacy.add_modules(self.cr, modules)
#         names_legacy = list(g.name for g in graph_legacy)
#         time1_legacy = time.time()
#
#         self.assertListEqual(names, names_legacy)
#         _logger.info('\nCurrent Graph order time: %s\nLegacy Graph order time: %s', time1 - time0, time1_legacy - time0_legacy)


# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

""" Modules dependency graph. """

import itertools
# import logging

import odoo
import odoo.tools as tools

# _logger = logging.getLogger(__name__)

class GraphLegacy(dict):
    """ Modules dependency graph.

    The graph is a mapping from module name to Nodes.

    """

    def add_node(self, name, info):
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

    def update_from_db(self, cr):
        return
        # if not len(self):
        #     return
        # # update the graph with values from the database (if exist)
        # ## First, we set the default values for each package in graph
        # additional_data = {key: {'id': 0, 'state': 'uninstalled', 'dbdemo': False, 'installed_version': None} for key in
        #                    self.keys()}
        # ## Then we get the values from the database
        # cr.execute('SELECT name, id, state, demo AS dbdemo, latest_version AS installed_version'
        #            '  FROM ir_module_module'
        #            ' WHERE name IN %s', (tuple(additional_data),)
        #            )
        #
        # ## and we update the default values with values from the database
        # additional_data.update((x['name'], x) for x in cr.dictfetchall())
        #
        # for package in self.values():
        #     for k, v in additional_data[package.name].items():
        #         setattr(package, k, v)

    def add_module(self, cr, module, force=None):
        self.add_modules(cr, [module], force)

    def add_modules(self, cr, module_list, force=None):
        if force is None:
            force = []
        packages = []
        len_graph = len(self)
        for module in module_list:
            info = odoo.modules.module.get_manifest(module)
            if info and info['installable']:
                packages.append((module, info)) # TODO directly a dict, like in get_modules_with_version
            # elif module != 'studio_customization':
            #     _logger.warning('module %s: not installable, skipped', module)

        dependencies = dict([(p, info['depends']) for p, info in packages])
        current, later = set([p for p, info in packages]), set()

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
                # for kind in ('init', 'demo', 'update'):
                #     if package in tools.config[kind] or 'all' in tools.config[kind] or kind in force:
                #         setattr(node, kind, True)
            else:
                later.add(package)
                packages.append((package, info))
            packages.pop(0)

        self.update_from_db(cr)

        for package in later:
            unmet_deps = [p for p in dependencies[package] if p not in self]
            # _logger.info('module %s: Unmet dependencies: %s', package, ', '.join(unmet_deps))

        return len(self) - len_graph


    def __iter__(self):
        level = 0
        done = set(self.keys())
        while done:
            level_modules = sorted((name, module) for name, module in self.items() if module.depth==level)
            for name, module in level_modules:
                done.remove(name)
                yield module
            level += 1

    def __str__(self):
        return '\n'.join(str(n) for n in self if n.depth == 0)

class Node(object):
    """ One module in the modules dependency graph.

    Node acts as a per-module singleton. A node is constructed via
    Graph.add_module() or Graph.add_modules(). Some of its fields are from
    ir_module_module (set by Graph.update_from_db()).

    """
    def __new__(cls, name, graph, info):
        if name in graph:
            inst = graph[name]
        else:
            inst = object.__new__(cls)
            graph[name] = inst
        return inst

    def __init__(self, name, graph, info):
        self.name = name
        self.graph = graph
        self.info = info or getattr(self, 'info', {})
        if not hasattr(self, 'children'):
            self.children = []
        if not hasattr(self, 'depth'):
            self.depth = 0

    @property
    def data(self):
        return self.info

    def add_child(self, name, info):
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
        super(Node, self).__setattr__(name, value)
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

    def _pprint(self, depth=0):
        s = '%s\n' % self.name
        for c in self.children:
            s += '%s`-> %s' % ('   ' * depth, c._pprint(depth+1))
        return s

    def should_have_demo(self):
        return (hasattr(self, 'demo') or (self.dbdemo and self.state != 'installed')) and all(p.dbdemo for p in self.parents)

    @property
    def parents(self):
        if self.depth == 0:
            return []

        return (
            node for node in self.graph.values()
            if node.depth < self.depth
            if self in node.children
        )



