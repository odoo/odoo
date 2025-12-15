#-----------------------------------------------------------
# Threaded, Gevent and Prefork Servers
#-----------------------------------------------------------
import contextlib
import collections
import datetime
import errno
import logging
import os
import os.path
import platform
import random
import select
import signal
import socket
import subprocess
import sys
import threading
import time
from collections import deque
from io import BytesIO

import psutil
import werkzeug.serving
from werkzeug .urls import uri_to_iri

if os.name == 'posix':
    # Unix only for workers
    import fcntl
    import resource
    try:
        import inotify
        from inotify.adapters import InotifyTrees
        from inotify.constants import IN_MODIFY, IN_CREATE, IN_MOVED_TO
        INOTIFY_LISTEN_EVENTS = IN_MODIFY | IN_CREATE | IN_MOVED_TO
    except ImportError:
        inotify = None
else:
    # Windows shim
    signal.SIGHUP = -1
    inotify = None

if not inotify:
    try:
        import watchdog
        from watchdog.observers import Observer
        from watchdog.events import FileCreatedEvent, FileModifiedEvent, FileMovedEvent
    except ImportError:
        watchdog = None

# Optional process names for workers
try:
    from setproctitle import setproctitle
except ImportError:
    setproctitle = lambda x: None

from odoo import api, sql_db
from odoo.modules.registry import Registry
from odoo.release import nt_service_name
from odoo.tools import config, gc, osutil, OrderedSet, profiler
from odoo.tools.cache import log_ormcache_stats
from odoo.tools.misc import stripped_sys_argv, dumpstacks
from .db import list_dbs

_logger = logging.getLogger(__name__)

SLEEP_INTERVAL = 60     # 1 min


# A global-ish object, each thread/worker uses its own
thread_local = threading.local()

# the model and method name that was called via rpc, for logging
thread_local.rpc_model_method = ''


def memory_info(process):
    """
    :return: the relevant memory usage according to the OS in bytes.
    """
    # psutil < 2.0 does not have memory_info, >= 3.0 does not have get_memory_info
    pmem = (getattr(process, 'memory_info', None) or process.get_memory_info)()
    # MacOSX allocates very large vms to all processes so we only monitor the rss usage.
    if platform.system() == 'Darwin':
        return pmem.rss
    return pmem.vms


def set_limit_memory_hard():
    if platform.system() != 'Linux':
        return
    limit_memory_hard = config['limit_memory_hard']
    import odoo  # for eventd
    if odoo.evented and config['limit_memory_hard_gevent']:
        limit_memory_hard = config['limit_memory_hard_gevent']
    if limit_memory_hard:
        rlimit = resource.RLIMIT_AS
        soft, hard = resource.getrlimit(rlimit)
        resource.setrlimit(rlimit, (limit_memory_hard, hard))

def empty_pipe(fd):
    try:
        while os.read(fd, 1):
            pass
    except OSError as e:
        if e.errno not in [errno.EAGAIN]:
            raise


def cron_database_list():
    return config['db_name'] or list_dbs(True)


#----------------------------------------------------------
# Werkzeug WSGI servers patched
#----------------------------------------------------------
class LoggingBaseWSGIServerMixIn(object):
    def handle_error(self, request, client_address):
        t, e, _ = sys.exc_info()
        if t == socket.error and e.errno == errno.EPIPE:
            # broken pipe, ignore error
            return
        _logger.exception('Exception happened during processing of request from %s', client_address)

class BaseWSGIServerNoBind(LoggingBaseWSGIServerMixIn, werkzeug.serving.BaseWSGIServer):
    """ werkzeug Base WSGI Server patched to skip socket binding. PreforkServer
    use this class, sets the socket and calls the process_request() manually
    """
    def __init__(self, app):
        werkzeug.serving.BaseWSGIServer.__init__(self, "127.0.0.1", 0, app, handler=CommonRequestHandler)
        # Directly close the socket. It will be replaced by WorkerHTTP when processing requests
        if self.socket:
            self.socket.close()

    def server_activate(self):
        # dont listen as we use PreforkServer#socket
        pass

class CommonRequestHandler(werkzeug.serving.WSGIRequestHandler):
    def log_request(self, code = "-", size = "-"):
        try:
            path = uri_to_iri(self.path)
            fragment = thread_local.rpc_model_method
            if fragment:
                path += '#' + fragment
            msg = f"{self.command} {path} {self.request_version}"
        except AttributeError:
            # path isn't set if the requestline was bad
            msg = self.requestline

        code = str(code)

        if code[0] == "1":  # 1xx - Informational
            msg = werkzeug.serving._ansi_style(msg, "bold")
        elif code == "200":  # 2xx - Success
            pass
        elif code == "304":  # 304 - Resource Not Modified
            msg = werkzeug.serving._ansi_style(msg, "cyan")
        elif code[0] == "3":  # 3xx - Redirection
            msg = werkzeug.serving._ansi_style(msg, "green")
        elif code == "404":  # 404 - Resource Not Found
            msg = werkzeug.serving._ansi_style(msg, "yellow")
        elif code[0] == "4":  # 4xx - Client Error
            msg = werkzeug.serving._ansi_style(msg, "bold", "red")
        else:  # 5xx, or any other response
            msg = werkzeug.serving._ansi_style(msg, "bold", "magenta")

        self.log("info", '"%s" %s %s', msg, code, size)


class RequestHandler(CommonRequestHandler):
    def setup(self):
        # timeout to avoid chrome headless preconnect during tests
        if config['test_enable']:
            self.timeout = 5
        # flag the current thread as handling a http request
        super(RequestHandler, self).setup()
        me = threading.current_thread()
        me.name = 'odoo.service.http.request.%s' % (me.ident,)

    def make_environ(self):
        environ = super().make_environ()
        # Add the TCP socket to environ in order for the websocket
        # connections to use it.
        environ['socket'] = self.connection
        if self.headers.get('Upgrade') == 'websocket':
            # Since the upgrade header is introduced in version 1.1, Firefox
            # won't accept a websocket connection if the version is set to
            # 1.0.
            self.protocol_version = "HTTP/1.1"
        return environ

    def send_header(self, keyword, value):
        # Prevent `WSGIRequestHandler` from sending the connection close header (compatibility with werkzeug >= 2.1.1 )
        # since it is incompatible with websocket.
        if self.headers.get('Upgrade') == 'websocket' and keyword == 'Connection' and value == 'close':
            # Do not keep processing requests.
            self.close_connection = True
            return
        super().send_header(keyword, value)

    def end_headers(self, *a, **kw):
        super().end_headers(*a, **kw)
        # At this point, Werkzeug assumes the connection is closed and will discard any incoming
        # data. In the case of WebSocket connections, data should not be discarded. Replace the
        # rfile/wfile of this handler to prevent any further action (compatibility with werkzeug >= 2.3.x).
        # See: https://github.com/pallets/werkzeug/blob/2.3.x/src/werkzeug/serving.py#L334
        if self.headers.get('Upgrade') == 'websocket':
            self.rfile = BytesIO()
            self.wfile = BytesIO()

    def log_error(self, format, *args):
        if format == "Request timed out: %r" and config['test_enable']:
            _logger.info(format, *args)
        else:
            super().log_error(format, *args)

