# Copyright (c) 2009 Denis Bilenko. See LICENSE for details.
"""
Low-level utilities.
"""

from __future__ import absolute_import, print_function, division

import functools
import pprint
import sys
import traceback

from greenlet import getcurrent

from gevent._compat import perf_counter
from gevent._compat import PYPY
from gevent._compat import thread_mod_name
from gevent._util import _NONE

__all__ = [
    'format_run_info',
    'print_run_info',
    'GreenletTree',
    'wrap_errors',
    'assert_switches',
]

# PyPy is very slow at formatting stacks
# for some reason.
_STACK_LIMIT = 20 if PYPY else None


def _noop():
    return None

def _ready():
    return False

class wrap_errors(object):
    """
    Helper to make function return an exception, rather than raise it.

    Because every exception that is unhandled by greenlet will be logged,
    it is desirable to prevent non-error exceptions from leaving a greenlet.
    This can done with a simple ``try/except`` construct::

        def wrapped_func(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except (TypeError, ValueError, AttributeError) as ex:
                return ex

    This class provides a shortcut to write that in one line::

        wrapped_func = wrap_errors((TypeError, ValueError, AttributeError), func)

    It also preserves ``__str__`` and ``__repr__`` of the original function.
    """
    # QQQ could also support using wrap_errors as a decorator

    def __init__(self, errors, func):
        """
        Calling this makes a new function from *func*, such that it catches *errors* (an
        :exc:`BaseException` subclass, or a tuple of :exc:`BaseException` subclasses) and
        return it as a value.
        """
        self.__errors = errors
        self.__func = func
        # Set __doc__, __wrapped__, etc, especially useful on Python 3.
        functools.update_wrapper(self, func)

    def __call__(self, *args, **kwargs):
        func = self.__func
        try:
            return func(*args, **kwargs)
        except self.__errors as ex:
            return ex

    def __str__(self):
        return str(self.__func)

    def __repr__(self):
        return repr(self.__func)

    def __getattr__(self, name):
        return getattr(self.__func, name)


def print_run_info(thread_stacks=True, greenlet_stacks=True, limit=_NONE, file=None):
    """
    Call `format_run_info` and print the results to *file*.

    If *file* is not given, `sys.stderr` will be used.

    .. versionadded:: 1.3b1
    """
    lines = format_run_info(thread_stacks=thread_stacks,
                            greenlet_stacks=greenlet_stacks,
                            limit=limit)
    file = sys.stderr if file is None else file
    for l in lines:
        print(l, file=file)


def format_run_info(thread_stacks=True,
                    greenlet_stacks=True,
                    limit=_NONE,
                    current_thread_ident=None):
    """
    format_run_info(thread_stacks=True, greenlet_stacks=True, limit=None) -> [str]

    Request information about the running threads of the current process.

    This is a debugging utility. Its output has no guarantees other than being
    intended for human consumption.

    :keyword bool thread_stacks: If true, then include the stacks for
       running threads.
    :keyword bool greenlet_stacks: If true, then include the stacks for
       running greenlets. (Spawning stacks will always be printed.)
       Setting this to False can reduce the output volume considerably
       without reducing the overall information if *thread_stacks* is true
       and you can associate a greenlet to a thread (using ``thread_ident``
       printed values).
    :keyword int limit: If given, passed directly to `traceback.format_stack`.
       If not given, this defaults to the whole stack under CPython, and a
       smaller stack under PyPy.

    :return: A sequence of text lines detailing the stacks of running
            threads and greenlets. (One greenlet will duplicate one thread,
            the current thread and greenlet. If there are multiple running threads,
            the stack for the current greenlet may be incorrectly duplicated in multiple
            greenlets.)
            Extra information about
            :class:`gevent.Greenlet` object will also be returned.

    .. versionadded:: 1.3a1
    .. versionchanged:: 1.3a2
       Renamed from ``dump_stacks`` to reflect the fact that this
       prints additional information about greenlets, including their
       spawning stack, parent, locals, and any spawn tree locals.
    .. versionchanged:: 1.3b1
       Added the *thread_stacks*, *greenlet_stacks*, and *limit* params.
    """
    if current_thread_ident is None:
        from gevent import monkey
        current_thread_ident = monkey.get_original(thread_mod_name, 'get_ident')()

    lines = []

    limit = _STACK_LIMIT if limit is _NONE else limit
    _format_thread_info(lines, thread_stacks, limit, current_thread_ident)
    _format_greenlet_info(lines, greenlet_stacks, limit)
    return lines


