# This is a list of known failures (=bugs).
# The tests listed there must fail (or testrunner.py will report error) unless they are prefixed with FLAKY
# in which cases the result of them is simply ignored
from __future__ import print_function

import sys
import struct

from gevent.testing import sysinfo

class Condition(object):
    __slots__ = ()

    def __and__(self, other):
        return AndCondition(self, other)

    def __or__(self, other):
        return OrCondition(self, other)

    def __nonzero__(self):
        return self.__bool__()

    def __bool__(self):
        raise NotImplementedError


class AbstractBinaryCondition(Condition): # pylint:disable=abstract-method
    __slots__ = (
        'lhs',
        'rhs',
    )
    OP = None
    def __init__(self, lhs, rhs):
        self.lhs = lhs
        self.rhs = rhs

    def __repr__(self):
        return "(%r %s %r)" % (
            self.lhs,
            self.OP,
            self.rhs
        )

class OrCondition(AbstractBinaryCondition):
    __slots__ = ()
    OP = '|'
    def __bool__(self):
        return bool(self.lhs) or bool(self.rhs)

class AndCondition(AbstractBinaryCondition):
    __slots__ = ()
    OP = '&'
    def __bool__(self):
        return bool(self.lhs) and bool(self.rhs)

class ConstantCondition(Condition):
    __slots__ = (
        'value',
        '__name__',
    )

    def __init__(self, value, name=None):
        self.value = bool(value)
        self.__name__ = name or str(value)

    def __bool__(self):
        return self.value

    def __repr__(self):
        return self.__name__

ALWAYS = ConstantCondition(True)
NEVER = ConstantCondition(False)

class _AttrCondition(ConstantCondition):
    __slots__ = (
    )

    def __init__(self, name):
        ConstantCondition.__init__(self, getattr(sysinfo, name), name)

PYPY = _AttrCondition('PYPY')
PYPY3 = _AttrCondition('PYPY3')
PY3 = _AttrCondition('PY3')
PY2 = _AttrCondition('PY2')
OSX = _AttrCondition('OSX')
LIBUV = _AttrCondition('LIBUV')
WIN = _AttrCondition('WIN')
APPVEYOR = _AttrCondition('RUNNING_ON_APPVEYOR')
TRAVIS = _AttrCondition('RUNNING_ON_TRAVIS')
CI = _AttrCondition('RUNNING_ON_CI')
LEAKTEST = _AttrCondition('RUN_LEAKCHECKS')
COVERAGE = _AttrCondition('RUN_COVERAGE')
RESOLVER_NOT_SYSTEM = _AttrCondition('RESOLVER_NOT_SYSTEM')
BIT_64 = ConstantCondition(struct.calcsize('P') * 8 == 64, 'BIT_64')
PY380_EXACTLY = ConstantCondition(sys.version_info[:3] == (3, 8, 0), 'PY380_EXACTLY')

class _Definition(object):
    __slots__ = (
        '__name__',
        # When does the class of this condition apply?
        'when',
        # When should this test be run alone, if it's run?
        'run_alone',
        # Should this test be ignored during coverage measurement?
        'ignore_coverage',
        # {name: (Condition, value)}
        'options',
    )

    def __init__(self, when, run_alone, ignore_coverage, options):
        assert isinstance(when, Condition)
        assert isinstance(run_alone, Condition)
        assert isinstance(ignore_coverage, Condition)
        self.when = when
        self.__name__ = None # pylint:disable=non-str-assignment-to-dunder-name
        self.run_alone = run_alone
        self.ignore_coverage = ignore_coverage
        if options:
            for v in options.values():
                assert isinstance(v, tuple) and len(v) == 2
                assert isinstance(v[0], Condition)
        self.options = options

    def __set_name__(self, owner, name):
        self.__name__ = name

    def __repr__(self):
        return '<%s for %s when=%r=%s run_alone=%r=%s>' % (
            type(self).__name__,
            self.__name__,
            self.when, bool(self.when),
            self.run_alone, bool(self.run_alone)
        )

class _Action(_Definition):
    __slots__ = (
        'reason',
    )
    def __init__(self, reason='', when=ALWAYS, run_alone=NEVER, ignore_coverage=NEVER,
                 options=None):
        _Definition.__init__(self, when, run_alone, ignore_coverage, options)
        self.reason = reason