class ThreadedWSGIServerReloadable(LoggingBaseWSGIServerMixIn, werkzeug.serving.ThreadedWSGIServer):
    """ werkzeug Threaded WSGI Server patched to allow reusing a listen socket
    given by the environment, this is used by autoreload to keep the listen
    socket open when a reload happens.
    """
    def __init__(self, host, port, app):
        # The ODOO_MAX_HTTP_THREADS environment variable allows to limit the amount of concurrent
        # socket connections accepted by a threaded server, implicitly limiting the amount of
        # concurrent threads running for http requests handling.
        self.max_http_threads = os.environ.get("ODOO_MAX_HTTP_THREADS")
        if self.max_http_threads:
            try:
                self.max_http_threads = int(self.max_http_threads)
            except ValueError:
                # If the value can't be parsed to an integer then it's computed in an automated way to
                # half the size of db_maxconn because while most requests won't borrow cursors concurrently
                # there are some exceptions where some controllers might allocate two or more cursors.
                self.max_http_threads = max((config['db_maxconn'] - config['max_cron_threads']) // 2, 1)
            self.http_threads_sem = threading.Semaphore(self.max_http_threads)
        super(ThreadedWSGIServerReloadable, self).__init__(host, port, app,
                                                           handler=RequestHandler)

        # See https://github.com/pallets/werkzeug/pull/770
        # This allow the request threads to not be set as daemon
        # so the server waits for them when shutting down gracefully.
        self.daemon_threads = False

    def server_bind(self):
        SD_LISTEN_FDS_START = 3
        if os.environ.get('LISTEN_FDS') == '1' and os.environ.get('LISTEN_PID') == str(os.getpid()):
            self.reload_socket = True
            self.socket = socket.fromfd(SD_LISTEN_FDS_START, socket.AF_INET, socket.SOCK_STREAM)
            _logger.info('HTTP service (werkzeug) running through socket activation')
        else:
            self.reload_socket = False
            super(ThreadedWSGIServerReloadable, self).server_bind()
            _logger.info('HTTP service (werkzeug) running on %s:%s', self.server_name, self.server_port)

    def server_activate(self):
        if not self.reload_socket:
            super(ThreadedWSGIServerReloadable, self).server_activate()

    def process_request(self, request, client_address):
        """
        Start a new thread to process the request.
        Override the default method of class socketserver.ThreadingMixIn
        to be able to get the thread object which is instantiated
        and set its start time as an attribute
        """
        t = threading.Thread(target = self.process_request_thread,
                             args = (request, client_address))
        t.daemon = self.daemon_threads
        t.type = 'http'
        t.start_time = time.time()
        t.start()

    def _handle_request_noblock(self):
        if self.max_http_threads and not self.http_threads_sem.acquire(timeout=0.1):
            # If the semaphore is full we will return immediately to the upstream (most probably
            # socketserver.BaseServer's serve_forever loop  which will retry immediately as the
            # selector will find a pending connection to accept on the socket. There is a 100 ms
            # penalty in such case in order to avoid cpu bound loop while waiting for the semaphore.
            return
        # upstream _handle_request_noblock will handle errors and call shutdown_request in any cases
        super(ThreadedWSGIServerReloadable, self)._handle_request_noblock()

    def shutdown_request(self, request):
        if self.max_http_threads:
            # upstream is supposed to call this function no matter what happens during processing
            self.http_threads_sem.release()
        super().shutdown_request(request)

#----------------------------------------------------------
# FileSystem Watcher for autoreload and cache invalidation
#----------------------------------------------------------
class FSWatcherBase(object):
    def handle_file(self, path):
        if path.endswith('.py') and not os.path.basename(path).startswith('.~'):
            try:
                source = open(path, 'rb').read() + b'\n'
                compile(source, path, 'exec')
            except IOError:
                _logger.error('autoreload: python code change detected, IOError for %s', path)
            except SyntaxError:
                _logger.error('autoreload: python code change detected, SyntaxError in %s', path)
            else:
                if not server_phoenix:
                    _logger.info('autoreload: python code updated, autoreload activated')
                    restart()
                    return True


class FSWatcherWatchdog(FSWatcherBase):
    def __init__(self):
        self.observer = Observer()
        import odoo.addons  # noqa: PLC0415
        for path in odoo.addons.__path__:
            _logger.info('Watching addons folder %s', path)
            self.observer.schedule(self, path, recursive=True)

    def dispatch(self, event):
        if isinstance(event, (FileCreatedEvent, FileModifiedEvent, FileMovedEvent)):
            if not event.is_directory:
                path = getattr(event, 'dest_path', '') or event.src_path
                self.handle_file(path)

    def start(self):
        self.observer.start()
        _logger.info('AutoReload watcher running with watchdog')

    def stop(self):
        self.observer.stop()
        self.observer.join()


class FSWatcherInotify(FSWatcherBase):
    def __init__(self):
        self.started = False
        # ignore warnings from inotify in case we have duplicate addons paths.
        inotify.adapters._LOGGER.setLevel(logging.ERROR)
        # recreate a list as InotifyTrees' __init__ deletes the list's items
        paths_to_watch = []
        import odoo.addons  # noqa: PLC0415
        for path in odoo.addons.__path__:
            paths_to_watch.append(path)
            _logger.info('Watching addons folder %s', path)
        self.watcher = InotifyTrees(paths_to_watch, mask=INOTIFY_LISTEN_EVENTS, block_duration_s=.5)

    def run(self):
        _logger.info('AutoReload watcher running with inotify')
        dir_creation_events = set(('IN_MOVED_TO', 'IN_CREATE'))
        while self.started:
            for event in self.watcher.event_gen(timeout_s=0, yield_nones=False):
                (_, type_names, path, filename) = event
                if 'IN_ISDIR' not in type_names:
                    # despite not having IN_DELETE in the watcher's mask, the
                    # watcher sends these events when a directory is deleted.
                    if 'IN_DELETE' not in type_names:
                        full_path = os.path.join(path, filename)
                        if self.handle_file(full_path):
                            return
                elif dir_creation_events.intersection(type_names):
                    full_path = os.path.join(path, filename)
                    for root, _, files in os.walk(full_path):
                        for file in files:
                            if self.handle_file(os.path.join(root, file)):
                                return

    def start(self):
        self.started = True
        self.thread = threading.Thread(target=self.run, name="odoo.service.autoreload.watcher")
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        self.started = False
        self.thread.join()
        del self.watcher  # ensures inotify watches are freed up before reexec


#----------------------------------------------------------
# Servers: Threaded, Gevented and Prefork
#----------------------------------------------------------

class CommonServer(object):
    _on_stop_funcs = []

    def __init__(self, app):
        self.app = app
        # config
        self.interface = config['http_interface'] or '0.0.0.0'
        self.port = config['http_port']
        # runtime
        self.pid = os.getpid()

    def close_socket(self, sock):
        """ Closes a socket instance cleanly
        :param sock: the network socket to close
        :type sock: socket.socket
        """
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except socket.error as e:
            if e.errno == errno.EBADF:
                # Werkzeug > 0.9.6 closes the socket itself (see commit
                # https://github.com/mitsuhiko/werkzeug/commit/4d8ca089)
                return
            # On OSX, socket shutdowns both sides if any side closes it
            # causing an error 57 'Socket is not connected' on shutdown
            # of the other side (or something), see
            # http://bugs.python.org/issue4397
            # note: stdlib fixed test, not behavior
            if e.errno != errno.ENOTCONN or platform.system() not in ['Darwin', 'Windows']:
                raise
        sock.close()

    @classmethod
    def on_stop(cls, func):
        """ Register a cleanup function to be executed when the server stops """
        cls._on_stop_funcs.append(func)

    def stop(self):
        for func in self._on_stop_funcs:
            try:
                _logger.debug("on_close call %s", func)
                func()
            except Exception:
                _logger.warning("Exception in %s", func.__name__, exc_info=True)


class ThreadedServer(CommonServer):
    def __init__(self, app):
        super(ThreadedServer, self).__init__(app)
        self.main_thread_id = threading.current_thread().ident
        # Variable keeping track of the number of calls to the signal handler defined
        # below. This variable is monitored by ``quit_on_signals()``.
        self.quit_signals_received = 0

        #self.socket = None
        self.httpd = None
        self.limits_reached_threads = set()
        self.limit_reached_time = None

    def signal_handler(self, sig, frame):
        if sig in [signal.SIGINT, signal.SIGTERM]:
            # shutdown on kill -INT or -TERM
            self.quit_signals_received += 1
            if self.quit_signals_received > 1:
                # logging.shutdown was already called at this point.
                sys.stderr.write("Forced shutdown.\n")
                os._exit(0)
            # interrupt run() to start shutdown
            raise KeyboardInterrupt()
        elif hasattr(signal, 'SIGXCPU') and sig == signal.SIGXCPU:
            sys.stderr.write("CPU time limit exceeded! Shutting down immediately\n")
            sys.stderr.flush()
            os._exit(0)
        elif sig == signal.SIGHUP:
            # restart on kill -HUP
            global server_phoenix  # noqa: PLW0603
            server_phoenix = True
            self.quit_signals_received += 1
            # interrupt run() to start shutdown
            raise KeyboardInterrupt()

    def process_limit(self):
        memory = memory_info(psutil.Process(os.getpid()))
        if config['limit_memory_soft'] and memory > config['limit_memory_soft']:
            _logger.warning('Server memory limit (%s) reached.', memory)
            self.limits_reached_threads.add(threading.current_thread())

        for thread in threading.enumerate():
            thread_type = getattr(thread, 'type', None)
            if not thread.daemon and thread_type != 'websocket' or thread_type == 'cron':
                # We apply the limits on cron threads and HTTP requests,
                # websocket requests excluded.
                if getattr(thread, 'start_time', None):
                    thread_execution_time = time.time() - thread.start_time
                    thread_limit_time_real = config['limit_time_real']
                    if (getattr(thread, 'type', None) == 'cron' and
                            config['limit_time_real_cron'] and config['limit_time_real_cron'] > 0):
                        thread_limit_time_real = config['limit_time_real_cron']
                    if thread_limit_time_real and thread_execution_time > thread_limit_time_real:
                        _logger.warning(
                            'Thread %s virtual real time limit (%d/%ds) reached.',
                            thread, thread_execution_time, thread_limit_time_real)
                        self.limits_reached_threads.add(thread)
        # Clean-up threads that are no longer alive
        # e.g. threads that exceeded their real time,
        # but which finished before the server could restart.
        for thread in list(self.limits_reached_threads):
            if not thread.is_alive():
                self.limits_reached_threads.remove(thread)
        if self.limits_reached_threads:
            self.limit_reached_time = self.limit_reached_time or time.time()
        else:
            self.limit_reached_time = None

    def cron_thread(self, number):
        # Steve Reich timing style with thundering herd mitigation.
        #
        # On startup, all workers bind on a notification channel in
        # postgres so they can be woken up at will. At worst they wake
        # up every SLEEP_INTERVAL with a jitter. The jitter creates a
        # chorus effect that helps distribute on the timeline the moment
        # when individual worker wake up.
        #
        # On NOTIFY, all workers are awaken at the same time, sleeping
        # just a bit prevents they all poll the database at the exact
        # same time. This is known as the thundering herd effect.

        from odoo.addons.base.models.ir_cron import IrCron  # noqa: PLC0415

        def _run_cron(cr):
            pg_conn = cr._cnx
            # LISTEN / NOTIFY doesn't work in recovery mode
            cr.execute("SELECT pg_is_in_recovery()")
            in_recovery = cr.fetchone()[0]
            if not in_recovery:
                cr.execute("LISTEN cron_trigger")
            else:
                _logger.warning("PG cluster in recovery mode, cron trigger not activated")
            cr.commit()
            check_all_time = 0.0  # last time that we listed databases, initialized far in the past
            all_db_names = []
            alive_time = time.monotonic()
            while config['limit_time_worker_cron'] <= 0 or (time.monotonic() - alive_time) <= config['limit_time_worker_cron']:
                select.select([pg_conn], [], [], SLEEP_INTERVAL + number)
                time.sleep(number / 100)
                try:
                    pg_conn.poll()
                except Exception:
                    if pg_conn.closed:
                        # connection closed, just exit the loop
                        return
                    raise
                notified = OrderedSet(
                    notif.payload
                    for notif in pg_conn.notifies
                    if notif.channel == 'cron_trigger'
                )
                pg_conn.notifies.clear()  # free resources

                if time.time() - SLEEP_INTERVAL > check_all_time:
                    # check all databases
                    # last time we checked them was `now - SLEEP_INTERVAL`
                    check_all_time = time.time()
                    # process notified databases first, then the other ones
                    all_db_names = OrderedSet(cron_database_list())
                    db_names = [
                        *(db for db in notified if db in all_db_names),
                        *(db for db in all_db_names if db not in notified),
                    ]
                else:
                    # restrict to notified databases only
                    db_names = notified.intersection(all_db_names)
                    if not db_names:
                        continue

                _logger.debug('cron%d polling for jobs (notified: %s)', number, notified)
                for db_name in db_names:
                    thread = threading.current_thread()
                    thread.start_time = time.time()
                    try:
                        IrCron._process_jobs(db_name)
                    except Exception:
                        _logger.warning('cron%d encountered an Exception:', number, exc_info=True)
                    thread.start_time = None

        while True:
            conn = sql_db.db_connect('postgres')
            with contextlib.closing(conn.cursor()) as cr:
                _run_cron(cr)
                cr._cnx.close()
            _logger.info('cron%d max age (%ss) reached, releasing connection.', number, config['limit_time_worker_cron'])

    def cron_spawn(self):
        """ Start the above runner function in a daemon thread.

        The thread is a typical daemon thread: it will never quit and must be
        terminated when the main process exits - with no consequence (the processing
        threads it spawns are not marked daemon).

        """
        for i in range(config['max_cron_threads']):
            t = threading.Thread(target=self.cron_thread, args=(i,), name=f"odoo.service.cron.cron{i}")
            t.daemon = True
            t.type = 'cron'
            t.start()
            _logger.debug("cron%d started!", i)

    def http_spawn(self):
        self.httpd = ThreadedWSGIServerReloadable(self.interface, self.port, self.app)
        threading.Thread(
            target=self.httpd.serve_forever,
            name="odoo.service.httpd",
            daemon=True,
        ).start()

    def start(self, stop=False):
        _logger.debug("Setting signal handlers")
        set_limit_memory_hard()
        if os.name == 'posix':
            signal.signal(signal.SIGINT, self.signal_handler)
            signal.signal(signal.SIGTERM, self.signal_handler)
            signal.signal(signal.SIGCHLD, self.signal_handler)
            signal.signal(signal.SIGHUP, self.signal_handler)
            signal.signal(signal.SIGXCPU, self.signal_handler)
            signal.signal(signal.SIGQUIT, dumpstacks)
            signal.signal(signal.SIGUSR1, log_ormcache_stats)
            signal.signal(signal.SIGUSR2, log_ormcache_stats)
        elif os.name == 'nt':
            import win32api
            win32api.SetConsoleCtrlHandler(lambda sig: self.signal_handler(sig, None), 1)

        if config['test_enable'] or (config['http_enable'] and not stop):
            # some tests need the http daemon to be available...
            self.http_spawn()

    def stop(self):
        """ Shutdown the WSGI server. Wait for non daemon threads.
        """
        if server_phoenix:
            _logger.info("Initiating server reload")
        else:
            _logger.info("Initiating shutdown")
            _logger.info("Hit CTRL-C again or send a second signal to force the shutdown.")

        stop_time = time.time()

        if self.httpd:
            self.httpd.shutdown()

        super().stop()

        # Manually join() all threads before calling sys.exit() to allow a second signal
        # to trigger _force_quit() in case some non-daemon threads won't exit cleanly.
        # threading.Thread.join() should not mask signals (at least in python 2.5).
        me = threading.current_thread()
        _logger.debug('current thread: %r', me)
        for thread in threading.enumerate():
            _logger.debug('process %r (%r)', thread, thread.daemon)
            if (thread != me and not thread.daemon and thread.ident != self.main_thread_id and
                    thread not in self.limits_reached_threads):
                while thread.is_alive() and (time.time() - stop_time) < 1:
                    # We wait for requests to finish, up to 1 second.
                    _logger.debug('join and sleep')
                    # Need a busyloop here as thread.join() masks signals
                    # and would prevent the forced shutdown.
                    thread.join(0.05)
                    time.sleep(0.05)

        sql_db.close_all()

        current_process = psutil.Process()
        children = current_process.children(recursive=False)
        for child in children:
            _logger.info('A child process was found, pid is %s, process may hang', child)

        _logger.debug('--')
        logging.shutdown()

    def run(self, preload=None, stop=False):
        """ Start the http server and the cron thread then wait for a signal.

        The first SIGINT or SIGTERM signal will initiate a graceful shutdown while
        a second one if any will force an immediate exit.
        """
        with Registry._lock:
            self.start(stop=stop)
            rc = preload_registries(preload)

        if stop:
            if config['test_enable']:
                from odoo.tests.result import _logger as logger  # noqa: PLC0415
                with Registry.registries._lock:
                    for db, registry in Registry.registries.items():
                        report = registry._assertion_report
                        log = logger.error if not report.wasSuccessful() \
                         else logger.warning if not report.testsRun \
                         else logger.info
                        log("%s when loading database %r", report, db)
            self.stop()
            return rc

        self.cron_spawn()

        # Wait for a first signal to be handled. (time.sleep will be interrupted
        # by the signal handler)
        try:
            while self.quit_signals_received == 0:
                self.process_limit()
                if self.limit_reached_time:
                    has_other_valid_requests = any(
                        not t.daemon and
                        t not in self.limits_reached_threads
                        for t in threading.enumerate()
                        if getattr(t, 'type', None) == 'http')
                    if (not has_other_valid_requests or
                            (time.time() - self.limit_reached_time) > SLEEP_INTERVAL):
                        # We wait there is no processing requests
                        # other than the ones exceeding the limits, up to 1 min,
                        # before asking for a reload.
                        _logger.info('Dumping stacktrace of limit exceeding threads before reloading')
                        dumpstacks(thread_idents=[thread.ident for thread in self.limits_reached_threads])
                        self.reload()
                        # `reload` increments `self.quit_signals_received`
                        # and the loop will end after this iteration,
                        # therefore leading to the server stop.
                        # `reload` also sets the `server_phoenix` flag
                        # to tell the server to restart the server after shutting down.
                    else:
                        time.sleep(1)
                else:
                    time.sleep(SLEEP_INTERVAL)
        except KeyboardInterrupt:
            pass

        self.stop()

    def reload(self):
        os.kill(self.pid, signal.SIGHUP)

class GeventServer(CommonServer):
    def __init__(self, app):
        super(GeventServer, self).__init__(app)
        self.port = config['gevent_port']
        self.httpd = None

    def process_limits(self):
        restart = False
        if self.ppid != os.getppid():
            _logger.warning("Gevent Parent changed: %s", self.pid)
            restart = True
        memory = memory_info(psutil.Process(self.pid))
        limit_memory_soft = config['limit_memory_soft_gevent'] or config['limit_memory_soft']
        if limit_memory_soft and memory > limit_memory_soft:
            _logger.warning('Gevent virtual memory limit reached: %s', memory)
            restart = True
        if restart:
            # suicide !!
            os.kill(self.pid, signal.SIGTERM)

    def watchdog(self, beat=4):
        import gevent
        self.ppid = os.getppid()
        while True:
            self.process_limits()
            gevent.sleep(beat)

    def start(self):
        import gevent
        try:
            from gevent.pywsgi import WSGIServer, WSGIHandler
        except ImportError:
            from gevent.wsgi import WSGIServer, WSGIHandler

        class ProxyHandler(WSGIHandler):
            """ When logging requests, try to get the client address from
            the environment so we get proxyfix's modifications (if any).

            Derived from werzeug.serving.WSGIRequestHandler.log
            / werzeug.serving.WSGIRequestHandler.address_string
            """
            def _connection_upgrade_requested(self):
                if self.headers.get('Connection', '').lower() == 'upgrade':
                    return True
                if self.headers.get('Upgrade', '').lower() == 'websocket':
                    return True
                return False

            def format_request(self):
                old_address = self.client_address
                if getattr(self, 'environ', None):
                    self.client_address = self.environ['REMOTE_ADDR']
                elif not self.client_address:
                    self.client_address = '<local>'
                # other cases are handled inside WSGIHandler
                try:
                    return super().format_request()
                finally:
                    self.client_address = old_address

            def finalize_headers(self):
                # We need to make gevent.pywsgi stop dealing with chunks when the connection
                # Is being upgraded. see https://github.com/gevent/gevent/issues/1712
                super().finalize_headers()
                if self.code == 101:
                    # Switching Protocols. Disable chunked writes.
                    self.response_use_chunked = False

            def get_environ(self):
                # Add the TCP socket to environ in order for the websocket
                # connections to use it.
                environ = super().get_environ()
                environ['socket'] = self.socket
                # Disable support for HTTP chunking on reads which cause
                # an issue when the connection is being upgraded, see
                # https://github.com/gevent/gevent/issues/1712
                if self._connection_upgrade_requested():
                    environ['wsgi.input'] = self.rfile
                    environ['wsgi.input_terminated'] = False
                return environ

        set_limit_memory_hard()
        if os.name == 'posix':
            # Set process memory limit as an extra safeguard
            signal.signal(signal.SIGQUIT, dumpstacks)
            signal.signal(signal.SIGUSR1, log_ormcache_stats)
            signal.signal(signal.SIGUSR2, log_ormcache_stats)
            gevent.spawn(self.watchdog)

        self.httpd = WSGIServer(
            (self.interface, self.port), self.app,
            log=logging.getLogger('longpolling'),
            error_log=logging.getLogger('longpolling'),
            handler_class=ProxyHandler,
        )
        _logger.info('Evented Service (longpolling) running on %s:%s', self.interface, self.port)
        try:
            self.httpd.serve_forever()
        except:
            _logger.exception("Evented Service (longpolling): uncaught error during main loop")
            raise

    def stop(self):
        import gevent
        self.httpd.stop()
        super().stop()
        gevent.shutdown()

    def run(self, preload, stop):
        self.start()
        self.stop()

class PreforkServer(CommonServer):
    """ Multiprocessing inspired by (g)unicorn.
    PreforkServer (aka Multicorn) currently uses accept(2) as dispatching
    method between workers but we plan to replace it by a more intelligent
    dispatcher to will parse the first HTTP request line.
    """
    def __init__(self, app):
        super().__init__(app)
        # config
        self.population = config['workers']
        self.timeout = config['limit_time_real']
        self.limit_request = config['limit_request']
        self.cron_timeout = config['limit_time_real_cron'] or None
        if self.cron_timeout == -1:
            self.cron_timeout = self.timeout
        # working vars
        self.beat = 4
        self.socket = None
        self.workers_http = {}
        self.workers_cron = {}
        self.workers = {}
        self.generation = 0
        self.queue = collections.deque()
        self.long_polling_pid = None

    def pipe_new(self):
        pipe = os.pipe()
        for fd in pipe:
            # non_blocking
            flags = fcntl.fcntl(fd, fcntl.F_GETFL) | os.O_NONBLOCK
            fcntl.fcntl(fd, fcntl.F_SETFL, flags)
            # close_on_exec
            flags = fcntl.fcntl(fd, fcntl.F_GETFD) | fcntl.FD_CLOEXEC
            fcntl.fcntl(fd, fcntl.F_SETFD, flags)
        return pipe

    def pipe_ping(self, pipe):
        try:
            os.write(pipe[1], b'.')
        except IOError as e:
            if e.errno not in [errno.EAGAIN, errno.EINTR]:
                raise

    def signal_handler(self, sig, frame):
        if len(self.queue) < 5 or sig == signal.SIGCHLD:
            self.queue.append(sig)
            self.pipe_ping(self.pipe)
        else:
            _logger.warning("Dropping signal: %s", sig)

    def worker_spawn(self, klass, workers_registry):
        self.generation += 1
        worker = klass(self)
        pid = os.fork()
        if pid != 0:
            worker.pid = pid
            self.workers[pid] = worker
            workers_registry[pid] = worker
            return worker
        else:
            worker.run()
            sys.exit(0)

    def long_polling_spawn(self):
        nargs = stripped_sys_argv()
        cmd = [sys.executable, sys.argv[0], 'gevent'] + nargs[1:]
        popen = subprocess.Popen(cmd)
        self.long_polling_pid = popen.pid

    def worker_pop(self, pid):
        if pid == self.long_polling_pid:
            self.long_polling_pid = None
        if pid in self.workers:
            _logger.debug("Worker (%s) unregistered", pid)
            try:
                self.workers_http.pop(pid, None)
                self.workers_cron.pop(pid, None)
                u = self.workers.pop(pid)
                u.close()
            except OSError:
                return

    def worker_kill(self, pid, sig):
        try:
            os.kill(pid, sig)
            if sig == signal.SIGKILL:
                self.worker_pop(pid)
        except OSError as e:
            if e.errno == errno.ESRCH:
                self.worker_pop(pid)

    def process_signals(self):
        while self.queue:
            sig = self.queue.popleft()
            if sig in [signal.SIGINT, signal.SIGTERM]:
                raise KeyboardInterrupt
            elif sig == signal.SIGHUP:
                # restart on kill -HUP
                global server_phoenix  # noqa: PLW0603
                server_phoenix = True
                raise KeyboardInterrupt
            elif sig == signal.SIGQUIT:
                # dump stacks on kill -3
                dumpstacks()
            elif sig in [signal.SIGUSR1, signal.SIGUSR2]:
                # log ormcache stats on kill -SIGUSR1 or kill -SIGUSR2
                log_ormcache_stats(sig)
            elif sig == signal.SIGTTIN:
                # increase number of workers
                self.population += 1
            elif sig == signal.SIGTTOU:
                # decrease number of workers
                self.population -= 1

    def process_zombie(self):
        # reap dead workers
        while 1:
            try:
                wpid, status = os.waitpid(-1, os.WNOHANG)
                if not wpid:
                    break
                if (status >> 8) == 3:
                    msg = "Critial worker error (%s)"
                    _logger.critical(msg, wpid)
                    raise Exception(msg % wpid)
                self.worker_pop(wpid)
            except OSError as e:
                if e.errno == errno.ECHILD:
                    break
                raise

    def process_timeout(self):
        now = time.time()
        for (pid, worker) in list(self.workers.items()):
            if worker.watchdog_timeout is not None and \
                    (now - worker.watchdog_time) >= worker.watchdog_timeout:
                _logger.error("%s (%s) timeout after %ss",
                              worker.__class__.__name__,
                              pid,
                              worker.watchdog_timeout)
                self.worker_kill(pid, signal.SIGKILL)

    def process_spawn(self):
        # Before spawning any process, check the registry signaling
        registries = Registry.registries.snapshot

        def check_registries():
            # check the registries on the first call only!
            if not registries:
                return
            for registry in registries.values():
                with registry.cursor() as cr:
                    registry.check_signaling(cr)
            registries.clear()
            # Close all opened cursors
            sql_db.close_all()

        if config['http_enable']:
            while len(self.workers_http) < self.population:
                check_registries()
                self.worker_spawn(WorkerHTTP, self.workers_http)
            if not self.long_polling_pid:
                check_registries()
                self.long_polling_spawn()
        while len(self.workers_cron) < config['max_cron_threads']:
            check_registries()
            self.worker_spawn(WorkerCron, self.workers_cron)

    def sleep(self):
        try:
            # map of fd -> worker
            fds = {w.watchdog_pipe[0]: w for w in self.workers.values()}
            fd_in = list(fds) + [self.pipe[0]]
            # check for ping or internal wakeups
            ready = select.select(fd_in, [], [], self.beat)
            # update worker watchdogs
            for fd in ready[0]:
                if fd in fds:
                    fds[fd].watchdog_time = time.time()
                empty_pipe(fd)
        except select.error as e:
            if e.args[0] not in [errno.EINTR]:
                raise

    def start(self):
        # wakeup pipe, python doesn't throw EINTR when a syscall is interrupted
        # by a signal simulating a pseudo SA_RESTART. We write to a pipe in the
        # signal handler to overcome this behaviour
        self.pipe = self.pipe_new()
        # set signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGHUP, self.signal_handler)
        signal.signal(signal.SIGCHLD, self.signal_handler)
        signal.signal(signal.SIGTTIN, self.signal_handler)
        signal.signal(signal.SIGTTOU, self.signal_handler)
        signal.signal(signal.SIGQUIT, dumpstacks)
        signal.signal(signal.SIGUSR1, log_ormcache_stats)
        signal.signal(signal.SIGUSR2, log_ormcache_stats)

        if config['http_enable']:
            if config.http_socket_activation:
                _logger.info('HTTP service (werkzeug) running through socket activation')
            else:
                _logger.info('HTTP service (werkzeug) running on %s:%s', self.interface, self.port)

            if os.environ.get('ODOO_HTTP_SOCKET_FD'):
                # reload
                self.socket = socket.socket(fileno=int(os.environ.pop('ODOO_HTTP_SOCKET_FD')))
            elif config.http_socket_activation:
                # socket activation
                SD_LISTEN_FDS_START = 3
                self.socket = socket.fromfd(SD_LISTEN_FDS_START, socket.AF_INET, socket.SOCK_STREAM)
            else:
                # default
                family = socket.AF_INET
                if ':' in self.interface:
                    family = socket.AF_INET6
                self.socket = socket.socket(family, socket.SOCK_STREAM)
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.socket.setblocking(0)
                self.socket.bind((self.interface, self.port))
                self.socket.listen(8 * self.population)

    def fork_and_reload(self):
        _logger.info("Reloading server")
        pid = os.fork()
        if pid != 0:
            # keep the http listening socket open during _reexec() to ensure uptime
            http_socket_fileno = self.socket.fileno()
            flags = fcntl.fcntl(http_socket_fileno, fcntl.F_GETFD)
            fcntl.fcntl(http_socket_fileno, fcntl.F_SETFD, flags & ~fcntl.FD_CLOEXEC)
            os.environ['ODOO_HTTP_SOCKET_FD'] = str(http_socket_fileno)
            os.environ['ODOO_READY_SIGHUP_PID'] = str(pid)
            _reexec()  # stops execution

        # child process handles old server shutdown
        _logger.info("Waiting for new server to start ...")
        phoenix_hatched = False

        def sighup_handler(sig, frame):
            nonlocal phoenix_hatched
            phoenix_hatched = True

        signal.signal(signal.SIGHUP, sighup_handler)

        reload_timeout = time.monotonic() + 60
        while not phoenix_hatched and time.monotonic() < reload_timeout:
            time.sleep(0.1)

        if not phoenix_hatched:
            _logger.error("Server reload timed out (check the updated code)")
        else:
            _logger.info("New server has started")

    def stop_workers_gracefully(self):
        _logger.info("Stopping workers gracefully")

        if self.long_polling_pid is not None:
            # FIXME make longpolling process handle SIGTERM correctly
            self.worker_kill(self.long_polling_pid, signal.SIGKILL)
            self.long_polling_pid = None

        # Signal workers to finish their current workload then stop
        for pid in self.workers:
            self.worker_kill(pid, signal.SIGINT)

        is_main_server = self.pid == os.getpid()  # False if server reload, cannot reap children -> use psutil
        if not is_main_server:
            processes = {}
            for pid in self.workers:
                with contextlib.suppress(psutil.NoSuchProcess):
                    processes[pid] = psutil.Process(pid)

        self.beat = 0.1
        while self.workers:
            try:
                self.process_signals()
            except KeyboardInterrupt:
                _logger.info("Forced shutdown.")
                break

            if is_main_server:
                self.process_zombie()
            else:
                for pid, proc in list(processes.items()):
                    if not proc.is_running():
                        self.worker_pop(pid)
                        processes.pop(pid)

            self.sleep()
            self.process_timeout()

    def stop(self, graceful=True):
        global server_phoenix  # noqa: PLW0603
        if server_phoenix:
            # PreforkServer reloads gracefully, disable outdated mechanism
            server_phoenix = False

            self.fork_and_reload()
            self.stop_workers_gracefully()

            _logger.info("Old server stopped")
            return

        if self.socket:
            self.socket.close()
        if graceful:
            super().stop()
            self.stop_workers_gracefully()
        else:
            _logger.info("Stopping forcefully")
        for pid in list(self.workers):
            self.worker_kill(pid, signal.SIGTERM)

    def run(self, preload, stop):
        self.start()

        rc = preload_registries(preload)

        if stop:
            self.stop()
            return rc

        # Empty the cursor pool, we dont want them to be shared among forked workers.
        sql_db.close_all()

        if os.environ.get('ODOO_READY_SIGHUP_PID'):
            os.kill(int(os.environ.pop('ODOO_READY_SIGHUP_PID')), signal.SIGHUP)

        _logger.debug("Multiprocess starting")
        while 1:
            try:
                #_logger.debug("Multiprocess beat (%s)",time.time())
                self.process_signals()
                self.process_zombie()
                self.process_timeout()
                self.process_spawn()
                self.sleep()
            except KeyboardInterrupt:
                _logger.debug("Multiprocess clean stop")
                self.stop()
                break
            except Exception as e:
                _logger.exception(e)
                self.stop(False)
                return -1

class Worker(object):
    """ Workers """
    def __init__(self, multi):
        self.multi = multi
        self.watchdog_time = time.time()
        self.watchdog_pipe = multi.pipe_new()
        self.eintr_pipe = multi.pipe_new()
        self.wakeup_fd_r, self.wakeup_fd_w = self.eintr_pipe
        # Can be set to None if no watchdog is desired.
        self.watchdog_timeout = multi.timeout
        self.ppid = os.getpid()
        self.pid = None
        self.alive = True
        # should we rename into lifetime ?
        self.request_max = multi.limit_request
        self.request_count = 0

    def setproctitle(self, title=""):
        setproctitle('odoo: %s %s %s' % (self.__class__.__name__, self.pid, title))

    def close(self):
        os.close(self.watchdog_pipe[0])
        os.close(self.watchdog_pipe[1])
        os.close(self.eintr_pipe[0])
        os.close(self.eintr_pipe[1])

    def signal_handler(self, sig, frame):
        self.alive = False

    def signal_time_expired_handler(self, n, stack):
        # TODO: print actual RUSAGE_SELF (since last check_limits) instead of
        #       just repeating the config setting
        _logger.info('Worker (%d) CPU time limit (%s) reached.', self.pid, config['limit_time_cpu'])
        # We dont suicide in such case
        raise Exception('CPU time limit exceeded.')

    def sleep(self):
        try:
            select.select([self.multi.socket, self.wakeup_fd_r], [], [], self.multi.beat)
            # clear wakeup pipe if we were interrupted
            empty_pipe(self.wakeup_fd_r)
        except select.error as e:
            if e.args[0] not in [errno.EINTR]:
                raise

    def check_limits(self):
        # If our parent changed suicide
        if self.ppid != os.getppid():
            _logger.info("Worker (%s) Parent changed", self.pid)
            self.alive = False
        # check for lifetime
        if self.request_count >= self.request_max:
            _logger.info("Worker (%d) max request (%s) reached.", self.pid, self.request_count)
            self.alive = False
        # Reset the worker if it consumes too much memory (e.g. caused by a memory leak).
        memory = memory_info(psutil.Process(os.getpid()))
        if config['limit_memory_soft'] and memory > config['limit_memory_soft']:
            _logger.info('Worker (%d) virtual memory limit (%s) reached.', self.pid, memory)
            self.alive = False      # Commit suicide after the request.

        set_limit_memory_hard()

        # update RLIMIT_CPU so limit_time_cpu applies per unit of work
        r = resource.getrusage(resource.RUSAGE_SELF)
        cpu_time = r.ru_utime + r.ru_stime
        soft, hard = resource.getrlimit(resource.RLIMIT_CPU)
        resource.setrlimit(resource.RLIMIT_CPU, (int(cpu_time + config['limit_time_cpu']), hard))

    def process_work(self):
        pass

    def start(self):
        self.pid = os.getpid()
        self.setproctitle()
        _logger.info("Worker %s (%s) alive", self.__class__.__name__, self.pid)
        # Reseed the random number generator
        random.seed()
        if self.multi.socket:
            # Prevent fd inheritance: close_on_exec
            flags = fcntl.fcntl(self.multi.socket, fcntl.F_GETFD) | fcntl.FD_CLOEXEC
            fcntl.fcntl(self.multi.socket, fcntl.F_SETFD, flags)
            # reset blocking status
            self.multi.socket.setblocking(0)

        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGXCPU, self.signal_time_expired_handler)

        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        signal.signal(signal.SIGHUP, signal.SIG_DFL)
        signal.signal(signal.SIGCHLD, signal.SIG_DFL)
        signal.signal(signal.SIGTTIN, signal.SIG_DFL)
        signal.signal(signal.SIGTTOU, signal.SIG_DFL)

        signal.set_wakeup_fd(self.wakeup_fd_w)

    def stop(self):
        pass

    def run(self):
        try:
            self.start()
            t = threading.Thread(name="Worker %s (%s) workthread" % (self.__class__.__name__, self.pid), target=self._runloop)
            t.daemon = True
            t.start()
            t.join()
            _logger.info("Worker (%s) exiting. request_count: %s, registry count: %s.",
                         self.pid, self.request_count,
                         len(Registry.registries))
            self.stop()
        except Exception:
            _logger.exception("Worker (%s) Exception occurred, exiting...", self.pid)
            # should we use 3 to abort everything ?
            sys.exit(1)

    def _runloop(self):
        signal.pthread_sigmask(signal.SIG_BLOCK, {
            signal.SIGXCPU,
            signal.SIGINT, signal.SIGQUIT,
            signal.SIGUSR1, signal.SIGUSR2,
        })
        try:
            while self.alive:
                self.check_limits()
                self.multi.pipe_ping(self.watchdog_pipe)
                self.sleep()
                if not self.alive:
                    break
                self.process_work()
        except:
            _logger.exception("Worker %s (%s) Exception occurred, exiting...", self.__class__.__name__, self.pid)
            sys.exit(1)

