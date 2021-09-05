# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import gc
import json
import logging
import sys
import time
import threading
import re

from psycopg2 import sql

from odoo import tools

_logger = logging.getLogger(__name__)


def _format_frame(frame):
    code = frame.f_code
    return (code.co_filename, frame.f_lineno, code.co_name, '')


def _format_stack(stack):
    return [list(frame) for frame in stack]


def get_current_frame(thread=None):
    if thread:
        frame = sys._current_frames()[thread.ident]
    else:
        frame = sys._getframe()
    while frame.f_code.co_filename == __file__:
        frame = frame.f_back
    return frame


def _get_stack_trace(frame, limit_frame=None):
    stack = []
    while frame is not None and frame != limit_frame:
        stack.append(_format_frame(frame))
        frame = frame.f_back
    if frame is None and limit_frame:
        _logger.error("Limit frame was not found")
    return list(reversed(stack))


def stack_size():
    frame = get_current_frame()
    size = 0
    while frame:
        size += 1
        frame = frame.f_back
    return size


def make_session(name=''):
    return f'{datetime.datetime.now():%Y-%m-%d %H:%M:%S} {name}'


class Collector:
    """
    Base class for objects that collect profiling data.

    A collector object is used by a profiler to collect profiling data, most
    likely a list of stack traces with time and some context information added
    by ExecutionContext decorator on current thread.

    This is a generic implementation of a basic collector, to be inherited.
    It defines default behaviors for creating an entry in the collector.
    """
    name = None                 # symbolic name of the collector
    _registry = {}              # map collector names to their class

    @classmethod
    def __init_subclass__(cls):
        if cls.name:
            cls._registry[cls.name] = cls
            cls._registry[cls.__name__] = cls

    @classmethod
    def make(cls, name, *args, **kwargs):
        """ Instantiate a collector corresponding to the given name. """
        return cls._registry[name](*args, **kwargs)

    def __init__(self):
        self._processed = False
        self._entries = []
        self.profiler = None

    def start(self):
        """ Start the collector. """

    def stop(self):
        """ Stop the collector. """

    def add(self, entry=None, frame=None):
        """ Add an entry (dict) to this collector. """
        # todo add entry count limit
        self._entries.append({
            'stack': self._get_stack_trace(frame),
            # make a copy of the current context, because it will change
            'exec_context': dict(getattr(self.profiler.init_thread, 'exec_context', ())),
            'start': time.time(),
            **(entry or {}),
        })

    def _get_stack_trace(self, frame=None):
        """ Return the stack trace to be included in a given entry. """
        frame = frame or get_current_frame(self.profiler.init_thread)
        return _get_stack_trace(frame, self.profiler.init_frame)

    def post_process(self):
        for entry in self._entries:
            stack = entry.get('stack', [])
            self.profiler._add_file_lines(stack)

    @property
    def entries(self):
        """ Return the entries of the collector after postprocessing. """
        if not self._processed:
            self.post_process()
            self._processed = True
        return self._entries


class SQLCollector(Collector):
    """
    Saves all executed queries in the current thread with the call stack.
    """
    name = 'sql'

    def start(self):
        init_thread = self.profiler.init_thread
        if not hasattr(init_thread, 'query_hooks'):
            init_thread.query_hooks = []
        init_thread.query_hooks.append(self.hook)

    def stop(self):
        self.profiler.init_thread.query_hooks.remove(self.hook)

    def hook(self, cr, query, params, query_start, query_time):
        self.add({
            'query': str(query),
            'full_query': str(cr._format(query, params)),
            'start': query_start,
            'time': query_time,
        })


class PeriodicCollector(Collector):
    """
    Record execution frames asynchronously at most every `interval` seconds.

    :param interval (float): time to wait in seconds between two samples.
    """
    name = 'traces_async'

    def __init__(self, interval=0.01):  # check duration. dynamic?
        super().__init__()
        self.active = False
        self.frame_interval = interval
        self.thread = threading.Thread(target=self.run)
        self.last_frame = None

    def run(self):
        self.active = True
        while self.active:  # maybe add a check on parent_thread state?
            self.add()
            time.sleep(self.frame_interval)
        self._entries.append({'stack': [], 'start': time.time()})  # add final end frame

    def start(self):
        interval = self.profiler.params.get('traces_async_interval')
        if interval:
            self.frame_interval = min(max(float(interval), 0.001), 1)
        self.thread.start()

    def stop(self):
        self.active = False
        self.thread.join()

    def add(self, entry=None, frame=None):
        """ Add an entry (dict) to this collector. """
        frame = frame or get_current_frame(self.profiler.init_thread)
        if frame == self.last_frame:
            # don't save if the frame is exactly the same as the previous one.
            # maybe modify the last entry to add a last seen?
            return
        self.last_frame = frame
        super().add(entry=entry, frame=frame)


