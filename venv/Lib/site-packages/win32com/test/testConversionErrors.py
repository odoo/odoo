import unittest

import win32com.client
import win32com.server.util
import win32com.test.util


class Tester:
    _public_methods_ = ["TestValue"]

    def TestValue(self, v):
        pass


def test_ob():
    return win32com.client.Dispatch(win32com.server.util.wrap(Tester()))


class TestException(Exception):
    pass


# The object we try and pass - pywin32 will call __float__ as a last resort.
class BadConversions:
    def __float__(self):
        raise TestException


class TestCase(win32com.test.util.TestCase):
    def test_float(self):
        self.assertRaises(TestException, test_ob().TestValue, BadConversions())


if __name__ == "__main__":
    unittest.main()
