# Copyright (c) 2018 gevent. See LICENSE for details.
# cython: auto_pickle=False,embedsignature=True,always_allow_keywords=False
from __future__ import print_function, absolute_import, division

import sys
import traceback

from greenlet import settrace
from greenlet import getcurrent

from gevent.util import format_run_info

from gevent._compat import perf_counter
from gevent._util import gmctime


__all__ = [
    'GreenletTracer',
    'HubSwitchTracer',
    'MaxSwitchTracer',
]

# Recall these classes are cython compiled, so
# class variable declarations are bad.


class GreenletTracer(object):
    def __init__(self):
        # A counter, incremented by the greenlet trace function
        # we install on every greenlet switch. This is reset when the
        # periodic monitoring thread runs.

        self.greenlet_switch_counter = 0

        # The greenlet last switched to.
        self.active_greenlet = None

        # The trace function that was previously installed,
        # if any.
        # NOTE: Calling a class instance is cheaper than
        # calling a bound method (at least when compiled with cython)
        # even when it redirects to another function.
        prev_trace = settrace(self)

        self.previous_trace_function = prev_trace

        self._killed = False

    def kill(self):
        # Must be called in the monitored thread.
        if not self._killed:
            self._killed = True
            settrace(self.previous_trace_function)
            self.previous_trace_function = None

    def _trace(self, event, args):
        # This function runs in the thread we are monitoring.
        self.greenlet_switch_counter += 1
        if event in ('switch', 'throw'):
            # args is (origin, target). This is the only defined
            # case
            self.active_greenlet = args[1]
        else:
            self.active_greenlet = None
        if self.previous_trace_function is not None:
            self.previous_trace_function(event, args)

    def __call__(self, event, args):
        return self._trace(event, args)

    def did_block_hub(self, hub):
        # Check to see if we have blocked since the last call to this
        # method. Returns a true value if we blocked (not in the hub),
        # a false value if everything is fine.

        # This may be called in the same thread being traced or a
        # different thread; if a different thread, there is a race
        # condition with this being incremented in the thread we're
        # monitoring, but probably not often enough to lead to
        # annoying false positives.

        active_greenlet = self.active_greenlet
        did_switch = self.greenlet_switch_counter != 0
        self.greenlet_switch_counter = 0

        if did_switch or active_greenlet is None or active_greenlet is hub:
            # Either we switched, or nothing is running (we got a
            # trace event we don't know about or were requested to
            # ignore), or we spent the whole time in the hub, blocked
            # for IO. Nothing to report.
            return False
        return True, active_greenlet

    def ignore_current_greenlet_blocking(self):
        # Don't pay attention to the current greenlet.
        self.active_greenlet = None

    def monitor_current_greenlet_blocking(self):
        self.active_greenlet = getcurrent()

    def did_block_hub_report(self, hub, active_greenlet, format_kwargs):
        # XXX: On Python 2 with greenlet 1.0a1, '%s' formatting a greenlet
        # results in a unicode object. This is a bug in greenlet, I think.
        # https://github.com/python-greenlet/greenlet/issues/218
        report = ['=' * 80,
                  '\n%s : Greenlet %s appears to be blocked' %
                  (gmctime(), str(active_greenlet))]
        report.append("    Reported by %s" % (self,))
        try:
            frame = sys._current_frames()[hub.thread_ident]
        except KeyError:
            # The thread holding the hub has died. Perhaps we shouldn't
            # even report this?
            stack = ["Unknown: No thread found for hub %r\n" % (hub,)]
        else:
            stack = traceback.format_stack(frame)
        report.append('Blocked Stack (for thread id %s):' % (hex(hub.thread_ident),))
        report.append(''.join(stack))
        report.append("Info:")
        report.extend(format_run_info(**format_kwargs))

        return report


class _HubTracer(GreenletTracer):
    def __init__(self, hub, max_blocking_time):
        GreenletTracer.__init__(self)
        self.max_blocking_time = max_blocking_time
        self.hub = hub

    def kill(self):
        self.hub = None
        GreenletTracer.kill(self)


class HubSwitchTracer(_HubTracer):
    # A greenlet tracer that records the last time we switched *into* the hub.

    def __init__(self, hub, max_blocking_time):
        _HubTracer.__init__(self, hub, max_blocking_time)
        self.last_entered_hub = 0

    def _trace(self, event, args):
        GreenletTracer._trace(self, event, args)
        if self.active_greenlet is self.hub:
            self.last_entered_hub = perf_counter()

    def did_block_hub(self, hub):
        if perf_counter() - self.last_entered_hub > self.max_blocking_time:
            return True, self.active_greenlet


class MaxSwitchTracer(_HubTracer):
    # A greenlet tracer that records the maximum time between switches,
    # not including time spent in the hub.

    def __init__(self, hub, max_blocking_time):
        _HubTracer.__init__(self, hub, max_blocking_time)
        self.last_switch = perf_counter()
        self.max_blocking = 0

    def _trace(self, event, args):
        old_active = self.active_greenlet
        GreenletTracer._trace(self, event, args)
        if old_active is not self.hub and old_active is not None:
            # If we're switching out of the hub, the blocking
            # time doesn't count.
            switched_at = perf_counter()
            self.max_blocking = max(self.max_blocking,
                                    switched_at - self.last_switch)

    def did_block_hub(self, hub):
        if self.max_blocking == 0:
            # We never switched. Check the time now
            self.max_blocking = perf_counter() - self.last_switch

        if self.max_blocking > self.max_blocking_time:
            return True, self.active_greenlet


from gevent._util import import_c_accel
import_c_accel(globals(), 'gevent.__tracer')
