# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import operator

from functools import reduce
from odoo.tools import lazy_property


class AbstractPath:
    def __init__(self, start):
        self.nodes = [start]

    def append(self, edge, node):
        self.nodes.append(node)

    def pop(self):
        return self.nodes.pop()

    def remove(self, count):
        del self.nodes[len(self.nodes) - count:]

    def traverse(self, graph, labels, marker, done):
        path = self._labels
        stack = [label for label in labels]
        while len(stack) > 0:
            edge = stack[-1]
            node = graph.target(self.nodes[-1], edge)
            self.append(edge, node)
            if marker(self) not in done:
                done.add(marker(self))
                stack.extend(graph[node])
                yield self

            count = next(filter(
                lambda i: i == len(path) or path[-(i + 1)] != stack[-(i + 1)],
                range(len(path) + 1)
            ))
            del stack[len(stack) - count:]
            self.remove(count)

    @classmethod
    def search(cls, graph, nodes, marker, collector=set):
        for node in nodes:
            path, labels = cls(node), graph[node]
            yield path
            yield from path.traverse(graph, labels, marker, collector())


class Path(AbstractPath):
    def __init__(self, start):
        super().__init__(start)
        self._labels = self.nodes


class LabeledPath(AbstractPath):
    def __init__(self, start):
        super().__init__(start)
        self.edges = []
        self._labels = self.edges

    def append(self, edge, node):
        super().append(edge, node)
        return self.edges.append(edge)

    def pop(self):
        super().pop()
        return self.edges.pop()

    def remove(self, count):
        del self.edges[len(self.edges) - count:]
        super().remove(count)


class Quiver:
    '''
    An abstract base class representing a graph traversable through it's
    adjacencies. Any concrete implementation should implement the __getitem__
    method returning a set of nodes connected by an edge to the provided node.
    '''
    Path = LabeledPath

    def reachable_from(self, nodes, collector=set):
        '''
        :param node: starting nodes
        :return: an iterator for nodes reachable from the start nodes
        '''
        paths = self.shortest_paths(nodes, collector)
        return (path.nodes[-1] for path in paths)

    def shortest_paths(self, nodes, collector=set):
        '''
        :param node: starting nodes
        :return: an iterator over shortest paths to nodes reachable from the
        start nodes
        '''
        return self.Path.search(self, nodes, lambda path: (
            path.nodes[-1]
        ), collector)

    def acyclic_paths(self, nodes, collector=set):
        return self.Path.search(self, nodes, lambda path: (
            path.nodes[-2], path.edges[-1], path.nodes[-1],
        ), collector)

    def subgraph(self, nodes):
        '''
        :param nodes: a set of nodes to include in the new graph
        :return: a graph including only edges between the input nodes
        :rtype: AdjacencyGraph
        '''
        nodes = set(nodes)
        return AdjacencyGraph({node: self[node] & nodes for node in nodes})

    def neighborhood(self, nodes):
        '''
        :param nodes: an iterable of starting nodes
        :return: an iterator for nodes reachable from the start nodes
        '''
        targets = (self[node] for node in nodes)
        sources = reduce(lambda all, node: all.update(node), targets, set())
        return self.subgraph(sources)

    def expand(self, nodes):
        '''
        :param nodes: an iterable of starting nodes
        :return: a subgraph containing all nodes reachable from the start nodes
        :rtype: AdjacencyGraph
        '''
        return self.subgraph(self.reachable_from(nodes))


