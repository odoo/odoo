# copyright 2019 Camptocamp
# license agpl-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import gc
import logging
from unittest import mock

from odoo.tests import common

from odoo.addons.queue_job.delay import Delayable, DelayableGraph


class TestDelayable(common.BaseCase):
    def setUp(self):
        super().setUp()
        self.recordset = mock.MagicMock(name="recordset")

    def test_delayable_set(self):
        # Use gc for garbage collection and use assertLogs to suppress WARNING
        with self.assertLogs("odoo.addons.queue_job.delay", level=logging.WARNING):
            dl = Delayable(self.recordset)
            dl.set(priority=15)
            self.assertEqual(dl.priority, 15)
            dl.set({"priority": 20, "description": "test"})
            self.assertEqual(dl.priority, 20)
            self.assertEqual(dl.description, "test")
            del dl
            gc.collect()

    def test_delayable_set_unknown(self):
        # Use gc for garbage collection and use assertLogs to suppress WARNING
        with self.assertLogs("odoo.addons.queue_job.delay", level=logging.WARNING):
            dl = Delayable(self.recordset)
            with self.assertRaises(ValueError):
                dl.set(foo=15)
            del dl
            gc.collect()

    def test_graph_add_vertex_edge(self):
        graph = DelayableGraph()
        graph.add_vertex("a")
        self.assertEqual(graph._graph, {"a": set()})
        graph.add_edge("a", "b")
        self.assertEqual(graph._graph, {"a": {"b"}, "b": set()})
        graph.add_edge("b", "c")
        self.assertEqual(graph._graph, {"a": {"b"}, "b": {"c"}, "c": set()})

    def test_graph_vertices(self):
        graph = DelayableGraph({"a": {"b"}, "b": {"c"}, "c": set()})
        self.assertEqual(graph.vertices(), {"a", "b", "c"})

    def test_graph_edges(self):
        graph = DelayableGraph(
            {"a": {"b"}, "b": {"c", "d"}, "c": {"e"}, "d": set(), "e": set()}
        )
        self.assertEqual(
            sorted(graph.edges()),
            sorted(
                [
                    ("a", "b"),
                    ("b", "c"),
                    ("b", "d"),
                    ("c", "e"),
                ]
            ),
        )

    def test_graph_connect(self):
        # Use gc for garbage collection and use assertLogs to suppress WARNING
        with self.assertLogs("odoo.addons.queue_job.delay", level=logging.WARNING):
            node_tail = Delayable(self.recordset)
            node_tail2 = Delayable(self.recordset)
            node_middle = Delayable(self.recordset)
            node_top = Delayable(self.recordset)
            node_middle.on_done(node_tail)
            node_middle.on_done(node_tail2)
            node_top.on_done(node_middle)
            collected = node_top._graph._connect_graphs()
            self.assertEqual(
                collected._graph,
                {
                    node_tail: set(),
                    node_tail2: set(),
                    node_middle: {node_tail, node_tail2},
                    node_top: {node_middle},
                },
            )

            del node_tail, node_tail2, node_middle, node_top, collected
            gc.collect()

    def test_graph_paths(self):
        graph = DelayableGraph(
            {"a": {"b"}, "b": {"c", "d"}, "c": {"e"}, "d": set(), "e": set()}
        )
        paths = list(graph.paths("a"))
        self.assertEqual(sorted(paths), sorted([["a", "b", "d"], ["a", "b", "c", "e"]]))
        paths = list(graph.paths("b"))
        self.assertEqual(sorted(paths), sorted([["b", "d"], ["b", "c", "e"]]))
        paths = list(graph.paths("c"))
        self.assertEqual(paths, [["c", "e"]])
        paths = list(graph.paths("d"))
        self.assertEqual(paths, [["d"]])
        paths = list(graph.paths("e"))
        self.assertEqual(paths, [["e"]])

    def test_graph_repr(self):
        graph = DelayableGraph(
            {"a": {"b"}, "b": {"c", "d"}, "c": {"e"}, "d": set(), "e": set()}
        )
        actual = repr(graph)
        expected = ["'a' → 'b' → 'c' → 'e'", "'a' → 'b' → 'd'"]
        self.assertEqual(sorted(actual.split("\n")), expected)

    def test_graph_topological_sort(self):
        # the graph is an example from
        # https://en.wikipedia.org/wiki/Topological_sorting
        # if you want a visual representation
        graph = DelayableGraph(
            {
                5: {11},
                7: {11, 8},
                3: {8, 10},
                11: {2, 9, 10},
                2: set(),
                8: {9},
                9: set(),
                10: set(),
            }
        )

        # these are all the pre-computed combinations that
        # respect the dependencies order
        valid_solutions = [
            [3, 5, 7, 8, 11, 2, 9, 10],
            [3, 5, 7, 8, 11, 2, 10, 9],
            [3, 5, 7, 8, 11, 9, 2, 10],
            [3, 5, 7, 8, 11, 9, 10, 2],
            [3, 5, 7, 8, 11, 10, 2, 9],
            [3, 5, 7, 8, 11, 10, 9, 2],
            [3, 5, 7, 11, 2, 8, 9, 10],
            [3, 5, 7, 11, 2, 8, 10, 9],
            [3, 5, 7, 11, 2, 10, 8, 9],
            [3, 5, 7, 11, 8, 2, 9, 10],
            [3, 5, 7, 11, 8, 2, 10, 9],
            [3, 5, 7, 11, 8, 9, 2, 10],
            [3, 5, 7, 11, 8, 9, 10, 2],
            [3, 5, 7, 11, 8, 10, 2, 9],
            [3, 5, 7, 11, 8, 10, 9, 2],
            [3, 5, 7, 11, 10, 2, 8, 9],
            [3, 5, 7, 11, 10, 8, 2, 9],
            [3, 5, 7, 11, 10, 8, 9, 2],
            [3, 7, 5, 8, 11, 2, 9, 10],
            [3, 7, 5, 8, 11, 2, 10, 9],
            [3, 7, 5, 8, 11, 9, 2, 10],
            [3, 7, 5, 8, 11, 9, 10, 2],
            [3, 7, 5, 8, 11, 10, 2, 9],
            [3, 7, 5, 8, 11, 10, 9, 2],
            [3, 7, 5, 11, 2, 8, 9, 10],
            [3, 7, 5, 11, 2, 8, 10, 9],
            [3, 7, 5, 11, 2, 10, 8, 9],
            [3, 7, 5, 11, 8, 2, 9, 10],
            [3, 7, 5, 11, 8, 2, 10, 9],
            [3, 7, 5, 11, 8, 9, 2, 10],
            [3, 7, 5, 11, 8, 9, 10, 2],
            [3, 7, 5, 11, 8, 10, 2, 9],
            [3, 7, 5, 11, 8, 10, 9, 2],
            [3, 7, 5, 11, 10, 2, 8, 9],
            [3, 7, 5, 11, 10, 8, 2, 9],
            [3, 7, 5, 11, 10, 8, 9, 2],
            [3, 7, 8, 5, 11, 2, 9, 10],
            [3, 7, 8, 5, 11, 2, 10, 9],
            [3, 7, 8, 5, 11, 9, 2, 10],
            [3, 7, 8, 5, 11, 9, 10, 2],
            [3, 7, 8, 5, 11, 10, 2, 9],
            [3, 7, 8, 5, 11, 10, 9, 2],
            [5, 3, 7, 8, 11, 2, 9, 10],
            [5, 3, 7, 8, 11, 2, 10, 9],
            [5, 3, 7, 8, 11, 9, 2, 10],
            [5, 3, 7, 8, 11, 9, 10, 2],
            [5, 3, 7, 8, 11, 10, 2, 9],
            [5, 3, 7, 8, 11, 10, 9, 2],
            [5, 3, 7, 11, 2, 8, 9, 10],
            [5, 3, 7, 11, 2, 8, 10, 9],
            [5, 3, 7, 11, 2, 10, 8, 9],
            [5, 3, 7, 11, 8, 2, 9, 10],
            [5, 3, 7, 11, 8, 2, 10, 9],
            [5, 3, 7, 11, 8, 9, 2, 10],
            [5, 3, 7, 11, 8, 9, 10, 2],
            [5, 3, 7, 11, 8, 10, 2, 9],
            [5, 3, 7, 11, 8, 10, 9, 2],
            [5, 3, 7, 11, 10, 2, 8, 9],
            [5, 3, 7, 11, 10, 8, 2, 9],
            [5, 3, 7, 11, 10, 8, 9, 2],
            [5, 7, 3, 8, 11, 2, 9, 10],
            [5, 7, 3, 8, 11, 2, 10, 9],
            [5, 7, 3, 8, 11, 9, 2, 10],
            [5, 7, 3, 8, 11, 9, 10, 2],
            [5, 7, 3, 8, 11, 10, 2, 9],
            [5, 7, 3, 8, 11, 10, 9, 2],
            [5, 7, 3, 11, 2, 8, 9, 10],
            [5, 7, 3, 11, 2, 8, 10, 9],
            [5, 7, 3, 11, 2, 10, 8, 9],
            [5, 7, 3, 11, 8, 2, 9, 10],
            [5, 7, 3, 11, 8, 2, 10, 9],
            [5, 7, 3, 11, 8, 9, 2, 10],
            [5, 7, 3, 11, 8, 9, 10, 2],
            [5, 7, 3, 11, 8, 10, 2, 9],
            [5, 7, 3, 11, 8, 10, 9, 2],
            [5, 7, 3, 11, 10, 2, 8, 9],
            [5, 7, 3, 11, 10, 8, 2, 9],
            [5, 7, 3, 11, 10, 8, 9, 2],
            [5, 7, 11, 2, 3, 8, 9, 10],
            [5, 7, 11, 2, 3, 8, 10, 9],
            [5, 7, 11, 2, 3, 10, 8, 9],
            [5, 7, 11, 3, 2, 8, 9, 10],
            [5, 7, 11, 3, 2, 8, 10, 9],
            [5, 7, 11, 3, 2, 10, 8, 9],
            [5, 7, 11, 3, 8, 2, 9, 10],
            [5, 7, 11, 3, 8, 2, 10, 9],
            [5, 7, 11, 3, 8, 9, 2, 10],
            [5, 7, 11, 3, 8, 9, 10, 2],
            [5, 7, 11, 3, 8, 10, 2, 9],
            [5, 7, 11, 3, 8, 10, 9, 2],
            [5, 7, 11, 3, 10, 2, 8, 9],
            [5, 7, 11, 3, 10, 8, 2, 9],
            [5, 7, 11, 3, 10, 8, 9, 2],
            [7, 3, 5, 8, 11, 2, 9, 10],
            [7, 3, 5, 8, 11, 2, 10, 9],
            [7, 3, 5, 8, 11, 9, 2, 10],
            [7, 3, 5, 8, 11, 9, 10, 2],
            [7, 3, 5, 8, 11, 10, 2, 9],
            [7, 3, 5, 8, 11, 10, 9, 2],
            [7, 3, 5, 11, 2, 8, 9, 10],
            [7, 3, 5, 11, 2, 8, 10, 9],
            [7, 3, 5, 11, 2, 10, 8, 9],
            [7, 3, 5, 11, 8, 2, 9, 10],
            [7, 3, 5, 11, 8, 2, 10, 9],
            [7, 3, 5, 11, 8, 9, 2, 10],
            [7, 3, 5, 11, 8, 9, 10, 2],
            [7, 3, 5, 11, 8, 10, 2, 9],
            [7, 3, 5, 11, 8, 10, 9, 2],
            [7, 3, 5, 11, 10, 2, 8, 9],
            [7, 3, 5, 11, 10, 8, 2, 9],
            [7, 3, 5, 11, 10, 8, 9, 2],
            [7, 3, 8, 5, 11, 2, 9, 10],
            [7, 3, 8, 5, 11, 2, 10, 9],
            [7, 3, 8, 5, 11, 9, 2, 10],
            [7, 3, 8, 5, 11, 9, 10, 2],
            [7, 3, 8, 5, 11, 10, 2, 9],
            [7, 3, 8, 5, 11, 10, 9, 2],
            [7, 5, 3, 8, 11, 2, 9, 10],
            [7, 5, 3, 8, 11, 2, 10, 9],
            [7, 5, 3, 8, 11, 9, 2, 10],
            [7, 5, 3, 8, 11, 9, 10, 2],
            [7, 5, 3, 8, 11, 10, 2, 9],
            [7, 5, 3, 8, 11, 10, 9, 2],
            [7, 5, 3, 11, 2, 8, 9, 10],
            [7, 5, 3, 11, 2, 8, 10, 9],
            [7, 5, 3, 11, 2, 10, 8, 9],
            [7, 5, 3, 11, 8, 2, 9, 10],
            [7, 5, 3, 11, 8, 2, 10, 9],
            [7, 5, 3, 11, 8, 9, 2, 10],
            [7, 5, 3, 11, 8, 9, 10, 2],
            [7, 5, 3, 11, 8, 10, 2, 9],
            [7, 5, 3, 11, 8, 10, 9, 2],
            [7, 5, 3, 11, 10, 2, 8, 9],
            [7, 5, 3, 11, 10, 8, 2, 9],
            [7, 5, 3, 11, 10, 8, 9, 2],
            [7, 5, 11, 2, 3, 8, 9, 10],
            [7, 5, 11, 2, 3, 8, 10, 9],
            [7, 5, 11, 2, 3, 10, 8, 9],
            [7, 5, 11, 3, 2, 8, 9, 10],
            [7, 5, 11, 3, 2, 8, 10, 9],
            [7, 5, 11, 3, 2, 10, 8, 9],
            [7, 5, 11, 3, 8, 2, 9, 10],
            [7, 5, 11, 3, 8, 2, 10, 9],
            [7, 5, 11, 3, 8, 9, 2, 10],
            [7, 5, 11, 3, 8, 9, 10, 2],
            [7, 5, 11, 3, 8, 10, 2, 9],
            [7, 5, 11, 3, 8, 10, 9, 2],
            [7, 5, 11, 3, 10, 2, 8, 9],
            [7, 5, 11, 3, 10, 8, 2, 9],
            [7, 5, 11, 3, 10, 8, 9, 2],
        ]

        self.assertIn(list(graph.topological_sort()), valid_solutions)
