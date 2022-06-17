# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

""" Modules dependency graph. """

import itertools
import logging

import odoo
import odoo.tools as tools

_logger = logging.getLogger(__name__)

class Graph(dict):
    """ Modules dependency graph.

    The graph is a mapping from module name to Nodes.

    """

    def add_node(self, name, info):
        child_node = None
        for d in info['depends'] + info['soft_depends']:
            n = self.get(d) or Node(d, self, None)  # lazy creation, do not use default value for get()
            # the child node instance is always the same as long as the name remains
            # the same (thanks to `Node.__new__` implementation). This allow us to have
            # the exact same Node under multiple parents.
            child_node = n.add_child(name, info)
        if child_node:
            return child_node
        else:
            return Node(name, self, info)

    def update_from_db(self, cr):
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
            elif module != 'studio_customization':
                _logger.warning('module %s: not installable, skipped', module)

        # sort packages by name to ensure consistent loading
        # m[0] is the module name, m[1] is the manifest dictionnary.
        packages.sort(key=lambda m: m[0])

        dependencies = dict([(p, info['depends']) for p, info in packages])
        current, later = set([p for p, info in packages]), set()

        while packages and current > later:
            package, info = packages[0]
            deps = info['depends']

            # add soft dependencies only if these modules exists
            available_deps = [x for x in info['soft_depends'] if x in dependencies]
            if available_deps:
                deps = deps + available_deps

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


    def __iter__(self):
        todo = set(self.keys())

        def fill_modules_children(module, modlist):
            modlist.append(module)
            for child in module.children:
                fill_modules_children(child, modlist)

        # retrieve all root modules
        root_modules = Node.sort([m for m in self.values() if not m.parents])
        all_modules = []
        for root_module in root_modules:
            fill_modules_children(root_module, all_modules)
        # now returns all modules in the given order which respects priorities but waits
        # for all dependencies to be added first.
        while todo:
            todo_modules = [m for m in all_modules if m.name in todo]
            for module in todo_modules:
                if module.name not in todo:
                    continue
                waiting_dependencies = [m for m in module.depends if m in todo]
                if waiting_dependencies:
                    continue
                todo.remove(module.name)
                yield module

    def __str__(self):
        return '\n'.join(str(n) for n in self if not n.parents)
    
    def _pprint(self):
        TABLE_FMT = "{:<6} {:<10} {:<60} {}\n"
        res = TABLE_FMT.format("Index", "Priority", "Name", "Dependencies")
        for index, node in enumerate(self):
            res += TABLE_FMT.format(index, node.priority or "", node.name, str(node.depends))
        return res

class Node(object):
    """ One module in the modules dependency graph.

    Node acts as a per-module singleton. A node is constructed via
    Graph.add_module() or Graph.add_modules(). Some of its fields are from
    ir_module_module (set by Graph.update_from_db()).

    """
    def __new__(cls, name, graph, info):
        if name in graph:
            inst = graph[name]
            inst.info = info
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
        if not hasattr(self, 'parents'):
            self.parents = []
        if not hasattr(self, 'priority'):
            self.priority = 0

    @property
    def data(self):
        return self.info

    @property
    def depends(self):
        if self.info:
            return self.info["depends"] + self.info["soft_depends"]
        return []

    @staticmethod
    def sort(nodes):
        return sorted(nodes, key=lambda node: (-node.priority, node.name))

    def add_child(self, name, info):
        node = Node(name, self.graph, info)
        if self not in node.parents:
            node.parents.append(self)
        if node not in self.children:
            self.children.append(node)
        for attr in ('init', 'update', 'demo'):
            if hasattr(self, attr):
                setattr(node, attr, True)
        if node.priority:
            self._add_priority(node.priority)
        self.children = Node.sort(self.children)
        return node

    def __setattr__(self, name, value):
        super(Node, self).__setattr__(name, value)
        if name in ('init', 'update', 'demo'):
            tools.config[name][self.name] = 1
            for child in self.children:
                setattr(child, name, value)
        if name == "info":
            if self.info and self.info.get("loading_priority"):
                self.priority = self.info.get("loading_priority")

    def _add_priority(self, value):
        self.priority += value
        for parent in self.parents:
            parent._add_priority(value)

    def __iter__(self):
        return itertools.chain(
            self.children,
            itertools.chain.from_iterable(self.children)
        )

    def __str__(self):
        return self._pprint()

    def _pprint(self, level=0):
        s = '%s' % self.name
        if self.priority:
            s += ' (priority: %d)' % self.priority
        s += '\n'
        for c in self.children:
            s += '%s`-> %s' % ('   ' * level, c._pprint(level+1))
        return s

    def should_have_demo(self):
        return (hasattr(self, 'demo') or (self.dbdemo and self.state != 'installed')) and all(p.dbdemo for p in self.parents)
