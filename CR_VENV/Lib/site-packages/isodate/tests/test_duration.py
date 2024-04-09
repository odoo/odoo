##############################################################################
# Copyright 2009, Gerhard Weis
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#  * Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#  * Neither the name of the authors nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT
##############################################################################
'''
Test cases for the isoduration module.
'''
import unittest
import operator
from datetime import timedelta, date, datetime

from isodate import Duration, parse_duration, ISO8601Error
from isodate import D_DEFAULT, D_WEEK, D_ALT_EXT, duration_isoformat

# the following list contains tuples of ISO duration strings and the expected
# result from the parse_duration method. A result of None means an ISO8601Error
# is expected.
PARSE_TEST_CASES = {'P18Y9M4DT11H9M8S': (Duration(4, 8, 0, 0, 9, 11, 0, 9, 18),
                                         D_DEFAULT, None),
                    'P2W': (timedelta(weeks=2), D_WEEK, None),
                    'P3Y6M4DT12H30M5S': (Duration(4, 5, 0, 0, 30, 12, 0, 6, 3),
                                         D_DEFAULT, None),
                    'P23DT23H': (timedelta(hours=23, days=23),
                                 D_DEFAULT, None),
                    'P4Y': (Duration(years=4), D_DEFAULT, None),
                    'P1M': (Duration(months=1), D_DEFAULT, None),
                    'PT1M': (timedelta(minutes=1), D_DEFAULT, None),
                    'P0.5Y': (Duration(years=0.5), D_DEFAULT, None),
                    'PT36H': (timedelta(hours=36), D_DEFAULT, 'P1DT12H'),
                    'P1DT12H': (timedelta(days=1, hours=12), D_DEFAULT, None),
                    '+P11D': (timedelta(days=11), D_DEFAULT, 'P11D'),
                    '-P2W': (timedelta(weeks=-2), D_WEEK, None),
                    '-P2.2W': (timedelta(weeks=-2.2), D_DEFAULT,
                               '-P15DT9H36M'),
                    'P1DT2H3M4S': (timedelta(days=1, hours=2, minutes=3,
                                             seconds=4), D_DEFAULT, None),
                    'P1DT2H3M': (timedelta(days=1, hours=2, minutes=3),
                                 D_DEFAULT, None),
                    'P1DT2H': (timedelta(days=1, hours=2), D_DEFAULT, None),
                    'PT2H': (timedelta(hours=2), D_DEFAULT, None),
                    'PT2.3H': (timedelta(hours=2.3), D_DEFAULT, 'PT2H18M'),
                    'PT2H3M4S': (timedelta(hours=2, minutes=3, seconds=4),
                                 D_DEFAULT, None),
                    'PT3M4S': (timedelta(minutes=3, seconds=4), D_DEFAULT,
                               None),
                    'PT22S': (timedelta(seconds=22), D_DEFAULT, None),
                    'PT22.22S': (timedelta(seconds=22.22), 'PT%S.%fS',
                                 'PT22.220000S'),
                    '-P2Y': (Duration(years=-2), D_DEFAULT, None),
                    '-P3Y6M4DT12H30M5S': (Duration(-4, -5, 0, 0, -30, -12, 0,
                                                   -6, -3), D_DEFAULT, None),
                    '-P1DT2H3M4S': (timedelta(days=-1, hours=-2, minutes=-3,
                                              seconds=-4), D_DEFAULT, None),
                    # alternative format
                    'P0018-09-04T11:09:08': (Duration(4, 8, 0, 0, 9, 11, 0, 9,
                                                      18), D_ALT_EXT, None),
                    # 'PT000022.22': timedelta(seconds=22.22),
                    }

#                       d1                    d2           '+', '-', '>'
# A list of test cases to test addition and subtraction between datetime and
# Duration objects.
# each tuple contains 2 duration strings, and a result string for addition and
# one for subtraction. The last value says, if the first duration is greater
# than the second.
MATH_TEST_CASES = (('P5Y7M1DT9H45M16.72S', 'PT27M24.68S',
                    'P5Y7M1DT10H12M41.4S', 'P5Y7M1DT9H17M52.04S', None),
                   ('PT28M12.73S', 'PT56M29.92S',
                    'PT1H24M42.65S', '-PT28M17.19S', False),
                   ('P3Y7M23DT5H25M0.33S', 'PT1H1.95S',
                    'P3Y7M23DT6H25M2.28S', 'P3Y7M23DT4H24M58.38S', None),
                   ('PT1H1.95S', 'P3Y7M23DT5H25M0.33S',
                    'P3Y7M23DT6H25M2.28S', '-P3Y7M23DT4H24M58.38S', None),
                   ('P1332DT55M0.33S', 'PT1H1.95S',
                    'P1332DT1H55M2.28S', 'P1331DT23H54M58.38S', True),
                   ('PT1H1.95S', 'P1332DT55M0.33S',
                    'P1332DT1H55M2.28S', '-P1331DT23H54M58.38S', False))


