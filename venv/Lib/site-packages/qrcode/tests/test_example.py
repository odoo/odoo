import unittest
from unittest import mock

from qrcode import run_example


class ExampleTest(unittest.TestCase):

    @mock.patch('PIL.Image.Image.show')
    def runTest(self, mock_show):
        run_example()
        mock_show.assert_called_with()
