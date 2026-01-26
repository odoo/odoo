# -*- coding: utf-8 -*-
"""
Tests for ``gevent.threading`` that DO NOT monkey patch. This
allows easy comparison with the standard module.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import threading

from gevent import threading as gthreading
from gevent import testing

class TestDummyThread(testing.TestCase):

    def test_name(self):
        # Matches the stdlib.
        # https://github.com/gevent/gevent/issues/1659
        std_dummy = threading._DummyThread()
        gvt_dummy = gthreading._DummyThread()
        self.assertIsNot(type(std_dummy), type(gvt_dummy))

        self.assertStartsWith(std_dummy.name, 'Dummy-')
        self.assertStartsWith(gvt_dummy.name, 'Dummy-')


if __name__ == '__main__':
    testing.main()
