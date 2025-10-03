# Part of Odoo. See LICENSE file for full copyright and licensing details.

from contextlib import nullcontext, ExitStack
from datetime import datetime
import json
import logging
import sys
import time
import threading
import re
import tracemalloc

from psycopg2 import OperationalError

from odoo import tools
from odoo.tools import SQL

from .gc import disabling_gc


_logger = logging.getLogger(__name__)

# ensure we have a non patched time for profiling times when using freezegun
real_datetime_now = datetime.now
real_time = time.time.__call__
real_cpu_time = time.thread_time.__call__


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
        _logger.runbot("Limit frame was not found")
    return list(reversed(stack))


def stack_size():
    frame = get_current_frame()
    size = 0
    while frame:
        size += 1
        frame = frame.f_back
    return size


def make_session(name=''):
    return f'{real_datetime_now():%Y-%m-%d %H:%M:%S} {name}'


def force_hook():
    """
    Force periodic profiling collectors to generate some stack trace.  This is
    useful before long calls that do not release the GIL, so that the time
    spent in those calls is attributed to a specific stack trace, instead of
    some arbitrary former frame.
    """
    thread = threading.current_thread()
    for func in getattr(thread, 'profile_hooks', ()):
        func()


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
    _store = name
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
        self._entries.append({
            'stack': self._get_stack_trace(frame),
            'exec_context': getattr(self.profiler.init_thread, 'exec_context', ()),
            'start': real_time(),
            **(entry or {}),
        })

    def progress(self, entry=None, frame=None):
        """ Checks if the limits were met and add to the entries"""
        if self.profiler.entry_count_limit \
            and self.profiler.entry_count() >= self.profiler.entry_count_limit:
            self.profiler.end()

        self.add(entry=entry,frame=frame)

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

    def summary(self):
        return f"{'='*10} {self.name} {'='*10} \n Entries: {len(self._entries)}"


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
        self.progress({
            'query': str(query),
            'full_query': str(cr._format(query, params)),
            'start': query_start,
            'time': query_time,
        })

    def summary(self):
        total_time = sum(entry['time'] for entry in self._entries) or 1
        sql_entries = ''
        for entry in self._entries:
            sql_entries += f"\n{'-' * 100}'\n'{entry['time']}  {'*' * int(entry['time'] / total_time * 100)}'\n'{entry['full_query']}"
        return super().summary() + sql_entries


class _BasePeriodicCollector(Collector):
    """
    Record execution frames asynchronously at most every `interval` seconds.

    :param interval (float): time to wait in seconds between two samples.
    """
    _min_interval = 0.001  # minimum interval allowed
    _max_interval = 5    # maximum interval allowed
    _default_interval = 0.001

    def __init__(self, interval=None):  # check duration. dynamic?
        super().__init__()
        self.active = False
        self.frame_interval = interval or self._default_interval
        self.__thread = threading.Thread(target=self.run)
        self.last_frame = None

    def start(self):
        interval = self.profiler.params.get(f'{self.name}_interval')
        if interval:
            self.frame_interval = min(max(float(interval), self._min_interval), self._max_interval)
        init_thread = self.profiler.init_thread
        if not hasattr(init_thread, 'profile_hooks'):
            init_thread.profile_hooks = []
        init_thread.profile_hooks.append(self.progress)
        self.__thread.start()

    def run(self):
        self.active = True
        self.last_time = real_time()
        while self.active:  # maybe add a check on parent_thread state?
            self.progress()
            time.sleep(self.frame_interval)

        self._entries.append({'stack': [], 'start': real_time()})  # add final end frame

    def stop(self):
        self.active = False
        self.__thread.join()
        self.profiler.init_thread.profile_hooks.remove(self.progress)


