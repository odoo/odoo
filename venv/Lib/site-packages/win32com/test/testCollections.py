# testCollections.py
#
# This code tests both the client and server side of collections
# and enumerators.
#
# Also has the side effect of testing some of the PythonCOM error semantics.
import sys
import unittest

import pythoncom
import win32com.client
import win32com.server.util
import win32com.test.util
import winerror


def MakeEmptyEnum():
    # create the Python enumerator object as a real COM object
    o = win32com.server.util.wrap(win32com.server.util.Collection())
    return win32com.client.Dispatch(o)


def MakeTestEnum():
    # create a sub-collection, just to make sure it works :-)
    sub = win32com.server.util.wrap(
        win32com.server.util.Collection(["Sub1", 2, "Sub3"])
    )
    # create the Python enumerator object as a real COM object
    o = win32com.server.util.wrap(win32com.server.util.Collection([1, "Two", 3, sub]))
    return win32com.client.Dispatch(o)


def TestEnumAgainst(o, check):
    for i in range(len(check)):
        assert o(i) == check[i], (
            f"Using default method gave the incorrect value - {o(i)!r}/{check[i]!r}"
        )

    for i in range(len(check)):
        assert o.Item(i) == check[i], (
            f"Using Item method gave the incorrect value - {o(i)!r}/{check[i]!r}"
        )

    # First try looping.
    cmp = []
    for s in o:
        cmp.append(s)

    assert cmp[: len(check)] == check, (
        f"Result after looping isn't correct - {cmp[: len(check)]!r}/{check!r}"
    )

    for i in range(len(check)):
        assert o[i] == check[i], "Using indexing gave the incorrect value"


def TestEnum(quiet=None):
    if quiet is None:
        quiet = not "-v" in sys.argv
    if not quiet:
        print("Simple enum test")
    o = MakeTestEnum()
    check = [1, "Two", 3]
    TestEnumAgainst(o, check)

    if not quiet:
        print("sub-collection test")
    sub = o[3]
    TestEnumAgainst(sub, ["Sub1", 2, "Sub3"])

    # Remove the sublist for this test!
    o.Remove(o.Count() - 1)

    if not quiet:
        print("Remove item test")
    del check[1]
    o.Remove(1)
    TestEnumAgainst(o, check)

    if not quiet:
        print("Add item test")
    o.Add("New Item")
    check.append("New Item")
    TestEnumAgainst(o, check)

    if not quiet:
        print("Insert item test")
    o.Insert(2, -1)
    check.insert(2, -1)
    TestEnumAgainst(o, check)

    ### This does not work!
    # if not quiet: print("Indexed replace item test")
    # o[2] = 'Replaced Item'
    # check[2] = 'Replaced Item'
    # TestEnumAgainst(o, check)

    try:
        o()
        raise AssertionError(
            "default method with no args worked when it shouldn't have!"
        )
    except pythoncom.com_error as exc:
        assert exc.hresult == winerror.DISP_E_BADPARAMCOUNT, (
            f"Expected DISP_E_BADPARAMCOUNT - got {exc}"
        )

    try:
        o.Insert("foo", 2)
        raise AssertionError("Insert worked when it shouldn't have!")
    except pythoncom.com_error as exc:
        assert exc.hresult == winerror.DISP_E_TYPEMISMATCH, (
            f"Expected DISP_E_TYPEMISMATCH - got {exc}"
        )

    # Remove the sublist for this test!
    try:
        o.Remove(o.Count())
        raise AssertionError("Remove worked when it shouldn't have!")
    except pythoncom.com_error as exc:
        assert exc.hresult == winerror.DISP_E_BADINDEX, (
            f"Expected DISP_E_BADINDEX - got {exc}"
        )

    # Test an empty collection
    if not quiet:
        print("Empty collection test")
    o = MakeEmptyEnum()
    for item in o:
        raise AssertionError("Empty list performed an iteration")

    try:
        ob = o[1]
        raise AssertionError("Empty list could be indexed")
    except IndexError:
        pass

    try:
        ob = o[0]
        raise AssertionError("Empty list could be indexed")
    except IndexError:
        pass

    try:
        ob = o(0)
        raise AssertionError("Empty list could be indexed")
    except pythoncom.com_error as exc:
        assert exc.hresult == winerror.DISP_E_BADINDEX, (
            f"Expected DISP_E_BADINDEX - got {exc}"
        )


class TestCase(win32com.test.util.TestCase):
    def testEnum(self):
        TestEnum()


if __name__ == "__main__":
    unittest.main()
