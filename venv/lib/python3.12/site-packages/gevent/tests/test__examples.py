"""
Test the contents of the ``examples/`` directory.

If an existing test in *this* directory named ``test__example_<fn>.py`` exists,
where ``<fn>`` is the base filename of an example file, it will not be tested
here.

Examples can specify that they need particular test resources to be enabled
by commenting (one per line) ``# gevent-test-requires-resource: <resource>``;
most commonly the resource will be ``network``. You can use this technique to specify
non-existant resources for things that should never be tested.
"""
import re
import os
import glob
import time
import unittest

import gevent.testing as greentest
from gevent.testing import util

this_dir = os.path.dirname(__file__)

def _find_files_to_ignore():
    old_dir = os.getcwd()
    try:
        os.chdir(this_dir)

        result = [x[14:] for x in glob.glob('test__example_*.py')]
        if greentest.PYPY and greentest.RUNNING_ON_APPVEYOR:
            # For some reason on Windows with PyPy, this times out,
            # when it should be very fast.
            result.append("processes.py")
    finally:
        os.chdir(old_dir)

    return result

default_time_range = (2, 10)
time_ranges = { # what is this even supposed to mean? pylint:disable=consider-using-namedtuple-or-dataclass
    'concurrent_download.py': (0, 30),
    'processes.py': (0, default_time_range[-1])
}

class _AbstractTestMixin(util.ExampleMixin):
    time_range = default_time_range
    example = None

    def _check_resources(self):
        from gevent.testing import resources

        # pylint:disable=unspecified-encoding
        with open(os.path.join(self.cwd, self.example), 'r') as f:
            contents = f.read()

        pattern = re.compile('^# gevent-test-requires-resource: (.*)$', re.MULTILINE)
        resources_needed = re.finditer(pattern, contents)
        for match in resources_needed:
            needed = contents[match.start(1):match.end(1)]
            resources.skip_without_resource(needed)

    def test_runs(self):
        self._check_resources()

        start = time.time()
        min_time, max_time = self.time_range
        self.start_kwargs = {
            'timeout': max_time,
            'quiet': True,
            'buffer_output': True,
            'nested': True,
            'setenv': {'GEVENT_DEBUG': 'error'}
        }
        if not self.run_example():
            self.fail("Failed example: " + self.example)
        else:
            took = time.time() - start
            self.assertGreaterEqual(took, min_time)

def _build_test_classes():
    result = {}
    try:
        example_dir = util.ExampleMixin().cwd
    except unittest.SkipTest:
        util.log("WARNING: No examples dir found", color='suboptimal-behaviour')
        return result

    ignore = _find_files_to_ignore()
    for filename in glob.glob(example_dir + '/*.py'):
        bn = os.path.basename(filename)
        if bn in ignore:
            continue

        tc = type(
            'Test_' + bn,
            (_AbstractTestMixin, greentest.TestCase),
            {
                'example': bn,
                'time_range': time_ranges.get(bn, _AbstractTestMixin.time_range)
            }
        )
        result[tc.__name__] = tc
    return result

for k, v in _build_test_classes().items():
    locals()[k] = v

if __name__ == '__main__':
    greentest.main()