class RunAlone(_Action):
    __slots__ = ()

    def __init__(self, reason='', when=ALWAYS, ignore_coverage=NEVER):
        _Action.__init__(self, reason, run_alone=when, ignore_coverage=ignore_coverage)

class Failing(_Action):
    __slots__ = ()

class Flaky(Failing):
    __slots__ = ()

class Ignored(_Action):
    __slots__ = ()

class Multi(object):
    def __init__(self):
        self._conds = []

    def flaky(self, reason='', when=True, ignore_coverage=NEVER, run_alone=NEVER):
        self._conds.append(
            Flaky(
                reason, when=when,
                ignore_coverage=ignore_coverage,
                run_alone=run_alone,
            )
        )
        return self

    def ignored(self, reason='', when=True):
        self._conds.append(Ignored(reason, when=when))
        return self

    def __set_name__(self, owner, name):
        for c in self._conds:
            c.__set_name__(owner, name)


class DefinitionsMeta(type):
    # a metaclass on Python 3 that makes sure we only set attributes once. pylint doesn't
    # warn about that.
    @classmethod
    def __prepare__(cls, name, bases): # pylint:disable=unused-argument
        return SetOnceMapping()


class SetOnceMapping(dict):

    def __setitem__(self, name, value):
        if name in self:
            raise AttributeError(name)
        dict.__setitem__(self, name, value)

som = SetOnceMapping()
som[1] = 1
try:
    som[1] = 2
except AttributeError:
    del som
else:
    raise AssertionError("SetOnceMapping is broken")

DefinitionsBase = DefinitionsMeta('DefinitionsBase', (object,), {})

