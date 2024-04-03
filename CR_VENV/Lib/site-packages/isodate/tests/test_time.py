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
Test cases for the isotime module.
'''
import unittest
from datetime import time

from isodate import parse_time, UTC, FixedOffset, ISO8601Error, time_isoformat
from isodate import TIME_BAS_COMPLETE, TIME_BAS_MINUTE
from isodate import TIME_EXT_COMPLETE, TIME_EXT_MINUTE
from isodate import TIME_HOUR
from isodate import TZ_BAS, TZ_EXT, TZ_HOUR

# the following list contains tuples of ISO time strings and the expected
# result from the parse_time method. A result of None means an ISO8601Error
# is expected.
TEST_CASES = [('232050', time(23, 20, 50), TIME_BAS_COMPLETE + TZ_BAS),
              ('23:20:50', time(23, 20, 50), TIME_EXT_COMPLETE + TZ_EXT),
              ('2320', time(23, 20), TIME_BAS_MINUTE),
              ('23:20', time(23, 20), TIME_EXT_MINUTE),
              ('23', time(23), TIME_HOUR),
              ('232050,5', time(23, 20, 50, 500000), None),
              ('23:20:50.5', time(23, 20, 50, 500000), None),
              # test precision
              ('15:33:42.123456', time(15, 33, 42, 123456), None),
              ('15:33:42.1234564', time(15, 33, 42, 123456), None),
              ('15:33:42.1234557', time(15, 33, 42, 123456), None),
              ('2320,8', time(23, 20, 48), None),
              ('23:20,8', time(23, 20, 48), None),
              ('23,3', time(23, 18), None),
              ('232030Z', time(23, 20, 30, tzinfo=UTC),
               TIME_BAS_COMPLETE + TZ_BAS),
              ('2320Z', time(23, 20, tzinfo=UTC), TIME_BAS_MINUTE + TZ_BAS),
              ('23Z', time(23, tzinfo=UTC), TIME_HOUR + TZ_BAS),
              ('23:20:30Z', time(23, 20, 30, tzinfo=UTC),
               TIME_EXT_COMPLETE + TZ_EXT),
              ('23:20Z', time(23, 20, tzinfo=UTC), TIME_EXT_MINUTE + TZ_EXT),
              ('152746+0100', time(15, 27, 46,
               tzinfo=FixedOffset(1, 0, '+0100')), TIME_BAS_COMPLETE + TZ_BAS),
              ('152746-0500', time(15, 27, 46,
                                   tzinfo=FixedOffset(-5, 0, '-0500')),
               TIME_BAS_COMPLETE + TZ_BAS),
              ('152746+01', time(15, 27, 46,
                                 tzinfo=FixedOffset(1, 0, '+01:00')),
               TIME_BAS_COMPLETE + TZ_HOUR),
              ('152746-05', time(15, 27, 46,
                                 tzinfo=FixedOffset(-5, -0, '-05:00')),
               TIME_BAS_COMPLETE + TZ_HOUR),
              ('15:27:46+01:00', time(15, 27, 46,
                                      tzinfo=FixedOffset(1, 0, '+01:00')),
               TIME_EXT_COMPLETE + TZ_EXT),
              ('15:27:46-05:00', time(15, 27, 46,
                                      tzinfo=FixedOffset(-5, -0, '-05:00')),
               TIME_EXT_COMPLETE + TZ_EXT),
              ('15:27:46+01', time(15, 27, 46,
                                   tzinfo=FixedOffset(1, 0, '+01:00')),
               TIME_EXT_COMPLETE + TZ_HOUR),
              ('15:27:46-05', time(15, 27, 46,
                                   tzinfo=FixedOffset(-5, -0, '-05:00')),
               TIME_EXT_COMPLETE + TZ_HOUR),
              ('15:27:46-05:30', time(15, 27, 46,
                                      tzinfo=FixedOffset(-5, -30, '-05:30')),
               TIME_EXT_COMPLETE + TZ_EXT),
              ('15:27:46-0545', time(15, 27, 46,
                                     tzinfo=FixedOffset(-5, -45, '-0545')),
               TIME_EXT_COMPLETE + TZ_BAS),
              ('1:17:30', None, TIME_EXT_COMPLETE)]


def create_testcase(timestring, expectation, format):
    """
    Create a TestCase class for a specific test.

    This allows having a separate TestCase for each test tuple from the
    TEST_CASES list, so that a failed test won't stop other tests.
    """

    class TestTime(unittest.TestCase):
        '''
        A test case template to parse an ISO time string into a time
        object.
        '''

        def test_parse(self):
            '''
            Parse an ISO time string and compare it to the expected value.
            '''
            if expectation is None:
                self.assertRaises(ISO8601Error, parse_time, timestring)
            else:
                result = parse_time(timestring)
                self.assertEqual(result, expectation)

        def test_format(self):
            '''
            Take time object and create ISO string from it.
            This is the reverse test to test_parse.
            '''
            if expectation is None:
                self.assertRaises(AttributeError,
                                  time_isoformat, expectation, format)
            elif format is not None:
                self.assertEqual(time_isoformat(expectation, format),
                                 timestring)

    return unittest.TestLoader().loadTestsFromTestCase(TestTime)


def test_suite():
    '''
    Construct a TestSuite instance for all test cases.
    '''
    suite = unittest.TestSuite()
    for timestring, expectation, format in TEST_CASES:
        suite.addTest(create_testcase(timestring, expectation, format))
    return suite


# load_tests Protocol
def load_tests(loader, tests, pattern):
    return test_suite()


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
