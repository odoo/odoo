import sys
import unittest

from gevent.testing import TestCase
import gevent
from gevent.timeout import Timeout

@unittest.skipUnless(
    hasattr(sys, 'gettotalrefcount'),
    "Needs debug build"
)
# XXX: This name makes no sense. What was this for originally?
class TestQueue(TestCase): # pragma: no cover
    # pylint:disable=bare-except,no-member

    def test(self):

        refcounts = []
        for _ in range(15):
            try:
                Timeout.start_new(0.01)
                gevent.sleep(0.1)
                self.fail('must raise Timeout')
            except Timeout:
                pass
            refcounts.append(sys.gettotalrefcount())

        # Refcounts may go down, but not up
        # XXX: JAM: I think this may just be broken. Each time we add
        # a new integer to our list of refcounts, we'll be
        # creating a new reference. This makes sense when we see the list
        # go up by one each iteration:
        #
        #   AssertionError: 530631 not less than or equal to 530630
        #     : total refcount mismatch:
        #      [530381, 530618, 530619, 530620, 530621,
        #       530622, 530623, 530624, 530625, 530626,
        #       530627, 530628, 530629, 530630, 530631]
        final = refcounts[-1]
        previous = refcounts[-2]
        self.assertLessEqual(
            final, previous,
            "total refcount mismatch: %s" % refcounts)


if __name__ == '__main__':
    unittest.main()
