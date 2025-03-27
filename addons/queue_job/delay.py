# Copyright 2019 Camptocamp
# Copyright 2019 Guewen Baconnier
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import itertools
import logging
import uuid
from collections import defaultdict, deque

from .job import Job
from .utils import must_run_without_delay

_logger = logging.getLogger(__name__)


def group(*delayables):
    """Return a group of delayable to form a graph

    A group means that jobs can be executed concurrently.
    A job or a group of jobs depending on a group can be executed only after
    all the jobs of the group are done.

    Shortcut to :class:`~odoo.addons.queue_job.delay.DelayableGroup`.

    Example::

        g1 = group(delayable1, delayable2)
        g2 = group(delayable3, delayable4)
        g1.on_done(g2)
        g1.delay()
    """
    return DelayableGroup(*delayables)


def chain(*delayables):
    """Return a chain of delayable to form a graph

    A chain means that jobs must be executed sequentially.
    A job or a group of jobs depending on a group can be executed only after
    the last job of the chain is done.

    Shortcut to :class:`~odoo.addons.queue_job.delay.DelayableChain`.

    Example::

        chain1 = chain(delayable1, delayable2, delayable3)
        chain2 = chain(delayable4, delayable5, delayable6)
        chain1.on_done(chain2)
        chain1.delay()
    """
    return DelayableChain(*delayables)


class Graph:
    """Acyclic directed graph holding vertices of any hashable type

    This graph is not specifically designed to hold :class:`~Delayable`
    instances, although ultimately it is used for this purpose.
    """

    __slots__ = "_graph"

    def __init__(self, graph=None):
        if graph:
            self._graph = graph
        else:
            self._graph = {}

    def add_vertex(self, vertex):
        """Add a vertex

        Has no effect if called several times with the same vertex
        """
        self._graph.setdefault(vertex, set())

    def add_edge(self, parent, child):
        """Add an edge between a parent and a child vertex

        Has no effect if called several times with the same pair of vertices
        """
        self.add_vertex(child)
        self._graph.setdefault(parent, set()).add(child)

    def vertices(self):
        """Return the vertices (nodes) of the graph"""
        return set(self._graph)

    def edges(self):
        """Return the edges (links) of the graph"""
        links = []
        for vertex, neighbours in self._graph.items():
            for neighbour in neighbours:
                links.append((vertex, neighbour))
        return links

    # from
    # https://codereview.stackexchange.com/questions/55767/finding-all-paths-from-a-given-graph
    def paths(self, vertex):
        """Generate the maximal cycle-free paths in graph starting at vertex.

        >>> g = {1: [2, 3], 2: [3, 4], 3: [1], 4: []}
        >>> sorted(self.paths(1))
        [[1, 2, 3], [1, 2, 4], [1, 3]]
        >>> sorted(self.paths(3))
        [[3, 1, 2, 4]]
        """
        path = [vertex]  # path traversed so far
        seen = {vertex}  # set of vertices in path

        def search():
            dead_end = True
            for neighbour in self._graph[path[-1]]:
                if neighbour not in seen:
                    dead_end = False
                    seen.add(neighbour)
                    path.append(neighbour)
                    yield from search()
                    path.pop()
                    seen.remove(neighbour)
            if dead_end:
                yield list(path)

        yield from search()

    def topological_sort(self):
        """Yields a proposed order of nodes to respect dependencies

        The order is not unique, the result may vary, but it is guaranteed
        that a node depending on another is not yielded before.
        It assumes the graph has no cycle.
        """
        depends_per_node = defaultdict(int)
        for __, tail in self.edges():
            depends_per_node[tail] += 1

        # the queue contains only elements for which all dependencies
        # are resolved
        queue = deque(self.root_vertices())
        while queue:
            vertex = queue.popleft()
            yield vertex
            for node in self._graph[vertex]:
                depends_per_node[node] -= 1
                if not depends_per_node[node]:
                    queue.append(node)

    def root_vertices(self):
        """Returns the root vertices

        meaning they do not depend on any other job.
        """
        dependency_vertices = set()
        for dependencies in self._graph.values():
            dependency_vertices.update(dependencies)
        return set(self._graph.keys()) - dependency_vertices

    def __repr__(self):
        paths = [path for vertex in self.root_vertices() for path in self.paths(vertex)]
        lines = []
        for path in paths:
            lines.append(" → ".join(repr(vertex) for vertex in path))
        return "\n".join(lines)


