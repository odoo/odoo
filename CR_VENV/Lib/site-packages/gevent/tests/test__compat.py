from __future__ import absolute_import, print_function, division

import os
import unittest

class TestFSPath(unittest.TestCase):

    def setUp(self):
        self.__path = None

    def __fspath__(self):
        if self.__path is not None:
            return self.__path
        raise AttributeError("Accessing path data")

    def _callFUT(self, arg):
        from gevent._compat import _fspath
        return _fspath(arg)

    def test_text(self):
        s = u'path'
        self.assertIs(s, self._callFUT(s))

    def test_bytes(self):
        s = b'path'
        self.assertIs(s, self._callFUT(s))

    def test_None(self):
        with self.assertRaises(TypeError):
            self._callFUT(None)

    def test_working_path(self):
        self.__path = u'text'
        self.assertIs(self.__path, self._callFUT(self))

        self.__path = b'bytes'
        self.assertIs(self.__path, self._callFUT(self))

    def test_failing_path_AttributeError(self):
        self.assertIsNone(self.__path)
        with self.assertRaises(AttributeError):
            self._callFUT(self)

    def test_fspath_non_str(self):
        self.__path = object()
        with self.assertRaises(TypeError):
            self._callFUT(self)

@unittest.skipUnless(hasattr(os, 'fspath'), "Tests native os.fspath")
class TestNativeFSPath(TestFSPath):

    def _callFUT(self, arg):
        return os.fspath(arg)

if __name__ == '__main__':
    unittest.main()
