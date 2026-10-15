# ruff: noqa: T201
"""
pg user needs:

- to own the base db (and every object)
- that the extensions be preinstalled (alter template0 probably)
- createdb
- pg_signal_autovacuum_worker
"""

import collections
import faulthandler
import gc
import json
import logging
import os
import secrets
import selectors
import shutil
import signal
import socket
import sys
import tempfile
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing, suppress

import psutil

from odoo import api, modules, sql_db
from odoo.http.router import root
from odoo.modules import db
from odoo.orm.registry import Registry
from odoo.service import server
from odoo.tests import case, loader
from odoo.tests.common import HttpCase
from odoo.tests.result import OdooTestResult
from odoo.tests.suite import OdooSuite
from odoo.tests.tag_selector import TagsSelector
from odoo.tools import SQL, config
from odoo.tools.sql import quoted_identifier

from . import Command
from .server import check_postgres_user, report_configuration

_logger = logging.getLogger(__name__)

# time given to workers to exit on SIGINT, before they are killed
TERMINATE_TIMEOUT = 30

# test outcomes, by increasing precedence when a test has several
OUTCOMES = ['passed', 'skipped', 'failed', 'error']
LETTERS = {'passed': '.', 'skipped': 's', 'failed': 'F', 'error': 'E', 'rerun': 'R'}


class Test(Command):
    """Run the post-install test suite of an existing database"""
    epilog = """
        Tests are run after the registry is fully loaded, regardless of their
        position: `-at_install` is always prepended to the test tags, so
        at_install tests are not run.

        All the server options (e.g. --addons-path, -d, --test-tags, database
        connection parameters) are accepted, see `odoo-bin --help`. Modules
        can not be installed or updated (-i, -u), use `odoo-bin module`.

        Each worker runs on its own copy of the database (named
        `<database>/<random>`), which is dropped afterwards. The output of the
        workers is captured in log files, which are kept if anything failed.

        Tests are identified by their test tag, which can be given to
        --test-tags to run them again.

        To run the tests in the current process, on the database itself, use
        `odoo-bin --test-enable` instead.
    """

    def run(self, cmdargs):
        parser = self.parser
        parser.allow_abbrev = False
        parser.add_argument(
            '--workers', type=int, default=0, metavar='N',
            help="run the tests in N worker processes, each with its own copy "
                 "of the database; 0 (default) uses the number of physical "
                 "cores if the CPU has hyperthreading, 80%% of them otherwise",
        )
        parser.add_argument(
            '-v', '--verbose', action='count', default=0,
            help="print a line per test instead of a character",
        )
        parser.add_argument(
            '--debug', action='store_true',
            help="to debug the runner itself: print a line when each test "
                 "starts, and the duration of each test, with the UTC time "
                 "and the worker on every line (implies -v)",
        )
        parser.add_argument(
            '--maxfail', type=int, default=0, metavar='N',
            help="stop after N failures or errors",
        )
        parser.add_argument(
            '-x', '--exitfirst', action='store_const', dest='maxfail', const=1,
            help="stop after the first failure or error, same as --maxfail 1",
        )
        parser.add_argument(
            '--reruns', type=int, metavar='N',
            help="retry failed tests up to N times, overrides the "
                 "ODOO_TEST_FAILURE_RETRIES environment variable",
        )
        parser.add_argument(
            '--timeout', type=float, default=0, metavar='SECONDS',
            help="fail a test running for more than SECONDS (including the "
                 "setup and teardown of its class), by dumping the stacks of "
                 "its worker into its output and killing it",
        )
        parser.add_argument(
            '--session-timeout', type=float, default=0, metavar='SECONDS',
            help="stop running tests after SECONDS, the running tests are not "
                 "interrupted",
        )
        args, server_args = parser.parse_known_args(cmdargs)

        config.parser.prog = self.prog
        config.parse_config(server_args, setup_logging=True)
        check_postgres_user()
        report_configuration()

        if len(config['db_name']) != 1:
            sys.exit("Exactly one database must be provided with -d/--database.")
        if config['init'] or config['update'] or config['reinit']:
            sys.exit("Modules can not be installed or updated when testing, use `odoo-bin module`.")
        if args.workers < 0:
            sys.exit("--workers must be positive.")
        if args.maxfail < 0:
            sys.exit("--maxfail must be positive.")
        if args.timeout < 0 or args.session_timeout < 0:
            sys.exit("--timeout and --session-timeout must be positive.")
        if args.reruns is not None:
            if args.reruns < 0:
                sys.exit("--reruns must be positive.")
            # read by the test suites of the workers
            # FIXME: also remove the per-class auto-disable?
            os.environ['ODOO_TEST_FAILURE_RETRIES'] = str(args.reruns)
        [dbname] = config['db_name']

        if not db.exist(dbname):
            sys.exit(f"Database {dbname!r} does not exist.")
        sql_db.close_db(dbname)

        # TODO: automatic import of runbot test tags? Match branches how?
        config['test_tags'] = ','.join(filter(None, ['-at_install', config['test_tags']]))
        # tests are only run once the registry is loaded, `test_enable` is
        # only set afterwards so no test runs while loading the modules
        config['test_enable'] = False
        config['stop_after_init'] = True
        config['workers'] = 0
        # let the OS select a free port (the http server stores it in config),
        # so concurrent test runs don't conflict with one another or a server
        config['http_port'] = 0

        workers = args.workers or default_workers()
        sys.exit(Controller(
            dbname, workers, args.verbose or args.debug, args.maxfail,
            debug=args.debug,
            timeout=args.timeout, session_timeout=args.session_timeout,
        ).run())


