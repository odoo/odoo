# Copyright (c) 2018 gevent. See LICENSE for details.
from __future__ import print_function, absolute_import, division

import os
import sys

from weakref import ref as wref

from greenlet import getcurrent

from gevent import config as GEVENT_CONFIG
from gevent.monkey import get_original
from gevent.events import notify
from gevent.events import EventLoopBlocked
from gevent.events import MemoryUsageThresholdExceeded
from gevent.events import MemoryUsageUnderThreshold
from gevent.events import IPeriodicMonitorThread
from gevent.events import implementer

from gevent._tracer import GreenletTracer
from gevent._compat import thread_mod_name
from gevent._compat import perf_counter
from gevent._compat import get_this_psutil_process



__all__ = [
    'PeriodicMonitoringThread',
]

get_thread_ident = get_original(thread_mod_name, 'get_ident')
start_new_thread = get_original(thread_mod_name, 'start_new_thread')
thread_sleep = get_original('time', 'sleep')



class MonitorWarning(RuntimeWarning):
    """The type of warnings we emit."""


class _MonitorEntry(object):

    __slots__ = ('function', 'period', 'last_run_time')

    def __init__(self, function, period):
        self.function = function
        self.period = period
        self.last_run_time = 0

    def __eq__(self, other):
        return self.function == other.function and self.period == other.period

    def __hash__(self):
        return hash((self.function, self.period))

    def __repr__(self):
        return repr((self.function, self.period, self.last_run_time))