class DelayableGraph(Graph):
    """Directed Graph for :class:`~Delayable` dependencies

    It connects together the :class:`~Delayable`, :class:`~DelayableGroup` and
    :class:`~DelayableChain` graphs, and creates then enqueued the jobs.
    """

    def _merge_graph(self, graph):
        """Merge a graph in the current graph

        It takes each vertex, which can be :class:`~Delayable`,
        :class:`~DelayableChain` or :class:`~DelayableGroup`, and updates the
        current graph with the edges between Delayable objects (connecting
        heads and tails of the groups and chains), so that at the end, the
        graph contains only Delayable objects and their links.
        """
        for vertex, neighbours in graph._graph.items():
            tails = vertex._tail()
            for tail in tails:
                # connect the tails with the heads of each node
                heads = {head for n in neighbours for head in n._head()}
                self._graph.setdefault(tail, set()).update(heads)

    def _connect_graphs(self):
        """Visit the vertices' graphs and connect them, return the whole graph

        Build a new graph, walk the vertices and their related vertices, merge
        their graph in the new one, until we have visited all the vertices
        """
        graph = DelayableGraph()
        graph._merge_graph(self)

        seen = set()
        visit_stack = deque([self])
        while visit_stack:
            current = visit_stack.popleft()
            if current in seen:
                continue

            vertices = current.vertices()
            for vertex in vertices:
                vertex_graph = vertex._graph
                graph._merge_graph(vertex_graph)
                visit_stack.append(vertex_graph)

            seen.add(current)

        return graph

    def _has_to_execute_directly(self, vertices):
        """Used for tests to run tests directly instead of storing them

        In tests, prefer to use
        :func:`odoo.addons.queue_job.tests.common.trap_jobs`.
        """
        envs = {vertex.recordset.env for vertex in vertices}
        for env in envs:
            if must_run_without_delay(env):
                return True
        return False

    @staticmethod
    def _ensure_same_graph_uuid(jobs):
        """Set the same graph uuid on all jobs of the same graph"""
        jobs_count = len(jobs)
        if jobs_count == 0:
            raise ValueError("Expecting jobs")
        elif jobs_count == 1:
            if jobs[0].graph_uuid:
                raise ValueError(
                    "Job %s is a single job, it should not"
                    " have a graph uuid" % (jobs[0],)
                )
        else:
            graph_uuids = {job.graph_uuid for job in jobs if job.graph_uuid}
            if len(graph_uuids) > 1:
                raise ValueError("Jobs cannot have dependencies between several graphs")
            elif len(graph_uuids) == 1:
                graph_uuid = graph_uuids.pop()
            else:
                graph_uuid = str(uuid.uuid4())
            for job in jobs:
                job.graph_uuid = graph_uuid

    def delay(self):
        """Build the whole graph, creates jobs and delay them"""
        graph = self._connect_graphs()

        vertices = graph.vertices()

        for vertex in vertices:
            vertex._build_job()

        self._ensure_same_graph_uuid([vertex._generated_job for vertex in vertices])

        if self._has_to_execute_directly(vertices):
            self._execute_graph_direct(graph)
            return

        for vertex, neighbour in graph.edges():
            neighbour._generated_job.add_depends({vertex._generated_job})

        # If all the jobs of the graph have another job with the same identity,
        # we do not create them. Maybe we should check that the found jobs are
        # part of the same graph, but not sure it's really required...
        # Also, maybe we want to check only the root jobs.
        existing_mapping = {}
        for vertex in vertices:
            if not vertex.identity_key:
                continue
            generated_job = vertex._generated_job
            existing = generated_job.job_record_with_same_identity_key()
            if not existing:
                # at least one does not exist yet, we'll delay the whole graph
                existing_mapping.clear()
                break
            existing_mapping[vertex] = existing

        # We'll replace the generated jobs by the existing ones, so callers
        # can retrieve the existing job in "_generated_job".
        # existing_mapping contains something only if *all* the job with an
        # identity have an existing one.
        for vertex, existing in existing_mapping.items():
            vertex._generated_job = existing
            return

        for vertex in vertices:
            vertex._generated_job.store()

    def _execute_graph_direct(self, graph):
        for delayable in graph.topological_sort():
            delayable._execute_direct()


