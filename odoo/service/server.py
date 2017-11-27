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

import werkzeug.serving
from werkzeug.debug import DebuggedApplication

if os.name == 'posix':
    # Unix only for workers
    import fcntl
    import resource
    import psutil
else:
    # Windows shim
    signal.SIGHUP = -1

# Optional process names for workers
try:
    from setproctitle import setproctitle
except ImportError:
    setproctitle = lambda x: None

import odoo
from odoo.modules.module import run_unit_tests, runs_post_install
from odoo.modules.registry import Registry
from odoo.release import nt_service_name
from odoo.tools import config
from odoo.tools import stripped_sys_argv, dumpstacks, log_ormcache_stats

_logger = logging.getLogger(__name__)

try:
    import watchdog
    from watchdog.observers import Observer
    from watchdog.events import FileCreatedEvent, FileModifiedEvent, FileMovedEvent
except ImportError:
    watchdog = None

SLEEP_INTERVAL = 60     # 1 min

def memory_info(process):
    """ psutil < 2.0 does not have memory_info, >= 3.0 does not have
    get_memory_info """
    pmem = (getattr(process, 'memory_info', None) or process.get_memory_info)()
    return (pmem.rss, pmem.vms)

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
        # flag the current thread as handling a http request
        super(RequestHandler, self).setup()
        me = threading.currentThread()
        me.name = 'odoo.service.http.request.%s' % (me.ident,)

# _reexec() should set LISTEN_* to avoid connection refused during reload time. It
# should also work with systemd socket activation. This is currently untested
# and not yet used.

class ThreadedWSGIServerReloadable(LoggingBaseWSGIServerMixIn, werkzeug.serving.ThreadedWSGIServer):
    """ werkzeug Threaded WSGI Server patched to allow reusing a listen socket
    given by the environement, this is used by autoreload to keep the listen
    socket open when a reload happens.
    """
    def __init__(self, host, port, app):
        super(ThreadedWSGIServerReloadable, self).__init__(host, port, app,
                                                           handler=RequestHandler)

    def server_bind(self):
        envfd = os.environ.get('LISTEN_FDS')
        if envfd and os.environ.get('LISTEN_PID') == str(os.getpid()):
            self.reload_socket = True
            self.socket = socket.fromfd(int(envfd), socket.AF_INET, socket.SOCK_STREAM)
            # should we os.close(int(envfd)) ? it seem python duplicate the fd.
        else:
            self.reload_socket = False
            super(ThreadedWSGIServerReloadable, self).server_bind()

    def server_activate(self):
        if not self.reload_socket:
            super(ThreadedWSGIServerReloadable, self).server_activate()

