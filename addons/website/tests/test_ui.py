import json
import subprocess
import unittest
import os
import time

ROOT = os.path.join(os.path.dirname(__file__), 'ui_suite')

__all__ = ['load_tests', 'WebsiteUiSuite']

def _exc_info_to_string(err, test):
    return err

class WebsiteUiTest(unittest.TestCase):
    def __init__(self, name):
        self.name = name
    def shortDescription(self):
        return None
    def __str__(self):
        return self.name

class WebsiteUiSuite(unittest.TestSuite):
    def __init__(self, testfile, timeout=5000):
        self.testfile = testfile
        self.timeout = timeout
        self._test = None

    def __iter__(self):
        return iter([self])

    def run(self, result):
        # Test if phantom is correctly installed
        try:
            subprocess.call(['phantomjs', '-v'],
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
        phantom = subprocess.Popen([
            'phantomjs',
            os.path.join(ROOT, self.testfile),
            json.dumps({ 'timeout': self.timeout })
        ], stdout=subprocess.PIPE)

        self._test = WebsiteUiTest(self.testfile)

        try:
            while True:
                line = phantom.stdout.readline()
                if line:
                    if self.process(line, result):
                        break
                else:
                    time.sleep(0.1)
        finally:
            # If the phantomjs process hasn't quit, kill it
            if phantom.poll() is None:
                phantom.terminate()

    def process(self, line, result):
        result.startTest(self._test)
        args = json.loads(line)
        event = args.get('event')
        message = args.get('message', "")

        # Test protocol
        # -------------
        # use console.log in phantomjs to output test results using the following format:
        # - for a success: { "event": "success" }
        # - for a failure: { "event": "failure", "message": "Failure description" }
        # any other message is treated as an error
        if event == 'success':
            result.addSuccess(self._test)
            result.stopTest(self._test)
            return True;
        elif event == 'failure':
            result.addFailure(self._test, message)
            result.stopTest(self._test)
            return True;
        else:
            result.addError(self._test, message)
            result.stopTest(self._test)
            return False

def load_tests(loader, base, _):
    base.addTest(WebsiteUiSuite('sample_test.js'))
    return base