class DelayableChain:
    """Chain of delayables to form a graph

    Delayables can be other :class:`~Delayable`, :class:`~DelayableChain` or
    :class:`~DelayableGroup` objects.

    A chain means that jobs must be executed sequentially.
    A job or a group of jobs depending on a group can be executed only after
    the last job of the chain is done.

    Chains can be connected to other Delayable, DelayableChain or
    DelayableGroup objects by using :meth:`~done`.

    A Chain is enqueued by calling :meth:`~delay`, which delays the whole
    graph.
    Important: :meth:`~delay` must be called on the top-level
    delayable/chain/group object of the graph.
    """

    __slots__ = ("_graph", "__head", "__tail")

    def __init__(self, *delayables):
        self._graph = DelayableGraph()
        iter_delayables = iter(delayables)
        head = next(iter_delayables)
        self.__head = head
        self._graph.add_vertex(head)
        for neighbour in iter_delayables:
            self._graph.add_edge(head, neighbour)
            head = neighbour
        self.__tail = head

    def _head(self):
        return self.__head._tail()

    def _tail(self):
        return self.__tail._head()

    def __repr__(self):
        inner_graph = "\n\t".join(repr(self._graph).split("\n"))
        return "DelayableChain(\n\t{}\n)".format(inner_graph)

    def on_done(self, *delayables):
        """Connects the current chain to other delayables/chains/groups

        The delayables/chains/groups passed in the parameters will be executed
        when the current Chain is done.
        """
        for delayable in delayables:
            self._graph.add_edge(self.__tail, delayable)
        return self

    def delay(self):
        """Delay the whole graph"""
        self._graph.delay()


class DelayableGroup:
    """Group of delayables to form a graph

    Delayables can be other :class:`~Delayable`, :class:`~DelayableChain` or
    :class:`~DelayableGroup` objects.

    A group means that jobs must be executed sequentially.
    A job or a group of jobs depending on a group can be executed only after
    the all the jobs of the group are done.

    Groups can be connected to other Delayable, DelayableChain or
    DelayableGroup objects by using :meth:`~done`.

    A group is enqueued by calling :meth:`~delay`, which delays the whole
    graph.
    Important: :meth:`~delay` must be called on the top-level
    delayable/chain/group object of the graph.
    """

    __slots__ = ("_graph", "_delayables")

    def __init__(self, *delayables):
        self._graph = DelayableGraph()
        self._delayables = set(delayables)
        for delayable in delayables:
            self._graph.add_vertex(delayable)

    def _head(self):
        return itertools.chain.from_iterable(node._head() for node in self._delayables)

    def _tail(self):
        return itertools.chain.from_iterable(node._tail() for node in self._delayables)

    def __repr__(self):
        inner_graph = "\n\t".join(repr(self._graph).split("\n"))
        return "DelayableGroup(\n\t{}\n)".format(inner_graph)

    def on_done(self, *delayables):
        """Connects the current group to other delayables/chains/groups

        The delayables/chains/groups passed in the parameters will be executed
        when the current Group is done.
        """
        for parent in self._delayables:
            for child in delayables:
                self._graph.add_edge(parent, child)
        return self

    def delay(self):
        """Delay the whole graph"""
        self._graph.delay()


