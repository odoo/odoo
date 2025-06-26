import gevent
import sys
import gevent.testing as greentest
from gevent.testing import six
from gevent.testing import ExpectedException as ExpectedError

if six.PY2:
    sys.exc_clear()

class RawException(Exception):
    pass


def hello(err):
    assert sys.exc_info() == (None, None, None), sys.exc_info()
    raise err


def hello2():
    try:
        hello(ExpectedError('expected exception in hello'))
    except ExpectedError:
        pass


class Test(greentest.TestCase):

    def test1(self):
        error = RawException('hello')
        expected_error = ExpectedError('expected exception in hello')
        try:
            raise error
        except RawException:
            self.expect_one_error()
            g = gevent.spawn(hello, expected_error)
            g.join()
            self.assert_error(ExpectedError, expected_error)
            self.assertIsInstance(g.exception, ExpectedError)

            try:
                raise
            except: # pylint:disable=bare-except
                ex = sys.exc_info()[1]
                self.assertIs(ex, error)

    def test2(self):
        timer = gevent.get_hub().loop.timer(0)
        timer.start(hello2)
        try:
            gevent.sleep(0.1)
            self.assertEqual(sys.exc_info(), (None, None, None))
        finally:
            timer.close()



if __name__ == '__main__':
    greentest.main()