class PeriodicCollector(_BasePeriodicCollector):

    name = 'traces_async'

    def add(self, entry=None, frame=None):
        """ Add an entry (dict) to this collector. """
        if self.last_frame:
            duration = real_time() - self._last_time
            if duration > self.frame_interval * 10 and self.last_frame:
                # The profiler has unexpectedly slept for more than 10 frame intervals. This may
                # happen when calling a C library without releasing the GIL. In that case, the
                # last frame was taken before the call, and the next frame is after the call, and
                # the call itself does not appear in any of those frames: the duration of the call
                # is incorrectly attributed to the last frame.
                self._entries[-1]['stack'].append(('profiling', 0, '⚠ Profiler freezed for %s s' % duration, ''))
            self.last_frame = None  # skip duplicate detection for the next frame.
        self._last_time = real_time()

        frame = frame or get_current_frame(self.profiler.init_thread)
        if frame == self.last_frame:
            # don't save if the frame is exactly the same as the previous one.
            # maybe modify the last entry to add a last seen?
            return
        self.last_frame = frame
        super().add(entry=entry, frame=frame)


_lock = threading.Lock()


class MemoryCollector(_BasePeriodicCollector):

    name = 'memory'
    _store = 'others'
    _min_interval = 0.01  # minimum interval allowed
    _default_interval = 1

    def start(self):
        _lock.acquire()
        tracemalloc.start()
        super().start()

    def add(self, entry=None, frame=None):
        """ Add an entry (dict) to this collector. """
        self._entries.append({
            'start': real_time(),
            'memory': tracemalloc.take_snapshot(),
        })

    def stop(self):
        _lock.release()
        tracemalloc.stop()
        super().stop()

    def post_process(self):
        for i, entry in enumerate(self._entries):
            if entry.get("memory", False):
                entry_statistics = entry["memory"].statistics('traceback')
                modified_entry_statistics = [{'traceback': list(statistic.traceback._frames),
                                            'size': statistic.size} for statistic in entry_statistics]
                self._entries[i] = {"memory_tracebacks": modified_entry_statistics, "start": entry['start']}


class QwebTracker:

    def __init__(self, view_id, arch, cr):
        current_thread = threading.current_thread()  # don't store current_thread on self
        self.execution_context_enabled = getattr(current_thread, 'profiler_params', {}).get('execution_context_qweb')
        self.qweb_hooks = getattr(current_thread, 'qweb_hooks', ())
        self.context_stack = []
        self.cr = cr
        self.view_id = view_id
        for hook in self.qweb_hooks:
            hook('render', self.cr.sql_log_count, view_id=view_id, arch=arch)

    def enter_directive(self, directive, attrib, xpath):
        execution_context = None
        if self.execution_context_enabled:
            directive_info = {}
            if ('t-' + directive) in attrib:
                directive_info['t-' + directive] = repr(attrib['t-' + directive])
            if directive == 'set':
                if 't-value' in attrib:
                    directive_info['t-value'] = repr(attrib['t-value'])
                if 't-valuef' in attrib:
                    directive_info['t-valuef'] = repr(attrib['t-valuef'])

                for key in attrib:
                    if key.startswith('t-set-') or key.startswith('t-setf-'):
                        directive_info[key] = repr(attrib[key])
            elif directive == 'foreach':
                directive_info['t-as'] = repr(attrib['t-as'])
            elif directive == 'groups' and 'groups' in attrib and not directive_info.get('t-groups'):
                directive_info['t-groups'] = repr(attrib['groups'])
            elif directive == 'att':
                for key in attrib:
                    if key.startswith('t-att-') or key.startswith('t-attf-'):
                        directive_info[key] = repr(attrib[key])
            elif directive == 'options':
                for key in attrib:
                    if key.startswith('t-options-'):
                        directive_info[key] = repr(attrib[key])
            elif ('t-' + directive) not in attrib:
                directive_info['t-' + directive] = None

            execution_context = tools.profiler.ExecutionContext(**directive_info, xpath=xpath)
            execution_context.__enter__()
            self.context_stack.append(execution_context)

        for hook in self.qweb_hooks:
            hook('enter', self.cr.sql_log_count, view_id=self.view_id, xpath=xpath, directive=directive, attrib=attrib)

    def leave_directive(self, directive, attrib, xpath):
        if self.execution_context_enabled:
            self.context_stack.pop().__exit__()

        for hook in self.qweb_hooks:
            hook('leave', self.cr.sql_log_count, view_id=self.view_id, xpath=xpath, directive=directive, attrib=attrib)