def is_idle_threadpool_worker(frame):
    return frame.f_locals and frame.f_locals.get('gevent_threadpool_worker_idle')


def _format_thread_info(lines, thread_stacks, limit, current_thread_ident):
    import threading

    threads = {th.ident: th for th in threading.enumerate()}
    lines.append('*' * 80)
    lines.append('* Threads')

    thread = None
    frame = None
    for thread_ident, frame in sys._current_frames().items():
        do_stacks = thread_stacks
        lines.append("*" * 80)
        thread = threads.get(thread_ident)
        name = None
        if not thread:
            # Is it an idle threadpool thread? thread pool threads
            # don't have a Thread object, they're low-level
            if is_idle_threadpool_worker(frame):
                name = 'idle threadpool worker'
                do_stacks = False
        else:
            name = thread.name
        if getattr(thread, 'gevent_monitoring_thread', None):
            name = repr(thread.gevent_monitoring_thread())
        if current_thread_ident == thread_ident:
            name = '%s) (CURRENT' % (name,)
        lines.append('Thread 0x%x (%s)\n' % (thread_ident, name))
        if do_stacks:
            lines.append(''.join(traceback.format_stack(frame, limit)))
        elif not thread_stacks:
            lines.append('\t...stack elided...')

    # We may have captured our own frame, creating a reference
    # cycle, so clear it out.
    del thread
    del frame
    del lines
    del threads

def _format_greenlet_info(lines, greenlet_stacks, limit):
    # Use the gc module to inspect all objects to find the greenlets
    # since there isn't a global registry
    lines.append('*' * 80)
    lines.append('* Greenlets')
    lines.append('*' * 80)
    for tree in sorted(GreenletTree.forest(),
                       key=lambda t: '' if t.is_current_tree else repr(t.greenlet)):
        lines.append("---- Thread boundary")
        lines.extend(tree.format_lines(details={
            # greenlets from other threads tend to have their current
            # frame just match our current frame, which is not helpful,
            # so don't render their stack.
            'running_stacks': greenlet_stacks if tree.is_current_tree else False,
            'running_stack_limit': limit,
        }))

    del lines

dump_stacks = format_run_info

def _line(f):
    @functools.wraps(f)
    def w(self, *args, **kwargs):
        r = f(self, *args, **kwargs)
        self.lines.append(r)

    return w

class _TreeFormatter(object):
    UP_AND_RIGHT = '+'
    HORIZONTAL = '-'
    VERTICAL = '|'
    VERTICAL_AND_RIGHT = '+'
    DATA = ':'

    label_space = 1
    horiz_width = 3
    indent = 1

    def __init__(self, details, depth=0):
        self.lines = []
        self.depth = depth
        self.details = details
        if not details:
            self.child_data = lambda *args, **kwargs: None

    def deeper(self):
        return type(self)(self.details, self.depth + 1)

    @_line
    def node_label(self, text):
        return text

    @_line
    def child_head(self, label, right=VERTICAL_AND_RIGHT):
        return (
            ' ' * self.indent
            + right
            + self.HORIZONTAL * self.horiz_width
            + ' ' * self.label_space
            + label
        )

    def last_child_head(self, label):
        return self.child_head(label, self.UP_AND_RIGHT)

    @_line
    def child_tail(self, line, vertical=VERTICAL):
        return (
            ' ' * self.indent
            + vertical
            + ' ' * self.horiz_width
            + line
        )

    def last_child_tail(self, line):
        return self.child_tail(line, vertical=' ' * len(self.VERTICAL))

    @_line
    def child_data(self, data, data_marker=DATA): # pylint:disable=method-hidden
        return ((
            ' ' * self.indent
            + (data_marker if not self.depth else ' ')
            + ' ' * self.horiz_width
            + ' ' * self.label_space
            + data
        ),)

    def last_child_data(self, data):
        return self.child_data(data, ' ')

    def child_multidata(self, data):
        # Remove embedded newlines
        for l in data.splitlines():
            self.child_data(l)


