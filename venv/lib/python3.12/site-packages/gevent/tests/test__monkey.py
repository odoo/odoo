from gevent import monkey
monkey.patch_all()

import sys
import unittest
from gevent.testing.testcase import SubscriberCleanupMixin

class TestMonkey(SubscriberCleanupMixin, unittest.TestCase):

    maxDiff = None

    def setUp(self):
        super(TestMonkey, self).setUp()

        self.all_events = []
        self.addSubscriber(self.all_events.append)
        self.orig_saved = orig_saved = {}
        for k, v in monkey.saved.items():
            orig_saved[k] = v.copy()


    def tearDown(self):
        monkey.saved = self.orig_saved
        del self.orig_saved
        del self.all_events
        super(TestMonkey, self).tearDown()

    def test_time(self):
        import time
        from gevent import time as gtime
        self.assertIs(time.sleep, gtime.sleep)

    def test_thread(self):
        try:
            import thread
        except ImportError:
            import _thread as thread
        import threading

        from gevent import thread as gthread
        self.assertIs(thread.start_new_thread, gthread.start_new_thread)
        self.assertIs(threading._start_new_thread, gthread.start_new_thread)

        # Event patched by default
        self.assertTrue(monkey.is_object_patched('threading', 'Event'))

        if sys.version_info[0] == 2:
            from gevent import threading as gthreading
            from gevent.event import Event as GEvent
            self.assertIs(threading._sleep, gthreading._sleep)
            self.assertTrue(monkey.is_object_patched('threading', '_Event'))
            self.assertIs(threading._Event, GEvent)

    def test_socket(self):
        import socket
        from gevent import socket as gevent_socket
        self.assertIs(socket.create_connection, gevent_socket.create_connection)

    def test_os(self):
        import os
        import types
        from gevent import os as gos
        for name in ('fork', 'forkpty'):
            if hasattr(os, name):
                attr = getattr(os, name)
                self.assertNotIn('built-in', repr(attr))
                self.assertNotIsInstance(attr, types.BuiltinFunctionType)
                self.assertIsInstance(attr, types.FunctionType)
                self.assertIs(attr, getattr(gos, name))

    def test_saved(self):
        self.assertTrue(monkey.saved)
        for modname, objects in monkey.saved.items():
            self.assertTrue(monkey.is_module_patched(modname))

            for objname in objects:
                self.assertTrue(monkey.is_object_patched(modname, objname))

    def test_patch_subprocess_twice(self):
        Popen = monkey.get_original('subprocess', 'Popen')
        self.assertNotIn('gevent', repr(Popen))
        self.assertIs(Popen, monkey.get_original('subprocess', 'Popen'))
        monkey.patch_subprocess()
        self.assertIs(Popen, monkey.get_original('subprocess', 'Popen'))

    def test_patch_twice_warnings_events(self):
        import warnings

        all_events = self.all_events

        with warnings.catch_warnings(record=True) as issued_warnings:
            # Patch again, triggering just one warning, for
            # a different set of arguments. Because we're going to False instead of
            # turning something on, nothing is actually done, no events are issued.
            monkey.patch_all(os=False, extra_kwarg=42)
            self.assertEqual(len(issued_warnings), 1)
            self.assertIn('more than once', str(issued_warnings[0].message))
            self.assertEqual(all_events, [])

            # Same warning again, but still nothing is done.
            del issued_warnings[:]
            monkey.patch_all(os=False)
            self.assertEqual(len(issued_warnings), 1)
            self.assertIn('more than once', str(issued_warnings[0].message))
            self.assertEqual(all_events, [])
            self.orig_saved['_gevent_saved_patch_all_module_settings'] = monkey.saved[
                '_gevent_saved_patch_all_module_settings']

        # Make sure that re-patching did not change the monkey.saved
        # attribute, overwriting the original functions.
        if 'logging' in monkey.saved and 'logging' not in self.orig_saved:
            # some part of the warning or unittest machinery imports logging
            self.orig_saved['logging'] = monkey.saved['logging']
        self.assertEqual(self.orig_saved, monkey.saved)

        # Make sure some problematic attributes stayed correct.
        # NOTE: This was only a problem if threading was not previously imported.
        for k, v in monkey.saved['threading'].items():
            self.assertNotIn('gevent', str(v), (k, v))

    def test_patch_events(self):
        from gevent import events
        from gevent.testing import verify
        all_events = self.all_events

        def veto(event):
            if isinstance(event, events.GeventWillPatchModuleEvent) and event.module_name == 'ssl':
                raise events.DoNotPatch
        self.addSubscriber(veto)

        monkey.saved = {} # Reset
        monkey.patch_all(thread=False, select=False, extra_kwarg=42) # Go again

        self.assertIsInstance(all_events[0], events.GeventWillPatchAllEvent)
        self.assertEqual({'extra_kwarg': 42}, all_events[0].patch_all_kwargs)
        verify.verifyObject(events.IGeventWillPatchAllEvent, all_events[0])

        self.assertIsInstance(all_events[1], events.GeventWillPatchModuleEvent)
        verify.verifyObject(events.IGeventWillPatchModuleEvent, all_events[1])

        self.assertIsInstance(all_events[2], events.GeventDidPatchModuleEvent)
        verify.verifyObject(events.IGeventWillPatchModuleEvent, all_events[1])

        self.assertIsInstance(all_events[-2], events.GeventDidPatchBuiltinModulesEvent)
        verify.verifyObject(events.IGeventDidPatchBuiltinModulesEvent, all_events[-2])

        self.assertIsInstance(all_events[-1], events.GeventDidPatchAllEvent)
        verify.verifyObject(events.IGeventDidPatchAllEvent, all_events[-1])

        for e in all_events:
            self.assertFalse(isinstance(e, events.GeventDidPatchModuleEvent)
                             and e.module_name == 'ssl')

    def test_patch_queue(self):
        try:
            import queue
        except ImportError:
            # Python 2 called this Queue. Note that having
            # python-future installed gives us a queue module on
            # Python 2 as well.
            queue = None
        if not hasattr(queue, 'SimpleQueue'):
            raise unittest.SkipTest("Needs SimpleQueue")
        # pylint:disable=no-member
        self.assertIs(queue.SimpleQueue, queue._PySimpleQueue)

if __name__ == '__main__':
    unittest.main()