class WorkerHTTP(Worker):
    """ HTTP Request workers """
    def __init__(self, multi):
        super(WorkerHTTP, self).__init__(multi)

        # The ODOO_HTTP_SOCKET_TIMEOUT environment variable allows to control socket timeout for
        # extreme latency situations. It's generally better to use a good buffering reverse proxy
        # to quickly free workers rather than increasing this timeout to accommodate high network
        # latencies & b/w saturation. This timeout is also essential to protect against accidental
        # DoS due to idle HTTP connections.
        sock_timeout = os.environ.get("ODOO_HTTP_SOCKET_TIMEOUT")
        self.sock_timeout = float(sock_timeout) if sock_timeout else 2

    def process_request(self, client, addr):
        client.setblocking(1)
        client.settimeout(self.sock_timeout)
        client.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        # Prevent fd inherientence close_on_exec
        flags = fcntl.fcntl(client, fcntl.F_GETFD) | fcntl.FD_CLOEXEC
        fcntl.fcntl(client, fcntl.F_SETFD, flags)
        # do request using BaseWSGIServerNoBind monkey patched with socket
        self.server.socket = client
        # tolerate broken pipe when the http client closes the socket before
        # receiving the full reply
        try:
            self.server.process_request(client, addr)
        except IOError as e:
            if e.errno != errno.EPIPE:
                raise
        self.request_count += 1

    def process_work(self):
        try:
            client, addr = self.multi.socket.accept()
            self.process_request(client, addr)
        except socket.error as e:
            if e.errno not in (errno.EAGAIN, errno.ECONNABORTED):
                raise

    def start(self):
        Worker.start(self)
        self.server = BaseWSGIServerNoBind(self.multi.app)

