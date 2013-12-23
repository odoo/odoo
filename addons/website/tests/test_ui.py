import unittest
import subprocess
import os
import select
import time
import json
from openerp import tools

ROOT = os.path.join(os.path.dirname(__file__), 'ui_suite')

__all__ = ['load_tests', 'WebsiteUiSuite']

def _exc_info_to_string(err, test):
    return err

class LineReader:
    def __init__(self, file_descriptor):
        self._file_descriptor = file_descriptor
        self._buffer = ''

    def fileno(self):
        return self._file_descriptor

    def readlines(self):
        data = os.read(self._file_descriptor, 4096)
        if not data:
            # EOF
            return None
        self._buffer += data
        if '\n' not in data:
            return []
        tmp = self._buffer.split('\n')
        lines, self._buffer = tmp[:-1], tmp[-1]
        return lines

class WebsiteUiTest(unittest.TestCase):
    def __init__(self, name):
        self.name = name
    def shortDescription(self):
        return None
    def __str__(self):
        return self.name

class WebsiteUiSuite(unittest.TestSuite):
    # timeout in seconds
    def __init__(self, testfile, timeout=10.0):
        self.testfile = testfile
        self.timeout = timeout
        self._test = None

    def __iter__(self):
        return iter([self])

    def run(self, result):
        # is PhantomJS correctly installed?
        try:
            subprocess.call([ 'phantomjs', '-v' ],
                stdout=open(os.devnull, 'w'),
                stderr=subprocess.STDOUT)
        except OSError:
            test = WebsiteUiTest('UI Tests')
            result.startTest(test)
            result.addSkip(test, "phantomjs command not found")
            result.stopTest(test)
            return

        result._exc_info_to_string = _exc_info_to_string
        try:
            self._run(result)
        finally:
            del result._exc_info_to_string

    def _run(self, result):
        self._test = WebsiteUiTest(self.testfile)
        self.start_time = time.time()
        last_check_time = time.time()

        phantomOptions = json.dumps({
            'timeout': self.timeout,
            'port': tools.config['xmlrpc_port']
        })

        phantom = subprocess.Popen([
                'phantomjs',
                os.path.join(ROOT, self.testfile),
                phantomOptions
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT)
        proc_stdout = LineReader(phantom.stdout.fileno())
        readable = [proc_stdout]
        try:
            while phantom.poll() is None and readable and last_check_time < self.start_time + self.timeout:
                ready, _, _ = select.select(readable, [], [], 0.1)
                if not ready:
                    last_check_time = time.time()
                    continue
                for stream in ready:
                    lines = stream.readlines()
                    if lines is None:
                        # EOF
                        readable.remove(stream)
                    else:
                        self.process(lines[0], result)
                        # the runner expects only one output line
                        # any subsequent line is ignored
                        readable.remove(stream)
            if last_check_time >= (self.start_time + self.timeout):
                result.addError(self._test, "Timeout after %s s" % (last_check_time - self.start_time ))
        finally:
            # kill phantomjs if phantom.exit() wasn't called in the test
            if phantom.poll() is None:
                phantom.terminate()
            result.stopTest(self._test)

    def process(self, line, result):
        # Test protocol
        # -------------
        # use console.log in phantomjs to output test results using the following format:
        # - for a success: { "event": "success" }
        # - for a failure: { "event": "failure", "message": "Failure description" }
        # - for an error:  { "event": "error",   "message": "Error description" }
        # any other message is treated as an error
        result.startTest(self._test)
        try:
            args = json.loads(line)
            event = args.get('event', None)
            if event == 'success':
                result.addSuccess(self._test)
            elif event == 'failure':
                message = args.get('message', "")
                result.addFailure(self._test, message)
            elif event == 'error':
                message = args.get('message', "")
                result.addError(self._test, message)
            else:
                result.addError(self._test, 'Unexpected JSON: "%s"' % line)
        except ValueError:
             result.addError(self._test, 'Unexpected message: "%s"' % line)

def load_tests(loader, base, _):
    base.addTest(WebsiteUiSuite('dummy_test.js'))
    base.addTest(WebsiteUiSuite('banner_tour_test.js'))
    return base