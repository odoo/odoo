# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
import logging
from unittest.mock import patch
from typing import Iterable, List, Dict

from odoo.tests.common import BaseCase, TransactionCase
from odoo.modules.graph import PackageGraph
from odoo.modules.module import _DEFAULT_MANIFEST, get_manifest
from odoo.tools import mute_logger

from .graph_legacy import Graph as GraphLegacy

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
                patch(__package__ + '.graph_legacy.Graph.update_from_db'), \
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


class TestGraphAll(TransactionCase):
    @mute_logger('odoo.modules.graph')
    def test_graph_order_all(self):
        self.env['ir.module.module'].update_list()
        modules = self.env['ir.module.module'].search([])
        module_names = modules.mapped('name')
        for module_name in module_names:  # cache manifest for fair performance comparison
            get_manifest(module_name)

        modules.filtered(lambda m: m.state != 'uninstallable').state = 'installed'
        modules.flush_model()

        graph = PackageGraph(self.cr)
        graph_legacy = GraphLegacy()

        time0 = time.time()
        graph.add(module_names)
        names = list(p.name for p in graph)
        time1 = time.time()

        time0_legacy = time.time()
        graph_legacy.add_modules(self.cr, module_names)
        names_legacy = list(g.name for g in graph_legacy)
        time1_legacy = time.time()

        self.assertListEqual(names, names_legacy)
        _logger.info('\nCurrent Graph order time: %s\nLegacy Graph order time: %s', time1 - time0, time1_legacy - time0_legacy)