class WorkerCron(Worker):
    """ Cron workers """

    def __init__(self, multi):
        super(WorkerCron, self).__init__(multi)
        self.alive_time = time.monotonic()
        self.watchdog_timeout = multi.cron_timeout  # Use a distinct value for CRON Worker
        # process_work() below process a single database per call.
        # self.db_queue keeps track of the databases to process (in order, from left to right).
        self.db_queue: deque[str] = deque()
        self.db_count: int = 0

    def sleep(self):
        # Really sleep once all the databases have been processed.
        if not self.db_queue:
            interval = SLEEP_INTERVAL + self.pid % 10   # chorus effect

            # simulate interruptible sleep with select(wakeup_fd, timeout)
            try:
                select.select([self.wakeup_fd_r, self.dbcursor._cnx], [], [], interval)
                # clear pg_conn/wakeup pipe if we were interrupted
                time.sleep(self.pid / 100 % .1)
                self.dbcursor._cnx.poll()
                empty_pipe(self.wakeup_fd_r)
            except select.error as e:
                if e.args[0] != errno.EINTR:
                    raise

    def check_limits(self):
        super().check_limits()

        if config['limit_time_worker_cron'] > 0 and (time.monotonic() - self.alive_time) > config['limit_time_worker_cron']:
            _logger.info('WorkerCron (%s) max age (%ss) reached.', self.pid, config['limit_time_worker_cron'])
            self.alive = False

    def process_work(self):
        """Process a single database."""
        _logger.debug("WorkerCron (%s) polling for jobs", self.pid)

        if not self.db_queue:
            # list databases
            db_names = OrderedSet(cron_database_list())
            pg_conn = self.dbcursor._cnx
            notified = OrderedSet(
                notif.payload
                for notif in pg_conn.notifies
                if notif.channel == 'cron_trigger'
            )
            pg_conn.notifies.clear()  # free resources
            # add notified databases (in order) first in the queue
            self.db_queue.extend(db for db in notified if db in db_names)
            self.db_queue.extend(db for db in db_names if db not in notified)
            self.db_count = len(self.db_queue)
            if not self.db_count:
                return

        # pop the leftmost element (because notified databases appear first)
        db_name = self.db_queue.popleft()
        self.setproctitle(db_name)

        from odoo.addons.base.models.ir_cron import IrCron  # noqa: PLC0415
        IrCron._process_jobs(db_name)

        # dont keep cursors in multi database mode
        if self.db_count > 1:
            sql_db.close_db(db_name)

        self.request_count += 1
        if self.request_count >= self.request_max and self.request_max < self.db_count:
            _logger.error(
                "There are more dabatases to process than allowed "
                "by the `limit_request` configuration variable: %s more.",
                self.db_count - self.request_max,
            )

    def start(self):
        os.nice(10)     # mommy always told me to be nice with others...
        Worker.start(self)
        if self.multi.socket:
            self.multi.socket.close()

        dbconn = sql_db.db_connect('postgres')
        self.dbcursor = dbconn.cursor()
        # LISTEN / NOTIFY doesn't work in recovery mode
        self.dbcursor.execute("SELECT pg_is_in_recovery()")
        in_recovery = self.dbcursor.fetchone()[0]
        if not in_recovery:
            self.dbcursor.execute("LISTEN cron_trigger")
        else:
            _logger.warning("PG cluster in recovery mode, cron trigger not activated")
        self.dbcursor.commit()

    def stop(self):
        super().stop()
        self.dbcursor._cnx.close()
        self.dbcursor.close()

