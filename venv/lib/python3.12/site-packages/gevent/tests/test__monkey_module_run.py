"""
Tests for running ``gevent.monkey`` as a module to launch a
patched script.

Uses files in the ``monkey_package/`` directory.
"""
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division


import os
import os.path
import sys

from gevent import testing as greentest
from gevent.testing.util import absolute_pythonpath
from gevent.testing.util import run

class TestRun(greentest.TestCase):
    maxDiff = None

    def setUp(self):
        self.abs_pythonpath = absolute_pythonpath() # before we cd
        self.cwd = os.getcwd()
        os.chdir(os.path.dirname(__file__))

    def tearDown(self):
        os.chdir(self.cwd)

    def _run(self, script, module=False):
        env = os.environ.copy()
        env['PYTHONWARNINGS'] = 'ignore'
        if self.abs_pythonpath:
            env['PYTHONPATH'] = self.abs_pythonpath
        run_kwargs = dict(
            buffer_output=True,
            quiet=True,
            nested=True,
            env=env,
            timeout=10,
        )

        args = [sys.executable, '-m', 'gevent.monkey']
        if module:
            args.append('--module')
        args += [script, 'patched']
        monkey_result = run(
            args,
            **run_kwargs
        )
        self.assertTrue(monkey_result)

        if module:
            args = [sys.executable, "-m", script, 'stdlib']
        else:
            args = [sys.executable, script, 'stdlib']
        std_result = run(
            args,
            **run_kwargs
        )
        self.assertTrue(std_result)

        monkey_out_lines = monkey_result.output_lines
        std_out_lines = std_result.output_lines
        self.assertEqual(monkey_out_lines, std_out_lines)
        self.assertEqual(monkey_result.error, std_result.error)

        return monkey_out_lines

    def test_run_simple(self):
        self._run(os.path.join('monkey_package', 'script.py'))

    def _run_package(self, module):
        lines = self._run('monkey_package', module=module)

        self.assertTrue(lines[0].endswith(u'__main__.py'), lines[0])
        self.assertEqual(lines[1].strip(), u'__main__')

    def test_run_package(self):
        # Run a __main__ inside a package, even without specifying -m
        self._run_package(module=False)

    def test_run_module(self):
        # Run a __main__ inside a package, when specifying -m
        self._run_package(module=True)

    def test_issue_302(self):
        monkey_lines = self._run(os.path.join('monkey_package', 'issue302monkey.py'))

        self.assertEqual(monkey_lines[0].strip(), u'True')
        monkey_lines[1] = monkey_lines[1].replace(u'\\', u'/') # windows path
        self.assertTrue(monkey_lines[1].strip().endswith(u'monkey_package/issue302monkey.py'))
        self.assertEqual(monkey_lines[2].strip(), u'True', monkey_lines)

    # These three tests all sometimes fail on Py2 on CI, writing
    # to stderr:
    #   Unhandled exception in thread started by \n
    #   sys.excepthook is missing\n
    #   lost sys.stderr\n
    #   Fatal Python error: PyImport_GetModuleDict: no module dictionary!\n'
    # I haven't been able to produce this locally on macOS or Linux.
    # The last line seems new with 2.7.17?
    # Also, occasionally, they get '3' instead of '2' for the number of threads.
    # That could have something to do with...? Most commonly that's PyPy, but
    # sometimes CPython. Again, haven't reproduced.
    # Not relevant since Py2 has been dropped.
    def test_threadpool_in_patched_after_patch(self):
        # Issue 1484
        # If we don't have this correct, then we get exceptions
        out = self._run(os.path.join('monkey_package', 'threadpool_monkey_patches.py'))
        self.assertEqual(out, ['False', '2'])

    def test_threadpool_in_patched_after_patch_module(self):
        # Issue 1484
        # If we don't have this correct, then we get exceptions
        out = self._run('monkey_package.threadpool_monkey_patches', module=True)
        self.assertEqual(out, ['False', '2'])

    def test_threadpool_not_patched_after_patch_module(self):
        # Issue 1484
        # If we don't have this correct, then we get exceptions
        out = self._run('monkey_package.threadpool_no_monkey', module=True)
        self.assertEqual(out, ['False', 'False', '2'])

if __name__ == '__main__':
    greentest.main()