@implementer(IPeriodicMonitorThread)
class PeriodicMonitoringThread(object):
    # This doesn't extend threading.Thread because that gets monkey-patched.
    # We use the low-level 'start_new_thread' primitive instead.

    # The amount of seconds we will sleep when we think we have nothing
    # to do.
    inactive_sleep_time = 2.0

    # The absolute minimum we will sleep, regardless of
    # what particular monitoring functions want to say.
    min_sleep_time = 0.005

    # The minimum period in seconds at which we will check memory usage.
    # Getting memory usage is fairly expensive.
    min_memory_monitor_period = 2

    # A list of _MonitorEntry objects: [(function(hub), period, last_run_time))]
    # The first entry is always our entry for self.monitor_blocking
    _monitoring_functions = None

    # The calculated min sleep time for the monitoring functions list.
    _calculated_sleep_time = None

    # A boolean value that also happens to capture the
    # memory usage at the time we exceeded the threshold. Reset
    # to 0 when we go back below.
    _memory_exceeded = 0

    # The instance of GreenletTracer we're using
    _greenlet_tracer = None

    def __init__(self, hub):
        self._hub_wref = wref(hub, self._on_hub_gc)
        self.should_run = True

        # Must be installed in the thread that the hub is running in;
        # the trace function is threadlocal
        assert get_thread_ident() == hub.thread_ident
        self._greenlet_tracer = GreenletTracer()

        self._monitoring_functions = [_MonitorEntry(self.monitor_blocking,
                                                    GEVENT_CONFIG.max_blocking_time)]
        self._calculated_sleep_time = GEVENT_CONFIG.max_blocking_time
        # Create the actual monitoring thread. This is effectively a "daemon"
        # thread.
        self.monitor_thread_ident = start_new_thread(self, ())

        # We must track the PID to know if your thread has died after a fork
        self.pid = os.getpid()

    def _on_fork(self):
        # Pseudo-standard method that resolver_ares and threadpool
        # also have, called by hub.reinit()
        pid = os.getpid()
        if pid != self.pid:
            self.pid = pid
            self.monitor_thread_ident = start_new_thread(self, ())

    @property
    def hub(self):
        return self._hub_wref()


    def monitoring_functions(self):
        # Return a list of _MonitorEntry objects

        # Update max_blocking_time each time.
        mbt = GEVENT_CONFIG.max_blocking_time # XXX: Events so we know when this changes.
        if mbt != self._monitoring_functions[0].period:
            self._monitoring_functions[0].period = mbt
            self._calculated_sleep_time = min(x.period for x in self._monitoring_functions)
        return self._monitoring_functions

    def add_monitoring_function(self, function, period):
        if not callable(function):
            raise ValueError("function must be callable")

        if period is None:
            # Remove.
            self._monitoring_functions = [
                x for x in self._monitoring_functions
                if x.function != function
            ]
        elif period <= 0:
            raise ValueError("Period must be positive.")
        else:
            # Add or update period
            entry = _MonitorEntry(function, period)
            self._monitoring_functions = [
                x if x.function != function else entry
                for x in self._monitoring_functions
            ]
            if entry not in self._monitoring_functions:
                self._monitoring_functions.append(entry)
        self._calculated_sleep_time = min(x.period for x in self._monitoring_functions)

    def calculate_sleep_time(self):
        min_sleep = self._calculated_sleep_time
        if min_sleep <= 0:
            # Everyone wants to be disabled. Sleep for a longer period of
            # time than usual so we don't spin unnecessarily. We might be
            # enabled again in the future.
            return self.inactive_sleep_time
        return max((min_sleep, self.min_sleep_time))

    def kill(self):
        if not self.should_run:
            # Prevent overwriting trace functions.
            return
        # Stop this monitoring thread from running.
        self.should_run = False
        # Uninstall our tracing hook
        self._greenlet_tracer.kill()

    def _on_hub_gc(self, _):
        self.kill()

    def __call__(self):
        # The function that runs in the monitoring thread.
        # We cannot use threading.current_thread because it would
        # create an immortal DummyThread object.
        getcurrent().gevent_monitoring_thread = wref(self)

        try:
            while self.should_run:
                functions = self.monitoring_functions()
                assert functions
                sleep_time = self.calculate_sleep_time()

                thread_sleep(sleep_time)

                # Make sure the hub is still around, and still active,
                # and keep it around while we are here.
                hub = self.hub
                if not hub:
                    self.kill()

                if self.should_run:
                    this_run = perf_counter()
                    for entry in functions:
                        f = entry.function
                        period = entry.period
                        last_run = entry.last_run_time
                        if period and last_run + period <= this_run:
                            entry.last_run_time = this_run
                            f(hub)
                del hub # break our reference to hub while we sleep

        except SystemExit:
            pass
        except: # pylint:disable=bare-except
            # We're a daemon thread, so swallow any exceptions that get here
            # during interpreter shutdown.
            if not sys or not sys.stderr: # pragma: no cover
                # Interpreter is shutting down
                pass
            else:
                hub = self.hub
                if hub is not None:
                    # XXX: This tends to do bad things like end the process, because we
                    # try to switch *threads*, which can't happen. Need something better.
                    hub.handle_error(self, *sys.exc_info())

    def monitor_blocking(self, hub):
        # Called periodically to see if the trace function has
        # fired to switch greenlets. If not, we will print
        # the greenlet tree.

        # For tests, we return a true value when we think we found something
        # blocking

        did_block = self._greenlet_tracer.did_block_hub(hub)
        if not did_block:
            return

        active_greenlet = did_block[1] # pylint:disable=unsubscriptable-object
        report = self._greenlet_tracer.did_block_hub_report(
            hub, active_greenlet,
            dict(greenlet_stacks=False, current_thread_ident=self.monitor_thread_ident))

        stream = hub.exception_stream
        for line in report:
            # Printing line by line may interleave with other things,
            # but it should also prevent a "reentrant call to print"
            # when the report is large.
            print(line, file=stream)

        notify(EventLoopBlocked(active_greenlet, GEVENT_CONFIG.max_blocking_time, report))
        return (active_greenlet, report)

    def ignore_current_greenlet_blocking(self):
        self._greenlet_tracer.ignore_current_greenlet_blocking()

    def monitor_current_greenlet_blocking(self):
        self._greenlet_tracer.monitor_current_greenlet_blocking()

    def _get_process(self): # pylint:disable=method-hidden
        proc = get_this_psutil_process()
        self._get_process = lambda: proc
        return proc

    def can_monitor_memory_usage(self):
        return self._get_process() is not None

    def install_monitor_memory_usage(self):
        # Start monitoring memory usage, if possible.
        # If not possible, emit a warning.
        if not self.can_monitor_memory_usage():
            import warnings
            warnings.warn("Unable to monitor memory usage. Install psutil.",
                          MonitorWarning)
            return

        self.add_monitoring_function(self.monitor_memory_usage,
                                     max(GEVENT_CONFIG.memory_monitor_period,
                                         self.min_memory_monitor_period))

    def monitor_memory_usage(self, _hub):
        max_allowed = GEVENT_CONFIG.max_memory_usage
        if not max_allowed:
            # They disabled it.
            return -1 # value for tests

        rusage = self._get_process().memory_full_info()
        # uss only documented available on Windows, Linux, and OS X.
        # If not available, fall back to rss as an aproximation.
        mem_usage = getattr(rusage, 'uss', 0) or rusage.rss

        event = None # Return value for tests

        if mem_usage > max_allowed:
            if mem_usage > self._memory_exceeded:
                # We're still growing
                event = MemoryUsageThresholdExceeded(
                    mem_usage, max_allowed, rusage)
                notify(event)
            self._memory_exceeded = mem_usage
        else:
            # we're below. Were we above it last time?
            if self._memory_exceeded:
                event = MemoryUsageUnderThreshold(
                    mem_usage, max_allowed, rusage, self._memory_exceeded)
                notify(event)
            self._memory_exceeded = 0

        return event

    def __repr__(self):
        return '<%s at %s in thread %s greenlet %r for %r>' % (
            self.__class__.__name__,
            hex(id(self)),
            hex(self.monitor_thread_ident),
            getcurrent(),
            self._hub_wref())