#----------------------------------------------------------
# FileSystem Watcher for autoreload and cache invalidation
#----------------------------------------------------------
class FSWatcher(object):
    def __init__(self):
        self.observer = Observer()
        for path in odoo.modules.module.ad_paths:
            _logger.info('Watching addons folder %s', path)
            self.observer.schedule(self, path, recursive=True)

    def dispatch(self, event):
        if isinstance(event, (FileCreatedEvent, FileModifiedEvent, FileMovedEvent)):
            if not event.is_directory:
                path = getattr(event, 'dest_path', event.src_path)
                if path.endswith('.py'):
                    try:
                        source = open(path, 'rb').read() + b'\n'
                        compile(source, path, 'exec')
                    except SyntaxError:
                        _logger.error('autoreload: python code change detected, SyntaxError in %s', path)
                    else:
                        if not getattr(odoo, 'phoenix', False):
                            _logger.info('autoreload: python code updated, autoreload activated')
                            restart()

    def start(self):
        self.observer.start()
        _logger.info('AutoReload watcher running')

    def stop(self):
        self.observer.stop()
        self.observer.join()

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
        elif sig == signal.SIGHUP:
            # restart on kill -HUP
            odoo.phoenix = True
            self.quit_signals_received += 1
            # interrupt run() to start shutdown
            raise KeyboardInterrupt()

    def cron_thread(self, number):
        from odoo.addons.base.ir.ir_cron import ir_cron
        while True:
            time.sleep(SLEEP_INTERVAL + number)     # Steve Reich timing style
            registries = odoo.modules.registry.Registry.registries
            _logger.debug('cron%d polling for jobs', number)
            for db_name, registry in registries.items():
                if registry.ready:
                    try:
                        ir_cron._acquire_job(db_name)
                    except Exception:
                        _logger.warning('cron%d encountered an Exception:', number, exc_info=True)

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
        _logger.info('HTTP service (werkzeug) running on %s:%s', self.interface, self.port)

    def start(self, stop=False):
        _logger.debug("Setting signal handlers")
        if os.name == 'posix':
            signal.signal(signal.SIGINT, self.signal_handler)
            signal.signal(signal.SIGTERM, self.signal_handler)
            signal.signal(signal.SIGCHLD, self.signal_handler)
            signal.signal(signal.SIGHUP, self.signal_handler)
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
        _logger.info("Initiating shutdown")
        _logger.info("Hit CTRL-C again or send a second signal to force the shutdown.")

        if self.httpd:
            self.httpd.shutdown()
            self.close_socket(self.httpd.socket)

        # Manually join() all threads before calling sys.exit() to allow a second signal
        # to trigger _force_quit() in case some non-daemon threads won't exit cleanly.
        # threading.Thread.join() should not mask signals (at least in python 2.5).
        me = threading.currentThread()
        _logger.debug('current thread: %r', me)
        for thread in threading.enumerate():
            _logger.debug('process %r (%r)', thread, thread.isDaemon())
            if thread != me and not thread.isDaemon() and thread.ident != self.main_thread_id:
                while thread.isAlive():
                    _logger.debug('join and sleep')
                    # Need a busyloop here as thread.join() masks signals
                    # and would prevent the forced shutdown.
                    thread.join(0.05)
                    time.sleep(0.05)

        _logger.debug('--')
        odoo.modules.registry.Registry.delete_all()
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
                time.sleep(60)
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
        rss, vms = memory_info(psutil.Process(self.pid))
        if vms > config['limit_memory_soft']:
            _logger.warning('LongPolling virtual memory limit reached: %s', vms)
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
        from gevent.wsgi import WSGIServer


        if os.name == 'posix':
            # Set process memory limit as an extra safeguard
            _, hard = resource.getrlimit(resource.RLIMIT_AS)
            resource.setrlimit(resource.RLIMIT_AS, (config['limit_memory_hard'], hard))
            signal.signal(signal.SIGQUIT, dumpstacks)
            signal.signal(signal.SIGUSR1, log_ormcache_stats)
            gevent.spawn(self.watchdog)
        
        self.httpd = WSGIServer((self.interface, self.port), self.app)
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
                self.dumpstacks()
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
                try:
                    # empty pipe
                    while os.read(fd, 1):
                        pass
                except OSError as e:
                    if e.errno not in [errno.EAGAIN]:
                        raise
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

    def sleep(self):
        try:
            wakeup_fd = self.eintr_pipe[0]
            select.select([self.multi.socket, wakeup_fd], [], [], self.multi.beat)
        except select.error as e:
            if e.args[0] not in [errno.EINTR]:
                raise

    def process_limit(self):
        # If our parent changed sucide
        if self.ppid != os.getppid():
            _logger.info("Worker (%s) Parent changed", self.pid)
            self.alive = False
        # check for lifetime
        if self.request_count >= self.request_max:
            _logger.info("Worker (%d) max request (%s) reached.", self.pid, self.request_count)
            self.alive = False
        # Reset the worker if it consumes too much memory (e.g. caused by a memory leak).
        rss, vms = memory_info(psutil.Process(os.getpid()))
        if vms > config['limit_memory_soft']:
            _logger.info('Worker (%d) virtual memory limit (%s) reached.', self.pid, vms)
            self.alive = False      # Commit suicide after the request.

        # VMS and RLIMIT_AS are the same thing: virtual memory, a.k.a. address space
        soft, hard = resource.getrlimit(resource.RLIMIT_AS)
        resource.setrlimit(resource.RLIMIT_AS, (config['limit_memory_hard'], hard))

        # SIGXCPU (exceeded CPU time) signal handler will raise an exception.
        r = resource.getrusage(resource.RUSAGE_SELF)
        cpu_time = r.ru_utime + r.ru_stime
        def time_expired(n, stack):
            _logger.info('Worker (%d) CPU time limit (%s) reached.', self.pid, config['limit_time_cpu'])
            # We dont suicide in such case
            raise Exception('CPU time limit exceeded.')
        signal.signal(signal.SIGXCPU, time_expired)
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
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        signal.signal(signal.SIGCHLD, signal.SIG_DFL)
        signal.set_wakeup_fd(self.eintr_pipe[1])

    def stop(self):
        pass

    def run(self):
        try:
            self.start()
            while self.alive:
                self.process_limit()
                self.multi.pipe_ping(self.watchdog_pipe)
                self.sleep()
                self.process_work()
            _logger.info("Worker (%s) exiting. request_count: %s, registry count: %s.",
                         self.pid, self.request_count,
                         len(odoo.modules.registry.Registry.registries))
            self.stop()
        except Exception:
            _logger.exception("Worker (%s) Exception occured, exiting..." % self.pid)
            # should we use 3 to abort everything ?
            sys.exit(1)

