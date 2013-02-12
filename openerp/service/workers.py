#-----------------------------------------------------------
# Multicorn, multiprocessing inspired by gunicorn
# TODO rename class: Multicorn -> Arbiter ?
#-----------------------------------------------------------
import errno
import fcntl
import logging
import os
import psutil
import random
import resource
import select
import signal
import socket
import sys
import time

import werkzeug.serving
try:
    from setproctitle import setproctitle
except ImportError:
    setproctitle = lambda x: None

import openerp
import openerp.tools.config as config

_logger = logging.getLogger(__name__)

class Multicorn(object):
    """ Multiprocessing inspired by (g)unicorn.
    Multicorn currently uses accept(2) as dispatching method between workers
    but we plan to replace it by a more intelligent dispatcher to will parse
    the first HTTP request line.
    """
    def __init__(self, app):
        # config
        self.address = (config['xmlrpc_interface'] or '0.0.0.0', config['xmlrpc_port'])
        self.population = config['workers']
        self.timeout = config['limit_time_real']
        self.limit_request = config['limit_request']
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
            os.write(pipe[1], '.')
        except IOError, e:
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

    def worker_pop(self, pid):
        if pid in self.workers:
            _logger.debug("Worker (%s) unregistered",pid)
            try:
                self.workers_http.pop(pid,None)
                self.workers_cron.pop(pid,None)
                u = self.workers.pop(pid)
                u.close()
            except OSError:
                return

    def worker_kill(self, pid, sig):
        try:
            os.kill(pid, sig)
        except OSError, e:
            if e.errno == errno.ESRCH:
                self.worker_pop(pid)

    def process_signals(self):
        while len(self.queue):
            sig = self.queue.pop(0)
            if sig in [signal.SIGINT,signal.SIGTERM]:
                raise KeyboardInterrupt

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
            except OSError, e:
                if e.errno == errno.ECHILD:
                    break
                raise

    def process_timeout(self):
        now = time.time()
        for (pid, worker) in self.workers.items():
            if now - worker.watchdog_time >= worker.watchdog_timeout:
                _logger.error("Worker (%s) timeout", pid)
                self.worker_kill(pid, signal.SIGKILL)

    def process_spawn(self):
        while len(self.workers_http) < self.population:
            self.worker_spawn(WorkerHTTP, self.workers_http)
        while len(self.workers_cron) < config['max_cron_threads']:
            self.worker_spawn(WorkerCron, self.workers_cron)

    def sleep(self):
        try:
            # map of fd -> worker
            fds = dict([(w.watchdog_pipe[0],w) for k,w in self.workers.items()])
            fd_in = fds.keys() + [self.pipe[0]]
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
                except OSError, e:
                    if e.errno not in [errno.EAGAIN]:
                        raise
        except select.error, e:
            if e[0] not in [errno.EINTR]:
                raise

    def start(self):
        # wakeup pipe, python doesnt throw EINTR when a syscall is interrupted
        # by a signal simulating a pseudo SA_RESTART. We write to a pipe in the
        # signal handler to overcome this behaviour
        self.pipe = self.pipe_new()
        # set signal
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGCHLD, self.signal_handler)
        # listen to socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setblocking(0)
        self.socket.bind(self.address)
        self.socket.listen(8)

    def stop(self, graceful=True):
        if graceful:
            _logger.info("Stopping gracefully")
            limit = time.time() + self.timeout
            for pid in self.workers.keys():
                self.worker_kill(pid, signal.SIGTERM)
            while self.workers and time.time() < limit:
                self.process_zombie()
                time.sleep(0.1)
        else:
            _logger.info("Stopping forcefully")
        for pid in self.workers.keys():
            self.worker_kill(pid, signal.SIGTERM)
        self.socket.close()
        openerp.cli.server.quit_signals_received = 1

    def run(self):
        self.start()
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
            except Exception,e:
                _logger.exception(e)
                self.stop(False)
                sys.exit(-1)