class IterableQuiver(Quiver):
    def target(self, node, edge):
        return edge

    def transpose(self):
        result = AdjacencyGraph()

        for node in self.nodes():
            result.build_node(node)

        for node in self.nodes():
            for dependent in self[node]:
                result.build_edge(dependent, node)

        return result

    def components(self):
        '''
        :return: an iterator for the components in reverse topological order
        '''
        stack = []
        indexes = {}

        def visit(node):
            if node in indexes:
                return

            current = len(indexes)
            indexes[node] = current
            depth = len(stack)
            stack.append(node)

            for successor in self[node]:
                yield from visit(successor)
                indexes[node] = min(indexes[node], indexes[successor])

            if current == indexes[node]:
                nodes = set(stack[depth:])
                del stack[depth:]
                yield self.subgraph(nodes)
                indexes.update({node: len(self) for node in nodes})

        for node in self.nodes():
            yield from visit(node)

    def __and__(self, other):
        return AdjacencyGraph({
            node: self[node] & other[node]
            for node in self.nodes() if node in other
        })


class SubGraph(IterableQuiver):
    def __init__(self, graph, nodes):
        self._graph = graph
        self._nodes = set(node for node in nodes if node in graph)

    def __getitem__(self, node):
        if node not in self._nodes:
            raise KeyError(f'KeyError: {node}')
        return self.graph[node]

    def __contains__(self, node):
        return node in self._nodes

    def nodes(self):
        return iter(self._nodes)


class AdjacencyGraph(IterableQuiver):
    def __init__(self, adjacencies={}):
        self.graph_nodes = adjacencies.copy()

    def __getitem__(self, node):
        return self.graph_nodes[node]

    def __contains__(self, node):
        return node in self.graph_nodes

    def __len__(self):
        return len(self.graph_nodes)

    def nodes(self):
        return self.graph_nodes.keys()

    def build_node(self, node):
        self.graph_nodes.setdefault(node, set())

    def build_edge(self, dependency, dependent):
        self.graph_nodes[dependency].add(dependent)


class ReversibleGraph(AdjacencyGraph):
    def __init__(self):
        super().__init__()
        self.in_edges = {}

    def build_node(self, node):
        self.in_edges.setdefault(node, set())
        super().build_node(node)

    def build_edge(self, dependency, dependent):
        self.in_edges[dependent].add(dependency)
        super().build_edge(dependency, dependent)

    def remove_node(self, node):
        for source in self.in_edges[node]:
            self.graph_nodes[source].remove(node)
        self.in_edges.pop(node)

        for target in self.graph_nodes[node]:
            self.in_edges[target].remove(node)
        self.graph_nodes.pop(node)

    def transpose(self):
        result = ReversibleGraph()
        result.graph_nodes = self.in_edges.copy()
        result.in_edges = self.graph_nodes.copy()
        return result


class RecordCollector():
    '''
    A representation of a heterogenous recordset. For any recordset added to
    the collector, subsets are also considered contained in the collector.
    '''
    def __init__(self):
        self.records = {}

    def add(self, records):
        self.records.setdefault(records._name, records.browse())
        self.records[records._name] |= records

    def pop(self):
        return self.records.pop(next(iter(self.records)))

    def __iter__(self):
        for records in self.records.values():
            yield from iter(records)

    def __contains__(self, records):
        entry = self.records.get(records._name, records.browse())
        return len(records & entry) == len(records)