# A list of test cases to test addition and subtraction of date/datetime
# and Duration objects. They are tested against the results of an
# equal long timedelta duration.
DATE_TEST_CASES = ((date(2008, 2, 29),
                    timedelta(days=10, hours=12, minutes=20),
                    Duration(days=10, hours=12, minutes=20)),
                   (date(2008, 1, 31),
                    timedelta(days=10, hours=12, minutes=20),
                    Duration(days=10, hours=12, minutes=20)),
                   (datetime(2008, 2, 29),
                    timedelta(days=10, hours=12, minutes=20),
                    Duration(days=10, hours=12, minutes=20)),
                   (datetime(2008, 1, 31),
                    timedelta(days=10, hours=12, minutes=20),
                    Duration(days=10, hours=12, minutes=20)),
                   (datetime(2008, 4, 21),
                    timedelta(days=10, hours=12, minutes=20),
                    Duration(days=10, hours=12, minutes=20)),
                   (datetime(2008, 5, 5),
                    timedelta(days=10, hours=12, minutes=20),
                    Duration(days=10, hours=12, minutes=20)),
                   (datetime(2000, 1, 1),
                    timedelta(hours=-33),
                    Duration(hours=-33)),
                   (datetime(2008, 5, 5),
                    Duration(years=1, months=1, days=10, hours=12,
                             minutes=20),
                    Duration(months=13, days=10, hours=12, minutes=20)),
                   (datetime(2000, 3, 30),
                    Duration(years=1, months=1, days=10, hours=12,
                             minutes=20),
                    Duration(months=13, days=10, hours=12, minutes=20)),
                   )

# A list of test cases of additon of date/datetime and Duration. The results
# are compared against a given expected result.
DATE_CALC_TEST_CASES = (
    (date(2000, 2, 1),
     Duration(years=1, months=1),
     date(2001, 3, 1)),
    (date(2000, 2, 29),
     Duration(years=1, months=1),
     date(2001, 3, 29)),
    (date(2000, 2, 29),
     Duration(years=1),
     date(2001, 2, 28)),
    (date(1996, 2, 29),
     Duration(years=4),
     date(2000, 2, 29)),
    (date(2096, 2, 29),
     Duration(years=4),
     date(2100, 2, 28)),
    (date(2000, 2, 1),
     Duration(years=-1, months=-1),
     date(1999, 1, 1)),
    (date(2000, 2, 29),
     Duration(years=-1, months=-1),
     date(1999, 1, 29)),
    (date(2000, 2, 1),
     Duration(years=1, months=1, days=1),
     date(2001, 3, 2)),
    (date(2000, 2, 29),
     Duration(years=1, months=1, days=1),
     date(2001, 3, 30)),
    (date(2000, 2, 29),
     Duration(years=1, days=1),
     date(2001, 3, 1)),
    (date(1996, 2, 29),
     Duration(years=4, days=1),
     date(2000, 3, 1)),
    (date(2096, 2, 29),
     Duration(years=4, days=1),
     date(2100, 3, 1)),
    (date(2000, 2, 1),
     Duration(years=-1, months=-1, days=-1),
     date(1998, 12, 31)),
    (date(2000, 2, 29),
     Duration(years=-1, months=-1, days=-1),
     date(1999, 1, 28)),
    (date(2001, 4, 1),
     Duration(years=-1, months=-1, days=-1),
     date(2000, 2, 29)),
    (date(2000, 4, 1),
     Duration(years=-1, months=-1, days=-1),
     date(1999, 2, 28)),
    (Duration(years=1, months=2),
     Duration(years=0, months=0, days=1),
     Duration(years=1, months=2, days=1)),
    (Duration(years=-1, months=-1, days=-1),
     date(2000, 4, 1),
     date(1999, 2, 28)),
    (Duration(years=1, months=1, weeks=5),
     date(2000, 1, 30),
     date(2001, 4, 4)),
    (parse_duration("P1Y1M5W"),
     date(2000, 1, 30),
     date(2001, 4, 4)),
    (parse_duration("P0.5Y"),
     date(2000, 1, 30),
     None),
    (Duration(years=1, months=1, hours=3),
     datetime(2000, 1, 30, 12, 15, 00),
     datetime(2001, 2, 28, 15, 15, 00)),
    (parse_duration("P1Y1MT3H"),
     datetime(2000, 1, 30, 12, 15, 00),
     datetime(2001, 2, 28, 15, 15, 00)),
    (Duration(years=1, months=2),
     timedelta(days=1),
     Duration(years=1, months=2, days=1)),
    (timedelta(days=1),
     Duration(years=1, months=2),
     Duration(years=1, months=2, days=1)),
    (datetime(2008, 1, 1, 0, 2),
     Duration(months=1),
     datetime(2008, 2, 1, 0, 2)),
    (datetime.strptime("200802", "%Y%M"),
     parse_duration("P1M"),
     datetime(2008, 2, 1, 0, 2)),
    (datetime(2008, 2, 1),
     Duration(months=1),
     datetime(2008, 3, 1)),
    (datetime.strptime("200802", "%Y%m"),
     parse_duration("P1M"),
     datetime(2008, 3, 1)),
    # (date(2000, 1, 1),
    #  Duration(years=1.5),
    #  date(2001, 6, 1)),
    # (date(2000, 1, 1),
    #  Duration(years=1, months=1.5),
    #  date(2001, 2, 14)),
    )