class Worker(object):
    """ Workers """
    def __init__(self, multi):
        self.multi = multi
        self.watchdog_time = time.time()
        self.watchdog_pipe = multi.pipe_new()
        self.watchdog_timeout = multi.timeout
        self.ppid = os.getpid()
        self.pid = None
        self.alive = True
        # should we rename into lifetime ?
        self.request_max = multi.limit_request
        self.request_count = 0

    def close(self):
        os.close(self.watchdog_pipe[0])
        os.close(self.watchdog_pipe[1])

    def signal_handler(self, sig, frame):
        self.alive = False

    def sleep(self):
        try:
            ret = select.select([self.multi.socket], [], [], self.multi.beat)
        except select.error, e:
            if e[0] not in [errno.EINTR]:
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
        rss, vms = psutil.Process(os.getpid()).get_memory_info()
        if vms > config['limit_memory_soft']:
            _logger.info('Worker (%d) virtual memory limit (%s) reached.', self.pid, vms)
            self.alive = False # Commit suicide after the request.

        # VMS and RLIMIT_AS are the same thing: virtual memory, a.k.a. address space
        soft, hard = resource.getrlimit(resource.RLIMIT_AS)
        resource.setrlimit(resource.RLIMIT_AS, (config['limit_memory_hard'], hard))

        # SIGXCPU (exceeded CPU time) signal handler will raise an exception.
        r = resource.getrusage(resource.RUSAGE_SELF)
        cpu_time = r.ru_utime + r.ru_stime
        def time_expired(n, stack):
            _logger.info('Worker (%d) CPU time limit (%s) reached.', config['limit_time_cpu'])
            # We dont suicide in such case
            raise Exception('CPU time limit exceeded.')
        signal.signal(signal.SIGXCPU, time_expired)
        soft, hard = resource.getrlimit(resource.RLIMIT_CPU)
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_time + config['limit_time_cpu'], hard))

    def process_work(self):
        pass

    def start(self):
        self.pid = os.getpid()
        setproctitle('openerp: %s %s' % (self.__class__.__name__, self.pid))
        _logger.info("Worker %s (%s) alive", self.__class__.__name__, self.pid)
        # Reseed the random number generator
        random.seed()
        # Prevent fd inherientence close_on_exec
        flags = fcntl.fcntl(self.multi.socket, fcntl.F_GETFD) | fcntl.FD_CLOEXEC
        fcntl.fcntl(self.multi.socket, fcntl.F_SETFD, flags)
        # reset blocking status
        self.multi.socket.setblocking(0)
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        signal.signal(signal.SIGCHLD, signal.SIG_DFL)

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
            _logger.info("Worker (%s) exiting. request_count: %s.", self.pid, self.request_count)
            self.stop()
        except Exception,e:
            _logger.exception("Worker (%s) Exception occured, exiting..." % self.pid)
            # should we use 3 to abort everything ?
            sys.exit(1)

class WorkerHTTP(Worker):
    """ HTTP Request workers """
    def process_request(self, client, addr):
        client.setblocking(1)
        client.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        # Prevent fd inherientence close_on_exec
        flags = fcntl.fcntl(client, fcntl.F_GETFD) | fcntl.FD_CLOEXEC
        fcntl.fcntl(client, fcntl.F_SETFD, flags)
        # do request using WorkerBaseWSGIServer monkey patched with socket
        self.server.socket = client
        # tolerate broken pipe when the http client closes the socket before
        # receiving the full reply
        try:
            self.server.process_request(client,addr)
        except IOError, e:
            if e.errno != errno.EPIPE:
                raise
        self.request_count += 1

    def process_work(self):
        try:
            client, addr = self.multi.socket.accept()
            self.process_request(client, addr)
        except socket.error, e:
            if e[0] not in (errno.EAGAIN, errno.ECONNABORTED):
                raise

    def start(self):
        Worker.start(self)
        self.server = WorkerBaseWSGIServer(self.multi.app)

class WorkerBaseWSGIServer(werkzeug.serving.BaseWSGIServer):
    """ werkzeug WSGI Server patched to allow using an external listen socket
    """
    def __init__(self, app):
        werkzeug.serving.BaseWSGIServer.__init__(self, "1", "1", app)
    def server_bind(self):
        # we dont bind beause we use the listen socket of Multicorn#socket
        # instead we close the socket
        if self.socket:
            self.socket.close()
    def server_activate(self):
        # dont listen as we use Multicorn#socket
        pass

class WorkerCron(Worker):
    """ Cron workers """
    def sleep(self):
        interval = 60 + self.pid % 10 # chorus effect
        time.sleep(interval)

    def process_work(self):
        rpc_request = logging.getLogger('openerp.netsvc.rpc.request')
        rpc_request_flag = rpc_request.isEnabledFor(logging.DEBUG)
        _logger.debug("WorkerCron (%s) polling for jobs", self.pid)
        if config['db_name']:
            db_names = config['db_name'].split(',')
        else:
            db_names = openerp.netsvc.ExportService._services['db'].exp_list(True)
        for db_name in db_names:
            if rpc_request_flag:
                start_time = time.time()
                start_rss, start_vms = psutil.Process(os.getpid()).get_memory_info()
            while True:
                # acquired = openerp.addons.base.ir.ir_cron.ir_cron._acquire_job(db_name)
                # TODO why isnt openerp.addons.base defined ?
                import base
                acquired = base.ir.ir_cron.ir_cron._acquire_job(db_name)
                if not acquired:
                    break
            # dont keep cursors in multi database mode
            if len(db_names) > 1:
                openerp.sql_db.close_db(db_name)
            if rpc_request_flag:
                end_time = time.time()
                end_rss, end_vms = psutil.Process(os.getpid()).get_memory_info()
                logline = '%s time:%.3fs mem: %sk -> %sk (diff: %sk)' % (db_name, end_time - start_time, start_vms / 1024, end_vms / 1024, (end_vms - start_vms)/1024)
                _logger.debug("WorkerCron (%s) %s", self.pid, logline)
        # TODO Each job should be considered as one request instead of each run
        self.request_count += 1

    def start(self):
        Worker.start(self)
        openerp.service.start_internal()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