#----------------------------------------------------------
# start/stop public api
#----------------------------------------------------------

server = None
server_phoenix = False


def load_server_wide_modules():
    from odoo.modules.module import load_openerp_module  # noqa: PLC0415
    with gc.disabling_gc():
        for m in config['server_wide_modules']:
            try:
                load_openerp_module(m)
            except Exception:
                msg = ''
                if m == 'web':
                    msg = """
    The `web` module is provided by the addons found in the `openerp-web` project.
    Maybe you forgot to add those addons in your addons_path configuration."""
                _logger.exception('Failed to load server-wide module `%s`.%s', m, msg)


def _reexec(updated_modules=None):
    """reexecute openerp-server process with (nearly) the same arguments"""
    if osutil.is_running_as_nt_service():
        subprocess.call('net stop {0} && net start {0}'.format(nt_service_name), shell=True)
    exe = os.path.basename(sys.executable)
    args = stripped_sys_argv()
    if updated_modules:
        args += ["-u", ','.join(updated_modules)]
    if not args or args[0] != exe:
        args.insert(0, exe)
    # We should keep the LISTEN_* environment variabled in order to support socket activation on reexec
    os.execve(sys.executable, args, os.environ)


def preload_registries(dbnames):
    """ Preload a registries, possibly run a test file."""
    # TODO: move all config checks to args dont check tools.config here
    dbnames = dbnames or []
    rc = 0

    preload_profiler = contextlib.nullcontext()

    for dbname in dbnames:
        if os.environ.get('ODOO_PROFILE_PRELOAD'):
            interval = float(os.environ.get('ODOO_PROFILE_PRELOAD_INTERVAL', '0.1'))
            collectors = [profiler.PeriodicCollector(interval=interval)]
            if os.environ.get('ODOO_PROFILE_PRELOAD_SQL'):
                collectors.append('sql')
            preload_profiler = profiler.Profiler(db=dbname, collectors=collectors)
        try:
            with preload_profiler:
                threading.current_thread().dbname = dbname
                update_module = config['init'] or config['update'] or config['reinit']

                registry = Registry.new(dbname, update_module=update_module, install_modules=config['init'], upgrade_modules=config['update'], reinit_modules=config['reinit'])

                # run post-install tests
                if config['test_enable']:
                    from odoo.tests import loader  # noqa: PLC0415
                    t0 = time.time()
                    t0_sql = sql_db.sql_counter
                    module_names = (registry.updated_modules if update_module else
                                    sorted(registry._init_modules))
                    _logger.info("Starting post tests")
                    tests_before = registry._assertion_report.testsRun
                    post_install_suite = loader.make_suite(module_names, 'post_install')
                    if post_install_suite.has_http_case():
                        with registry.cursor() as cr:
                            env = api.Environment(cr, api.SUPERUSER_ID, {})
                            env['ir.qweb']._pregenerate_assets_bundles()
                    result = loader.run_suite(post_install_suite, global_report=registry._assertion_report)
                    registry._assertion_report.update(result)
                    _logger.info("%d post-tests in %.2fs, %s queries",
                                registry._assertion_report.testsRun - tests_before,
                                time.time() - t0,
                                sql_db.sql_counter - t0_sql)

                    registry._assertion_report.log_stats()
                if registry._assertion_report and not registry._assertion_report.wasSuccessful():
                    rc += 1
        except Exception:
            _logger.critical('Failed to initialize database `%s`.', dbname, exc_info=True)
            return -1
    return rc