class QwebCollector(Collector):
    """
    Record qweb execution with directive trace.
    """
    name = 'qweb'

    def __init__(self):
        super().__init__()
        self.events = []

        def hook(event, sql_log_count, **kwargs):
            self.events.append((event, kwargs, sql_log_count, real_time()))
        self.hook = hook

    def _get_directive_profiling_name(self, directive, attrib):
        expr = ''
        if directive == 'set':
            if 't-set' in attrib:
                expr = f"t-set={repr(attrib['t-set'])}"
                if 't-value' in attrib:
                    expr += f" t-value={repr(attrib['t-value'])}"
                if 't-valuef' in attrib:
                    expr += f" t-valuef={repr(attrib['t-valuef'])}"
            for key in attrib:
                if key.startswith('t-set-') or key.startswith('t-setf-'):
                    if expr:
                        expr += ' '
                    expr += f"{key}={repr(attrib[key])}"
        elif directive == 'foreach':
            expr = f"t-foreach={repr(attrib['t-foreach'])} t-as={repr(attrib['t-as'])}"
        elif directive == 'options':
            if attrib.get('t-options'):
                expr = f"t-options={repr(attrib['t-options'])}"
            for key in attrib:
                if key.startswith('t-options-'):
                    expr = f"{expr}  {key}={repr(attrib[key])}"
        elif directive == 'att':
            for key in attrib:
                if key == 't-att' or key.startswith('t-att-') or key.startswith('t-attf-'):
                    if expr:
                        expr += ' '
                    expr += f"{key}={repr(attrib[key])}"
        elif ('t-' + directive) in attrib:
            expr = f"t-{directive}={repr(attrib['t-' + directive])}"
        else:
            expr = f"t-{directive}"

        return expr

    def start(self):
        init_thread = self.profiler.init_thread
        if not hasattr(init_thread, 'qweb_hooks'):
            init_thread.qweb_hooks = []
        init_thread.qweb_hooks.append(self.hook)

    def stop(self):
        self.profiler.init_thread.qweb_hooks.remove(self.hook)

    def post_process(self):
        last_event_query = None
        last_event_time = None
        stack = []
        results = []
        archs = {}
        for event, kwargs, sql_count, time in self.events:
            if event == 'render':
                archs[kwargs['view_id']] = kwargs['arch']
                continue

            # update the active directive with the elapsed time and queries
            if stack:
                top = stack[-1]
                top['delay'] += time - last_event_time
                top['query'] += sql_count - last_event_query
            last_event_time = time
            last_event_query = sql_count

            directive = self._get_directive_profiling_name(kwargs['directive'], kwargs['attrib'])
            if directive:
                if event == 'enter':
                    data = {
                        'view_id': kwargs['view_id'],
                        'xpath': kwargs['xpath'],
                        'directive': directive,
                        'delay': 0,
                        'query': 0,
                    }
                    results.append(data)
                    stack.append(data)
                else:
                    assert event == "leave"
                    data = stack.pop()

        self.add({'results': {'archs': archs, 'data': results}})
        super().post_process()


class ExecutionContext:
    """
    Add some context on thread at current call stack level.
    This context stored by collector beside stack and is used by Speedscope
    to add a level to the stack with this information.
    """
    def __init__(self, **context):
        self.context = context
        self.previous_context = None

    def __enter__(self):
        current_thread = threading.current_thread()
        self.previous_context = getattr(current_thread, 'exec_context', ())
        current_thread.exec_context = self.previous_context + ((stack_size(), self.context),)

    def __exit__(self, *_args):
        threading.current_thread().exec_context = self.previous_context


