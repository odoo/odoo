# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#    Copyright (C) 2010-2011 OpenERP s.a. (<http://openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

""" Modules dependency graph. """

import os, sys, imp
from os.path import join as opj
import itertools
import zipimport

import openerp

import openerp.osv as osv
import openerp.tools as tools
import openerp.tools.osutil as osutil
from openerp.tools.safe_eval import safe_eval as eval
import openerp.pooler as pooler
from openerp.tools.translate import _

import openerp.netsvc as netsvc

import zipfile
import openerp.release as release

import re
import base64
from zipfile import PyZipFile, ZIP_DEFLATED
from cStringIO import StringIO

import logging

logger = netsvc.Logger()


class Graph(dict):
    """ Modules dependency graph.

    The graph is a mapping from module name to Nodes.

    """

    def add_node(self, name, info):
        max_depth, father = 0, None
        for n in [Node(x, self, None) for x in info['depends']]:
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
        additional_data = dict.fromkeys(self.keys(), {'id': 0, 'state': 'uninstalled', 'dbdemo': False, 'installed_version': None})
        ## Then we get the values from the database
        cr.execute('SELECT name, id, state, demo AS dbdemo, latest_version AS installed_version'
                   '  FROM ir_module_module'
                   ' WHERE name IN %s',(tuple(additional_data),)
                   )

        ## and we update the default values with values from the database
        additional_data.update(dict([(x.pop('name'), x) for x in cr.dictfetchall()]))

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
            info = openerp.modules.module.load_information_from_description_file(module)
            if info['installable']:
                packages.append((module, info)) # TODO directly a dict, like in get_modules_with_version
            else:
                logger.notifyChannel('init', netsvc.LOG_WARNING, 'module %s: not installable, skipped' % (module))

        dependencies = dict([(p, info['depends']) for p, info in packages])
        current, later = set([p for p, info in packages]), set()

        while packages and current > later:
            package, info = packages[0]
            deps = info['depends']

            # if all dependencies of 'package' are already in the graph, add 'package' in the graph
            if reduce(lambda x, y: x and y in self, deps, True):
                if not package in current:
                    packages.pop(0)
                    continue
                later.clear()
                current.remove(package)
                node = self.add_node(package, info)
                node.data = info
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
            logger.notifyChannel('init', netsvc.LOG_ERROR, 'module %s: Unmet dependencies: %s' % (package, ', '.join(unmet_deps)))

        result = len(self) - len_graph
        if result != len(module_list):
            logger.notifyChannel('init', netsvc.LOG_WARNING, 'Not all modules have loaded.')
        return result


    def __iter__(self):
        level = 0
        done = set(self.keys())
        while done:
            level_modules = [(name, module) for name, module in self.items() if module.depth==level]
            for name, module in level_modules:
                done.remove(name)
                yield module
            level += 1


class Singleton(object):
    def __new__(cls, name, graph, info):
        if name in graph:
            inst = graph[name]
        else:
            inst = object.__new__(cls)
            inst.name = name
            inst.info = info
            graph[name] = inst
        return inst


class Node(Singleton):
    """ One module in the modules dependency graph.

    Node acts as a per-module singleton. A node is constructed via
    Graph.add_module() or Graph.add_modules(). Some of its fields are from
    ir_module_module (setted by Graph.update_from_db()).

    """

    def __init__(self, name, graph, info):
        self.graph = graph
        if not hasattr(self, 'children'):
            self.children = []
        if not hasattr(self, 'depth'):
            self.depth = 0

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
        super(Singleton, self).__setattr__(name, value)
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


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