def start(preload=None, stop=False):
    """ Start the odoo http server and cron processor.
    """
    global server

    load_server_wide_modules()
    import odoo.http  # noqa: PLC0415

    if odoo.evented:
        server = GeventServer(odoo.http.root)
    elif config['workers']:
        if config['test_enable']:
            _logger.warning("Unit testing in workers mode could fail; use --workers 0.")

        server = PreforkServer(odoo.http.root)
    else:
        if platform.system() == "Linux" and sys.maxsize > 2**32 and "MALLOC_ARENA_MAX" not in os.environ:
            # glibc's malloc() uses arenas [1] in order to efficiently handle memory allocation of multi-threaded
            # applications. This allows better memory allocation handling in case of multiple threads that
            # would be using malloc() concurrently [2].
            # Due to the python's GIL, this optimization have no effect on multithreaded python programs.
            # Unfortunately, a downside of creating one arena per cpu core is the increase of virtual memory
            # which Odoo is based upon in order to limit the memory usage for threaded workers.
            # On 32bit systems the default size of an arena is 512K while on 64bit systems it's 64M [3],
            # hence a threaded worker will quickly reach it's default memory soft limit upon concurrent requests.
            # We therefore set the maximum arenas allowed to 2 unless the MALLOC_ARENA_MAX env variable is set.
            # Note: Setting MALLOC_ARENA_MAX=0 allow to explicitly set the default glibs's malloc() behaviour.
            #
            # [1] https://sourceware.org/glibc/wiki/MallocInternals#Arenas_and_Heaps
            # [2] https://www.gnu.org/software/libc/manual/html_node/The-GNU-Allocator.html
            # [3] https://sourceware.org/git/?p=glibc.git;a=blob;f=malloc/malloc.c;h=00ce48c;hb=0a8262a#l862
            try:
                import ctypes
                libc = ctypes.CDLL("libc.so.6")
                M_ARENA_MAX = -8
                assert libc.mallopt(ctypes.c_int(M_ARENA_MAX), ctypes.c_int(2))
            except Exception:
                _logger.warning("Could not set ARENA_MAX through mallopt()")
        server = ThreadedServer(odoo.http.root)

    watcher = None
    if 'reload' in config['dev_mode'] and not odoo.evented:
        if inotify:
            watcher = FSWatcherInotify()
            watcher.start()
        elif watchdog:
            watcher = FSWatcherWatchdog()
            watcher.start()
        else:
            if os.name == 'posix' and platform.system() != 'Darwin':
                module = 'inotify'
            else:
                module = 'watchdog'
            _logger.warning("'%s' module not installed. Code autoreload feature is disabled", module)

    rc = server.run(preload, stop)

    if watcher:
        watcher.stop()
    # like the legend of the phoenix, all ends with beginnings
    if server_phoenix:
        _reexec()

    return rc if rc else 0

def restart():
    """ Restart the server
    """
    if os.name == 'nt':
        # run in a thread to let the current thread return response to the caller.
        threading.Thread(target=_reexec).start()
    else:
        os.kill(server.pid, signal.SIGHUP)
