# tests for win32gui
import array
import operator
import sys
import unittest

import pywintypes
import win32api
import win32gui


class TestPyGetString(unittest.TestCase):
    def test_get_string(self):
        # test invalid addresses cause a ValueError rather than crash!
        self.assertRaises(ValueError, win32gui.PyGetString, 0)
        self.assertRaises(ValueError, win32gui.PyGetString, 1)
        self.assertRaises(ValueError, win32gui.PyGetString, 1, 1)


class TestPyGetMemory(unittest.TestCase):
    def test_ob(self):
        # Check the PyGetMemory result and a bytes string can be compared
        test_data = b"\0\1\2\3\4\5\6"
        c = array.array("b", test_data)
        addr, buflen = c.buffer_info()
        got = win32gui.PyGetMemory(addr, buflen)
        self.assertEqual(len(got), len(test_data))
        self.assertEqual(bytes(got), test_data)

    def test_memory_index(self):
        # Check we can index into the buffer object returned by PyGetMemory
        test_data = b"\0\1\2\3\4\5\6"
        c = array.array("b", test_data)
        addr, buflen = c.buffer_info()
        got = win32gui.PyGetMemory(addr, buflen)
        self.assertEqual(got[0], 0)

    def test_memory_slice(self):
        # Check we can slice the buffer object returned by PyGetMemory
        test_data = b"\0\1\2\3\4\5\6"
        c = array.array("b", test_data)
        addr, buflen = c.buffer_info()
        got = win32gui.PyGetMemory(addr, buflen)
        self.assertEqual(list(got[0:3]), [0, 1, 2])

    def test_real_view(self):
        # Do the PyGetMemory, then change the original memory, then ensure
        # the initial object we fetched sees the new value.
        test_data = b"\0\1\2\3\4\5\6"
        c = array.array("b", test_data)
        addr, buflen = c.buffer_info()
        got = win32gui.PyGetMemory(addr, buflen)
        self.assertEqual(got[0], 0)
        c[0] = 1
        self.assertEqual(got[0], 1)

    def test_memory_not_writable(self):
        # Check the buffer object fetched by PyGetMemory isn't writable.
        test_data = b"\0\1\2\3\4\5\6"
        c = array.array("b", test_data)
        addr, buflen = c.buffer_info()
        got = win32gui.PyGetMemory(addr, buflen)
        self.assertRaises(TypeError, operator.setitem, got, 0, 1)


class TestEnumWindowsFamily(unittest.TestCase):
    @classmethod
    def enum_callback_sle(cls, handle, data):
        win32api.SetLastError(1)
        return data

    @classmethod
    def enum_callback_exc(cls, handle, data):
        raise ValueError

    @classmethod
    def enum_callback(cls, handle, data):
        return data

    def setUp(self):
        self.default_data_set = (None, -1, 0, 1, True, False)
        self.type_data_set = ("", (), {})

    def test_enumwindows(self):
        win32api.SetLastError(0)
        for data in (0, False):
            self.assertRaises(
                pywintypes.error, win32gui.EnumWindows, self.enum_callback_sle, data
            )
        for data in (None, 1, True):
            self.assertIsNone(win32gui.EnumWindows(self.enum_callback_sle, data))
        win32api.SetLastError(0)
        for data in self.default_data_set:
            self.assertIsNone(win32gui.EnumWindows(self.enum_callback, data))
        for data in self.default_data_set:
            self.assertRaises(
                ValueError, win32gui.EnumWindows, self.enum_callback_exc, data
            )
        for func in (
            self.enum_callback,
            self.enum_callback_sle,
        ):
            for data in self.type_data_set:
                self.assertRaises(TypeError, win32gui.EnumWindows, func, data)
        if sys.version_info >= (3, 10):
            for func in (
                self.enum_callback,
                self.enum_callback_sle,
            ):
                self.assertRaises(
                    TypeError, win32gui.EnumWindows, func, self.enum_callback, 2.718282
                )

    def test_enumchildwindows(self):
        win32api.SetLastError(0)
        for data in self.default_data_set:
            self.assertIsNone(win32gui.EnumChildWindows(None, self.enum_callback, data))
        for data in self.default_data_set:
            self.assertIsNone(
                win32gui.EnumChildWindows(None, self.enum_callback_sle, data)
            )
        win32api.SetLastError(0)
        for data in self.default_data_set:
            self.assertRaises(
                ValueError,
                win32gui.EnumChildWindows,
                None,
                self.enum_callback_exc,
                data,
            )
        for data in self.type_data_set:
            for func in (
                self.enum_callback,
                self.enum_callback_sle,
            ):
                self.assertRaises(
                    TypeError, win32gui.EnumChildWindows, None, func, data
                )
        if sys.version_info >= (3, 10):
            for func in (
                self.enum_callback,
                self.enum_callback_sle,
            ):
                self.assertRaises(
                    TypeError,
                    win32gui.EnumChildWindows,
                    None,
                    func,
                    self.enum_callback,
                    2.718282,
                )

    def test_enumdesktopwindows(self):
        win32api.SetLastError(0)
        desktop = None
        for data in (0, False):
            self.assertRaises(
                pywintypes.error,
                win32gui.EnumDesktopWindows,
                desktop,
                self.enum_callback_sle,
                data,
            )
        for data in (None, 1, True):
            self.assertIsNone(
                win32gui.EnumDesktopWindows(desktop, self.enum_callback_sle, data)
            )
        win32api.SetLastError(0)
        for data in self.default_data_set:
            self.assertIsNone(
                win32gui.EnumDesktopWindows(desktop, self.enum_callback, data)
            )
        for data in self.default_data_set:
            self.assertRaises(
                ValueError,
                win32gui.EnumDesktopWindows,
                desktop,
                self.enum_callback_exc,
                data,
            )
        desktops = (0, None)
        for desktop in desktops:
            for data in self.default_data_set:
                self.assertRaises(
                    ValueError,
                    win32gui.EnumDesktopWindows,
                    desktop,
                    self.enum_callback_exc,
                    data,
                )
        for func in (
            self.enum_callback,
            self.enum_callback_sle,
        ):
            for desktop in desktops:
                for data in self.type_data_set:
                    self.assertRaises(
                        TypeError, win32gui.EnumDesktopWindows, 0, func, data
                    )
        if sys.version_info >= (3, 10):
            for func in (
                self.enum_callback,
                self.enum_callback_sle,
            ):
                for desktop in desktops:
                    self.assertRaises(
                        TypeError, win32gui.EnumDesktopWindows, 0, func, 2.718282
                    )


class TestWindowProperties(unittest.TestCase):
    def setUp(self):
        self.class_functions = (
            win32gui.GetClassName,
            win32gui.RealGetWindowClass,
        )

    def test_classname(self):
        for func in self.class_functions:
            self.assertRaises(pywintypes.error, func, 0)
        wnd = win32gui.GetDesktopWindow()
        for func in self.class_functions:
            self.assertTrue(func(wnd))


if __name__ == "__main__":
    unittest.main()
