# -*- coding: utf-8 -*-
# Copyright 2018 gevent contributes
# See LICENSE for details.

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import gc
import unittest

import gevent.testing as greentest

import gevent
from gevent import util
from gevent import local
from greenlet import getcurrent

from gevent._compat import NativeStrIO

class MyLocal(local.local):
    # pylint:disable=disallowed-name
    def __init__(self, foo):
        self.foo = foo

@greentest.skipOnPyPy("5.10.x is *very* slow formatting stacks")
class TestFormat(greentest.TestCase):

    def test_basic(self):
        lines = util.format_run_info()

        value = '\n'.join(lines)
        self.assertIn('Threads', value)
        self.assertIn('Greenlets', value)

        # because it's a raw greenlet, we have no data for it.
        self.assertNotIn("Spawned at", value)
        self.assertNotIn("Parent greenlet", value)
        self.assertNotIn("Spawn Tree Locals", value)

    def test_with_Greenlet(self):
        rl = local.local()
        rl.some_attr = 1
        def root():
            l = MyLocal(42)
            assert l
            # And an empty local.
            l2 = local.local()
            assert l2
            gevent.getcurrent().spawn_tree_locals['a value'] = 42
            io = NativeStrIO()
            g = gevent.spawn(util.print_run_info, file=io)
            g.join()

            return io.getvalue()

        g = gevent.spawn(root)
        g.name = 'Printer'
        g.join()
        value = g.value


        self.assertIn("Spawned at", value)
        self.assertIn("Parent:", value)
        self.assertIn("Spawn Tree Locals", value)
        self.assertIn("Greenlet Locals:", value)
        self.assertIn('MyLocal', value)
        self.assertIn("Printer", value) # The name is printed
        # Empty locals should not be printed
        self.assertNotIn('{}', value)

@greentest.skipOnPyPy("See TestFormat")
class TestTree(greentest.TestCase):

    def setUp(self):
        super(TestTree, self).setUp()
        self.track_greenlet_tree = gevent.config.track_greenlet_tree
        gevent.config.track_greenlet_tree = True
        self.maxDiff = None

    def tearDown(self):
        gevent.config.track_greenlet_tree = self.track_greenlet_tree
        super(TestTree, self).tearDown()

    def _build_tree(self):
        # pylint:disable=too-many-locals
        # Python 2.7 on Travis seems to show unexpected greenlet objects
        # so perhaps we need a GC?
        for _ in range(3):
            gc.collect()
        gevent.get_hub().resolver = None # Reset resolver, don't need to see it
        gevent.get_hub().threadpool = None # ditto the pool
        glets = []
        l = MyLocal(42)
        assert l

        def s(f):
            str(getcurrent())
            g = gevent.spawn(f)
            # Access this in spawning order for consistent sorting
            # at print time in the test case.
            getattr(g, 'minimal_ident')
            str(g)
            return g

        def t1():
            raise greentest.ExpectedException()

        def t2():
            l = MyLocal(16)
            assert l
            g = s(t1)
            g.name = 'CustomName-' + str(g.minimal_ident)
            return g

        s1 = s(t2)
        #self.assertEqual(0, s1.minimal_ident)
        s1.join()

        glets.append(s(t2))

        def t3():
            return s(t2)

        s3 = s(t3)
        if s3.spawn_tree_locals is not None:
            # Can only do this if we're tracking spawn trees
            s3.spawn_tree_locals['stl'] = 'STL'
        s3.join()

        s4 = s(util.GreenletTree.current_tree)
        s4.join()

        tree = s4.value
        return tree, str(tree), tree.format(details={'running_stacks': False,
                                                     'spawning_stacks': False})

    def _normalize_tree_format(self, value):
        import re
        hexobj = re.compile('0x[0123456789abcdef]+L?', re.I)

        hub_repr = repr(gevent.get_hub())
        value = value.replace(hub_repr, "<HUB>")

        value = hexobj.sub('X', value)
        value = value.replace('epoll', 'select')
        value = value.replace('select', 'default')
        value = value.replace('test__util', '__main__')
        value = re.compile(' fileno=.').sub('', value)
        value = value.replace('ref=-1', 'ref=0')
        value = value.replace("type.current_tree", 'GreenletTree.current_tree')
        value = value.replace('gevent.tests.__main__.MyLocal', '__main__.MyLocal')
        # The repr in CPython greenlet 1.0a1 added extra info
        value = value.replace('(otid=X) ', '')
        value = value.replace(' dead>', '>')
        value = value.replace(' current active started main>', '>')
        return value

    @greentest.ignores_leakcheck
    def test_tree(self):
        with gevent.get_hub().ignoring_expected_test_error():
            tree, str_tree, tree_format = self._build_tree()

        self.assertTrue(tree.root)

        self.assertNotIn('Parent', str_tree) # Simple output
        value = self._normalize_tree_format(tree_format)

        expected = """\
<greenlet.greenlet object at X>
 :    Parent: None
 :    Greenlet Locals:
 :      Local <class '__main__.MyLocal'> at X
 :        {'foo': 42}
 +--- <HUB>
 :          Parent: <greenlet.greenlet object at X>
 +--- <Greenlet "Greenlet-1" at X: t2>; finished with value <Greenlet "CustomName-0" at 0x
 :          Parent: <HUB>
 |    +--- <Greenlet "CustomName-0" at X: t1>; finished with exception ExpectedException()
 :                Parent: <HUB>
 +--- <Greenlet "Greenlet-2" at X: t2>; finished with value <Greenlet "CustomName-4" at 0x
 :          Parent: <HUB>
 |    +--- <Greenlet "CustomName-4" at X: t1>; finished with exception ExpectedException()
 :                Parent: <HUB>
 +--- <Greenlet "Greenlet-3" at X: t3>; finished with value <Greenlet "Greenlet-5" at X
 :          Parent: <HUB>
 :          Spawn Tree Locals
 :          {'stl': 'STL'}
 |    +--- <Greenlet "Greenlet-5" at X: t2>; finished with value <Greenlet "CustomName-6" at 0x
 :                Parent: <HUB>
 |         +--- <Greenlet "CustomName-6" at X: t1>; finished with exception ExpectedException()
 :                      Parent: <HUB>
 +--- <Greenlet "Greenlet-7" at X: <bound method GreenletTree.current_tree of <class 'gevent.util.GreenletTree'>>>; finished with value <gevent.util.GreenletTree obje
            Parent: <HUB>
        """.strip()
        self.assertEqual(expected, value)

    @greentest.ignores_leakcheck
    def test_tree_no_track(self):
        gevent.config.track_greenlet_tree = False
        with gevent.get_hub().ignoring_expected_test_error():
            self._build_tree()

    @greentest.ignores_leakcheck
    def test_forest_fake_parent(self):
        from greenlet import greenlet as RawGreenlet

        def t4():
            # Ignore this one, make the child the parent,
            # and don't be a child of the hub.
            c = RawGreenlet(util.GreenletTree.current_tree)
            c.parent.greenlet_tree_is_ignored = True
            c.greenlet_tree_is_root = True
            return c.switch()


        g = RawGreenlet(t4)
        tree = g.switch()

        tree_format = tree.format(details={'running_stacks': False,
                                           'spawning_stacks': False})
        value = self._normalize_tree_format(tree_format)

        expected = """\
<greenlet.greenlet object at X>; not running
 :    Parent: <greenlet.greenlet object at X>
        """.strip()

        self.assertEqual(expected, value)