class Profiler:
    """
    Context manager to use to start the recording of some execution.
    Will save sql and async stack trace by default.
    """
    def __init__(self, collectors=None, db=..., profile_session=None,
                 description=None, disable_gc=False, params=None, log=False):
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
        self.start_cpu_time = 0
        self.cpu_duration = 0
        self.profile_session = profile_session or make_session()
        self.description = description
        self.init_frame = None
        self.init_stack_trace = None
        self.init_thread = None
        self.disable_gc = disable_gc
        self.filecache = {}
        self.params = params or {}  # custom parameters usable by collectors
        self.profile_id = None
        self.log = log
        self.sub_profilers = []
        self.entry_count_limit = int(self.params.get("entry_count_limit",0)) # the limit could be set using a smarter way
        self.done = False
        self.exit_stack = ExitStack()

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
        try:
            self.init_frame = get_current_frame(self.init_thread)
            self.init_stack_trace = _get_stack_trace(self.init_frame)
        except KeyError:
            # when using thread pools (gevent) the thread won't exist in the current_frames
            # this case is managed by http.py but will still fail when adding a profiler
            # inside a piece of code that may be called by a longpolling route.
            # in this case, avoid crashing the caller and disable all collectors
            self.init_frame = self.init_stack_trace = self.collectors = []
            self.db = self.params = None
            message = "Cannot start profiler, thread not found. Is the thread part of a thread pool?"
            if not self.description:
                self.description = message
            _logger.warning(message)

        if self.description is None:
            frame = self.init_frame
            code = frame.f_code
            self.description = f"{frame.f_code.co_name} ({code.co_filename}:{frame.f_lineno})"
        if self.params:
            self.init_thread.profiler_params = self.params
        if self.disable_gc:
            self.exit_stack.enter_context(disabling_gc())
        self.start_time = real_time()
        self.start_cpu_time = real_cpu_time()
        for collector in self.collectors:
            collector.start()
        return self

    def __exit__(self, *args):
        self.end()

    def end(self):
        if self.done:
            return
        self.done = True
        try:
            for collector in self.collectors:
                collector.stop()
            self.duration = real_time() - self.start_time
            self.cpu_duration = real_cpu_time() - self.start_cpu_time
            self._add_file_lines(self.init_stack_trace)

            if self.db:
                # pylint: disable=import-outside-toplevel
                from odoo.sql_db import db_connect  # only import from odoo if/when needed.
                with db_connect(self.db).cursor() as cr:
                    values = {
                        "name": self.description,
                        "session": self.profile_session,
                        "create_date": real_datetime_now(),
                        "init_stack_trace": json.dumps(_format_stack(self.init_stack_trace)),
                        "duration": self.duration,
                        "cpu_duration": self.cpu_duration,
                        "entry_count": self.entry_count(),
                        "sql_count": sum(len(collector.entries) for collector in self.collectors if collector.name == 'sql')
                    }
                    others = {}
                    for collector in self.collectors:
                        if collector.entries:
                            if collector._store == "others":
                                others[collector.name] = json.dumps(collector.entries)
                            else:
                                values[collector.name] = json.dumps(collector.entries)
                    if others:
                        values['others'] = json.dumps(others)
                    query = SQL(
                        "INSERT INTO ir_profile(%s) VALUES %s RETURNING id",
                        SQL(",").join(map(SQL.identifier, values)),
                        tuple(values.values()),
                    )
                    cr.execute(query)
                    self.profile_id = cr.fetchone()[0]
                    _logger.info('ir_profile %s (%s) created', self.profile_id, self.profile_session)
        except OperationalError:
            _logger.exception("Could not save profile in database")
        finally:
            self.exit_stack.close()
            if self.params:
                del self.init_thread.profiler_params
            if self.log:
                _logger.info(self.summary())

    def _get_cm_proxy(self):
        return Nested(self)

    def _add_file_lines(self, stack):
        for index, frame in enumerate(stack):
            (filename, lineno, name, line) = frame
            if line != '':
                continue
            # retrieve file lines from the filecache
            if not lineno:
                continue
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
            time=real_datetime_now().strftime("%Y%m%d-%H%M%S"),
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
            "create_date": real_datetime_now().strftime("%Y%m%d-%H%M%S"),
            "init_stack_trace": _format_stack(self.init_stack_trace),
            "duration": self.duration,
            "collectors": {collector.name: collector.entries for collector in self.collectors},
        }, indent=4)

    def summary(self):
        result = ''
        for profiler in [self, *self.sub_profilers]:
            for collector in profiler.collectors:
                result += f'\n{self.description}\n{collector.summary()}'
        return result


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
    def __init__(self, profiler, context_manager=None):
        self._profiler__ = profiler
        self.context_manager = context_manager or nullcontext()

    def __enter__(self):
        self._profiler__.__enter__()
        return self.context_manager.__enter__()

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return self.context_manager.__exit__(exc_type, exc_value, traceback)
        finally:
            self._profiler__.__exit__(exc_type, exc_value, traceback)
