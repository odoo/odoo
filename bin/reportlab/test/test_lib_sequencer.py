#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/test/test_lib_sequencer.py
"""Tests for the reportlab.lib.sequencer module.
"""


import sys, random

from reportlab.test import unittest
from reportlab.test.utils import makeSuiteForClasses, printLocation
from reportlab.lib.sequencer import Sequencer


class SequencerTestCase(unittest.TestCase):
    "Test Sequencer usage."

    def test0(self):
        "Test sequencer default counter."

        seq = Sequencer()
        msg = 'Initial value is not zero!'
        assert seq._this() == 0, msg


    def test1(self):
        "Test incrementing default counter."

        seq = Sequencer()

        for i in range(1, 101):
            n = seq.next()
            msg = 'Sequence value is not correct!'
            assert seq._this() == n, msg


    def test2(self):
        "Test resetting default counter."

        seq = Sequencer()
        start = seq._this()

        for i in range(1, 101):
            n = seq.next()

        seq.reset()

        msg = 'Sequence value not correctly reset!'
        assert seq._this() == start, msg


    def test3(self):
        "Test incrementing dedicated counter."

        seq = Sequencer()

        for i in range(1, 101):
            n = seq.next('myCounter1')
            msg = 'Sequence value is not correct!'
            assert seq._this('myCounter1') == n, msg


    def test4(self):
        "Test resetting dedicated counter."

        seq = Sequencer()
        start = seq._this('myCounter1')

        for i in range(1, 101):
            n = seq.next('myCounter1')

        seq.reset('myCounter1')

        msg = 'Sequence value not correctly reset!'
        assert seq._this('myCounter1') == start, msg


    def test5(self):
        "Test incrementing multiple dedicated counters."

        seq = Sequencer()
        startMyCounter0 = seq._this('myCounter0')
        startMyCounter1 = seq._this('myCounter1')

        for i in range(1, 101):
            n = seq.next('myCounter0')
            msg = 'Sequence value is not correct!'
            assert seq._this('myCounter0') == n, msg
            m = seq.next('myCounter1')
            msg = 'Sequence value is not correct!'
            assert seq._this('myCounter1') == m, msg


##    def testRandom(self):
##        "Test randomly manipulating multiple dedicated counters."
##
##        seq = Sequencer()
##        counterNames = ['c0', 'c1', 'c2', 'c3']
##
##        # Init.
##        for cn in counterNames:
##            setattr(self, cn, seq._this(cn))
##            msg = 'Counter start value is not correct!'
##            assert seq._this(cn) == 0, msg
##
##        # Increment/decrement.
##        for i in range(1, 101):
##            n = seq.next('myCounter0')
##            msg = 'Sequence value is not correct!'
##            assert seq._this('myCounter0') == n, msg
##            m = seq.next('myCounter1')
##            msg = 'Sequence value is not correct!'
##            assert seq._this('myCounter1') == m, msg


def makeSuite():
    return makeSuiteForClasses(SequencerTestCase)


#noruntests
if __name__ == "__main__":
    unittest.TextTestRunner().run(makeSuite())
    printLocation()
