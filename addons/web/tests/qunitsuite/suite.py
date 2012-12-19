import json
import subprocess
import unittest
import os
import time

ROOT = os.path.join(os.path.dirname(__file__), 'grunt')

__all__ = ['QUnitSuite']

def _exc_info_to_string(err, test):
    return err

class QUnitTest(unittest.TestCase):
    def __init__(self, module, name):
        self.module = module
        self.name = name
        self.failed = False
    def shortDescription(self):
        return None
    def __repr__(self):
        return '<QUnitTest %s:%s>' % (self.module, self.name)
    def __str__(self):
        return '%s: %s' % (self.module, self.name)

class QUnitSuite(unittest.TestSuite):
    def __init__(self, qunitfile, timeout=5000):
        self.testfile = qunitfile
        self.timeout = timeout
        self._module = None
        self._test = None

    def __iter__(self):
        return iter([self])

    def run(self, result):
        try:
            subprocess.call(['phantomjs', '-v'],
                            stdout=open(os.devnull, 'w'),
                            stderr=subprocess.STDOUT)
        except OSError:
            test = QUnitTest('phantomjs', 'javascript tests')
            result.startTest(test)
            result.startTest(test)
            result.addSkip(test , "phantomjs command not found")
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
            '--config=%s' % os.path.join(ROOT, 'phantomjs.json'),
            os.path.join(ROOT, 'bootstrap.js'), self.testfile,
            json.dumps({
                'timeout': self.timeout,
                'inject': os.path.join(ROOT, 'qunit-phantomjs-bridge.js')
            })
        ], stdout=subprocess.PIPE)

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
        args = json.loads(line)
        event_name = args[0]

        if event_name == 'qunit.done':
            return True
        elif event_name == 'fail.load':
            self.add_error(result, "PhantomJS unable to load %s" % args[1])
            return True
        elif event_name == 'fail.timeout':
            self.add_error(result, "PhantomJS timed out, possibly due to a"
                                   " missing QUnit start() call")
            return True

        elif event_name == 'qunit.moduleStart':
            self._module = args[1].encode('utf-8')
        elif event_name == 'qunit.moduleStop':
            self._test = None
            self._module = None
        elif event_name == 'qunit.testStart':
            self._test = QUnitTest(self._module, args[1].encode('utf-8'))
            result.startTest(self._test)
        elif event_name == 'qunit.testDone':
            if not self._test.failed:
                result.addSuccess(self._test)
            result.stopTest(self._test)
            self._test = None
        elif event_name == 'qunit.log':
            if args[1]:
                return False

            self._test.failed = True
            result.addFailure(
                self._test, self.failure_to_str(*args[2:]))

        return False

    def add_error(self, result, s):
        test = QUnitTest('phantomjs', 'startup')
        result.startTest(test)
        result.addError(test, s)
        result.stopTest(test)

    def failure_to_str(self, actual, expected, message, source):
        if message or actual == expected:
            formatted = str(message or '')
        else:
            formatted = "%s != %s" % (actual, expected)

        if source:
            formatted += '\n\n' + source

        return formatted