# A list of test cases of multiplications of durations
# are compared against a given expected result.
DATE_MUL_TEST_CASES = (
    (Duration(years=1, months=1),
     3,
     Duration(years=3, months=3)),
    (Duration(years=1, months=1),
     -3,
     Duration(years=-3, months=-3)),
    (3,
     Duration(years=1, months=1),
     Duration(years=3, months=3)),
    (-3,
     Duration(years=1, months=1),
     Duration(years=-3, months=-3)),
    (5,
     Duration(years=2, minutes=40),
     Duration(years=10, hours=3, minutes=20)),
    (-5,
     Duration(years=2, minutes=40),
     Duration(years=-10, hours=-3, minutes=-20)),
    (7,
     Duration(years=1, months=2, weeks=40),
     Duration(years=8, months=2, weeks=280)))


class DurationTest(unittest.TestCase):
    '''
    This class tests various other aspects of the isoduration module,
    which are not covered with the test cases listed above.
    '''

    def test_associative(self):
        '''
        Adding 2 durations to a date is not associative.
        '''
        days1 = Duration(days=1)
        months1 = Duration(months=1)
        start = date(2000, 3, 30)
        res1 = start + days1 + months1
        res2 = start + months1 + days1
        self.assertNotEqual(res1, res2)

    def test_typeerror(self):
        '''
        Test if TypError is raised with certain parameters.
        '''
        self.assertRaises(TypeError, parse_duration, date(2000, 1, 1))
        self.assertRaises(TypeError, operator.sub, Duration(years=1),
                          date(2000, 1, 1))
        self.assertRaises(TypeError, operator.sub, 'raise exc',
                          Duration(years=1))
        self.assertRaises(TypeError, operator.add,
                          Duration(years=1, months=1, weeks=5),
                          'raise exception')
        self.assertRaises(TypeError, operator.add, 'raise exception',
                          Duration(years=1, months=1, weeks=5))
        self.assertRaises(TypeError, operator.mul,
                          Duration(years=1, months=1, weeks=5),
                          'raise exception')
        self.assertRaises(TypeError, operator.mul, 'raise exception',
                          Duration(years=1, months=1, weeks=5))
        self.assertRaises(TypeError, operator.mul,
                          Duration(years=1, months=1, weeks=5),
                          3.14)
        self.assertRaises(TypeError, operator.mul, 3.14,
                          Duration(years=1, months=1, weeks=5))

    def test_parseerror(self):
        '''
        Test for unparseable duration string.
        '''
        self.assertRaises(ISO8601Error, parse_duration, 'T10:10:10')

    def test_repr(self):
        '''
        Test __repr__ and __str__ for Duration objects.
        '''
        dur = Duration(10, 10, years=10, months=10)
        self.assertEqual('10 years, 10 months, 10 days, 0:00:10', str(dur))
        self.assertEqual('isodate.duration.Duration(10, 10, 0,'
                         ' years=10, months=10)', repr(dur))
        dur = Duration(months=0)
        self.assertEqual('0:00:00', str(dur))
        dur = Duration(months=1)
        self.assertEqual('1 month, 0:00:00', str(dur))

    def test_hash(self):
        '''
        Test __hash__ for Duration objects.
        '''
        dur1 = Duration(10, 10, years=10, months=10)
        dur2 = Duration(9, 9, years=9, months=9)
        dur3 = Duration(10, 10, years=10, months=10)
        self.assertNotEqual(hash(dur1), hash(dur2))
        self.assertNotEqual(id(dur1), id(dur2))
        self.assertEqual(hash(dur1), hash(dur3))
        self.assertNotEqual(id(dur1), id(dur3))
        durSet = set()
        durSet.add(dur1)
        durSet.add(dur2)
        durSet.add(dur3)
        self.assertEqual(len(durSet), 2)

    def test_neg(self):
        '''
        Test __neg__ for Duration objects.
        '''
        self.assertEqual(-Duration(0), Duration(0))
        self.assertEqual(-Duration(years=1, months=1),
                         Duration(years=-1, months=-1))
        self.assertEqual(-Duration(years=1, months=1), Duration(months=-13))
        self.assertNotEqual(-Duration(years=1), timedelta(days=-365))
        self.assertNotEqual(-timedelta(days=365), Duration(years=-1))
        # FIXME: this test fails in python 3... it seems like python3
        #        treats a == b the same b == a
        # self.assertNotEqual(-timedelta(days=10), -Duration(days=10))

    def test_format(self):
        '''
        Test various other strftime combinations.
        '''
        self.assertEqual(duration_isoformat(Duration(0)), 'P0D')
        self.assertEqual(duration_isoformat(-Duration(0)), 'P0D')
        self.assertEqual(duration_isoformat(Duration(seconds=10)), 'PT10S')
        self.assertEqual(duration_isoformat(Duration(years=-1, months=-1)),
                         '-P1Y1M')
        self.assertEqual(duration_isoformat(-Duration(years=1, months=1)),
                         '-P1Y1M')
        self.assertEqual(duration_isoformat(-Duration(years=-1, months=-1)),
                         'P1Y1M')
        self.assertEqual(duration_isoformat(-Duration(years=-1, months=-1)),
                         'P1Y1M')
        dur = Duration(years=3, months=7, days=23, hours=5, minutes=25,
                       milliseconds=330)
        self.assertEqual(duration_isoformat(dur), 'P3Y7M23DT5H25M0.33S')
        self.assertEqual(duration_isoformat(-dur), '-P3Y7M23DT5H25M0.33S')

    def test_equal(self):
        '''
        Test __eq__ and __ne__ methods.
        '''
        self.assertEqual(Duration(years=1, months=1),
                         Duration(years=1, months=1))
        self.assertEqual(Duration(years=1, months=1), Duration(months=13))
        self.assertNotEqual(Duration(years=1, months=2),
                            Duration(years=1, months=1))
        self.assertNotEqual(Duration(years=1, months=1), Duration(months=14))
        self.assertNotEqual(Duration(years=1), timedelta(days=365))
        self.assertFalse(Duration(years=1, months=1) !=
                         Duration(years=1, months=1))
        self.assertFalse(Duration(years=1, months=1) != Duration(months=13))
        self.assertTrue(Duration(years=1, months=2) !=
                        Duration(years=1, months=1))
        self.assertTrue(Duration(years=1, months=1) != Duration(months=14))
        self.assertTrue(Duration(years=1) != timedelta(days=365))
        self.assertEqual(Duration(days=1), timedelta(days=1))
        # FIXME: this test fails in python 3... it seems like python3
        #        treats a != b the same b != a
        # self.assertNotEqual(timedelta(days=1), Duration(days=1))

    def test_totimedelta(self):
        '''
        Test conversion form Duration to timedelta.
        '''
        dur = Duration(years=1, months=2, days=10)
        self.assertEqual(dur.totimedelta(datetime(1998, 2, 25)),
                         timedelta(434))
        # leap year has one day more in february
        self.assertEqual(dur.totimedelta(datetime(2000, 2, 25)),
                         timedelta(435))
        dur = Duration(months=2)
        # march is longer than february, but april is shorter than
        # march (cause only one day difference compared to 2)
        self.assertEqual(dur.totimedelta(datetime(2000, 2, 25)), timedelta(60))
        self.assertEqual(dur.totimedelta(datetime(2001, 2, 25)), timedelta(59))
        self.assertEqual(dur.totimedelta(datetime(2001, 3, 25)), timedelta(61))


