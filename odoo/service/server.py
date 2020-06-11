#-----------------------------------------------------------
# Threaded, Gevent and Prefork Servers
#-----------------------------------------------------------
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
import unittest

import psutil
import werkzeug.serving
from werkzeug.debug import DebuggedApplication

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

import odoo
from odoo.modules import get_modules
from odoo.modules.module import run_unit_tests, get_test_modules
from odoo.modules.registry import Registry
from odoo.release import nt_service_name
from odoo.tools import config
from odoo.tools import stripped_sys_argv, dumpstacks, log_ormcache_stats

_logger = logging.getLogger(__name__)

SLEEP_INTERVAL = 60     # 1 min

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
    if os.name == 'posix' and config['limit_memory_hard']:
        rlimit = resource.RLIMIT_RSS if platform.system() == 'Darwin' else resource.RLIMIT_AS
        soft, hard = resource.getrlimit(rlimit)
        resource.setrlimit(rlimit, (config['limit_memory_hard'], hard))

def empty_pipe(fd):
    try:
        while os.read(fd, 1):
            pass
    except OSError as e:
        if e.errno not in [errno.EAGAIN]:
            raise

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
        werkzeug.serving.BaseWSGIServer.__init__(self, "127.0.0.1", 0, app)
        # Directly close the socket. It will be replaced by WorkerHTTP when processing requests
        if self.socket:
            self.socket.close()

    def server_activate(self):
        # dont listen as we use PreforkServer#socket
        pass


class RequestHandler(werkzeug.serving.WSGIRequestHandler):
    def setup(self):
        # timeout to avoid chrome headless preconnect during tests
        if config['test_enable'] or config['test_file']:
            self.timeout = 5
        # flag the current thread as handling a http request
        super(RequestHandler, self).setup()
        me = threading.currentThread()
        me.name = 'odoo.service.http.request.%s' % (me.ident,)


