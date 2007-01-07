#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/test/test_widgetbase_tpc.py
"""
Tests for TypedPropertyCollection class.
"""

import os, sys, copy
from os.path import join, basename, splitext

from reportlab.test import unittest
from reportlab.test.utils import makeSuiteForClasses, printLocation

from reportlab.graphics.widgetbase import PropHolder, TypedPropertyCollection
from reportlab.lib.attrmap import AttrMap, AttrMapValue
from reportlab.lib.validators import isNumber


TPC = TypedPropertyCollection


class PH(PropHolder):
    _attrMap = AttrMap(
        a = AttrMapValue(isNumber),
        b = AttrMapValue(isNumber)
        )


class APH(PH):
    def __init__(self):
        self.a = 1


class BPH(APH):
    def __init__(self):
        APH.__init__(self)

    def __getattr__(self,name):
        if name=='b': return -1
        raise AttributeError


class TPCTestCase(unittest.TestCase):
    "Test TypedPropertyCollection class."

    def test0(self):
        "Test setting an invalid collective attribute."

        t = TPC(PH)
        try:
            t.c = 42
        except AttributeError:
            pass


    def test1(self):
        "Test setting a valid collective attribute."

        t = TPC(PH)
        t.a = 42
        assert t.a == 42


    def test2(self):
        "Test setting a valid collective attribute with an invalid value."

        t = TPC(PH)
        try:
            t.a = 'fourty-two'
        except AttributeError:
            pass


    def test3(self):
        "Test setting a valid collective attribute with a convertible invalid value."

        t = TPC(PH)
        t.a = '42'
        assert t.a == '42' # Or should it rather be an integer?


    def test4(self):
        "Test accessing an unset collective attribute."

        t = TPC(PH)
        try:
            t.a
        except AttributeError:
            pass


    def test5(self):
        "Test overwriting a collective attribute in one slot."

        t = TPC(PH)
        t.a = 42
        t[0].a = 4242
        assert t[0].a == 4242


    def test6(self):
        "Test overwriting a one slot attribute with a collective one."

        t = TPC(PH)
        t[0].a = 4242
        t.a = 42
        assert t[0].a == 4242


    def test7(self):
        "Test to ensure we can handle classes with __getattr__ methods"

        a=TypedPropertyCollection(APH)
        b=TypedPropertyCollection(BPH)

        a.a=3
        b.a=4
        try:
            a.b
            assert 1, "Shouldn't be able to see a.b"
        except AttributeError:
            pass
        a.b=0
        assert a.b==0, "Wrong value for "+str(a.b)
        assert b.b==-1, "This should call __getattr__ special"
        b.b=0
        assert a[0].b==0
        assert b[0].b==-1, "Class __getattr__ should return -1"


def makeSuite():
    return makeSuiteForClasses(TPCTestCase)


#noruntests
if __name__ == "__main__":
    unittest.TextTestRunner().run(makeSuite())
    printLocation()