def create_parsetestcase(durationstring, expectation, format, altstr):
    """
    Create a TestCase class for a specific test.

    This allows having a separate TestCase for each test tuple from the
    PARSE_TEST_CASES list, so that a failed test won't stop other tests.
    """

    class TestParseDuration(unittest.TestCase):
        '''
        A test case template to parse an ISO duration string into a
        timedelta or Duration object.
        '''

        def test_parse(self):
            '''
            Parse an ISO duration string and compare it to the expected value.
            '''
            result = parse_duration(durationstring)
            self.assertEqual(result, expectation)

        def test_format(self):
            '''
            Take duration/timedelta object and create ISO string from it.
            This is the reverse test to test_parse.
            '''
            if altstr:
                self.assertEqual(duration_isoformat(expectation, format),
                                 altstr)
            else:
                # if durationstring == '-P2W':
                #     import pdb; pdb.set_trace()
                self.assertEqual(duration_isoformat(expectation, format),
                                 durationstring)

    return unittest.TestLoader().loadTestsFromTestCase(TestParseDuration)


def create_mathtestcase(dur1, dur2, resadd, ressub, resge):
    """
    Create a TestCase class for a specific test.

    This allows having a separate TestCase for each test tuple from the
    MATH_TEST_CASES list, so that a failed test won't stop other tests.
    """

    dur1 = parse_duration(dur1)
    dur2 = parse_duration(dur2)
    resadd = parse_duration(resadd)
    ressub = parse_duration(ressub)

    class TestMathDuration(unittest.TestCase):
        '''
        A test case template test addition, subtraction and >
        operators for Duration objects.
        '''

        def test_add(self):
            '''
            Test operator + (__add__, __radd__)
            '''
            self.assertEqual(dur1 + dur2, resadd)

        def test_sub(self):
            '''
            Test operator - (__sub__, __rsub__)
            '''
            self.assertEqual(dur1 - dur2, ressub)

        def test_ge(self):
            '''
            Test operator > and <
            '''
            def dogetest():
                ''' Test greater than.'''
                return dur1 > dur2

            def doletest():
                ''' Test less than.'''
                return dur1 < dur2
            if resge is None:
                self.assertRaises(TypeError, dogetest)
                self.assertRaises(TypeError, doletest)
            else:
                self.assertEqual(dogetest(), resge)
                self.assertEqual(doletest(), not resge)

    return unittest.TestLoader().loadTestsFromTestCase(TestMathDuration)