class ThreadedWSGIServerReloadable(LoggingBaseWSGIServerMixIn, werkzeug.serving.ThreadedWSGIServer):
    """ werkzeug Threaded WSGI Server patched to allow reusing a listen socket
    given by the environement, this is used by autoreload to keep the listen
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
                self.max_http_threads = config['db_maxconn'] // 2
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

    # TODO: Remove this method as soon as either of the revision
    # - python/cpython@8b1f52b5a93403acd7d112cd1c1bc716b31a418a for Python 3.6,
    # - python/cpython@908082451382b8b3ba09ebba638db660edbf5d8e for Python 3.7,
    # is included in all Python 3 releases installed on all operating systems supported by Odoo.
    # These revisions are included in Python from releases 3.6.8 and Python 3.7.2 respectively.
    def _handle_request_noblock(self):
        """
        In the python module `socketserver` `process_request` loop,
        the __shutdown_request flag is not checked between select and accept.
        Thus when we set it to `True` thanks to the call `httpd.shutdown`,
        a last request is accepted before exiting the loop.
        We override this function to add an additional check before the accept().
        """
        if self._BaseServer__shutdown_request:
            return
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
                if not getattr(odoo, 'phoenix', False):
                    _logger.info('autoreload: python code updated, autoreload activated')
                    restart()
                    return True


class FSWatcherWatchdog(FSWatcherBase):
    def __init__(self):
        self.observer = Observer()
        for path in odoo.addons.__path__:
            _logger.info('Watching addons folder %s', path)
            self.observer.schedule(self, path, recursive=True)

    def dispatch(self, event):
        if isinstance(event, (FileCreatedEvent, FileModifiedEvent, FileMovedEvent)):
            if not event.is_directory:
                path = getattr(event, 'dest_path', event.src_path)
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
        self.thread.setDaemon(True)
        self.thread.start()

    def stop(self):
        self.started = False
        self.thread.join()


#----------------------------------------------------------
# Servers: Threaded, Gevented and Prefork
#----------------------------------------------------------

class CommonServer(object):
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

class ThreadedServer(CommonServer):
    def __init__(self, app):
        super(ThreadedServer, self).__init__(app)
        self.main_thread_id = threading.currentThread().ident
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
            odoo.phoenix = True
            self.quit_signals_received += 1
            # interrupt run() to start shutdown
            raise KeyboardInterrupt()

    def process_limit(self):
        memory = memory_info(psutil.Process(os.getpid()))
        if config['limit_memory_soft'] and memory > config['limit_memory_soft']:
            _logger.warning('Server memory limit (%s) reached.', memory)
            self.limits_reached_threads.add(threading.currentThread())

        for thread in threading.enumerate():
            if not thread.daemon or getattr(thread, 'type', None) == 'cron':
                # We apply the limits on cron threads and HTTP requests,
                # longpolling requests excluded.
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
            if not thread.isAlive():
                self.limits_reached_threads.remove(thread)
        if self.limits_reached_threads:
            self.limit_reached_time = self.limit_reached_time or time.time()
        else:
            self.limit_reached_time = None

    def cron_thread(self, number):
        from odoo.addons.base.models.ir_cron import ir_cron
        while True:
            time.sleep(SLEEP_INTERVAL + number)     # Steve Reich timing style
            registries = odoo.modules.registry.Registry.registries
            _logger.debug('cron%d polling for jobs', number)
            for db_name, registry in registries.items():
                if registry.ready:
                    thread = threading.currentThread()
                    thread.start_time = time.time()
                    try:
                        ir_cron._acquire_job(db_name)
                    except Exception:
                        _logger.warning('cron%d encountered an Exception:', number, exc_info=True)
                    thread.start_time = None

    def cron_spawn(self):
        """ Start the above runner function in a daemon thread.

        The thread is a typical daemon thread: it will never quit and must be
        terminated when the main process exits - with no consequence (the processing
        threads it spawns are not marked daemon).

        """
        # Force call to strptime just before starting the cron thread
        # to prevent time.strptime AttributeError within the thread.
        # See: http://bugs.python.org/issue7980
        datetime.datetime.strptime('2012-01-01', '%Y-%m-%d')
        for i in range(odoo.tools.config['max_cron_threads']):
            def target():
                self.cron_thread(i)
            t = threading.Thread(target=target, name="odoo.service.cron.cron%d" % i)
            t.setDaemon(True)
            t.type = 'cron'
            t.start()
            _logger.debug("cron%d started!" % i)

    def http_thread(self):
        def app(e, s):
            return self.app(e, s)
        self.httpd = ThreadedWSGIServerReloadable(self.interface, self.port, app)
        self.httpd.serve_forever()

    def http_spawn(self):
        t = threading.Thread(target=self.http_thread, name="odoo.service.httpd")
        t.setDaemon(True)
        t.start()

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
        elif os.name == 'nt':
            import win32api
            win32api.SetConsoleCtrlHandler(lambda sig: self.signal_handler(sig, None), 1)

        test_mode = config['test_enable'] or config['test_file']
        if test_mode or (config['http_enable'] and not stop):
            # some tests need the http deamon to be available...
            self.http_spawn()

    def stop(self):
        """ Shutdown the WSGI server. Wait for non deamon threads.
        """
        if getattr(odoo, 'phoenix', None):
            _logger.info("Initiating server reload")
        else:
            _logger.info("Initiating shutdown")
            _logger.info("Hit CTRL-C again or send a second signal to force the shutdown.")

        stop_time = time.time()

        if self.httpd:
            self.httpd.shutdown()

        # Manually join() all threads before calling sys.exit() to allow a second signal
        # to trigger _force_quit() in case some non-daemon threads won't exit cleanly.
        # threading.Thread.join() should not mask signals (at least in python 2.5).
        me = threading.currentThread()
        _logger.debug('current thread: %r', me)
        for thread in threading.enumerate():
            _logger.debug('process %r (%r)', thread, thread.isDaemon())
            if (thread != me and not thread.isDaemon() and thread.ident != self.main_thread_id and
                    thread not in self.limits_reached_threads):
                while thread.isAlive() and (time.time() - stop_time) < 1:
                    # We wait for requests to finish, up to 1 second.
                    _logger.debug('join and sleep')
                    # Need a busyloop here as thread.join() masks signals
                    # and would prevent the forced shutdown.
                    thread.join(0.05)
                    time.sleep(0.05)

        _logger.debug('--')
        logging.shutdown()

    def run(self, preload=None, stop=False):
        """ Start the http server and the cron thread then wait for a signal.

        The first SIGINT or SIGTERM signal will initiate a graceful shutdown while
        a second one if any will force an immediate exit.
        """
        self.start(stop=stop)

        rc = preload_registries(preload)

        if stop:
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
                        # `reload` also sets the `phoenix` flag
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
        self.port = config['longpolling_port']
        self.httpd = None

    def process_limits(self):
        restart = False
        if self.ppid != os.getppid():
            _logger.warning("LongPolling Parent changed", self.pid)
            restart = True
        memory = memory_info(psutil.Process(self.pid))
        if config['limit_memory_soft'] and memory > config['limit_memory_soft']:
            _logger.warning('LongPolling virtual memory limit reached: %s', memory)
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

        set_limit_memory_hard()
        if os.name == 'posix':
            # Set process memory limit as an extra safeguard
            signal.signal(signal.SIGQUIT, dumpstacks)
            signal.signal(signal.SIGUSR1, log_ormcache_stats)
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
        # config
        self.address = config['http_enable'] and \
            (config['http_interface'] or '0.0.0.0', config['http_port'])
        self.population = config['workers']
        self.timeout = config['limit_time_real']
        self.limit_request = config['limit_request']
        self.cron_timeout = config['limit_time_real_cron'] or None
        if self.cron_timeout == -1:
            self.cron_timeout = self.timeout
        # working vars
        self.beat = 4
        self.app = app
        self.pid = os.getpid()
        self.socket = None
        self.workers_http = {}
        self.workers_cron = {}
        self.workers = {}
        self.generation = 0
        self.queue = []
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
            _logger.warn("Dropping signal: %s", sig)

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
        except OSError as e:
            if e.errno == errno.ESRCH:
                self.worker_pop(pid)

    def process_signals(self):
        while len(self.queue):
            sig = self.queue.pop(0)
            if sig in [signal.SIGINT, signal.SIGTERM]:
                raise KeyboardInterrupt
            elif sig == signal.SIGHUP:
                # restart on kill -HUP
                odoo.phoenix = True
                raise KeyboardInterrupt
            elif sig == signal.SIGQUIT:
                # dump stacks on kill -3
                dumpstacks()
            elif sig == signal.SIGUSR1:
                # log ormcache stats on kill -SIGUSR1
                log_ormcache_stats()
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
        for (pid, worker) in self.workers.items():
            if worker.watchdog_timeout is not None and \
                    (now - worker.watchdog_time) >= worker.watchdog_timeout:
                _logger.error("%s (%s) timeout after %ss",
                              worker.__class__.__name__,
                              pid,
                              worker.watchdog_timeout)
                self.worker_kill(pid, signal.SIGKILL)

    def process_spawn(self):
        if config['http_enable']:
            while len(self.workers_http) < self.population:
                self.worker_spawn(WorkerHTTP, self.workers_http)
            if not self.long_polling_pid:
                self.long_polling_spawn()
        while len(self.workers_cron) < config['max_cron_threads']:
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
        # wakeup pipe, python doesnt throw EINTR when a syscall is interrupted
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

        if self.address:
            # listen to socket
            _logger.info('HTTP service (werkzeug) running on %s:%s', *self.address)
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.setblocking(0)
            self.socket.bind(self.address)
            self.socket.listen(8 * self.population)

    def stop(self, graceful=True):
        if self.long_polling_pid is not None:
            # FIXME make longpolling process handle SIGTERM correctly
            self.worker_kill(self.long_polling_pid, signal.SIGKILL)
            self.long_polling_pid = None
        if graceful:
            _logger.info("Stopping gracefully")
            limit = time.time() + self.timeout
            for pid in self.workers:
                self.worker_kill(pid, signal.SIGINT)
            while self.workers and time.time() < limit:
                try:
                    self.process_signals()
                except KeyboardInterrupt:
                    _logger.info("Forced shutdown.")
                    break
                self.process_zombie()
                time.sleep(0.1)
        else:
            _logger.info("Stopping forcefully")
        for pid in self.workers:
            self.worker_kill(pid, signal.SIGTERM)
        if self.socket:
            self.socket.close()

    def run(self, preload, stop):
        self.start()

        rc = preload_registries(preload)

        if stop:
            self.stop()
            return rc

        # Empty the cursor pool, we dont want them to be shared among forked workers.
        odoo.sql_db.close_all()

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
        # If our parent changed sucide
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
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_time + config['limit_time_cpu'], hard))

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
                         len(odoo.modules.registry.Registry.registries))
            self.stop()
        except Exception:
            _logger.exception("Worker (%s) Exception occured, exiting..." % self.pid)
            # should we use 3 to abort everything ?
            sys.exit(1)

    def _runloop(self):
        signal.pthread_sigmask(signal.SIG_BLOCK, {
            signal.SIGXCPU,
            signal.SIGINT, signal.SIGQUIT, signal.SIGUSR1,
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
            _logger.exception("Worker %s (%s) Exception occured, exiting...", self.__class__.__name__, self.pid)
            sys.exit(1)

class WorkerHTTP(Worker):
    """ HTTP Request workers """
    def __init__(self, multi):
        super(WorkerHTTP, self).__init__(multi)

        # The ODOO_HTTP_SOCKET_TIMEOUT environment variable allows to control socket timeout for
        # extreme latency situations. It's generally better to use a good buffering reverse proxy
        # to quickly free workers rather than increasing this timeout to accomodate high network
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
        # process_work() below process a single database per call.
        # The variable db_index is keeping track of the next database to
        # process.
        self.db_index = 0
        self.watchdog_timeout = multi.cron_timeout  # Use a distinct value for CRON Worker

    def sleep(self):
        # Really sleep once all the databases have been processed.
        if self.db_index == 0:
            interval = SLEEP_INTERVAL + self.pid % 10   # chorus effect

            # simulate interruptible sleep with select(wakeup_fd, timeout)
            try:
                select.select([self.wakeup_fd_r], [], [], interval)
                # clear wakeup pipe if we were interrupted
                empty_pipe(self.wakeup_fd_r)
            except select.error as e:
                if e.args[0] != errno.EINTR:
                    raise

    def _db_list(self):
        if config['db_name']:
            db_names = config['db_name'].split(',')
        else:
            db_names = odoo.service.db.list_dbs(True)
        return db_names

    def process_work(self):
        rpc_request = logging.getLogger('odoo.netsvc.rpc.request')
        rpc_request_flag = rpc_request.isEnabledFor(logging.DEBUG)
        _logger.debug("WorkerCron (%s) polling for jobs", self.pid)
        db_names = self._db_list()
        if len(db_names):
            self.db_index = (self.db_index + 1) % len(db_names)
            db_name = db_names[self.db_index]
            self.setproctitle(db_name)
            if rpc_request_flag:
                start_time = time.time()
                start_memory = memory_info(psutil.Process(os.getpid()))

            from odoo.addons import base
            base.models.ir_cron.ir_cron._acquire_job(db_name)

            # dont keep cursors in multi database mode
            if len(db_names) > 1:
                odoo.sql_db.close_db(db_name)
            if rpc_request_flag:
                run_time = time.time() - start_time
                end_memory = memory_info(psutil.Process(os.getpid()))
                vms_diff = (end_memory - start_memory) / 1024
                logline = '%s time:%.3fs mem: %sk -> %sk (diff: %sk)' % \
                    (db_name, run_time, start_memory / 1024, end_memory / 1024, vms_diff)
                _logger.debug("WorkerCron (%s) %s", self.pid, logline)

            self.request_count += 1
            if self.request_count >= self.request_max and self.request_max < len(db_names):
                _logger.error("There are more dabatases to process than allowed "
                              "by the `limit_request` configuration variable: %s more.",
                              len(db_names) - self.request_max)
        else:
            self.db_index = 0

    def start(self):
        os.nice(10)     # mommy always told me to be nice with others...
        Worker.start(self)
        if self.multi.socket:
            self.multi.socket.close()

#----------------------------------------------------------
# start/stop public api
#----------------------------------------------------------

server = None

def load_server_wide_modules():
    server_wide_modules = {'base', 'web'} | set(odoo.conf.server_wide_modules)
    for m in server_wide_modules:
        try:
            odoo.modules.module.load_openerp_module(m)
        except Exception:
            msg = ''
            if m == 'web':
                msg = """
