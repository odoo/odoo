# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import BaseCase, TransactionCase
from odoo.tools.graph import PrimalGraph, ReversibleGraph, RelationalGraph


class TestGraph(BaseCase):
    def setUp(self) -> None:
        super().setUp()

        self.graph = ReversibleGraph()
        self.graph.build_node(1)
        for i in range(2, 16):
            self.graph.build_node(i)
            self.graph.build_edge(i//2, i)

    def test_graph_size(self):
        self.assertEqual(len(self.graph), 15)

    def test_depth_first_search(self):
        self.graph.build_edge(5, 4)
        self.graph.build_edge(4, 5)
        reachable = list(self.graph.reachable_from({2}))
        self.assertSetEqual(set(reachable), {2, 4, 5, 8, 9, 10, 11})
        self.assertEqual(len(reachable), len(set(reachable)))

    def test_acyclic_paths(self):
        self.graph.build_edge(10, 6)
        self.graph.build_edge(14, 6)
        result = {node: 0 for node in self.graph.nodes()}
        for path in self.graph.acyclic_paths({1}):
            result[path.nodes[-1]] += 1
        self.assertEqual(result[6], 3)

    def test_components(self):
        # Strongly connect the nodes 10, 11 and 12.
        self.graph.build_edge(10, 11)
        self.graph.build_edge(11, 12)
        self.graph.build_edge(12, 10)
        for component in self.graph.components():
            size = 3 if 10 in component else 1
            self.assertTrue(len(component) == size)


class TestRegistryGraph(TransactionCase):
    def setUp(self) -> None:
        super().setUp()

        self.graph = RelationalGraph(self.registry, reverse=True)

    def test_selectors(self):
        self.graph.include(lambda field: field.type == 'many2one')
        self.graph.include(lambda field: field.type == 'many2many')
        self.graph.require(lambda field: field.store)
        self.graph.require(lambda field: not field.company_dependent)
        for field in self.graph[self.env['ir.model']]:
            self.assertIn(field.type, ('many2one', 'many2many'))
            self.assertFalse(field.company_dependent)
            self.assertTrue(field.store)


class TestHyperGraph(BaseCase):
    def setUp(self):
        self.graph = PrimalGraph(constructor=lambda x: (x,))

    def test_build_nodes(self):
        self.graph.build_nodes((1, 2, 3, 4, 5))
        self.assertEqual(len(self.graph._nodes), 5)
        self.assertEqual(len(self.graph._sizes), 1)

        self.graph.build_nodes((2, 3, 4, 5, 6))
        self.assertEqual(len(self.graph._nodes), 6)
        self.assertEqual(len(self.graph._sizes), 3)

        self.graph.build_nodes((3, 4, 6, 7, 8))
        self.assertEqual(len(self.graph._nodes), 8)
        self.assertEqual(len(self.graph._sizes), 5)

    def test_reachable_from(self):
        a, x = (1, 2, 3), (6, 7, 8)
        b, y = (3, 4, 5), (8, 9)

        for nodes in [a, b, x, y]:
            self.graph.build_nodes(nodes)

        self.graph.build_edges(a, x)
        self.graph.build_edges(b, y)

        gen = self.graph.reachable_from([(3,)])
        self.assertSetEqual(set(gen), {(3,), (6, 7), (8,), (9,)})

        gen = self.graph.reachable_from([(1, 2)])
        self.assertSetEqual(set(gen), {(1, 2), (6, 7), (8,)})

        self.graph = self.graph.transpose()

        gen = self.graph.reachable_from([(8,)])
        self.assertSetEqual(set(gen), {(8,), (1, 2), (3,), (4, 5)})

        gen = self.graph.reachable_from([(6, 7)])
        self.assertSetEqual(set(gen), {(6, 7), (1, 2), (3,)})