def default_workers():
    """ Number of workers matching the computing capacity of the machine.

    Test execution is mostly sequential (python does not run during SQL
    queries, HTTP requests are serialized during tests), but tours can run
    javascript, python and SQL concurrently. So use one worker per physical
    core when hyperthreading is available (a hyperthread being worth 10~20%
    of a core), and leave some headroom otherwise.
    """
    logical = psutil.cpu_count() or 1
    physical = psutil.cpu_count(logical=False) or logical
    if physical != logical:
        return physical
    return max(1, physical * 4 // 5)


# ---------------------------------------------------------------------------
# test runner (worker side)
# ---------------------------------------------------------------------------

def class_id(test_class):
    return f'{test_class.__module__}.{test_class.__qualname__}'.removeprefix('odoo.addons.')


def test_tag(test, *, method=True):
    """ Test tag selecting ``test`` (or its class if not ``method``). """
    params = test._get_canonical_tags_params(None)
    if not method:
        params['test_method'] = None
    tag = test._make_canonical_tag(**params)
    # a tag without tag name implies `standard`
    return tag if 'standard' in test.test_tags else f'*{tag}'


class ReportingResult(OdooTestResult):
    """ Reports the outcome of each test of a class to the controller,
    and stops running the tests when the controller says so.
    """
    def __init__(self, tests, dispatch):
        super().__init__()
        self.tests = tests
        self.dispatch = dispatch
        # [test, outcome, message] of the running test, and when it started
        self.current = None
        self.started_at = None
        # a passed attempt of a test is only reported once the next test
        # starts, as it may still be retried (if it logged an error)
        self.pending = None

    def startTest(self, test):
        if not self.pending:
            pass
        elif self.pending['tag'] == test_tag(test):
            self.send({**self.pending, 'outcome': 'rerun', 'message': "logged an error", 'test': False})
        else:
            self.send(self.pending)
        self.pending = None
        # lets the controller know which test crashed or timed out
        if not self.dispatch({'start': test_tag(test)}):
            self.shouldStop = True
        self.current = [test, 'passed', None]
        self.started_at = time.monotonic()
        super().startTest(test)

    def stopTest(self, test):
        super().stopTest(test)
        test, outcome, message = self.current
        self.current = None
        event = {
            'tag': test_tag(test), 'outcome': outcome, 'message': message, 'test': True,
            'duration': time.monotonic() - self.started_at,
        }
        if not self._soft_fail:
            self.send(event)
        elif self.had_failure:
            # the attempt failed, and will be retried
            self.send({**event, 'outcome': 'rerun', 'test': False})
        else:
            self.pending = event

    def flush(self):
        if self.pending:
            self.send(self.pending)
            self.pending = None

    def send(self, event):
        if not self.dispatch({'test': event}):
            self.shouldStop = True

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.record(test, 'failed', format_error(err))

    def addError(self, test, err):
        super().addError(test, err)
        self.record(test, 'error', format_error(err))

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.record(test, 'skipped', reason)

    def record(self, test, outcome, message):
        if self.current:
            # the running test, or one of its subtests
            if OUTCOMES.index(outcome) > OUTCOMES.index(self.current[1]):
                self.current[1:] = outcome, message
        elif test.description.startswith('setUpClass'):
            # none of the tests of the class will run, the output of the
            # error goes with the first one
            first = test_tag(self.tests[0])
            for t in self.tests:
                tag = test_tag(t)
                self.send({
                    'tag': tag, 'outcome': outcome, 'message': message, 'test': True,
                    'same_as': None if tag == first else first,
                })
        else:
            # error tearing down the class, after all its tests ran
            self.send({'tag': test_tag(self.tests[0], method=False), 'outcome': outcome, 'message': message, 'test': False})


def format_error(err):
    exc_type, exc, _ = err
    if isinstance(exc, case.SkipTest):
        return str(exc)
    message = str(exc).strip().partition('\n')[0]
    return f'{exc_type.__name__}: {message}' if message else exc_type.__name__


def run_tests(dbname, dispatch):
    """ Load the registry of ``dbname``, collect the tests matching the
    configured test tags and run them class by class, in the current process.

    ``dispatch`` sends a message to the controller and returns its reply:

    - ``{"classes": {class_id: {"tests": count, "tag": tag}}}`` (in
      execution order) once the tests are collected, and ``{"done":
      class_id}`` after each class has run, reply with the id of the next
      class to run, or ``None`` to stop;
    - ``{"start": tag}`` before each test and ``{"test": {...}}`` after it,
      reply whether to continue running the tests.
    """
    server.load_server_wide_modules()
    registry = Registry.new(dbname)
    config['test_enable'] = True

    server.server = server.ThreadedServer(root)
    server.server.http_spawn()

    module_names = sorted(registry._init_modules)
    selector = TagsSelector(config['test_tags'], module_names)
    tests = sorted((
        test
        for module_name in module_names
        for module in loader.get_test_modules(module_name)
        for test in loader.get_module_test_cases(module)
        if selector.check(test)
    ), key=lambda t: getattr(t, 'test_sequence', 0))
    classes = collections.defaultdict(list)
    for test in tests:
        classes[class_id(type(test))].append(test)

    assets_generated = False
    next_id = dispatch({'classes': {
        cid: {'tests': len(tests), 'tag': test_tag(tests[0], method=False)}
        for cid, tests in classes.items()
    }})
    while next_id is not None:
        tests = classes.pop(next_id)
        if not assets_generated and issubclass(type(tests[0]), HttpCase):
            with registry.cursor() as cr:
                api.Environment(cr, api.SUPERUSER_ID, {})['ir.qweb']._pregenerate_assets_bundles()
            assets_generated = True

        result = ReportingResult(tests, dispatch)
        OdooSuite(tests)(result)
        result.flush()
        modules.module.current_test = None
        next_id = dispatch({'done': next_id})

    server.server.stop_event.set()


def worker_main(dbname, sock, log_path):
    """ Entry point of a forked worker process. """
    # leave the controller's process group, so terminal signals don't reach
    # the worker, and the controller can kill the worker and its children
    # (e.g. chrome) at once
    os.setpgid(0, 0)

    signal.signal(signal.SIGTERM, signal.SIG_DFL)

    # the controller interrupts workers to stop them: the KeyboardInterrupt
    # unwinds the running test (it is not caught as a test error) and the
    # worker, which exits
    interrupted = False

    def interrupt(signum, frame):
        nonlocal interrupted
        interrupted = True
        signal.default_int_handler(signum, frame)

    # explicitly, as SIGINT may be ignored (e.g. background jobs)
    signal.signal(signal.SIGINT, interrupt)
    null = os.open(os.devnull, os.O_RDONLY)
    os.dup2(null, 0)
    log = os.open(log_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    os.dup2(log, 1)
    os.dup2(log, 2)
    os.close(null)
    os.close(log)
    # keep prints in order with the logs
    sys.stdout.reconfigure(line_buffering=True)
    # used by the controller before killing a worker on timeout
    faulthandler.register(signal.SIGUSR1, all_threads=True)

    config['db_name'] = [dbname]
    config['dbfilter'] = ''

    stream = sock.makefile('rw', encoding='utf-8')

    def dispatch(message):
        if interrupted:
            # the controller does not expect messages anymore
            raise KeyboardInterrupt
        # the controller reads the log file to get the output of the test
        sys.stdout.flush()
        sys.stderr.flush()
        stream.write(json.dumps(message) + '\n')
        stream.flush()
        return json.loads(stream.readline())

    run_tests(dbname, dispatch)

    sql_db.close_all()


# ---------------------------------------------------------------------------
# controller
# ---------------------------------------------------------------------------

class Worker:
    def __init__(self, index, dbname, log_path):
        self.index = index
        self.dbname = dbname
        self.log_path = log_path
        self.pid = None
        self.sock = None
        self.stream = None
        # id of the class being run, and tag of the test being run
        self.current = None
        self.current_test = None
        self.test_started_at = None
        # size of the log file and time when the worker was last replied to
        self.output_start = 0
        self.replied_at = 0
        self.timed_out = False
        # time at which to kill the worker, if it does not exit on SIGINT
        self.kill_at = None
        self.returncode = None

    def output(self):
        """ Output of the worker since it was last replied to. """
        with open(self.log_path, 'rb') as f:
            f.seek(self.output_start)
            return f.read().decode(errors='replace')

    def reply(self, value):
        self.output_start = os.path.getsize(self.log_path)
        self.replied_at = time.monotonic()
        self.stream.write(json.dumps(value) + '\n')
        self.stream.flush()


class InconsistentWorkers(Exception):
    pass


class Controller:
    def __init__(self, dbname, workers, verbose=False, maxfail=0, *,
                 debug=False, timeout=0, session_timeout=0):
        self.dbname = dbname
        self.workers_count = workers
        self.verbose = verbose
        self.debug = debug
        self.maxfail = maxfail
        self.timeout = timeout
        self.session_timeout = session_timeout
        self.workers = []
        self.selector = selectors.DefaultSelector()
        self.log_dir = None
        # number of tests and tag of each class, set when the first worker reports
        self.class_tests = {}
        # ids of the classes not handed out yet
        self.pending = None
        # test events, in the order they were received
        self.events = []
        self.outcomes = collections.Counter()
        # why the run was stopped early, if it was
        self.stopped = None
        self.t0 = time.time()
        self.started_at = time.monotonic()
        # whether the current line of the sea of dots is not empty
        self.dots_pending = False

    @property
    def tests_count(self):
        return sum(c['tests'] for c in self.class_tests.values())

    def run(self):
        self.log_dir = tempfile.mkdtemp(prefix='odoo-test-')
        interrupted = False
        error = None
        signal.signal(signal.SIGTERM, signal.default_int_handler)
        try:
            for _ in range(self.workers_count):
                self.new_worker(f'{self.dbname}/{secrets.token_hex(4)}')
            # copying a large database takes ages with lots of workers, so do it in parallel
            with ThreadPoolExecutor(self.workers_count) as executor:
                for future in [executor.submit(copy_database, self.dbname, w.dbname) for w in self.workers]:
                    future.result()
            # don't share database connections with the workers
            sql_db.close_all()
            # keep the GC from touching (and thus copying) the memory shared
            # with the workers
            gc.freeze()
            for worker in self.workers:
                self.spawn(worker)
            self.loop()
        except KeyboardInterrupt:
            interrupted = True
        except InconsistentWorkers as e:
            error = str(e)
        finally:
            self.end_dots()
            self.terminate()
            # don't log every drop, failures are logged below
            logging.getLogger('odoo.modules.db').setLevel(logging.WARNING)
            # replacement workers reuse the database of the worker they replace
            for dbname in dict.fromkeys(w.dbname for w in self.workers):
                if not db.exist(dbname):
                    continue  # its copy failed or was interrupted
                try:
                    db.drop(dbname)
                except Exception:  # noqa: BLE001
                    _logger.warning("Failed to drop worker database %r", dbname, exc_info=True)

        success = self.report(interrupted)
        if error:
            print(f"\naborted: {error}")
            success = False
        if success:
            shutil.rmtree(self.log_dir)
        else:
            print(f"\nworker logs: {self.log_dir}")
        return 0 if success else 1

    def new_worker(self, dbname):
        index = len(self.workers)
        worker = Worker(index, dbname, os.path.join(self.log_dir, f'worker-{index}.log'))
        self.workers.append(worker)
        return worker

    def spawn(self, worker):
        controller_sock, worker_sock = socket.socketpair()
        sys.stdout.flush()
        sys.stderr.flush()
        pid = os.fork()
        if pid == 0:
            # don't keep the controller's descriptors, in particular its end
            # of the other workers' sockets, which would then not see the
            # controller exiting (the stream has to be closed for the socket
            # to really be)
            self.selector.close()
            controller_sock.close()
            for other in self.workers:
                if other.stream:
                    other.stream.close()
                if other.sock:
                    other.sock.close()
            code = 0
            try:
                worker_main(worker.dbname, worker_sock, worker.log_path)
            except BaseException:  # noqa: BLE001
                traceback.print_exc()
                code = 1
            finally:
                sys.stdout.flush()
                sys.stderr.flush()
                # never return into the controller's stack
                os._exit(code)
        worker_sock.close()
        worker.pid = pid
        worker.sock = controller_sock
        worker.stream = controller_sock.makefile('rw', encoding='utf-8')
        self.selector.register(worker.sock, selectors.EVENT_READ, worker)

    def loop(self):
        classes = None
        while self.selector.get_map():
            ready = self.selector.select(self.time_to_deadline())
            self.check_timeouts()
            for key, _ in ready:
                worker = key.data
                line = worker.stream.readline()
                if not line:
                    self.selector.unregister(worker.sock)
                    self.worker_exited(worker)
                    continue

                message = json.loads(line)
                if 'start' in message:
                    worker.current_test = message['start']
                    worker.test_started_at = time.monotonic()
                    if self.debug:
                        print(f"{timestamp()} [{self.progress():4.0%}] [w{worker.index}] START {worker.current_test}", flush=True)
                    worker.reply(not self.stopped)
                    continue
                if 'test' in message:
                    worker.current_test = None
                    self.test_done(worker, message['test'])
                    worker.reply(not self.stopped)
                    continue

                if 'classes' in message:
                    if classes is None:
                        classes = set(message['classes'])
                        self.pending = collections.deque(message['classes'])
                        self.class_tests = message['classes']
                        print(
                            f"Running {self.tests_count} tests"
                            f" on {self.workers_count} workers",
                            flush=True,
                        )
                    elif classes != (new_classes := message['classes'].keys()):
                        raise_classes_error(worker, classes, new_classes)

                worker.current = self.pending.popleft() if self.pending and not self.stopped else None
                worker.reply(worker.current)

    def deadlines(self):
        """ Times at which the session or a running test times out. """
        if self.session_timeout and not self.stopped:
            yield self.started_at + self.session_timeout
        for worker in self.workers:
            if not worker.pid:
                continue
            if worker.kill_at:
                yield worker.kill_at
            elif self.timeout and worker.current is not None and not worker.timed_out:
                yield worker.replied_at + self.timeout

    def time_to_deadline(self):
        deadline = min(self.deadlines(), default=None)
        return None if deadline is None else max(0, deadline - time.monotonic())

    def check_timeouts(self):
        now = time.monotonic()
        if self.session_timeout and not self.stopped and now >= self.started_at + self.session_timeout:
            # like pytest-timeout, don't interrupt the running tests
            self.stopped = f"stopping: session timeout of {self.session_timeout}s exceeded"
        for worker in self.workers:
            if not worker.pid:
                continue
            if worker.kill_at and now >= worker.kill_at:
                # the worker did not exit on SIGINT
                with suppress(ProcessLookupError):
                    os.killpg(worker.pid, signal.SIGKILL)
                worker.kill_at = None
            elif self.timeout and worker.current is not None and not worker.timed_out \
                    and now >= worker.replied_at + self.timeout:
                worker.timed_out = True
                # dump the stacks of the worker (see `worker_main`) into its
                # log, then ask it and its children (e.g. chrome) to exit
                os.kill(worker.pid, signal.SIGUSR1)
                os.killpg(worker.pid, signal.SIGINT)
                worker.kill_at = now + TERMINATE_TIMEOUT

    def test_done(self, worker, event):
        self.events.append(event)
        if event['outcome'] in ('failed', 'error', 'rerun'):
            # the log of the test, including the error and its traceback
            event['output'] = worker.output()
        if event['test']:
            self.outcomes['tests'] += 1
        self.outcomes[event['outcome']] += 1
        failures = self.outcomes['failed'] + self.outcomes['error']
        if self.maxfail and failures >= self.maxfail and not self.stopped:
            self.stopped = f"stopping after {failures} failures"
        self.status(worker, event)

    def worker_exited(self, worker):
        _, status = os.waitpid(worker.pid, 0)
        worker.returncode = os.waitstatus_to_exitcode(status)
        worker.pid = None
        worker.kill_at = None
        worker.sock.close()
        if worker.current is None:
            return

        # report the test (or the class, outside of tests) the worker was running
        if worker.timed_out:
            outcome, message = 'failed', f"Timeout >{self.timeout}s"
        else:
            outcome, message = 'error', f"worker exited ({worker.returncode}) while running the test"
        self.test_done(worker, {
            'tag': worker.current_test or self.class_tests[worker.current]['tag'],
            'test': worker.current_test is not None,
            'outcome': outcome,
            'message': message,
            'duration': time.monotonic() - worker.test_started_at if worker.current_test else None,
        })
        worker.current = worker.current_test = None

        # replace the worker, unless crashes keep happening
        replacements = len(self.workers) - self.workers_count
        if self.pending and not self.stopped and replacements < self.workers_count:
            self.spawn(self.new_worker(worker.dbname))

    def terminate(self):
        workers = [w for w in self.workers if w.pid]
        for worker in workers:
            with suppress(ProcessLookupError):
                os.killpg(worker.pid, signal.SIGINT)
        deadline = time.time() + TERMINATE_TIMEOUT
        for worker in workers:
            while os.waitpid(worker.pid, os.WNOHANG) == (0, 0):
                if time.time() > deadline:
                    os.killpg(worker.pid, signal.SIGKILL)
                    os.waitpid(worker.pid, 0)
                    break
                time.sleep(0.1)
            worker.pid = None

    def progress(self):
        return self.outcomes['tests'] / self.tests_count

    def end_dots(self):
        """ Terminate the current line of the sea of dots, if any. """
        if self.dots_pending:
            print(flush=True)
            self.dots_pending = False

    def status(self, worker, event):
        """ Report the outcome of a test: a character by default, a line with
        -v, followed by the output of the test if it failed.
        """
        outcome = event['outcome']
        if not self.verbose:
            print(LETTERS[outcome], end='', flush=True)
            self.dots_pending = True
        else:
            line = f"[{self.progress():4.0%}]"
            if self.debug:
                line = f"{timestamp()} {line} [w{worker.index}]"
            line += f" {outcome.upper()} {event['tag']}"
            if outcome == 'skipped' and event['message']:
                line += f" ({event['message']})"
            if self.debug and (duration := event.get('duration')) is not None:
                line += f" in {duration:.3f}s"
            print(line, flush=True)
        if outcome in ('failed', 'error', 'rerun'):
            # the sea of dots resumes on the line after the output
            self.end_dots()
            print_output(event)

    def report(self, interrupted):
        failures = [e for e in self.events if e['outcome'] in ('failed', 'error')]
        crashed = [w for w in self.workers if w.returncode]
        not_run = self.tests_count - self.outcomes['tests']

        # the output of failed tests has been printed as they failed
        if failures:
            print(rule("short test summary info", '='))
            for event in failures:
                print(f"{event['outcome'].upper()} {event['tag']} - {event['message']}")
        for worker in crashed:
            print(f"worker {worker.index} exited with status {worker.returncode}, see {worker.log_path}")
        if self.stopped:
            print(self.stopped)

        counts = [
            f"{count} {label}"
            for outcome in ['failed', 'passed', 'skipped', 'error', 'rerun']
            if (count := self.outcomes[outcome])
            for label in [f'{outcome}s' if outcome == 'error' and count > 1 else outcome]
        ]
        if not_run:
            counts.append(f"{not_run} not run")
        print(
            f"\n{', '.join(counts) or 'no tests ran'} in {time.time() - self.t0:.2f}s"
            + (" (interrupted)" if interrupted else "")
        )
        return not (interrupted or failures or crashed or not_run)


def timestamp():
    """ Current UTC time, to reconstruct the occupancy of the workers. """
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def rule(title, char):
    """ ``title`` centered in a line of ``char`` as wide as the terminal. """
    return f" {title} ".center(shutil.get_terminal_size().columns, char)


def print_output(event):
    print(rule(event['tag'], '_'))
    if not (output := event['output'].rstrip('\n')):
        output = f"(same as {same_as})" if (same_as := event.get('same_as')) else "(no output captured)"
    print(output, flush=True)


def copy_database(source, target):
    """ Create ``target`` as a copy of ``source``, including its filestore
    (hardlinked when possible, as filestore files are never modified).
    """
    with closing(sql_db.db_connect(config['db_system']).cursor()) as cr:
        # database-altering operations cannot be executed inside a transaction
        cr._cnx.autocommit = True
        cr.execute(SQL(
            # copying the files is faster than through the WAL (the default)
            "CREATE DATABASE %s ENCODING 'unicode' TEMPLATE %s STRATEGY FILE_COPY",
            quoted_identifier(cr, target),
            quoted_identifier(cr, source),
        ))

    from_fs = config.filestore(source)
    if not os.path.isdir(from_fs):
        return

    def link(src, dst):
        try:
            os.link(src, dst)
        except OSError:
            shutil.copy2(src, dst)

    # the target filestore lives inside the source's (`<db>/<random>`): only
    # copy the files (in `xx/` directories), not the filestores of other
    # workers or the gc checklist
    shutil.copytree(
        from_fs, config.filestore(target),
        ignore=lambda path, names: [n for n in names if path == from_fs and len(n) != 2],
        copy_function=link,
    )

def raise_classes_error(worker: Worker, classes: set[str], new_classes: set[str]):
    missing = classes - new_classes
    extra = new_classes - classes
    raise InconsistentWorkers(
        f"worker {worker.index} collected different test classes than "
        f"the first worker: missing {sorted(missing)[:5]} ({len(missing)}), "
        f"extra {sorted(extra)[:5]} ({len(extra)})"
    )
