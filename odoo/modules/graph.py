# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

""" Modules dependency graph. """

import os, sys, imp
from os.path import join as opj
import itertools
import zipimport

import odoo

import odoo.osv as osv
import odoo.tools as tools
import odoo.tools.osutil as osutil
from odoo.tools.translate import _

import zipfile
import odoo.release as release

import re
import base64
from zipfile import PyZipFile, ZIP_DEFLATED
from cStringIO import StringIO

import logging

_logger = logging.getLogger(__name__)

class Graph(dict):
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
        if not len(self):
            return
        # update the graph with values from the database (if exist)
        ## First, we set the default values for each package in graph
        additional_data = dict((key, {'id': 0, 'state': 'uninstalled', 'dbdemo': False, 'installed_version': None}) for key in self.keys())
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

    def add_module(self, cr, module, force=None):
        self.add_modules(cr, [module], force)

    def add_modules(self, cr, module_list, force=None):
        if force is None:
            force = []
        packages = []
        len_graph = len(self)
        for module in module_list:
            # This will raise an exception if no/unreadable descriptor file.
            # NOTE The call to load_information_from_description_file is already
            # done by db.initialize, so it is possible to not do it again here.
            info = odoo.modules.module.load_information_from_description_file(module)
            if info and info['installable']:
                packages.append((module, info)) # TODO directly a dict, like in get_modules_with_version
            else:
                _logger.warning('module %s: not installable, skipped', module)

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
                for kind in ('init', 'demo', 'update'):
                    if package in tools.config[kind] or 'all' in tools.config[kind] or kind in force:
                        setattr(node, kind, True)
            else:
                later.add(package)
                packages.append((package, info))
            packages.pop(0)

        self.update_from_db(cr)

        for package in later:
            unmet_deps = filter(lambda p: p not in self, dependencies[package])
            _logger.error('module %s: Unmet dependencies: %s', package, ', '.join(unmet_deps))

        result = len(self) - len_graph
        if result != len(module_list):
            _logger.warning('Some modules were not loaded.')
        return result


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
    ir_module_module (setted by Graph.update_from_db()).

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
        self.children.sort(lambda x, y: cmp(x.name, y.name))
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
        return itertools.chain(iter(self.children), *map(iter, self.children))

    def __str__(self):
        return self._pprint()

    def _pprint(self, depth=0):
        s = '%s\n' % self.name
        for c in self.children:
            s += '%s`-> %s' % ('   ' * depth, c._pprint(depth+1))
        return s