class Definitions(DefinitionsBase):

    test__issue6 = Flaky(
        """test__issue6 (see comments in test file) is really flaky on both Travis and Appveyor;
        on Travis we could just run the test again (but that gets old fast), but on appveyor
        we don't have that option without a new commit---and sometimes we really need a build
        to succeed in order to get a release wheel"""
    )

    test__core_fork = Ignored(
        """fork watchers don't get called on windows
        because fork is not a concept windows has.
        See this file for a detailed explanation.""",
        when=WIN
    )

    test__greenletset = Flaky(
        when=WIN,
        ignore_coverage=PYPY
    )

    test__example_udp_client = test__example_udp_server = Flaky(
        """
        These both run on port 9000 and can step on each other...seems
        like the appveyor containers aren't fully port safe? Or it
        takes longer for the processes to shut down? Or we run them in
        a different order in the process pool than we do other places?

        On PyPy on Travis, this fails to get the correct results,
        sometimes. I can't reproduce locally
        """,
        when=APPVEYOR | (PYPY & TRAVIS)
    )

    # This one sometimes randomly closes connections, but no indication
    # of a server crash, only a client side close.
    test__server_pywsgi = Flaky(when=APPVEYOR)

    test_threading = Multi().ignored(
        """
        This one seems to just stop right after patching is done. It
        passes on a local win 10 vm, and the main test_threading_2.py
        does as well. Based on the printouts we added, it appears to
        not even finish importing:
        https://ci.appveyor.com/project/denik/gevent/build/1.0.1277/job/tpvhesij5gldjxqw#L1190
        Ignored because it takes two minutes to time out.
        """,
        when=APPVEYOR & LIBUV & PYPY
    ).flaky(
        """
        test_set_and_clear in Py3 relies on 5 threads all starting and
        coming to an Event wait point while a sixth thread sleeps for a half
        second. The sixth thread then does something and checks that
        the 5 threads were all at the wait point. But the timing is sometimes
        too tight for appveyor. This happens even if Event isn't
        monkey-patched
        """,
        when=APPVEYOR & PY3
    )

    test_ftplib = Flaky(
        r"""
        could be a problem of appveyor - not sure
         ======================================================================
          ERROR: test_af (__main__.TestIPv6Environment)
         ----------------------------------------------------------------------
          File "C:\Python27-x64\lib\ftplib.py", line 135, in connect
            self.sock = socket.create_connection((self.host, self.port), self.timeout)
          File "c:\projects\gevent\gevent\socket.py", line 73, in create_connection
            raise err
          error: [Errno 10049] [Error 10049] The requested address is not valid in its context.
        XXX: On Jan 3 2016 this suddenly started passing on Py27/64; no idea why, the python version
        was 2.7.11 before and after.
        """,
        when=APPVEYOR & BIT_64
    )


    test__backdoor = Flaky(when=LEAKTEST | PYPY)
    test__socket_errors = Flaky(when=LEAKTEST)
    test_signal = Multi().flaky(
        "On Travis, this very frequently fails due to timing",
        when=TRAVIS & LEAKTEST,
        # Partial workaround for the _testcapi issue on PyPy,
        # but also because signal delivery can sometimes be slow, and this
        # spawn processes of its own
        run_alone=APPVEYOR,
    ).ignored(
        """
        This fails to run a single test. It looks like just importing the module
        can hang. All I see is the output from patch_all()
        """,
        when=APPVEYOR & PYPY3
    )

    test__monkey_sigchld_2 = Ignored(
        """
        This hangs for no apparent reason when run by the testrunner,
        even wher maked standalone when run standalone from the
        command line, it's fine. Issue in pypy2 6.0?
        """,
        when=PYPY & LIBUV
    )

    test_ssl = Ignored(
        """
        PyPy 7.0 and 7.1 on Travis with Ubunto Xenial 16.04 can't
        allocate SSL Context objects, either in Python 2.7 or 3.6.
        There must be some library incompatibility. No point even
        running them. XXX: Remember to turn this back on.

        On Windows, with PyPy3.7 7.3.7, there seem to be all kind of certificate
        errors.
        """,
        when=(PYPY & TRAVIS) | (PYPY3 & WIN)
    )

    test_httpservers = Ignored(
        """
        All the CGI tests hang. There appear to be subprocess problems.
        """,
        when=PYPY3 & WIN
    )



    test__pywsgi = Ignored(
        """
        XXX: Re-enable this when we can investigate more. This has
        started crashing with a SystemError. I cannot reproduce with
        the same version on macOS and I cannot reproduce with the same
        version in a Linux vm. Commenting out individual tests just
        moves the crash around.
        https://bitbucket.org/pypy/pypy/issues/2769/systemerror-unexpected-internal-exception

        On Appveyor 3.8.0, for some reason this takes *way* too long, about 100s, which
        often goes just over the default timeout of 100s. This makes no sense.
        But it also takes nearly that long in 3.7. 3.6 and earlier are much faster.

        It also takes just over 100s on PyPy 3.7.
        """,
        when=(PYPY & TRAVIS & LIBUV) | PY380_EXACTLY,
        # https://bitbucket.org/pypy/pypy/issues/2769/systemerror-unexpected-internal-exception
        run_alone=(CI & LEAKTEST & PY3) | (PYPY & LIBUV),
        # This often takes much longer on PyPy on CI.
        options={'timeout': (CI & PYPY, 180)},
    )

    test_subprocess = Multi().flaky(
        "Unknown, can't reproduce locally; times out one test",
        when=PYPY & PY3 & TRAVIS,
        ignore_coverage=ALWAYS,
    ).ignored(
        "Tests don't even start before the process times out.",
        when=PYPY3 & WIN
    )

    test__threadpool = Ignored(
        """
        XXX: Re-enable these when we have more time to investigate.

        This test, which normally takes ~60s, sometimes
        hangs forever after running several tests. I cannot reproduce,
        it seems highly load dependent. Observed with both libev and libuv.
        """,
        when=TRAVIS & (PYPY | OSX),
        # This often takes much longer on PyPy on CI.
        options={'timeout': (CI & PYPY, 180)},
    )

    test__threading_2 = Ignored(
        """
        This test, which normally takes 4-5s, sometimes
        hangs forever after running two tests. I cannot reproduce,
        it seems highly load dependent. Observed with both libev and libuv.
        """,
        when=TRAVIS & (PYPY | OSX),
        # This often takes much longer on PyPy on CI.
        options={'timeout': (CI & PYPY, 180)},
    )

    test__issue230 = Ignored(
        """
        This rarely hangs for unknown reasons. I cannot reproduce
        locally.
        """,
        when=TRAVIS & OSX
    )

    test_selectors = Flaky(
        """
        Timing issues on appveyor.
        """,
        when=PY3 & APPVEYOR,
        ignore_coverage=ALWAYS,
    )

    test__example_portforwarder = Flaky(
        """
        This one sometimes times out, often after output "The process
        with PID XXX could not be terminated. Reason: There is no
        running instance of the task.",
        """,
        when=APPVEYOR | COVERAGE
    )

    test__issue302monkey = test__threading_vs_settrace = Flaky(
        """
        The gevent concurrency plugin tends to slow things
        down and get us past our default timeout value. These
        tests in particular are sensitive to it. So in fact we just turn them
        off.
        """,
        when=COVERAGE,
        ignore_coverage=ALWAYS,
    )

    test__hub_join_timeout = Ignored(
        r"""
        This sometimes times out. It appears to happen when the
        times take too long and a test raises a FlakyTestTimeout error,
        aka a unittest.SkipTest error. This probably indicates that we're
        not cleaning something up correctly:

        .....ss
        GEVENTTEST_USE_RESOURCES=-network C:\Python38-x64\python.exe -u \
           -mgevent.tests.test__hub_join_timeout [code TIMEOUT] [took 100.4s]
        """,
        when=APPVEYOR
    )

    test__example_wsgiserver = test__example_webproxy = RunAlone(
        """
        These share the same port, which means they can conflict
        between concurrent test runs too
        XXX: Fix this by dynamically picking a port.
        """,
    )

    test__pool = RunAlone(
        """
        On a heavily loaded box, these can all take upwards of 200s.
        """,
        when=(CI & LEAKTEST) | (PYPY3 & APPVEYOR)
    )

    test_socket = RunAlone(
        "Sometimes has unexpected timeouts",
        when=CI & PYPY & PY3,
        ignore_coverage=ALWAYS, # times out
    )

    test__refcount = Ignored(
        "Sometimes fails to connect for no reason",
        when=(CI & OSX) | (CI & PYPY) | APPVEYOR,
        ignore_coverage=PYPY
    )

    test__doctests = Ignored(
        "Sometimes times out during/after gevent._config.Config",
        when=CI & OSX
    )