def create_datetestcase(start, tdelta, duration):
    """
    Create a TestCase class for a specific test.

    This allows having a separate TestCase for each test tuple from the
    DATE_TEST_CASES list, so that a failed test won't stop other tests.
    """

    class TestDateCalc(unittest.TestCase):
        '''
        A test case template test addition, subtraction
        operators for Duration objects.
        '''

        def test_add(self):
            '''
            Test operator +.
            '''
            self.assertEqual(start + tdelta, start + duration)

        def test_sub(self):
            '''
            Test operator -.
            '''
            self.assertEqual(start - tdelta, start - duration)

    return unittest.TestLoader().loadTestsFromTestCase(TestDateCalc)


def create_datecalctestcase(start, duration, expectation):
    """
    Create a TestCase class for a specific test.

    This allows having a separate TestCase for each test tuple from the
    DATE_CALC_TEST_CASES list, so that a failed test won't stop other tests.
    """

    class TestDateCalc(unittest.TestCase):
        '''
        A test case template test addition operators for Duration objects.
        '''

        def test_calc(self):
            '''
            Test operator +.
            '''
            if expectation is None:
                self.assertRaises(ValueError, operator.add, start, duration)
            else:
                self.assertEqual(start + duration, expectation)

    return unittest.TestLoader().loadTestsFromTestCase(TestDateCalc)


def create_datemultestcase(operand1, operand2, expectation):
    """
    Create a TestCase class for a specific test.

    This allows having a separate TestCase for each test tuple from the
    DATE_CALC_TEST_CASES list, so that a failed test won't stop other tests.
    """

    class TestDateMul(unittest.TestCase):
        '''
        A test case template test addition operators for Duration objects.
        '''

        def test_mul(self):
            '''
            Test operator *.
            '''
            self.assertEqual(operand1 * operand2, expectation)

    return unittest.TestLoader().loadTestsFromTestCase(TestDateMul)


def test_suite():
    '''
    Return a test suite containing all test defined above.
    '''
    suite = unittest.TestSuite()
    for durationstring, (expectation, format,
                         altstr) in PARSE_TEST_CASES.items():
        suite.addTest(create_parsetestcase(durationstring, expectation,
                                           format, altstr))
    for testdata in MATH_TEST_CASES:
        suite.addTest(create_mathtestcase(*testdata))
    for testdata in DATE_TEST_CASES:
        suite.addTest(create_datetestcase(*testdata))
    for testdata in DATE_CALC_TEST_CASES:
        suite.addTest(create_datecalctestcase(*testdata))
    for testdata in DATE_MUL_TEST_CASES:
        suite.addTest(create_datemultestcase(*testdata))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(DurationTest))
    return suite


# load_tests Protocol
def load_tests(loader, tests, pattern):
    return test_suite()


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