The `web` module is provided by the addons found in the `openerp-web` project.
Maybe you forgot to add those addons in your addons_path configuration."""
            _logger.exception('Failed to load server-wide module `%s`.%s', m, msg)

def _reexec(updated_modules=None):
    """reexecute openerp-server process with (nearly) the same arguments"""
    if odoo.tools.osutil.is_running_as_nt_service():
        subprocess.call('net stop {0} && net start {0}'.format(nt_service_name), shell=True)
    exe = os.path.basename(sys.executable)
    args = stripped_sys_argv()
    if updated_modules:
        args += ["-u", ','.join(updated_modules)]
    if not args or args[0] != exe:
        args.insert(0, exe)
    # We should keep the LISTEN_* environment variabled in order to support socket activation on reexec
    os.execve(sys.executable, args, os.environ)

def load_test_file_py(registry, test_file):
    threading.currentThread().testing = True
    try:
        test_path, _ = os.path.splitext(os.path.abspath(test_file))
        for mod in [m for m in get_modules() if '/%s/' % m in test_file]:
            for mod_mod in get_test_modules(mod):
                mod_path, _ = os.path.splitext(getattr(mod_mod, '__file__', ''))
                if test_path == mod_path:
                    suite = unittest.TestSuite()
                    for t in unittest.TestLoader().loadTestsFromModule(mod_mod):
                        suite.addTest(t)
                    _logger.log(logging.INFO, 'running tests %s.', mod_mod.__name__)
                    result = odoo.modules.module.OdooTestRunner().run(suite)
                    success = result.wasSuccessful()
                    if hasattr(registry._assertion_report,'report_result'):
                        registry._assertion_report.report_result(success)
                    if not success:
                        _logger.error('%s: at least one error occurred in a test', test_file)
                    return
    finally:
        threading.currentThread().testing = False

def preload_registries(dbnames):
    """ Preload a registries, possibly run a test file."""
    # TODO: move all config checks to args dont check tools.config here
    dbnames = dbnames or []
    rc = 0
    for dbname in dbnames:
        try:
            update_module = config['init'] or config['update']
            registry = Registry.new(dbname, update_module=update_module)

            # run test_file if provided
            if config['test_file']:
                test_file = config['test_file']
                if not os.path.isfile(test_file):
                    _logger.warning('test file %s cannot be found', test_file)
                elif not test_file.endswith('py'):
                    _logger.warning('test file %s is not a python file', test_file)
                else:
                    _logger.info('loading test file %s', test_file)
                    with odoo.api.Environment.manage():
                        load_test_file_py(registry, test_file)

            # run post-install tests
            if config['test_enable']:
                t0 = time.time()
                t0_sql = odoo.sql_db.sql_counter
                module_names = (registry.updated_modules if update_module else
                                registry._init_modules)
                _logger.info("Starting post tests")
                with odoo.api.Environment.manage():
                    for module_name in module_names:
                        result = run_unit_tests(module_name, position='post_install')
                        registry._assertion_report.record_result(result)
                _logger.info("All post-tested in %.2fs, %s queries",
                             time.time() - t0, odoo.sql_db.sql_counter - t0_sql)

            if registry._assertion_report.failures:
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
    odoo.service.wsgi_server._patch_xmlrpc_marshaller()

    if odoo.evented:
        server = GeventServer(odoo.service.wsgi_server.application)
    elif config['workers']:
        if config['test_enable'] or config['test_file']:
            _logger.warning("Unit testing in workers mode could fail; use --workers 0.")

        server = PreforkServer(odoo.service.wsgi_server.application)

        # Workaround for Python issue24291, fixed in 3.6 (see Python issue26721)
        if sys.version_info[:2] == (3,5):
            # turn on buffering also for wfile, to avoid partial writes (Default buffer = 8k)
            werkzeug.serving.WSGIRequestHandler.wbufsize = -1
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
            # Note: Setting MALLOC_ARENA_MAX=0 allow to explicitely set the default glibs's malloc() behaviour.
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
        server = ThreadedServer(odoo.service.wsgi_server.application)

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
    if 'werkzeug' in config['dev_mode']:
        server.app = DebuggedApplication(server.app, evalex=True)

    rc = server.run(preload, stop)

    if watcher:
        watcher.stop()
    # like the legend of the phoenix, all ends with beginnings
    if getattr(odoo, 'phoenix', False):
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