# tests that can't be run when coverage is enabled
# TODO: Now that we have this declarative, we could eliminate this list,
# just add them to the main IGNORED_TESTS list.
IGNORE_COVERAGE = [
]

# A mapping from test file basename to a dictionary of
# options that will be applied on top of the DEFAULT_RUN_OPTIONS.
TEST_FILE_OPTIONS = {

}

FAILING_TESTS = []
IGNORED_TESTS = []
# tests that don't do well when run on busy box
# or that are mutually exclusive
RUN_ALONE = [

]

def populate(): # pylint:disable=too-many-branches
    # TODO: Maybe move to the metaclass.
    # TODO: This could be better.
    for k, v in Definitions.__dict__.items():
        if isinstance(v, Multi):
            actions = v._conds
        else:
            actions = (v,)
        test_name = k + '.py'
        del k, v

        for action in actions:
            if not isinstance(action, _Action):
                continue

            if action.run_alone:
                RUN_ALONE.append(test_name)
            if action.ignore_coverage:
                IGNORE_COVERAGE.append(test_name)
            if action.options:
                for opt_name, (condition, value) in action.options.items():
                    # TODO: Verify that this doesn't match more than once.
                    if condition:
                        TEST_FILE_OPTIONS.setdefault(test_name, {})[opt_name] = value
            if action.when:
                if isinstance(action, Ignored):
                    IGNORED_TESTS.append(test_name)
                elif isinstance(action, Flaky):
                    FAILING_TESTS.append('FLAKY ' + test_name)
                elif isinstance(action, Failing):
                    FAILING_TESTS.append(test_name)

    FAILING_TESTS.sort()
    IGNORED_TESTS.sort()
    RUN_ALONE.sort()

populate()

if __name__ == '__main__':
    print('known_failures:\n', FAILING_TESTS)
    print('ignored tests:\n', IGNORED_TESTS)
    print('run alone:\n', RUN_ALONE)
    print('options:\n', TEST_FILE_OPTIONS)
    print("ignore during coverage:\n", IGNORE_COVERAGE)
