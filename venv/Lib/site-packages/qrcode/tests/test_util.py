import unittest

from qrcode import util


class UtilTests(unittest.TestCase):

    def test_check_wrong_version(self):
        with self.assertRaises(ValueError):
            util.check_version(0)

        with self.assertRaises(ValueError):
            util.check_version(41)
