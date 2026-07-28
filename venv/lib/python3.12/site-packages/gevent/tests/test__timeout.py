import gevent.testing as greentest
import gevent
from gevent.hub import get_hub
import sys

SHOULD_EXPIRE = 0.01
if not greentest.RUNNING_ON_CI:
    SHOULD_NOT_EXPIRE = SHOULD_EXPIRE * 2.0
else:
    SHOULD_NOT_EXPIRE = SHOULD_EXPIRE * 20.0


class TestDirectRaise(greentest.TestCase):
    switch_expected = False

    def test_direct_raise_class(self):
        try:
            raise gevent.Timeout
        except gevent.Timeout as t:
            assert not t.pending, repr(t)

    def test_direct_raise_instance(self):
        timeout = gevent.Timeout()
        try:
            raise timeout
        except gevent.Timeout as t:
            assert timeout is t, (timeout, t)
            assert not t.pending, repr(t)


class Test(greentest.TestCase):

    def _test(self, timeout, close):
        try:
            get_hub().switch()
            self.fail('Must raise Timeout')
        except gevent.Timeout as ex:
            if ex is not timeout:
                raise
            if close:
                ex.close()
            return ex

    def _check_expires(self, timeout):
        timeout.start()
        self._test(timeout, False)
        # Restart
        timeout.start()
        return self._test(timeout, True)

    def test_expires(self):
        timeout = gevent.Timeout(SHOULD_EXPIRE)
        self._check_expires(timeout)

    def test_expires_false(self):
        # A False exception value only matters to a
        # context manager
        timeout = gevent.Timeout(SHOULD_EXPIRE, False)
        self._check_expires(timeout)

    def test_expires_str(self):
        # str values are accepted but not documented; they change
        # the message
        timeout = gevent.Timeout(SHOULD_EXPIRE, 'XXX')
        ex = self._check_expires(timeout)
        self.assertTrue(str(ex).endswith('XXX'))

    def assert_type_err(self, ex):
        # PyPy3 uses 'exceptions must derive', everyone else uses "exceptions must be"
        self.assertTrue("exceptions must be" in str(ex) or "exceptions must derive" in str(ex), str(ex))

    def test_expires_non_exception(self):
        timeout = gevent.Timeout(SHOULD_EXPIRE, object())
        timeout.start()
        try:
            get_hub().switch()
            self.fail("Most raise TypeError")
        except TypeError as ex:
            self.assert_type_err(ex)
        timeout.close()

        class OldStyle:
            pass
        timeout = gevent.Timeout(SHOULD_EXPIRE, OldStyle) # Type
        timeout.start()
        try:
            get_hub().switch()
            self.fail("Must raise OldStyle")
        except TypeError as ex:
            self.assertTrue(greentest.PY3, "Py3 raises a TypeError for non-BaseExceptions")
            self.assert_type_err(ex)
        except: # pylint:disable=bare-except
            self.assertTrue(greentest.PY2, "Old style classes can only be raised on Py2")
            t = sys.exc_info()[0]
            self.assertEqual(t, OldStyle)
        timeout.close()

        timeout = gevent.Timeout(SHOULD_EXPIRE, OldStyle()) # instance
        timeout.start()
        try:
            get_hub().switch()
            self.fail("Must raise OldStyle")
        except TypeError as ex:
            self.assertTrue(greentest.PY3, "Py3 raises a TypeError for non-BaseExceptions")
            self.assert_type_err(ex)
        except: # pylint:disable=bare-except
            self.assertTrue(greentest.PY2, "Old style classes can only be raised on Py2")
            t = sys.exc_info()[0]
            self.assertEqual(t, OldStyle)
        timeout.close()

    def _check_context_manager_expires(self, timeout, raises=True):
        try:
            with timeout:
                get_hub().switch()
        except gevent.Timeout as ex:
            if ex is not timeout:
                raise
            return ex

        if raises:
            self.fail("Must raise Timeout")

    def test_context_manager(self):
        timeout = gevent.Timeout(SHOULD_EXPIRE)
        self._check_context_manager_expires(timeout)

    def test_context_manager_false(self):
        # Suppress the exception
        timeout = gevent.Timeout(SHOULD_EXPIRE, False)
        self._check_context_manager_expires(timeout, raises=False)
        self.assertTrue(str(timeout).endswith('(silent)'), str(timeout))

    def test_context_manager_str(self):
        timeout = gevent.Timeout(SHOULD_EXPIRE, 'XXX')
        ex = self._check_context_manager_expires(timeout)
        self.assertTrue(str(ex).endswith('XXX'), str(ex))

    def test_cancel(self):
        timeout = gevent.Timeout(SHOULD_EXPIRE)
        timeout.start()
        timeout.cancel()
        gevent.sleep(SHOULD_NOT_EXPIRE)
        self.assertFalse(timeout.pending, timeout)
        timeout.close()

    @greentest.ignores_leakcheck
    def test_with_timeout(self):
        with self.assertRaises(gevent.Timeout):
            gevent.with_timeout(SHOULD_EXPIRE, gevent.sleep, SHOULD_NOT_EXPIRE)
        X = object()
        r = gevent.with_timeout(SHOULD_EXPIRE, gevent.sleep, SHOULD_NOT_EXPIRE, timeout_value=X)
        self.assertIs(r, X)
        r = gevent.with_timeout(SHOULD_NOT_EXPIRE, gevent.sleep, SHOULD_EXPIRE, timeout_value=X)
        self.assertIsNone(r)


if __name__ == '__main__':
    greentest.main()