class TestAssertSwitches(unittest.TestCase):

    def test_time_sleep(self):
        # A real blocking function
        from time import sleep

        # No time given, we detect the failure to switch immediately
        with self.assertRaises(util._FailedToSwitch) as exc:
            with util.assert_switches():
                sleep(0.001)

        message = str(exc.exception)
        self.assertIn('To any greenlet in', message)

        # Supply a max blocking allowed and exceed it
        with self.assertRaises(util._FailedToSwitch):
            with util.assert_switches(0.001):
                sleep(0.1)


        # Supply a max blocking allowed, and exit before that happens,
        # but don't switch to the hub as requested
        with self.assertRaises(util._FailedToSwitch) as exc:
            with util.assert_switches(0.001, hub_only=True):
                sleep(0)

        message = str(exc.exception)
        self.assertIn('To the hub in', message)
        self.assertIn('(max allowed 0.0010 seconds)', message)

        # Supply a max blocking allowed, and exit before that happens,
        # and allow any switch (or no switch).
        # Note that we need to use a relatively long duration;
        # sleep(0) on Windows can actually take a substantial amount of time
        # sometimes (more than 0.001s)
        with util.assert_switches(1.0, hub_only=False):
            sleep(0)


    def test_no_switches_no_function(self):
        # No blocking time given, no switch performed: exception
        with self.assertRaises(util._FailedToSwitch):
            with util.assert_switches():
                pass

        # blocking time given, for all greenlets, no switch performed: nothing
        with util.assert_switches(max_blocking_time=1, hub_only=False):
            pass

    def test_exception_not_supressed(self):

        with self.assertRaises(NameError):
            with util.assert_switches():
                raise NameError()

    def test_nested(self):
        from greenlet import gettrace
        with util.assert_switches() as outer:
            self.assertEqual(gettrace(), outer.tracer)
            self.assertIsNotNone(outer.tracer.active_greenlet)

            with util.assert_switches() as inner:
                self.assertEqual(gettrace(), inner.tracer)
                self.assertEqual(inner.tracer.previous_trace_function, outer.tracer)

                inner.tracer('switch', (self, self))

                self.assertIs(self, inner.tracer.active_greenlet)
                self.assertIs(self, outer.tracer.active_greenlet)

            self.assertEqual(gettrace(), outer.tracer)

if __name__ == '__main__':
    greentest.main()