class Delayable:
    """Unit of a graph, one Delayable will lead to an enqueued job

    Delayables can have dependencies on each others, as well as dependencies on
    :class:`~DelayableGroup` or :class:`~DelayableChain` objects.

    This class will generally not be used directly, it is used internally
    by :meth:`~odoo.addons.queue_job.models.base.Base.delayable`. Look
    in the base model for more details.

    Delayables can be connected to other Delayable, DelayableChain or
    DelayableGroup objects by using :meth:`~done`.

    Properties of the future job can be set using the :meth:`~set` method,
    which always return ``self``::

        delayable.set(priority=15).set({"max_retries": 5, "eta": 15}).delay()

    It can be used for example to set properties dynamically.

    A Delayable is enqueued by calling :meth:`delay()`, which delays the whole
    graph.
    Important: :meth:`delay()` must be called on the top-level
    delayable/chain/group object of the graph.
    """

    _properties = (
        "priority",
        "eta",
        "max_retries",
        "description",
        "channel",
        "identity_key",
    )
    __slots__ = _properties + (
        "recordset",
        "_graph",
        "_job_method",
        "_job_args",
        "_job_kwargs",
        "_generated_job",
    )

    def __init__(
        self,
        recordset,
        priority=None,
        eta=None,
        max_retries=None,
        description=None,
        channel=None,
        identity_key=None,
    ):
        self._graph = DelayableGraph()
        self._graph.add_vertex(self)

        self.recordset = recordset

        self.priority = priority
        self.eta = eta
        self.max_retries = max_retries
        self.description = description
        self.channel = channel
        self.identity_key = identity_key

        self._job_method = None
        self._job_args = ()
        self._job_kwargs = {}

        self._generated_job = None

    def _head(self):
        return [self]

    def _tail(self):
        return [self]

    def __repr__(self):
        return "Delayable({}.{}({}, {}))".format(
            self.recordset,
            self._job_method.__name__ if self._job_method else "",
            self._job_args,
            self._job_kwargs,
        )

    def __del__(self):
        if not self._generated_job:
            _logger.warning("Delayable %s was prepared but never delayed", self)

    def _set_from_dict(self, properties):
        for key, value in properties.items():
            if key not in self._properties:
                raise ValueError("No property %s" % (key,))
            setattr(self, key, value)

    def set(self, *args, **kwargs):
        """Set job properties and return self

        The values can be either a dictionary and/or keywork args
        """
        if args:
            # args must be a dict
            self._set_from_dict(*args)
        self._set_from_dict(kwargs)
        return self

    def on_done(self, *delayables):
        """Connects the current Delayable to other delayables/chains/groups

        The delayables/chains/groups passed in the parameters will be executed
        when the current Delayable is done.
        """
        for child in delayables:
            self._graph.add_edge(self, child)
        return self

    def delay(self):
        """Delay the whole graph"""
        self._graph.delay()

    def _build_job(self):
        if self._generated_job:
            return self._generated_job
        self._generated_job = Job(
            self._job_method,
            args=self._job_args,
            kwargs=self._job_kwargs,
            priority=self.priority,
            max_retries=self.max_retries,
            eta=self.eta,
            description=self.description,
            channel=self.channel,
            identity_key=self.identity_key,
        )
        return self._generated_job

    def _store_args(self, *args, **kwargs):
        self._job_args = args
        self._job_kwargs = kwargs
        return self

    def __getattr__(self, name):
        if name in self.__slots__:
            return super().__getattr__(name)
        if name in self.recordset:
            raise AttributeError(
                "only methods can be delayed (%s called on %s)" % (name, self.recordset)
            )
        recordset_method = getattr(self.recordset, name)
        self._job_method = recordset_method
        return self._store_args

    def _execute_direct(self):
        assert self._generated_job
        self._generated_job.perform()


class DelayableRecordset(object):
    """Allow to delay a method for a recordset (shortcut way)

    Usage::

        delayable = DelayableRecordset(recordset, priority=20)
        delayable.method(args, kwargs)

    The method call will be processed asynchronously in the job queue, with
    the passed arguments.

    This class will generally not be used directly, it is used internally
    by :meth:`~odoo.addons.queue_job.models.base.Base.with_delay`
    """

    __slots__ = ("delayable",)

    def __init__(
        self,
        recordset,
        priority=None,
        eta=None,
        max_retries=None,
        description=None,
        channel=None,
        identity_key=None,
    ):
        self.delayable = Delayable(
            recordset,
            priority=priority,
            eta=eta,
            max_retries=max_retries,
            description=description,
            channel=channel,
            identity_key=identity_key,
        )

    @property
    def recordset(self):
        return self.delayable.recordset

    def __getattr__(self, name):
        def _delay_delayable(*args, **kwargs):
            getattr(self.delayable, name)(*args, **kwargs).delay()
            return self.delayable._generated_job

        return _delay_delayable

    def __str__(self):
        return "DelayableRecordset(%s%s)" % (
            self.delayable.recordset._name,
            getattr(self.delayable.recordset, "_ids", ""),
        )

    __repr__ = __str__
