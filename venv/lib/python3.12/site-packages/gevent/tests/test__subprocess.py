import sys
import os
import errno
import unittest

import time
import tempfile

import gevent.testing as greentest
import gevent
from gevent.testing import mock
from gevent import subprocess

if not hasattr(subprocess, 'mswindows'):
    # PyPy3, native python subprocess
    subprocess.mswindows = False


PYPY = hasattr(sys, 'pypy_version_info')
PY3 = sys.version_info[0] >= 3


if subprocess.mswindows:
    SETBINARY = 'import msvcrt; msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY);'
else:
    SETBINARY = ''


python_universal_newlines = hasattr(sys.stdout, 'newlines')
# The stdlib of Python 3 on Windows doesn't properly handle universal newlines
# (it produces broken results compared to Python 2)
# See gevent.subprocess for more details.
python_universal_newlines_broken = PY3 and subprocess.mswindows

@greentest.skipWithoutResource('subprocess')
class TestPopen(greentest.TestCase):

    # Use the normal error handling. Make sure that any background greenlets
    # subprocess spawns propagate errors as expected.
    error_fatal = False

    def test_exit(self):
        popen = subprocess.Popen([sys.executable, '-c', 'import sys; sys.exit(10)'])
        self.assertEqual(popen.wait(), 10)

    def test_wait(self):
        popen = subprocess.Popen([sys.executable, '-c', 'import sys; sys.exit(11)'])
        gevent.wait([popen])
        self.assertEqual(popen.poll(), 11)

    def test_child_exception(self):
        with self.assertRaises(OSError) as exc:
            subprocess.Popen(['*']).wait()

        self.assertEqual(exc.exception.errno, 2)

    def test_leak(self):
        num_before = greentest.get_number_open_files()
        p = subprocess.Popen([sys.executable, "-c", "print()"],
                             stdout=subprocess.PIPE)
        p.wait()
        p.stdout.close()
        del p

        num_after = greentest.get_number_open_files()
        self.assertEqual(num_before, num_after)

    @greentest.skipOnLibuvOnPyPyOnWin("hangs")
    def test_communicate(self):
        p = subprocess.Popen([sys.executable, "-W", "ignore",
                              "-c",
                              'import sys,os;'
                              'sys.stderr.write("pineapple");'
                              'sys.stdout.write(sys.stdin.read())'],
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        (stdout, stderr) = p.communicate(b"banana")
        self.assertEqual(stdout, b"banana")
        if sys.executable.endswith('-dbg'):
            assert stderr.startswith(b'pineapple')
        else:
            self.assertEqual(stderr, b"pineapple")

    @greentest.skipIf(subprocess.mswindows,
                      "Windows does weird things here")
    @greentest.skipOnLibuvOnCIOnPyPy("Sometimes segfaults")
    def test_communicate_universal(self):
        # Native string all the things. See https://github.com/gevent/gevent/issues/1039
        p = subprocess.Popen(
            [
                sys.executable,
                "-W", "ignore",
                "-c",
                'import sys,os;'
                'sys.stderr.write("pineapple\\r\\n\\xff\\xff\\xf2\\xf9\\r\\n");'
                'sys.stdout.write(sys.stdin.read())'
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        (stdout, stderr) = p.communicate('banana\r\n\xff\xff\xf2\xf9\r\n')
        self.assertIsInstance(stdout, str)
        self.assertIsInstance(stderr, str)
        self.assertEqual(stdout,
                         'banana\n\xff\xff\xf2\xf9\n')

        self.assertEqual(stderr,
                         'pineapple\n\xff\xff\xf2\xf9\n')

    @greentest.skipOnWindows("Windows IO is weird; this doesn't raise")
    def test_communicate_undecodable(self):
        # If the subprocess writes non-decodable data, `communicate` raises the
        # same UnicodeDecodeError that the stdlib does, instead of
        # printing it to the hub. This only applies to Python 3, because only it
        # will actually use text mode.
        # See https://github.com/gevent/gevent/issues/1510
        with subprocess.Popen(
                [
                    sys.executable,
                    '-W', 'ignore',
                    '-c',
                    "import os, sys; "
                    r'os.write(sys.stdout.fileno(), b"\xff")'
                ],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True, universal_newlines=True
        ) as p:
            with self.assertRaises(UnicodeDecodeError):
                p.communicate()

    @greentest.skipOnLibuvOnPyPyOnWin("hangs")
    def test_universal1(self):
        with subprocess.Popen(
                [
                    sys.executable, "-c",
                    'import sys,os;' + SETBINARY +
                    'sys.stdout.write("line1\\n");'
                    'sys.stdout.flush();'
                    'sys.stdout.write("line2\\r");'
                    'sys.stdout.flush();'
                    'sys.stdout.write("line3\\r\\n");'
                    'sys.stdout.flush();'
                    'sys.stdout.write("line4\\r");'
                    'sys.stdout.flush();'
                    'sys.stdout.write("\\nline5");'
                    'sys.stdout.flush();'
                    'sys.stdout.write("\\nline6");'
                ],
                stdout=subprocess.PIPE,
                universal_newlines=1,
                bufsize=1
        ) as p:
            stdout = p.stdout.read()
            if python_universal_newlines:
                # Interpreter with universal newline support
                if not python_universal_newlines_broken:
                    self.assertEqual(stdout,
                                     "line1\nline2\nline3\nline4\nline5\nline6")
                else:
                    # Note the extra newline after line 3
                    self.assertEqual(stdout,
                                     'line1\nline2\nline3\n\nline4\n\nline5\nline6')
            else:
                # Interpreter without universal newline support
                self.assertEqual(stdout,
                                 "line1\nline2\rline3\r\nline4\r\nline5\nline6")

    @greentest.skipOnLibuvOnPyPyOnWin("hangs")
    def test_universal2(self):
        with subprocess.Popen(
                [
                    sys.executable, "-c",
                    'import sys,os;' + SETBINARY +
                    'sys.stdout.write("line1\\n");'
                    'sys.stdout.flush();'
                    'sys.stdout.write("line2\\r");'
                    'sys.stdout.flush();'
                    'sys.stdout.write("line3\\r\\n");'
                    'sys.stdout.flush();'
                    'sys.stdout.write("line4\\r\\nline5");'
                    'sys.stdout.flush();'
                    'sys.stdout.write("\\nline6");'
                ],
                stdout=subprocess.PIPE,
                universal_newlines=1,
                bufsize=1
        ) as p:
            stdout = p.stdout.read()
            if python_universal_newlines:
                # Interpreter with universal newline support
                if not python_universal_newlines_broken:
                    self.assertEqual(stdout,
                                     "line1\nline2\nline3\nline4\nline5\nline6")
                else:
                    # Note the extra newline after line 3
                    self.assertEqual(stdout,
                                     'line1\nline2\nline3\n\nline4\n\nline5\nline6')
            else:
                # Interpreter without universal newline support
                self.assertEqual(stdout,
                                 "line1\nline2\rline3\r\nline4\r\nline5\nline6")

    @greentest.skipOnWindows("Uses 'grep' command")
    def test_nonblock_removed(self):
        # see issue #134
        r, w = os.pipe()
        stdin = subprocess.FileObject(r)
        with subprocess.Popen(['grep', 'text'], stdin=stdin) as p:
            try:
                # Closing one half of the pipe causes Python 3 on OS X to terminate the
                # child process; it exits with code 1 and the assert that p.poll is None
                # fails. Removing the close lets it pass under both Python 3 and 2.7.
                # If subprocess.Popen._remove_nonblock_flag is changed to a noop, then
                # the test fails (as expected) even with the close removed
                #os.close(w)
                time.sleep(0.1)
                self.assertEqual(p.poll(), None)
            finally:
                if p.poll() is None:
                    p.kill()
                stdin.close()
                os.close(w)

    def test_issue148(self):
        for _ in range(7):
            with self.assertRaises(OSError) as exc:
                with subprocess.Popen('this_name_must_not_exist'):
                    pass

            self.assertEqual(exc.exception.errno, errno.ENOENT)

    @greentest.skipOnLibuvOnPyPyOnWin("hangs")
    def test_check_output_keyword_error(self):
        with self.assertRaises(subprocess.CalledProcessError) as exc: # pylint:disable=no-member
            subprocess.check_output([sys.executable, '-c', 'import sys; sys.exit(44)'])

        self.assertEqual(exc.exception.returncode, 44)

    @greentest.skipOnPy3("The default buffer changed in Py3")
    def test_popen_bufsize(self):
        # Test that subprocess has unbuffered output by default
        # (as the vanilla subprocess module)
        with subprocess.Popen(
                [sys.executable, '-u', '-c',
                 'import sys; sys.stdout.write(sys.stdin.readline())'],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE
        ) as p:
            p.stdin.write(b'foobar\n')
            r = p.stdout.readline()
        self.assertEqual(r, b'foobar\n')

    @greentest.ignores_leakcheck
    @greentest.skipOnWindows("Not sure why?")
    def test_subprocess_in_native_thread(self):
        # gevent.subprocess doesn't work from a background
        # native thread. See #688
        from gevent import monkey

        # must be a native thread; defend against monkey-patching
        ex = []
        Thread = monkey.get_original('threading', 'Thread')

        def fn():
            with self.assertRaises(TypeError) as exc:
                gevent.subprocess.Popen('echo 123', shell=True)
            ex.append(exc.exception)

        thread = Thread(target=fn)
        thread.start()
        thread.join()

        self.assertEqual(len(ex), 1)
        self.assertTrue(isinstance(ex[0], TypeError), ex)
        self.assertEqual(ex[0].args[0], 'child watchers are only available on the default loop')


    @greentest.skipOnLibuvOnPyPyOnWin("hangs")
    def __test_no_output(self, kwargs, kind):
        with subprocess.Popen(
                [sys.executable, '-c', 'pass'],
                stdout=subprocess.PIPE,
                **kwargs
        ) as proc:
            stdout, stderr = proc.communicate()

        self.assertIsInstance(stdout, kind)
        self.assertIsNone(stderr)

    @greentest.skipOnLibuvOnCIOnPyPy("Sometimes segfaults; "
                                     "https://travis-ci.org/gevent/gevent/jobs/327357682")
    def test_universal_newlines_text_mode_no_output_is_always_str(self):
        # If the file is in universal_newlines mode, we should always get a str when
        # there is no output.
        # https://github.com/gevent/gevent/pull/939
        self.__test_no_output({'universal_newlines': True}, str)

    @greentest.skipIf(sys.version_info[:2] < (3, 6), "Need encoding argument")
    def test_encoded_text_mode_no_output_is_str(self):
        # If the file is in universal_newlines mode, we should always get a str when
        # there is no output.
        # https://github.com/gevent/gevent/pull/939
        self.__test_no_output({'encoding': 'utf-8'}, str)

    def test_default_mode_no_output_is_always_str(self):
        # If the file is in default mode, we should always get a str when
        # there is no output.
        # https://github.com/gevent/gevent/pull/939
        self.__test_no_output({}, bytes)

@greentest.skipOnWindows("Testing POSIX fd closing")
class TestFDs(unittest.TestCase):

    @mock.patch('os.closerange')
    @mock.patch('gevent.subprocess._set_inheritable')
    @mock.patch('os.close')
    def test_close_fds_brute_force(self, close, set_inheritable, closerange):
        keep = (
            4, 5,
            # Leave a hole
            # 6,
            7,
        )
        subprocess.Popen._close_fds_brute_force(keep, None)

        closerange.assert_has_calls([
            mock.call(3, 4),
            mock.call(8, subprocess.MAXFD),
        ])

        set_inheritable.assert_has_calls([
            mock.call(4, True),
            mock.call(5, True),
        ])

        close.assert_called_once_with(6)

    @mock.patch('gevent.subprocess.Popen._close_fds_brute_force')
    @mock.patch('os.listdir')
    def test_close_fds_from_path_bad_values(self, listdir, brute_force):
        listdir.return_value = 'Not an Integer'

        subprocess.Popen._close_fds_from_path('path', [], 42)
        brute_force.assert_called_once_with([], 42)

    @mock.patch('os.listdir')
    @mock.patch('os.closerange')
    @mock.patch('gevent.subprocess._set_inheritable')
    @mock.patch('os.close')
    def test_close_fds_from_path(self, close, set_inheritable, closerange, listdir):
        keep = (
            4, 5,
            # Leave a hole
            # 6,
            7,
        )
        listdir.return_value = ['1', '6', '37']

        subprocess.Popen._close_fds_from_path('path', keep, 5)

        self.assertEqual([], closerange.mock_calls)

        set_inheritable.assert_has_calls([
            mock.call(4, True),
            mock.call(7, True),
        ])

        close.assert_has_calls([
            mock.call(6),
            mock.call(37),
        ])

    @mock.patch('gevent.subprocess.Popen._close_fds_brute_force')
    @mock.patch('os.path.isdir')
    def test_close_fds_no_dir(self, isdir, brute_force):
        isdir.return_value = False

        subprocess.Popen._close_fds([], 42)
        brute_force.assert_called_once_with([], 42)
        isdir.assert_has_calls([
            mock.call('/proc/self/fd'),
            mock.call('/dev/fd'),
        ])

    @mock.patch('gevent.subprocess.Popen._close_fds_from_path')
    @mock.patch('gevent.subprocess.Popen._close_fds_brute_force')
    @mock.patch('os.path.isdir')
    def test_close_fds_with_dir(self, isdir, brute_force, from_path):
        isdir.return_value = True

        subprocess.Popen._close_fds([7], 42)

        self.assertEqual([], brute_force.mock_calls)
        from_path.assert_called_once_with('/proc/self/fd', [7], 42)

class RunFuncTestCase(greentest.TestCase):
    # Based on code from python 3.6+

    __timeout__ = greentest.LARGE_TIMEOUT

    @greentest.skipWithoutResource('subprocess')
    def run_python(self, code, **kwargs):
        """Run Python code in a subprocess using subprocess.run"""
        argv = [sys.executable, "-c", code]
        return subprocess.run(argv, **kwargs)

    def test_returncode(self):
        # call() function with sequence argument
        cp = self.run_python("import sys; sys.exit(47)")
        self.assertEqual(cp.returncode, 47)
        with self.assertRaises(subprocess.CalledProcessError): # pylint:disable=no-member
            cp.check_returncode()

    def test_check(self):
        with self.assertRaises(subprocess.CalledProcessError) as c: # pylint:disable=no-member
            self.run_python("import sys; sys.exit(47)", check=True)
        self.assertEqual(c.exception.returncode, 47)

    def test_check_zero(self):
        # check_returncode shouldn't raise when returncode is zero
        cp = self.run_python("import sys; sys.exit(0)", check=True)
        self.assertEqual(cp.returncode, 0)

    def test_timeout(self):
        # run() function with timeout argument; we want to test that the child
        # process gets killed when the timeout expires.  If the child isn't
        # killed, this call will deadlock since subprocess.run waits for the
        # child.
        with self.assertRaises(subprocess.TimeoutExpired):
            self.run_python("while True: pass", timeout=0.0001)

    @greentest.skipOnLibuvOnPyPyOnWin("hangs")
    def test_capture_stdout(self):
        # capture stdout with zero return code
        cp = self.run_python("print('BDFL')", stdout=subprocess.PIPE)
        self.assertIn(b'BDFL', cp.stdout)

    @greentest.skipOnLibuvOnPyPyOnWin("hangs")
    def test_capture_stderr(self):
        cp = self.run_python("import sys; sys.stderr.write('BDFL')",
                             stderr=subprocess.PIPE)
        self.assertIn(b'BDFL', cp.stderr)

    @greentest.skipOnLibuvOnPyPyOnWin("hangs")
    def test_check_output_stdin_arg(self):
        # run() can be called with stdin set to a file
        with tempfile.TemporaryFile() as tf:
            tf.write(b'pear')
            tf.seek(0)
            cp = self.run_python(
                "import sys; sys.stdout.write(sys.stdin.read().upper())",
                stdin=tf, stdout=subprocess.PIPE)
            self.assertIn(b'PEAR', cp.stdout)

    @greentest.skipOnLibuvOnPyPyOnWin("hangs")
    def test_check_output_input_arg(self):
        # check_output() can be called with input set to a string
        cp = self.run_python(
            "import sys; sys.stdout.write(sys.stdin.read().upper())",
            input=b'pear', stdout=subprocess.PIPE)
        self.assertIn(b'PEAR', cp.stdout)

    @greentest.skipOnLibuvOnPyPyOnWin("hangs")
    def test_check_output_stdin_with_input_arg(self):
        # run() refuses to accept 'stdin' with 'input'
        with tempfile.TemporaryFile() as tf:
            tf.write(b'pear')
            tf.seek(0)
            with self.assertRaises(ValueError,
                                   msg="Expected ValueError when stdin and input args supplied.") as c:
                self.run_python("print('will not be run')",
                                stdin=tf, input=b'hare')
            self.assertIn('stdin', c.exception.args[0])
            self.assertIn('input', c.exception.args[0])

    @greentest.skipOnLibuvOnPyPyOnWin("hangs")
    def test_check_output_timeout(self):
        with self.assertRaises(subprocess.TimeoutExpired) as c:
            self.run_python(
                (
                    "import sys, time\n"
                    "sys.stdout.write('BDFL')\n"
                    "sys.stdout.flush()\n"
                    "time.sleep(3600)"
                ),
                # Some heavily loaded buildbots (sparc Debian 3.x) require
                # this much time to start and print.
                timeout=3, stdout=subprocess.PIPE)
        self.assertEqual(c.exception.output, b'BDFL')
        # output is aliased to stdout
        self.assertEqual(c.exception.stdout, b'BDFL')

    def test_run_kwargs(self):
        newenv = os.environ.copy()
        newenv["FRUIT"] = "banana"
        cp = self.run_python(('import sys, os;'
                              'sys.exit(33 if os.getenv("FRUIT")=="banana" else 31)'),
                             env=newenv)
        self.assertEqual(cp.returncode, 33)

    # This test _might_ wind up a bit fragile on loaded build+test machines
    # as it depends on the timing with wide enough margins for normal situations
    # but does assert that it happened "soon enough" to believe the right thing
    # happened.
    @greentest.skipOnWindows("requires posix like 'sleep' shell command")
    def test_run_with_shell_timeout_and_capture_output(self):
        #Output capturing after a timeout mustn't hang forever on open filehandles
        with self.runs_in_given_time(0.1):
            with self.assertRaises(subprocess.TimeoutExpired):
                subprocess.run('sleep 3', shell=True, timeout=0.1,
                               capture_output=True)  # New session unspecified.

if __name__ == '__main__':
    greentest.main()
