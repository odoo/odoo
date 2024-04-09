import unittest

from six.moves import cPickle as pickle

import isodate


class TestPickle(unittest.TestCase):
    '''
    A test case template to parse an ISO datetime string into a
    datetime object.
    '''

    def test_pickle_datetime(self):
        '''
        Parse an ISO datetime string and compare it to the expected value.
        '''
        dti = isodate.parse_datetime('2012-10-26T09:33+00:00')
        for proto in range(0, pickle.HIGHEST_PROTOCOL + 1):
            pikl = pickle.dumps(dti, proto)
            self.assertEqual(dti, pickle.loads(pikl),
                             "pickle proto %d failed" % proto)

    def test_pickle_duration(self):
        '''
        Pickle / unpickle duration objects.
        '''
        from isodate.duration import Duration
        dur = Duration()
        failed = []
        for proto in range(0, pickle.HIGHEST_PROTOCOL + 1):
            try:
                pikl = pickle.dumps(dur, proto)
                if dur != pickle.loads(pikl):
                    raise Exception("not equal")
            except Exception as e:
                failed.append("pickle proto %d failed (%s)" % (proto, repr(e)))
        self.assertEqual(len(failed), 0, "pickle protos failed: %s" %
                         str(failed))

    def test_pickle_utc(self):
        '''
        isodate.UTC objects remain the same after pickling.
        '''
        self.assertTrue(isodate.UTC is pickle.loads(pickle.dumps(isodate.UTC)))


def test_suite():
    '''
    Construct a TestSuite instance for all test cases.
    '''
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestPickle))
    return suite


# load_tests Protocol
def load_tests(loader, tests, pattern):
    return test_suite()


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
