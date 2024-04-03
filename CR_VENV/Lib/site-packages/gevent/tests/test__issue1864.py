import sys
import unittest

from gevent.testing import skipOnPy2

class TestSubnormalFloatsAreNotDisabled(unittest.TestCase):

    @skipOnPy2('This test always fails on Python 2')
    def test_subnormal_is_not_zero(self):
        # Enabling the -Ofast compiler flag resulted in subnormal floats getting
        # disabled the moment when gevent was imported. This impacted libraries
        # that expect subnormal floats to be enabled.
        #
        # NOTE: This test is supposed to catch that. It doesn't seem to work perfectly, though.
        # The test passes under Python 2 on macOS no matter whether -ffast-math is given or not;
        # perhaps this is a difference in clang vs gcc? In contrast, the test on Python 2.7 always
        # *fails* on GitHub actions (in both CPython 2.7 and PyPy). We're far past the EOL of
        # Python 2.7 so I'm not going to spend much time investigating.
        __import__('gevent')

        # `sys.float_info.min` is the minimum representable positive normalized
        # float, so dividing it by two gives us a positive subnormal float,
        # as long as subnormals floats are not disabled.
        self.assertGreater(sys.float_info.min / 2, 0)


if __name__ == "__main__":
    unittest.main()
