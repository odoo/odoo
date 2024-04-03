import os
import sys
import unittest
from tempfile import mkdtemp
from unittest import mock

from qrcode.console_scripts import main


def bad_read():
    raise UnicodeDecodeError('utf-8', b'0x80', 0, 1, 'invalid start byte')


class ScriptTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = mkdtemp()

    def tearDown(self):
        os.rmdir(self.tmpdir)

    @mock.patch('os.isatty', lambda *args: True)
    @mock.patch('qrcode.main.QRCode.print_ascii')
    def test_isatty(self, mock_print_ascii):
        main(['testtext'])
        mock_print_ascii.assert_called_with(tty=True)

    @mock.patch('os.isatty', lambda *args: False)
    @mock.patch('sys.stdout')
    def test_piped(self, mock_stdout):
        main(['testtext'])

    @mock.patch('os.isatty', lambda *args: True)
    @mock.patch('qrcode.main.QRCode.print_ascii')
    def test_stdin(self, mock_print_ascii):
        mock_stdin = mock.Mock(sys.stdin)
        stdin_buffer = getattr(mock_stdin, 'buffer', mock_stdin)
        stdin_buffer.read.return_value = 'testtext'
        with mock.patch('sys.stdin', mock_stdin):
            main([])
        self.assertTrue(stdin_buffer.read.called)
        mock_print_ascii.assert_called_with(tty=True)

    @mock.patch('os.isatty', lambda *args: True)
    @mock.patch('qrcode.main.QRCode.print_ascii')
    def test_stdin_py3_unicodedecodeerror(self, mock_print_ascii):
        mock_stdin = mock.Mock(sys.stdin)
        mock_stdin.buffer.read.return_value = 'testtext'
        mock_stdin.read.side_effect = bad_read
        with mock.patch('sys.stdin', mock_stdin):
            # sys.stdin.read() will raise an error...
            self.assertRaises(UnicodeDecodeError, sys.stdin.read)
            # ... but it won't be used now.
            main([])
        mock_print_ascii.assert_called_with(tty=True)

    @mock.patch('os.isatty', lambda *args: True)
    @mock.patch('qrcode.main.QRCode.print_ascii')
    def test_optimize(self, mock_print_ascii):
        main('testtext --optimize 0'.split())

    @mock.patch('sys.stdout')
    def test_factory(self, mock_stdout):
        main('testtext --factory svg'.split())

    @mock.patch('sys.stderr')
    def test_bad_factory(self, mock_stderr):
        self.assertRaises(SystemExit, main, 'testtext --factory fish'.split())

    def test_output(self):
        tmpfile = os.path.join(self.tmpdir, "test.png")
        main(['testtext', '--output', tmpfile])
        os.remove(tmpfile)