class SyncCollector(Collector):
    """
    Record complete execution synchronously.
    Note that --limit-memory-hard may need to be increased when launching Odoo.
    """
    name = 'traces_sync'

    def start(self):
        assert not self._processed, "You cannot start SyncCollector after accessing entries."
        sys.settrace(self.hook)  # todo test setprofile, but maybe not multithread safe

    def stop(self):
        sys.settrace(None)

    def hook(self, _frame, event, _arg=None):
        if event == 'line':
            return
        entry = {'event': event, 'frame': _format_frame(_frame)}
        if event == 'call' and _frame.f_back:
            # we need the parent frame to determine the line number of the call
            entry['parent_frame'] = _format_frame(_frame.f_back)
        self.add(entry, frame=_frame)
        return self.hook

    def _get_stack_trace(self, frame=None):
        # Getting the full stack trace is slow, and not useful in this case.
        # SyncCollector only saves the top frame and event at each call and
        # recomputes the complete stack at the end.
        return None

    def post_process(self):
        # Transform the evented traces to full stack traces. This processing
        # could be avoided since speedscope will transform that back to
        # evented anyway, but it is actually simpler to integrate into the
        # current speedscope logic, especially when mixed with SQLCollector.
        # We could improve it by saving as evented and manage it later.
        stack = []
        for entry in self._entries:
            frame = entry.pop('frame')
            event = entry.pop('event')
            if event == 'call':
                if stack:
                    stack[-1] = entry.pop('parent_frame')
                stack.append(frame)
            elif event == 'return':
                stack.pop()
            entry['stack'] = stack[:]
        super().post_process()


class ExecutionContext:
    """
    Add some context on thread at current call stack level.
    This context stored by collector beside stack and is used by Speedscope
    to add a level to the stack with this information.
    """
    def __init__(self, **context):
        self.context = context
        self.stack_trace_level = None

    def __enter__(self):
        current_thread = threading.current_thread()
        self.stack_trace_level = stack_size()
        if not hasattr(current_thread, 'exec_context'):
            current_thread.exec_context = {}
        current_thread.exec_context[self.stack_trace_level] = self.context

    def __exit__(self, *_args):
        threading.current_thread().exec_context.pop(self.stack_trace_level)