class GreenletTree(object):
    """
    Represents a tree of greenlets.

    In gevent, the *parent* of a greenlet is usually the hub, so this
    tree is primarily arganized along the *spawning_greenlet* dimension.

    This object has a small str form showing this hierarchy. The `format`
    method can output more details. The exact output is unspecified but is
    intended to be human readable.

    Use the `forest` method to get the root greenlet trees for
    all threads, and the `current_tree` to get the root greenlet tree for
    the current thread.
    """

    #: The greenlet this tree represents.
    greenlet = None

    #: Is this tree the root for the current thread?
    is_current_tree = False

    def __init__(self, greenlet):
        self.greenlet = greenlet
        self.child_trees = []

    def add_child(self, tree):
        if tree is self:
            return
        self.child_trees.append(tree)

    @property
    def root(self):
        return self.greenlet.parent is None

    def __getattr__(self, name):
        return getattr(self.greenlet, name)

    DEFAULT_DETAILS = {
        'running_stacks': True,
        'running_stack_limit': _STACK_LIMIT,
        'spawning_stacks': True,
        'locals': True,
    }

    def format_lines(self, details=True):
        """
        Return a sequence of lines for the greenlet tree.

        :keyword bool details: If true (the default),
            then include more informative details in the output.
        """
        if not isinstance(details, dict):
            if not details:
                details = {}
            else:
                details = self.DEFAULT_DETAILS.copy()
        else:
            params = details
            details = self.DEFAULT_DETAILS.copy()
            details.update(params)
        tree = _TreeFormatter(details, depth=0)
        lines = [l[0] if isinstance(l, tuple) else l
                 for l in self._render(tree)]
        return lines

    def format(self, details=True):
        """
        Like `format_lines` but returns a string.
        """
        lines = self.format_lines(details)
        return '\n'.join(lines)

    def __str__(self):
        return self.format(False)

    # Prior to greenlet 3.0rc1, getting tracebacks of inactive
    # greenlets could crash on Python 3.12. So we added a
    # version-based setting here to disable it. That's fixed in the
    # 3.0 final releases, but appears to be back with Python 3.12.1;
    # this is likely related to https://github.com/python-greenlet/greenlet/issues/388
    #_SUPPORTS_TRACEBACK = sys.version_info[:3] < (3, 12, 1)
    _SUPPORTS_TRACEBACK = True

    @classmethod
    def __render_tb(cls, tree, label, frame, limit):
        tree.child_data(label)

        if cls._SUPPORTS_TRACEBACK:
            tb = ''.join(traceback.format_stack(frame, limit))
        else:
            tb = ''
        tree.child_multidata(tb)

    @staticmethod
    def __spawning_parent(greenlet):
        return (getattr(greenlet, 'spawning_greenlet', None) or _noop)()

    def __render_locals(self, tree):
        # Defer the import to avoid cycles
        from gevent.local import all_local_dicts_for_greenlet

        gr_locals = all_local_dicts_for_greenlet(self.greenlet)
        if gr_locals:
            tree.child_data("Greenlet Locals:")
            for (kind, idl), vals in gr_locals:
                if not vals:
                    continue # not set in this greenlet; ignore it.
                tree.child_data("  Local %s at %s" % (kind, hex(idl)))
                tree.child_multidata("    " + pprint.pformat(vals))

    def _render(self, tree):
        label = repr(self.greenlet)
        if not self.greenlet: # Not running or dead
            # raw greenlets do not have ready
            if getattr(self.greenlet, 'ready', _ready)():
                label += '; finished'
                if self.greenlet.value is not None:
                    label += ' with value ' + repr(self.greenlet.value)[:30]
                elif getattr(self.greenlet, 'exception', None) is not None:
                    label += ' with exception ' + repr(self.greenlet.exception)
            else:
                label += '; not running'
        tree.node_label(label)

        tree.child_data('Parent: ' + repr(self.greenlet.parent))

        if getattr(self.greenlet, 'gevent_monitoring_thread', None) is not None:
            tree.child_data('Monitoring Thread:' + repr(self.greenlet.gevent_monitoring_thread()))

        if self.greenlet and tree.details and tree.details['running_stacks']:
            self.__render_tb(tree, 'Running:', self.greenlet.gr_frame,
                             tree.details['running_stack_limit'])


        spawning_stack = getattr(self.greenlet, 'spawning_stack', None)
        if spawning_stack and tree.details and tree.details['spawning_stacks']:
            # We already placed a limit on the spawning stack when we captured it.
            self.__render_tb(tree, 'Spawned at:', spawning_stack, None)

        spawning_parent = self.__spawning_parent(self.greenlet)
        tree_locals = getattr(self.greenlet, 'spawn_tree_locals', None)
        if tree_locals and tree_locals is not getattr(spawning_parent, 'spawn_tree_locals', None):
            tree.child_data('Spawn Tree Locals')
            tree.child_multidata(pprint.pformat(tree_locals))

        self.__render_locals(tree)
        try:
            self.__render_children(tree)
        except RuntimeError: # pragma: no cover
            # If the tree is exceptionally deep, we can hit the recursion error.
            # Usually it's several levels down so we can make a print call.
            # This came up in test__semaphore before TestSemaphoreFair
            # was fixed.
            print("When rendering children", *sys.exc_info())
        return tree.lines

    def __render_children(self, tree):
        children = sorted(self.child_trees,
                          key=lambda c: (
                              # raw greenlets first. Note that we could be accessing
                              # minimal_ident for a hub from a different thread, which isn't
                              # technically thread safe.
                              getattr(c, 'minimal_ident', -1),
                              # running greenlets next
                              getattr(c, 'ready', _ready)(),
                              id(c.parent)))
        for n, child in enumerate(children):
            child_tree = child._render(tree.deeper())

            head = tree.child_head
            tail = tree.child_tail
            data = tree.child_data

            if n == len(children) - 1:
                # last child does not get the line drawn
                head = tree.last_child_head
                tail = tree.last_child_tail
                data = tree.last_child_data

            head(child_tree.pop(0))
            for child_data in child_tree:
                if isinstance(child_data, tuple):
                    data(child_data[0])
                else:
                    tail(child_data)

        return tree.lines


    @staticmethod
    def _root_greenlet(greenlet):
        while greenlet.parent is not None and not getattr(greenlet, 'greenlet_tree_is_root', False):
            greenlet = greenlet.parent
        return greenlet

    @classmethod
    def _forest(cls):
        from gevent._greenlet_primitives import get_reachable_greenlets
        main_greenlet = cls._root_greenlet(getcurrent())

        trees = {} # greenlet -> GreenletTree
        roots = {} # root greenlet -> GreenletTree
        current_tree = roots[main_greenlet] = trees[main_greenlet] = cls(main_greenlet)
        current_tree.is_current_tree = True

        root_greenlet = cls._root_greenlet
        glets = get_reachable_greenlets()

        for ob in glets:
            spawn_parent = cls.__spawning_parent(ob)

            if spawn_parent is None:
                # spawn parent is dead, or raw greenlet.
                # reparent under the root.
                spawn_parent = root_greenlet(ob)

            if spawn_parent is root_greenlet(spawn_parent) and spawn_parent not in roots:
                assert spawn_parent not in trees
                trees[spawn_parent] = roots[spawn_parent] = cls(spawn_parent)


            try:
                parent_tree = trees[spawn_parent]
            except KeyError: # pragma: no cover
                parent_tree = trees[spawn_parent] = cls(spawn_parent)

            try:
                # If the child also happened to be a spawning parent,
                # we could have seen it before; the reachable greenlets
                # are in no particular order.
                child_tree = trees[ob]
            except KeyError:
                trees[ob] = child_tree = cls(ob)
            parent_tree.add_child(child_tree)

        return roots, current_tree

    @classmethod
    def forest(cls):
        """
        forest() -> sequence

        Return a sequence of `GreenletTree`, one for each running
        native thread.
        """

        return list(cls._forest()[0].values())

    @classmethod
    def current_tree(cls):
        """
        current_tree() -> GreenletTree

        Returns the `GreenletTree` for the current thread.
        """
        return cls._forest()[1]

