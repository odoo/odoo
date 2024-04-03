from __future__ import print_function

import pickle
import gevent.testing as greentest
try:
    from gevent.resolver.cares import ares_host_result
except ImportError: # pragma: no cover
    ares_host_result = None


@greentest.skipIf(ares_host_result is None,
                  "Must be able to import ares")
class TestPickle(greentest.TestCase):
    # Issue 104: ares.ares_host_result unpickleable

    def _test(self, protocol):
        r = ares_host_result('family', ('arg1', 'arg2', ))
        dumped = pickle.dumps(r, protocol)
        loaded = pickle.loads(dumped)
        self.assertEqual(r, loaded)
        self.assertEqual(r.family, loaded.family)


for i in range(0, pickle.HIGHEST_PROTOCOL):
    def make_test(j):
        return lambda self: self._test(j)
    setattr(TestPickle, 'test' + str(i), make_test(i))


if __name__ == '__main__':
    greentest.main()