class WorkerHTTP(Worker):
    """ HTTP Request workers """
    def process_request(self, client, addr):
        client.setblocking(1)
        client.settimeout(2)
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
                wakeup_fd = self.eintr_pipe[0]
                select.select([wakeup_fd], [], [], interval)
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
                start_rss, start_vms = memory_info(psutil.Process(os.getpid()))

            from odoo.addons import base
            base.ir.ir_cron.ir_cron._acquire_job(db_name)
            odoo.modules.registry.Registry.delete(db_name)

            # dont keep cursors in multi database mode
            if len(db_names) > 1:
                odoo.sql_db.close_db(db_name)
            if rpc_request_flag:
                run_time = time.time() - start_time
                end_rss, end_vms = memory_info(psutil.Process(os.getpid()))
                vms_diff = (end_vms - start_vms) / 1024
                logline = '%s time:%.3fs mem: %sk -> %sk (diff: %sk)' % \
                    (db_name, run_time, start_vms / 1024, end_vms / 1024, vms_diff)
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
    for m in odoo.conf.server_wide_modules:
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
    os.execv(sys.executable, args)

def load_test_file_yml(registry, test_file):
    with registry.cursor() as cr:
        odoo.tools.convert_yaml_import(cr, 'base', open(test_file, 'rb'), 'test', {}, 'init')
        if config['test_commit']:
            _logger.info('test %s has been commited', test_file)
            cr.commit()
        else:
            _logger.info('test %s has been rollbacked', test_file)
            cr.rollback()

def load_test_file_py(registry, test_file):
    # Locate python module based on its filename and run the tests
    test_path, _ = os.path.splitext(os.path.abspath(test_file))
    for mod_name, mod_mod in list(sys.modules.items()):
        if mod_mod:
            mod_path, _ = os.path.splitext(getattr(mod_mod, '__file__', ''))
            if test_path == mod_path:
                suite = unittest.TestSuite()
                for t in unittest.TestLoader().loadTestsFromModule(mod_mod):
                    suite.addTest(t)
                _logger.log(logging.INFO, 'running tests %s.', mod_mod.__name__)
                stream = odoo.modules.module.TestStream()
                result = unittest.TextTestRunner(verbosity=2, stream=stream).run(suite)
                success = result.wasSuccessful()
                if hasattr(registry._assertion_report,'report_result'):
                    registry._assertion_report.report_result(success)
                if not success:
                    _logger.error('%s: at least one error occurred in a test', test_file)

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
                _logger.info('loading test file %s', test_file)
                with odoo.api.Environment.manage():
                    if test_file.endswith('yml'):
                        load_test_file_yml(registry, test_file)
                    elif test_file.endswith('py'):
                        load_test_file_py(registry, test_file)

            # run post-install tests
            if config['test_enable']:
                t0 = time.time()
                t0_sql = odoo.sql_db.sql_counter
                module_names = (registry.updated_modules if update_module else
                                registry._init_modules)
                with odoo.api.Environment.manage():
                    for module_name in module_names:
                        result = run_unit_tests(module_name, registry.db_name,
                                                position=runs_post_install)
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
        server = ThreadedServer(odoo.service.wsgi_server.application)

    watcher = None
    if 'reload' in config['dev_mode']:
        if watchdog:
            watcher = FSWatcher()
            watcher.start()
        else:
            _logger.warning("'watchdog' module not installed. Code autoreload feature is disabled")
    if 'werkzeug' in config['dev_mode']:
        server.app = DebuggedApplication(server.app, evalex=True)

    rc = server.run(preload, stop)

    # like the legend of the phoenix, all ends with beginnings
    if getattr(odoo, 'phoenix', False):
        if watcher:
            watcher.stop()
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
