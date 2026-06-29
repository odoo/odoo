# A greenlet that's killed before it is ever started
# should never be switched to
import gevent
import gevent.testing as greentest


class MyException(Exception):
    pass

class TestSwitch(greentest.TestCase):

    def setUp(self):
        super(TestSwitch, self).setUp()
        self.switched_to = [False, False]
        self.caught = None

    def should_never_run(self, i): # pragma: no cover
        self.switched_to[i] = True

    def check(self, g, g2):
        gevent.joinall((g, g2))
        self.assertEqual([False, False], self.switched_to)

        # They both have a GreenletExit as their value
        self.assertIsInstance(g.value, gevent.GreenletExit)
        self.assertIsInstance(g2.value, gevent.GreenletExit)

        # They both have no reported exc_info
        self.assertIsNone(g.exc_info)
        self.assertIsNone(g2.exc_info)
        self.assertIsNone(g.exception)
        self.assertIsNone(g2.exception)


    def test_gevent_kill(self):
        g = gevent.spawn(self.should_never_run, 0) # create but do not switch to
        g2 = gevent.spawn(self.should_never_run, 1) # create but do not switch to
        # Using gevent.kill
        gevent.kill(g)
        gevent.kill(g2)
        self.check(g, g2)

    def test_greenlet_kill(self):
        # killing directly
        g = gevent.spawn(self.should_never_run, 0)
        g2 = gevent.spawn(self.should_never_run, 1)
        g.kill()
        g2.kill()
        self.check(g, g2)

    def test_throw(self):
        # throwing
        g = gevent.spawn(self.should_never_run, 0)
        g2 = gevent.spawn(self.should_never_run, 1)
        g.throw(gevent.GreenletExit)
        g2.throw(gevent.GreenletExit)
        self.check(g, g2)


    def catcher(self):
        try:
            while True:
                gevent.sleep(0)
        except MyException as e:
            self.caught = e

    def test_kill_exception(self):
        # Killing with gevent.kill gets the right exception,
        # and we can pass exception objects, not just exception classes.

        g = gevent.spawn(self.catcher)
        g.start()
        gevent.sleep()
        gevent.kill(g, MyException())
        gevent.sleep()

        self.assertIsInstance(self.caught, MyException)
        self.assertIsNone(g.exception, MyException)


if __name__ == '__main__':
    greentest.main()