class PrimalGraph(IterableQuiver):
    '''
    This class describes the induced primal graph associated with a directed
    hypergraph. The class provides for easy insertion of directed hyperedges
    while also implementing a graph interface to the primal graph. Its utility
    derives mostly from the fact that it can be used to describe generalized
    incidence structures between recordsets.
    '''
    def __init__(self, constructor, concat=operator.iconcat):
        self._graph = ReversibleGraph()
        self._constructor = constructor
        self._concat = concat
        self._blocks = []
        self._groups = {}
        self._sizes = []
        self._nodes = {}

    @lazy_property
    def _chunks(self):
        chunks = {}
        for node, index in self._nodes.items():
            chunk = self._constructor(node)
            if index in chunks:
                chunks[index] = self._concat(chunks[index], chunk)
            else:
                chunks[index] = chunk
        return [chunks[index] for index in range(0, len(self._sizes))]

    def __len__(self):
        return len(self._chunks)

    def __contains__(self, nodes):
        chunks = set(self._nodes.get(node, len(self._sizes)) for node in nodes)
        return len(chunks) == 1 and self._sizes[chunks.pop()] == len(nodes)

    def __getitem__(self, nodes):
        return set(
            self._chunks[index] for source in self.groups(nodes)
            for target in self._graph[source] for index in self._groups[target]
        )

    def chunks(self, nodes):
        return (self._chunks[index] for index in self._groups[nodes])

    def groups(self, nodes):
        indices = set(self._nodes.get(node, len(self._sizes)) for node in nodes)
        if len(indices) != 1:
            raise KeyError(f'KeyError: {nodes}')
        return self._blocks[indices.pop()]

    def transpose(self):
        result = PrimalGraph(self._constructor, self._concat)
        result._graph = self._graph.transpose()
        result._groups = self._groups.copy()
        result._blocks = self._blocks.copy()
        result._sizes = self._sizes.copy()
        result._nodes = self._nodes.copy()
        return result

    def build_nodes(self, nodes):
        lazy_property.reset_all(self)
        if nodes in self._groups:
            return

        indices = {}
        lengths = {}
        position = len(self._sizes)
        self._groups.setdefault(nodes, ())
        self._graph.build_node(nodes)

        processed = set()
        for node in nodes:
            self._nodes.setdefault(node, position)
            index = self._nodes[node]
            lengths[index] = lengths.get(index, 0) + int(node not in processed)
            processed.add(node)

        if position in lengths:
            self._blocks.append(())
            self._sizes.append(lengths[position])

        for index, count in lengths.items():
            if count < self._sizes[index]:
                indices[index] = len(self._sizes)
                # The following takes care of duplicate entries in nodes.
                indices[len(self._sizes)] = len(self._sizes)
                for collection in self._blocks[index]:
                    self._groups[collection] += (indices[index],)
                self._blocks.append(self._blocks[index] + (nodes,))
                self._sizes.append(count)
                self._sizes[index] -= count
            else:
                indices[index] = index
                self._blocks[index] += (nodes,)
            self._groups[nodes] += (indices[index],)

        for node in nodes:
            self._nodes[node] = indices[self._nodes[node]]

    def build_edges(self, sources, targets):
        lazy_property.reset_all(self)
        self._graph.build_edge(sources, targets)

    def nodes(self):
        return iter(self._chunks)

    def order(self):
        return len(self._sizes)

    def size(self):
        return sum(map(len, self._graph))


class RelationalGraph(IterableQuiver):
    def __init__(self, pool, reverse=False):
        self.pool = pool
        self.reverse = reverse
        self.selector = None

    def include(self, test):
        lazy_property.reset_all(self)
        selector = self.selector or (lambda field: False)
        self.selector = lambda field: selector(field) or test(field)

    def require(self, test):
        lazy_property.reset_all(self)
        selector = self.selector or (lambda field: True)
        self.selector = lambda field: selector(field) and test(field)

    def exclude(self, test):
        self.require(lambda field: not test(field))

    def __getitem__(self, node):
        for field in self.relational_fields.get(node._name, set()):
            if self.selector(field):
                yield field

    def target(self, source, field):
        if not self.reverse:
            return source[field.name]

        # TODO Support many2one references. Use inverse field when possible
        # to support caching. See _modified_triggers for similar logic.
        domain = [(field.name, 'in', source.ids)]
        corecords = source.env[field.model_name].search(domain)

        return corecords

    def __contains__(self, node):
        return node._name in self.pool.models

    @lazy_property
    def relational_fields(self):
        fields = {}
        for model in self.pool.models.values():
            if model._abstract:
                continue

            for field in model._fields.values():
                has_inverse = field in self.pool.field_inverses
                if not field.relational and not has_inverse:
                    continue

                if self.reverse:
                    fields.setdefault(field.comodel_name, set())
                    fields[field.comodel_name].add(field)
                else:
                    fields.setdefault(field.model_name, set())
                    fields[field.model_name].add(field)

        return fields