class Profiler:
    """
    Context manager to use to start the recording of some execution.
    Will save sql and async stack trace by default.
    """
    def __init__(self, collectors=None, db=..., profile_session=None,
                 description=None, disable_gc=False, params=None):
        """
        :param db: database name to use to save results.
            Will try to define database automatically by default.
            Use value ``None`` to not save results in a database.
        :param collectors: list of string and Collector object Ex: ['sql', PeriodicCollector(interval=0.2)]. Use `None` for default collectors
        :param profile_session: session description to use to reproup multiple profile. use make_session(name) for default format.
        :param description: description of the current profiler Suggestion: (route name/test method/loading module, ...)
        :param disable_gc: flag to disable gc durring profiling (usefull to avoid gc while profiling, especially during sql execution)
        :param params: parameters usable by collectors (like frame interval)
        """
        self.start_time = 0
        self.duration = 0
        self.profile_session = profile_session or make_session()
        self.description = description
        self.init_frame = None
        self.init_stack_trace = None
        self.init_thread = None
        self.disable_gc = disable_gc
        self.filecache = {}
        self.params = params or {}  # custom parameters usable by collectors

        if db is ...:
            # determine database from current thread
            db = getattr(threading.current_thread(), 'dbname', None)
            if not db:
                # only raise if path is not given and db is not explicitely disabled
                raise Exception('Database name cannot be defined automaticaly. \n Please provide a valid/falsy dbname or path parameter')
        self.db = db

        # collectors
        if collectors is None:
            collectors = ['sql', 'traces_async']
        self.collectors = []
        for collector in collectors:
            if isinstance(collector, str):
                try:
                    collector = Collector.make(collector)
                except Exception:
                    _logger.error("Could not create collector with name %r", collector)
                    continue
            collector.profiler = self
            self.collectors.append(collector)

    def __enter__(self):
        self.init_thread = threading.current_thread()
        self.init_frame = get_current_frame(self.init_thread)
        self.init_stack_trace = _get_stack_trace(self.init_frame)
        if self.description is None:
            frame = self.init_frame
            code = frame.f_code
            self.description = f"{frame.f_code.co_name} ({code.co_filename}:{frame.f_lineno})"
        if self.disable_gc and gc.isenabled():
            gc.disable()
        self.start_time = time.time()
        for collector in self.collectors:
            collector.start()
        return self

    def __exit__(self, *args):
        try:
            for collector in self.collectors:
                collector.stop()
            self.duration = time.time() - self.start_time
            self._add_file_lines(self.init_stack_trace)

            if self.db:
                # pylint: disable=import-outside-toplevel
                from odoo.sql_db import db_connect  # only import from odoo if/when needed.
                with db_connect(self.db).cursor() as cr:
                    values = {
                        "name": self.description,
                        "session": self.profile_session,
                        "create_date": datetime.datetime.now(),
                        "init_stack_trace": json.dumps(_format_stack(self.init_stack_trace)),
                        "duration": self.duration,
                        "entry_count": self.entry_count(),
                    }
                    for collector in self.collectors:
                        if collector.entries:
                            values[collector.name] = json.dumps(collector.entries)
                    query = sql.SQL("INSERT INTO {}({}) VALUES %s RETURNING id").format(
                        sql.Identifier("ir_profile"),
                        sql.SQL(",").join(map(sql.Identifier, values)),
                    )
                    cr.execute(query, [tuple(values.values())])
                    profile_id = cr.fetchone()[0]
                    _logger.info('ir_profile %s (%s) created', profile_id, self.profile_session)
        finally:
            if self.disable_gc:
                gc.enable()

    def _add_file_lines(self, stack):
        for index, frame in enumerate(stack):
            (filename, lineno, name, line) = frame
            if line != '':
                continue
            # retrieve file lines from the filecache
            try:
                filelines = self.filecache[filename]
            except KeyError:
                try:
                    with tools.file_open(filename, filter_ext=('.py',)) as f:
                        filelines = f.readlines()
                except (ValueError, FileNotFoundError):  # mainly for <decorator> "filename"
                    filelines = None
                self.filecache[filename] = filelines
            # fill in the line
            if filelines is not None:
                line = filelines[lineno - 1]
                stack[index] = (filename, lineno, name, line)

    def entry_count(self):
        """ Return the total number of entries collected in this profiler. """
        return sum(len(collector.entries) for collector in self.collectors)

    def format_path(self, path):
        """
        Utility function to format a path for this profiler.
        This is mainly useful to uniquify a path between executions.
        """
        return path.format(
            time=datetime.datetime.now().strftime("%Y%m%d-%H%M%S"),
            len=self.entry_count(),
            desc=re.sub("[^0-9a-zA-Z-]+", "_", self.description)
        )

    def json(self):
        """
        Utility function to generate a json version of this profiler.
        This is useful to write profiling entries into a file, such as::

            with Profiler(db=None) as profiler:
                do_stuff()

            filename = p.format_path('/home/foo/{desc}_{len}.json')
            with open(filename, 'w') as f:
                f.write(profiler.json())
        """
        return json.dumps({
            "name": self.description,
            "session": self.profile_session,
            "create_date": datetime.datetime.now().strftime("%Y%m%d-%H%M%S"),
            "init_stack_trace": _format_stack(self.init_stack_trace),
            "duration": self.duration,
            "collectors": {collector.name: collector.entries for collector in self.collectors},
        }, indent=4)


class Nested:
    """
    Utility to nest another context manager inside a profiler.

    The profiler should only be called directly in the "with" without nesting it
    with ExitStack. If not, the retrieval of the 'init_frame' may be incorrect
    and lead to an error "Limit frame was not found" when profiling. Since the
    stack will ignore all stack frames inside this file, the nested frames will
    be ignored, too. This is also why Nested() does not use
    contextlib.contextmanager.
    """
    def __init__(self, profiler, context_manager):
        self.profiler = profiler
        self.context_manager = context_manager

    def __enter__(self):
        self.profiler.__enter__()
        return self.context_manager.__enter__()

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return self.context_manager.__exit__(exc_type, exc_value, traceback)
        finally:
            self.profiler.__exit__(exc_type, exc_value, traceback)
