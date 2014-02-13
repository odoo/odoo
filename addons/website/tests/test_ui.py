import unittest
import subprocess
import os
import select
import time
import json
from openerp import sql_db, tools

# avoid "ValueError: too many values to unpack"
def _exc_info_to_string(err, test):
    return err

class Stream:
    def __init__(self, file_descriptor):
        self._file_descriptor = file_descriptor
        self._buffer = ''

    def fileno(self):
        return self._file_descriptor
    # TODO Rewrite & fix
    def readlines(self):
        data = os.read(self._file_descriptor, 4096)
        if not data: # EOF
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
        self._timeout = timeout + 5.0
        self._options = options
        self._test = None
        self._ignore_filters = [
            # Ignore phantomjs warnings
            "*** WARNING:",
            # Disabled because of the 'web_hello' addon
            "hello",
            # Fixes an issue with PhantomJS 1.9.2 on OS X 10.9 (Mavericks)
            # cf. https://github.com/ariya/phantomjs/issues/11418
            "CoreText performance note",
        ]

    def __iter__(self):
        return iter([self])

    def run(self, result):
        # clean slate
        if sql_db._Pool is not None:
            sql_db._Pool.close_all(sql_db.dsn(tools.config['db_name']))
        # check for PhantomJS...
        try:
            subprocess.call([ 'phantomjs', '-v' ], stdout=open(os.devnull, 'w'), stderr=subprocess.STDOUT)
        except OSError:
            test = WebsiteUiTest('UI Tests')
            result.startTest(test)
            result.addSkip(test, "phantomjs command not found (cf. http://phantomjs.org/)")
            result.stopTest(test)
            return
        # ...then run the actual test
        result._exc_info_to_string = _exc_info_to_string
        try:
            self._run(result)
        finally:
            del result._exc_info_to_string

    def _run(self, result):
        self._test = WebsiteUiTest("%s (as %s)" %
            (self._testfile, self._options.get('user') or "Anonymous" if 'user' in self._options else "admin" ))
        start_time = time.time()
        last_check_time = time.time()

        self._options['timeout'] = self._timeout
        self._options['port'] = tools.config.get('xmlrpc_port', 80)
        self._options['db'] = tools.config.get('db_name', '')
        if 'user' not in self._options:
            self._options['user'] = 'admin'
            self._options['password'] = 'admin'

        phantom = subprocess.Popen([
            'phantomjs',
            #'--debug=true',
            self._testfile,
            json.dumps(self._options)
        ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        readable = [Stream(phantom.stdout.fileno())]

        try:
            output = []
            while phantom.poll() is None and readable and last_check_time < start_time + self._timeout:
                ready, _, _ = select.select(readable, [], [], 0.1)
                if not ready:
                    last_check_time = time.time()
                    continue
                for stream in ready:
                    lines = stream.readlines()
                    if lines is None: # EOF
                        filtered_lines = [line for line in output if not any(ignore in line for ignore in self._ignore_filters)]
                        if (filtered_lines):
                            self.process(filtered_lines, result)
                        readable.remove(stream)
                    else:
                        output += lines
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
        # - for an error:  { "event": "error", "message": "Short error description" }
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
                result.addError(self._test, args.get('message', "")+"\n"+"\n".join(lines[1::]))
            else:
                result.addError(self._test, 'Unexpected message: "%s"' % "\n".join(lines))
        except ValueError:
            result.addError(self._test, 'Unexpected message: "%s"' % "\n".join(lines))

def full_path(pyfile, filename):
    return os.path.join(os.path.join(os.path.dirname(pyfile), 'ui_suite'), filename)

def load_tests(loader, base, _):
    base.addTest(WebsiteUiSuite(full_path(__file__, 'dummy_test.js'), {}, 5.0))
    #base.addTest(WebsiteUiSuite(full_path(__file__, 'login_test.js'), {'path': '/', 'user': None}, 60.0))
    base.addTest(WebsiteUiSuite(full_path(__file__, 'simple_dom_test.js'), {'redirect': '/page/website.homepage'}, 60.0))
    base.addTest(WebsiteUiSuite(full_path(__file__, 'homepage_test.js'), {'redirect': '/page/website.homepage'}, 60.0))
    return base
