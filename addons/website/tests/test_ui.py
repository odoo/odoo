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
    def __init__(self, testfile, options, timeout=60.0):
        self._testfile = testfile
        self._timeout = timeout
        self._options = options
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
        self._test = WebsiteUiTest(self._testfile)
        start_time = time.time()
        last_check_time = time.time()

        self._options['timeout'] = self._timeout
        self._options['port'] = tools.config.get('xmlrpc_port', 80)
        self._options['db'] = tools.config.get('db_name', '')
        # TODO Use correct key
        self._options['user'] = 'admin'
        self._options['admin_password'] = tools.config.get('admin_passwd', 'admin')

        phantom = subprocess.Popen([
                'phantomjs',
                os.path.join(ROOT, self._testfile),
                json.dumps(self._options)
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT)
        proc_stdout = LineReader(phantom.stdout.fileno())
        readable = [proc_stdout]
        try:
            while phantom.poll() is None and readable and last_check_time < start_time + self._timeout:
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
                        self.process(lines, result)
                        readable.remove(stream)
            if last_check_time >= (start_time + self._timeout):
                result.addError(self._test, "Timeout after %s s" % (last_check_time - start_time ))
        finally:
            # kill phantomjs if phantom.exit() wasn't called in the test
            if phantom.poll() is None:
                phantom.terminate()
            result.stopTest(self._test)

    def process(self, lines, result):
        # Test protocol
        # -------------
        # use console.log in phantomjs to output test results using the following format:
        # - for a success: { "event": "success" }
        # - for an error:  { "event": "error",   "message": "Short error description" }
        # the first line is treated as a JSON message (JSON should be formatted on one line)
        # subsequent lines are displayed only if the first line indicated an error
        # or if the first line was not a JSON message (still an error)
        result.startTest(self._test)
        try:
            args = json.loads(lines[0])
            event = args.get('event', None)
            if event == 'success':
                result.addSuccess(self._test)
            elif event == 'error':
                message = args.get('message', "")
                result.addError(self._test, message+"\n"+"\n".join(lines[1::]))
            else:
                result.addError(self._test, 'Unexpected message: "%s"' % "\n".join(lines))
        except ValueError:
             result.addError(self._test, 'Unexpected message: "%s"' % "\n".join(lines))

def load_tests(loader, base, _):
    base.addTest(WebsiteUiSuite('dummy_test.js', {}))
    base.addTest(WebsiteUiSuite('simple_dom_test.js', { 'action': 'website.action_website_homepage' }), 120.0)
    base.addTest(WebsiteUiSuite('homepage_test.js',   { 'action': 'website.action_website_homepage' }), 120.0)
    return base