class _FailedToSwitch(AssertionError):
    pass

class assert_switches(object):
    """
    A context manager for ensuring a block of code switches greenlets.

    This performs a similar function as the :doc:`monitoring thread
    </monitoring>`, but the scope is limited to the body of the with
    statement. If the code within the body doesn't yield to the hub
    (and doesn't raise an exception), then upon exiting the
    context manager an :exc:`AssertionError` will be raised.

    This is useful in unit tests and for debugging purposes.

    :keyword float max_blocking_time: If given, the body is allowed
        to block for up to this many fractional seconds before
        an error is raised.
    :keyword bool hub_only: If True, then *max_blocking_time* only
        refers to the amount of time spent between switches into the
        hub. If False, then it refers to the maximum time between
        *any* switches. If *max_blocking_time* is not given, has no
        effect.

    Example::

        # This will always raise an exception: nothing switched
        with assert_switches():
            pass

        # This will never raise an exception; nothing switched,
        # but it happened very fast
        with assert_switches(max_blocking_time=1.0):
            pass

    .. versionadded:: 1.3

    .. versionchanged:: 1.4
        If an exception is raised, it now includes information about
        the duration of blocking and the parameters of this object.
    """

    hub = None
    tracer = None
    _entered = None


    def __init__(self, max_blocking_time=None, hub_only=False):
        self.max_blocking_time = max_blocking_time
        self.hub_only = hub_only

    def __enter__(self):
        from gevent import get_hub
        from gevent import _tracer

        self.hub = hub = get_hub()

        # TODO: We could optimize this to use the GreenletTracer
        # installed by the monitoring thread, if there is one.
        # As it is, we will chain trace calls back to it.
        if not self.max_blocking_time:
            self.tracer = _tracer.GreenletTracer()
        elif self.hub_only:
            self.tracer = _tracer.HubSwitchTracer(hub, self.max_blocking_time)
        else:
            self.tracer = _tracer.MaxSwitchTracer(hub, self.max_blocking_time)

        self._entered = perf_counter()
        self.tracer.monitor_current_greenlet_blocking()
        return self

    def __exit__(self, t, v, tb):
        self.tracer.kill()
        hub = self.hub; self.hub = None
        tracer = self.tracer; self.tracer = None

        # Only check if there was no exception raised, we
        # don't want to hide anything
        if t is not None:
            return


        did_block = tracer.did_block_hub(hub)
        if did_block:
            execution_time_s = perf_counter() - self._entered
            active_greenlet = did_block[1]
            report_lines = tracer.did_block_hub_report(hub, active_greenlet, {})

            message = 'To the hub' if self.hub_only else 'To any greenlet'
            message += ' in %.4f seconds' % (execution_time_s,)
            max_block = self.max_blocking_time
            message += ' (max allowed %.4f seconds)' % (max_block,) if max_block else ''
            message += '\n'
            message += '\n'.join(report_lines)
            raise _FailedToSwitch(message)


def clear_stack_frames(frame):
    """Do our best to clear local variables in all frames in a stack."""
    # On Python 3, frames have a .clear() method that can raise a RuntimeError.
    while frame is not None:
        try:
            frame.clear()
        except (RuntimeError, AttributeError):
            pass
        frame.f_locals.clear()
        frame = frame.f_back
