# -*- coding: utf-8 -*-
# ftpserver.py
#
#  pyftpdlib is released under the MIT license, reproduced below:
#  ======================================================================
#  Copyright (C) 2007 Giampaolo Rodola' <g.rodola@gmail.com>
#  Hacked by Fabien Pinckaers (C) 2008 <fp@tinyerp.com>
#                         All Rights Reserved
#
#  Permission to use, copy, modify, and distribute this software and
#  its documentation for any purpose and without fee is hereby
#  granted, provided that the above copyright notice appear in all
#  copies and that both that copyright notice and this permission
#  notice appear in supporting documentation, and that the name of
#  Giampaolo Rodola' not be used in advertising or publicity pertaining to
#  distribution of the software without specific, written prior
#  permission.
#
#  Giampaolo Rodola' DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS SOFTWARE,
#  INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS, IN
#  NO EVENT Giampaolo Rodola' BE LIABLE FOR ANY SPECIAL, INDIRECT OR
#  CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS
#  OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT,
#  NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN
#  CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
#  ======================================================================


"""pyftpdlib: RFC-959 asynchronous FTP server.

pyftpdlib implements a fully functioning asynchronous FTP server as
defined in RFC-959.  A hierarchy of classes outlined below implement
the backend functionality for the FTPd:

    [FTPServer] - the base class for the backend.

    [FTPHandler] - a class representing the server-protocol-interpreter
    (server-PI, see RFC-959). Each time a new connection occurs
    FTPServer will create a new FTPHandler instance to handle the
    current PI session.

    [ActiveDTP], [PassiveDTP] - base classes for active/passive-DTP
    backends.

    [DTPHandler] - this class handles processing of data transfer
    operations (server-DTP, see RFC-959).

    [DummyAuthorizer] - an "authorizer" is a class handling FTPd
    authentications and permissions. It is used inside FTPHandler class
    to verify user passwords, to get user's home directory and to get
    permissions when a filesystem read/write occurs. "DummyAuthorizer"
    is the base authorizer class providing a platform independent
    interface for managing virtual users.

    [AbstractedFS] - class used to interact with the file system,
    providing a high level, cross-platform interface compatible
    with both Windows and UNIX style filesystems.

    [CallLater] - calls a function at a later time whithin the polling
    loop asynchronously.

    [AuthorizerError] - base class for authorizers exceptions.


pyftpdlib also provides 3 different logging streams through 3 functions
which can be overridden to allow for custom logging.

    [log] - the main logger that logs the most important messages for
    the end user regarding the FTPd.

    [logline] - this function is used to log commands and responses
    passing through the control FTP channel.

    [logerror] - log traceback outputs occurring in case of errors.


Usage example:

>>> from pyftpdlib import ftpserver
>>> authorizer = ftpserver.DummyAuthorizer()
>>> authorizer.add_user('user', 'password', '/home/user', perm='elradfmw')
>>> authorizer.add_anonymous('/home/nobody')
>>> ftp_handler = ftpserver.FTPHandler
>>> ftp_handler.authorizer = authorizer
>>> address = ("127.0.0.1", 21)
>>> ftpd = ftpserver.FTPServer(address, ftp_handler)
>>> ftpd.serve_forever()
Serving FTP on 127.0.0.1:21
[]127.0.0.1:2503 connected.
127.0.0.1:2503 ==> 220 Ready.
127.0.0.1:2503 <== USER anonymous
127.0.0.1:2503 ==> 331 Username ok, send password.
127.0.0.1:2503 <== PASS ******
127.0.0.1:2503 ==> 230 Login successful.
[anonymous]@127.0.0.1:2503 User anonymous logged in.
127.0.0.1:2503 <== TYPE A
127.0.0.1:2503 ==> 200 Type set to: ASCII.
127.0.0.1:2503 <== PASV
127.0.0.1:2503 ==> 227 Entering passive mode (127,0,0,1,9,201).
127.0.0.1:2503 <== LIST
127.0.0.1:2503 ==> 150 File status okay. About to open data connection.
[anonymous]@127.0.0.1:2503 OK LIST "/". Transfer starting.
127.0.0.1:2503 ==> 226 Transfer complete.
[anonymous]@127.0.0.1:2503 Transfer complete. 706 bytes transmitted.
127.0.0.1:2503 <== QUIT
127.0.0.1:2503 ==> 221 Goodbye.
[anonymous]@127.0.0.1:2503 Disconnected.
"""


import asyncore
import asynchat
import socket
import os
import sys
import traceback
import errno
import time
import glob
import tempfile
import warnings
import random
import stat
import heapq
from tarfile import filemode

try:
    import pwd
    import grp
except ImportError:
    pwd = grp = None


__all__ = ['proto_cmds', 'Error', 'log', 'logline', 'logerror', 'DummyAuthorizer',
           'AuthorizerError', 'FTPHandler', 'FTPServer', 'PassiveDTP',
           'ActiveDTP', 'DTPHandler', 'FileProducer', 'BufferedIteratorProducer',
           'AbstractedFS', 'CallLater']


__pname__   = 'Python FTP server library (pyftpdlib)'
__ver__     = '0.5.1'
__date__    = '2009-01-21'
__author__  = "Giampaolo Rodola' <g.rodola@gmail.com>"
__web__     = 'http://code.google.com/p/pyftpdlib/'


proto_cmds = {
    # cmd : (perm, auth,  arg,   path,  help)
    'ABOR': (None, True,  False, False, 'Syntax: ABOR (abort transfer).'),
    'ALLO': (None, True,  True,  False, 'Syntax: ALLO <SP> bytes (noop; allocate storage).'),
    'APPE': ('a',  True,  True,  True,  'Syntax: APPE <SP> file-name (append data to an existent file).'),
    'CDUP': ('e',  True,  False, True,  'Syntax: CDUP (go to parent directory).'),
    'CWD' : ('e',  True,  None,  True,  'Syntax: CWD [<SP> dir-name] (change current working directory).'),
    'DELE': ('d',  True,  True,  True,  'Syntax: DELE <SP> file-name (delete file).'),
    'EPRT': (None, True,  True,  False, 'Syntax: EPRT <SP> |proto|ip|port| (set server in extended active mode).'),
    'EPSV': (None, True,  None,  False, 'Syntax: EPSV [<SP> proto/"ALL"] (set server in extended passive mode).'),
    'FEAT': (None, False, False, False, 'Syntax: FEAT (list all new features supported).'),
    'HELP': (None, False, None,  False, 'Syntax: HELP [<SP> cmd] (show help).'),
    'LIST': ('l',  True,  None,  True,  'Syntax: LIST [<SP> path-name] (list files).'),
    'MDTM': (None, True,  True,  True,  'Syntax: MDTM [<SP> file-name] (get last modification time).'),
    'MLSD': ('l',  True,  None,  True,  'Syntax: MLSD [<SP> dir-name] (list files in a machine-processable form)'),
    'MLST': (None, True,  None,  True,  'Syntax: MLST [<SP> path-name] (show a path in a machine-processable form)'),
    'MODE': (None, True,  True,  False, 'Syntax: MODE <SP> mode (noop; set data transfer mode).'),
    'MKD' : ('m',  True,  True,  True,  'Syntax: MDK <SP> dir-name (create directory).'),
    'NLST': ('l',  True,  None,  True,  'Syntax: NLST [<SP> path-name] (list files in a compact form).'),
    'NOOP': (None, False, False, False, 'Syntax: NOOP (just do nothing).'),
    'OPTS': (None, True,  True,  False, 'Syntax: OPTS <SP> ftp-command [<SP> option] (specify options for FTP commands)'),
    'PASS': (None, False, True,  False, 'Syntax: PASS <SP> user-name (set user password).'),
    'PASV': (None, True,  False, False, 'Syntax: PASV (set server in passive mode).'),
    'PORT': (None, True,  True,  False, 'Syntax: PORT <sp> h1,h2,h3,h4,p1,p2 (set server in active mode).'),
    'PWD' : (None, True,  False, False, 'Syntax: PWD (get current working directory).'),
    'QUIT': (None, False, False, False, 'Syntax: QUIT (quit current session).'),
    'REIN': (None, True,  False, False, 'Syntax: REIN (reinitialize / flush account).'),
    'REST': (None, True,  True,  False, 'Syntax: REST <SP> marker (restart file position).'),
    'RETR': ('r',  True,  True,  True,  'Syntax: RETR <SP> file-name (retrieve a file).'),
    'RMD' : ('d',  True,  True,  True,  'Syntax: RMD <SP> dir-name (remove directory).'),
    'RNFR': ('f',  True,  True,  True,  'Syntax: RNFR <SP> file-name (file renaming (source name)).'),
    'RNTO': (None, True,  True,  True,  'Syntax: RNTO <SP> file-name (file renaming (destination name)).'),
    'SITE': (None, False, True, False,  'Syntax: SITE <SP> site-command (execute the specified SITE command).'),
    'SITE HELP' : (None, False, None, False, 'Syntax: SITE HELP [<SP> site-command] (show SITE command help).'),
    'SIZE': (None, True,  True,  True,  'Syntax: HELP <SP> file-name (get file size).'),
    'STAT': ('l',  False, None,  True,  'Syntax: STAT [<SP> path name] (status information [list files]).'),
    'STOR': ('w',  True,  True,  True,  'Syntax: STOR <SP> file-name (store a file).'),
    'STOU': ('w',  True,  None,  True,  'Syntax: STOU [<SP> file-name] (store a file with a unique name).'),
    'STRU': (None, True,  True,  False, 'Syntax: STRU <SP> type (noop; set file structure).'),
    'SYST': (None, False, False, False, 'Syntax: SYST (get operating system type).'),
    'TYPE': (None, True,  True,  False, 'Syntax: TYPE <SP> [A | I] (set transfer type).'),
    'USER': (None, False, True,  False, 'Syntax: USER <SP> user-name (set username).'),
    'XCUP': ('e',  True,  False, True,  'Syntax: XCUP (obsolete; go to parent directory).'),
    'XCWD': ('e',  True,  None,  True,  'Syntax: XCWD [<SP> dir-name] (obsolete; change current directory).'),
    'XMKD': ('m',  True,  True,  True,  'Syntax: XMDK <SP> dir-name (obsolete; create directory).'),
    'XPWD': (None, True,  False, False, 'Syntax: XPWD (obsolete; get current dir).'),
    'XRMD': ('d',  True,  True,  True,  'Syntax: XRMD <SP> dir-name (obsolete; remove directory).'),
    }

class _CommandProperty:
    def __init__(self, perm, auth_needed, arg_needed, check_path, help):
        self.perm = perm
        self.auth_needed = auth_needed
        self.arg_needed = arg_needed
        self.check_path = check_path
        self.help = help

for cmd, properties in proto_cmds.iteritems():
    proto_cmds[cmd] = _CommandProperty(*properties)
del cmd, properties


# hack around format_exc function of traceback module to grant
# backward compatibility with python < 2.4
if not hasattr(traceback, 'format_exc'):
    try:
        import cStringIO as StringIO
    except ImportError:
        import StringIO

    def _format_exc():
        f = StringIO.StringIO()
        traceback.print_exc(file=f)
        data = f.getvalue()
        f.close()
        return data

    traceback.format_exc = _format_exc


def _strerror(err):
    """A wrap around os.strerror() which may be not available on all
    platforms (e.g. pythonCE).

     - (instance) err: an EnvironmentError or derived class instance.
    """
    if hasattr(os, 'strerror'):
        return os.strerror(err.errno)
    else:
        return err.strerror

# the heap used for the scheduled tasks
_tasks = []

def _scheduler():
    """Run the scheduled functions due to expire soonest (if any)."""
    now = time.time()
    while _tasks and now >= _tasks[0].timeout:
        call = heapq.heappop(_tasks)
        if call.repush:
            heapq.heappush(_tasks, call)
            call.repush = False
            continue
        try:
            call.call()
        finally:
            if not call.cancelled:
                call.cancel()


class CallLater:
    """Calls a function at a later time.

    It can be used to asynchronously schedule a call within the polling
    loop without blocking it. The instance returned is an object that
    can be used to cancel or reschedule the call.
    """

    def __init__(self, seconds, target, *args, **kwargs):
        """
         - (int) seconds: the number of seconds to wait
         - (obj) target: the callable object to call later
         - args: the arguments to call it with
         - kwargs: the keyword arguments to call it with
        """
        assert callable(target), "%s is not callable" %target
        assert sys.maxint >= seconds >= 0, "%s is not greater than or equal " \
                                           "to 0 seconds" % (seconds)
        self.__delay = seconds
        self.__target = target
        self.__args = args
        self.__kwargs = kwargs
        # seconds from the epoch at which to call the function
        self.timeout = time.time() + self.__delay
        self.repush = False
        self.cancelled = False
        heapq.heappush(_tasks, self)

    def __le__(self, other):
        return self.timeout <= other.timeout

    def call(self):
        """Call this scheduled function."""
        assert not self.cancelled, "Already cancelled"
        self.__target(*self.__args, **self.__kwargs)

    def reset(self):
        """Reschedule this call resetting the current countdown."""
        assert not self.cancelled, "Already cancelled"
        self.timeout = time.time() + self.__delay
        self.repush = True

    def delay(self, seconds):
        """Reschedule this call for a later time."""
        assert not self.cancelled, "Already cancelled."
        assert sys.maxint >= seconds >= 0, "%s is not greater than or equal " \
                                           "to 0 seconds" %(seconds)
        self.__delay = seconds
        newtime = time.time() + self.__delay
        if newtime > self.timeout:
            self.timeout = newtime
            self.repush = True
        else:
            # XXX - slow, can be improved
            self.timeout = newtime
            heapq.heapify(_tasks)

    def cancel(self):
        """Unschedule this call."""
        assert not self.cancelled, "Already cancelled"
        self.cancelled = True
        del self.__target, self.__args, self.__kwargs
        if self in _tasks:
            pos = _tasks.index(self)
            if pos == 0:
                heapq.heappop(_tasks)
            elif pos == len(_tasks) - 1:
                _tasks.pop(pos)
            else:
                _tasks[pos] = _tasks.pop()
                heapq._siftup(_tasks, pos)


# --- library defined exceptions

class Error(Exception):
    """Base class for module exceptions."""

class AuthorizerError(Error):
    """Base class for authorizer exceptions."""


# --- loggers

def log(msg):
    """Log messages intended for the end user."""
    print msg

def logline(msg):
    """Log commands and responses passing through the command channel."""
    print msg

def logerror(msg):
    """Log traceback outputs occurring in case of errors."""
    sys.stderr.write(str(msg) + '\n')
    sys.stderr.flush()


# --- authorizers

class DummyAuthorizer:
    """Basic "dummy" authorizer class, suitable for subclassing to
    create your own custom authorizers.

    An "authorizer" is a class handling authentications and permissions
    of the FTP server.  It is used inside FTPHandler class for verifying
    user's password, getting users home directory, checking user
    permissions when a file read/write event occurs and changing user
    before accessing the filesystem.

    DummyAuthorizer is the base authorizer, providing a platform
    independent interface for managing "virtual" FTP users. System
    dependent authorizers can by written by subclassing this base
    class and overriding appropriate methods as necessary.
    """

    read_perms = "elr"
    write_perms = "adfmw"

    def __init__(self):
        self.user_table = {}

    def add_user(self, username, password, homedir, perm='elr',
                    msg_login="Login successful.", msg_quit="Goodbye."):
        """Add a user to the virtual users table.

        AuthorizerError exceptions raised on error conditions such as
        invalid permissions, missing home directory or duplicate usernames.

        Optional perm argument is a string referencing the user's
        permissions explained below:

        Read permissions:
         - "e" = change directory (CWD command)
         - "l" = list files (LIST, NLST, MLSD commands)
         - "r" = retrieve file from the server (RETR command)

        Write permissions:
         - "a" = append data to an existing file (APPE command)
         - "d" = delete file or directory (DELE, RMD commands)
         - "f" = rename file or directory (RNFR, RNTO commands)
         - "m" = create directory (MKD command)
         - "w" = store a file to the server (STOR, STOU commands)

        Optional msg_login and msg_quit arguments can be specified to
        provide customized response strings when user log-in and quit.
        """
        if self.has_user(username):
            raise AuthorizerError('User "%s" already exists' %username)
        if not os.path.isdir(homedir):
            raise AuthorizerError('No such directory: "%s"' %homedir)
        homedir = os.path.realpath(homedir)
        self._check_permissions(username, perm)
        dic = {'pwd': str(password),
               'home': homedir,
               'perm': perm,
               'operms': {},
               'msg_login': str(msg_login),
               'msg_quit': str(msg_quit)
               }
        self.user_table[username] = dic

    def add_anonymous(self, homedir, **kwargs):
        """Add an anonymous user to the virtual users table.

        AuthorizerError exception raised on error conditions such as
        invalid permissions, missing home directory, or duplicate
        anonymous users.

        The keyword arguments in kwargs are the same expected by
        add_user method: "perm", "msg_login" and "msg_quit".

        The optional "perm" keyword argument is a string defaulting to
        "elr" referencing "read-only" anonymous user's permissions.

        Using write permission values ("adfmw") results in a
        RuntimeWarning.
        """
        DummyAuthorizer.add_user(self, 'anonymous', '', homedir, **kwargs)

    def remove_user(self, username):
        """Remove a user from the virtual users table."""
        del self.user_table[username]

    def override_perm(self, username, directory, perm, recursive=False):
        """Override permissions for a given directory."""
        self._check_permissions(username, perm)
        if not os.path.isdir(directory):
            raise AuthorizerError('No such directory: "%s"' %directory)
        directory = os.path.normcase(os.path.realpath(directory))
        home = os.path.normcase(self.get_home_dir(username))
        if directory == home:
            raise AuthorizerError("Can't override home directory permissions")
        if not self._issubpath(directory, home):
            raise AuthorizerError("Path escapes user home directory")
        self.user_table[username]['operms'][directory] = perm, recursive

    def validate_authentication(self, username, password):
        """Return True if the supplied username and password match the
        stored credentials."""
        if not self.has_user(username):
            return False
        if username == 'anonymous':
            return True
        return self.user_table[username]['pwd'] == password

    def impersonate_user(self, username, password):
        """Impersonate another user (noop).

        It is always called before accessing the filesystem.
        By default it does nothing.  The subclass overriding this
        method is expected to provide a mechanism to change the
        current user.
        """

    def terminate_impersonation(self):
        """Terminate impersonation (noop).

        It is always called after having accessed the filesystem.
        By default it does nothing.  The subclass overriding this
        method is expected to provide a mechanism to switch back
        to the original user.
        """

    def has_user(self, username):
        """Whether the username exists in the virtual users table."""
        return username in self.user_table

    def has_perm(self, username, perm, path=None):
        """Whether the user has permission over path (an absolute
        pathname of a file or a directory).

        Expected perm argument is one of the following letters:
        "elradfmw".
        """
        if path is None:
            return perm in self.user_table[username]['perm']

        path = os.path.normcase(path)
        for dir in self.user_table[username]['operms'].keys():
            operm, recursive = self.user_table[username]['operms'][dir]
            if self._issubpath(path, dir):
                if recursive:
                    return perm in operm
                if (path == dir) or (os.path.dirname(path) == dir \
                and not os.path.isdir(path)):
                    return perm in operm

        return perm in self.user_table[username]['perm']

    def get_perms(self, username):
        """Return current user permissions."""
        return self.user_table[username]['perm']

    def get_home_dir(self, username):
        """Return the user's home directory."""
        return self.user_table[username]['home']

    def get_msg_login(self, username):
        """Return the user's login message."""
        return self.user_table[username]['msg_login']

    def get_msg_quit(self, username):
        """Return the user's quitting message."""
        return self.user_table[username]['msg_quit']

    def _check_permissions(self, username, perm):
        warned = 0
        for p in perm:
            if p not in self.read_perms + self.write_perms:
                raise AuthorizerError('No such permission "%s"' %p)
            if (username == 'anonymous') and (p in self.write_perms) and not warned:
                warnings.warn("Write permissions assigned to anonymous user.",
                              RuntimeWarning)
                warned = 1

    def _issubpath(self, a, b):
        """Return True if a is a sub-path of b or if the paths are equal."""
        p1 = a.rstrip(os.sep).split(os.sep)
        p2 = b.rstrip(os.sep).split(os.sep)
        return p1[:len(p2)] == p2



# --- DTP classes

class PassiveDTP(asyncore.dispatcher):
    """This class is an asyncore.disptacher subclass.  It creates a
    socket listening on a local port, dispatching the resultant
    connection to DTPHandler.

     - (int) timeout: the timeout for a remote client to establish
       connection with the listening socket. Defaults to 30 seconds.
    """
    timeout = 30

    def __init__(self, cmd_channel, extmode=False):
        """Initialize the passive data server.

         - (instance) cmd_channel: the command channel class instance.
         - (bool) extmode: wheter use extended passive mode response type.
        """
        asyncore.dispatcher.__init__(self)
        self.cmd_channel = cmd_channel
        if self.timeout:
            self.idler = CallLater(self.timeout, self.handle_timeout)
        else:
            self.idler = None

        ip = self.cmd_channel.getsockname()[0]
        self.create_socket(self.cmd_channel.af, socket.SOCK_STREAM)

        if self.cmd_channel.passive_ports is None:
            # By using 0 as port number value we let kernel choose a
            # free unprivileged random port.
            self.bind((ip, 0))
        else:
            ports = list(self.cmd_channel.passive_ports)
            while ports:
                port = ports.pop(random.randint(0, len(ports) -1))
                try:
                    self.bind((ip, port))
                except socket.error, why:
                    if why[0] == errno.EADDRINUSE:  # port already in use
                        if ports:
                            continue
                        # If cannot use one of the ports in the configured
                        # range we'll use a kernel-assigned port, and log
                        # a message reporting the issue.
                        # By using 0 as port number value we let kernel
                        # choose a free unprivileged random port.
                        else:
                            self.bind((ip, 0))
                            self.cmd_channel.log(
                                "Can't find a valid passive port in the "
                                "configured range. A random kernel-assigned "
                                "port will be used."
                                )
                    else:
                        raise
                else:
                    break
        self.listen(5)
        port = self.socket.getsockname()[1]
        if not extmode:
            if self.cmd_channel.masquerade_address:
                ip = self.cmd_channel.masquerade_address
            # The format of 227 response in not standardized.
            # This is the most expected:
            self.cmd_channel.respond('227 Entering passive mode (%s,%d,%d).' %(
                    ip.replace('.', ','), port / 256, port % 256))
        else:
            self.cmd_channel.respond('229 Entering extended passive mode '
                                     '(|||%d|).' %port)

    # --- connection / overridden

    def handle_accept(self):
        """Called when remote client initiates a connection."""
        try:
            sock, addr = self.accept()
        except TypeError:
            # for some reason sometimes accept() returns None instead
            # of a socket
            return
        # Check the origin of data connection.  If not expressively
        # configured we drop the incoming data connection if remote
        # IP address does not match the client's IP address.
        if (self.cmd_channel.remote_ip != addr[0]):
            if not self.cmd_channel.permit_foreign_addresses:
                try:
                    sock.close()
                except socket.error:
                    pass
                msg = 'Rejected data connection from foreign address %s:%s.' \
                        %(addr[0], addr[1])
                self.cmd_channel.respond("425 %s" %msg)
                self.cmd_channel.log(msg)
                # do not close listening socket: it couldn't be client's blame
                return
            else:
                # site-to-site FTP allowed
                msg = 'Established data connection with foreign address %s:%s.'\
                        %(addr[0], addr[1])
                self.cmd_channel.log(msg)
        # Immediately close the current channel (we accept only one
        # connection at time) and avoid running out of max connections
        # limit.
        self.close()
        # delegate such connection to DTP handler
        handler = self.cmd_channel.dtp_handler(sock, self.cmd_channel)
        self.cmd_channel.data_channel = handler
        self.cmd_channel.on_dtp_connection()

    def handle_timeout(self):
        self.cmd_channel.respond("421 Passive data channel timed out.")
        self.close()

    def writable(self):
        return 0

    def handle_error(self):
        """Called to handle any uncaught exceptions."""
        try:
            raise
        except (KeyboardInterrupt, SystemExit, asyncore.ExitNow):
            raise
        logerror(traceback.format_exc())
        self.close()

    def close(self):
        if self.idler is not None and not self.idler.cancelled:
            self.idler.cancel()
        asyncore.dispatcher.close(self)


class ActiveDTP(asyncore.dispatcher):
    """This class is an asyncore.disptacher subclass. It creates a
    socket resulting from the connection to a remote user-port,
    dispatching it to DTPHandler.

     - (int) timeout: the timeout for us to establish connection with
       the client's listening data socket.
    """
    timeout = 30

    def __init__(self, ip, port, cmd_channel):
        """Initialize the active data channel attemping to connect
        to remote data socket.

         - (str) ip: the remote IP address.
         - (int) port: the remote port.
         - (instance) cmd_channel: the command channel class instance.
        """
        asyncore.dispatcher.__init__(self)
        self.cmd_channel = cmd_channel
        if self.timeout:
            self.idler = CallLater(self.timeout, self.handle_timeout)
        else:
            self.idler = None
        self.create_socket(self.cmd_channel.af, socket.SOCK_STREAM)
        try:
            self.connect((ip, port))
        except socket.gaierror:
            self.cmd_channel.respond("425 Can't connect to specified address.")
            self.close()

    # --- connection / overridden

    # NOOP, overridden to prevent unhandled read/write event
    # messages to be printed on Python < 2.6

    def handle_write(self):
        pass

    def handle_read(self):
        pass

    def handle_connect(self):
        """Called when connection is established."""
        if self.idler is not None and not self.idler.cancelled:
            self.idler.cancel()
        self.cmd_channel.respond('200 Active data connection established.')
        # delegate such connection to DTP handler
        handler = self.cmd_channel.dtp_handler(self.socket, self.cmd_channel)
        self.cmd_channel.data_channel = handler
        self.cmd_channel.on_dtp_connection()
        #self.close()  # <-- (done automatically)

    def handle_timeout(self):
        self.cmd_channel.respond("421 Active data channel timed out.")
        self.close()

    def handle_expt(self):
        self.cmd_channel.respond("425 Can't connect to specified address.")
        self.close()

    def handle_error(self):
        """Called to handle any uncaught exceptions."""
        try:
            raise
        except (KeyboardInterrupt, SystemExit, asyncore.ExitNow):
            raise
        except socket.error:
            pass
        except:
            logerror(traceback.format_exc())
        self.cmd_channel.respond("425 Can't connect to specified address.")
        self.close()

    def close(self):
        if self.idler is not None and not self.idler.cancelled:
            self.idler.cancel()
        asyncore.dispatcher.close(self)


try:
    from collections import deque
except ImportError:
    # backward compatibility with Python < 2.4 by replacing deque with a list
    class deque(list):
        def appendleft(self, obj):
            list.insert(self, 0, obj)


class DTPHandler(asyncore.dispatcher):
    """Class handling server-data-transfer-process (server-DTP, see
    RFC-959) managing data-transfer operations involving sending
    and receiving data.

    Class attributes:

     - (int) timeout: the timeout which roughly is the maximum time we
       permit data transfers to stall for with no progress. If the
       timeout triggers, the remote client will be kicked off
       (defaults 300).

     - (int) ac_in_buffer_size: incoming data buffer size (defaults 65536)

     - (int) ac_out_buffer_size: outgoing data buffer size (defaults 65536)

    DTPHandler implementation note:

    When a producer is consumed and close_when_done() has been called
    previously, refill_buffer() erroneously calls close() instead of
    handle_close() - (see: http://bugs.python.org/issue1740572)

    To avoid this problem DTPHandler is implemented as a subclass of
    asyncore.dispatcher instead of asynchat.async_chat.
    This implementation follows the same approach that asynchat module
    should use in Python 2.6.

    The most important change in the implementation is related to
    producer_fifo, which is a pure deque object instead of a
    producer_fifo instance.

    Since we don't want to break backward compatibily with older python
    versions (deque has been introduced in Python 2.4), if deque is not
    available we use a list instead.
    """

    timeout = 300
    ac_in_buffer_size = 65536
    ac_out_buffer_size = 65536

    def __init__(self, sock_obj, cmd_channel):
        """Initialize the command channel.

         - (instance) sock_obj: the socket object instance of the newly
            established connection.
         - (instance) cmd_channel: the command channel class instance.
        """
        asyncore.dispatcher.__init__(self, sock_obj)
        # we toss the use of the asynchat's "simple producer" and
        # replace it  with a pure deque, which the original fifo
        # was a wrapping of
        self.producer_fifo = deque()

        self.cmd_channel = cmd_channel
        self.file_obj = None
        self.receive = False
        self.transfer_finished = False
        self.tot_bytes_sent = 0
        self.tot_bytes_received = 0
        self.data_wrapper = lambda x: x
        self._lastdata = 0
        self._closed = False
        if self.timeout:
            self.idler = CallLater(self.timeout, self.handle_timeout)
        else:
            self.idler = None

    # --- utility methods

    def enable_receiving(self, type):
        """Enable receiving of data over the channel. Depending on the
        TYPE currently in use it creates an appropriate wrapper for the
        incoming data.

         - (str) type: current transfer type, 'a' (ASCII) or 'i' (binary).
        """
        if type == 'a':
            if os.linesep == '\r\n':
                self.data_wrapper = lambda x: x
            else:
                self.data_wrapper = lambda x: x.replace('\r\n', os.linesep)
        elif type == 'i':
            self.data_wrapper = lambda x: x
        else:
            raise TypeError, "Unsupported type"
        self.receive = True

    def get_transmitted_bytes(self):
        "Return the number of transmitted bytes."
        return self.tot_bytes_sent + self.tot_bytes_received

    def transfer_in_progress(self):
        "Return True if a transfer is in progress, else False."
        return self.get_transmitted_bytes() != 0

    # --- connection

    def handle_read(self):
        """Called when there is data waiting to be read."""
        try:
            chunk = self.recv(self.ac_in_buffer_size)
        except socket.error:
            self.handle_error()
        else:
            self.tot_bytes_received += len(chunk)
            if not chunk:
                self.transfer_finished = True
                #self.close()  # <-- asyncore.recv() already do that...
                return
            # while we're writing on the file an exception could occur
            # in case  that filesystem gets full;  if this happens we
            # let handle_error() method handle this exception, providing
            # a detailed error message.
            self.file_obj.write(self.data_wrapper(chunk))

    def handle_write(self):
        """Called when data is ready to be written, initiates send."""
        self.initiate_send()

    def push(self, data):
        """Push data onto the deque and initiate send."""
        sabs = self.ac_out_buffer_size
        if len(data) > sabs:
            for i in xrange(0, len(data), sabs):
                self.producer_fifo.append(data[i:i+sabs])
        else:
            self.producer_fifo.append(data)
        self.initiate_send()

    def push_with_producer(self, producer):
        """Push data using a producer and initiate send."""
        self.producer_fifo.append(producer)
        self.initiate_send()

    def readable(self):
        """Predicate for inclusion in the readable for select()."""
        return self.receive

    def writable(self):
        """Predicate for inclusion in the writable for select()."""
        return self.producer_fifo or (not self.connected)

    def close_when_done(self):
        """Automatically close this channel once the outgoing queue is empty."""
        self.producer_fifo.append(None)

    def initiate_send(self):
        """Attempt to send data in fifo order."""
        while self.producer_fifo and self.connected:
            first = self.producer_fifo[0]
            # handle empty string/buffer or None entry
            if not first:
                del self.producer_fifo[0]
                if first is None:
                    self.transfer_finished = True
                    self.handle_close()
                    return

            # handle classic producer behavior
            obs = self.ac_out_buffer_size
            try:
                data = buffer(first, 0, obs)
            except TypeError:
                data = first.more()
                if data:
                    self.producer_fifo.appendleft(data)
                else:
                    del self.producer_fifo[0]
                continue

            # send the data
            try:
                num_sent = self.send(data)
            except socket.error:
                self.handle_error()
                return

            if num_sent:
                self.tot_bytes_sent += num_sent
                if num_sent < len(data) or obs < len(first):
                    self.producer_fifo[0] = first[num_sent:]
                else:
                    del self.producer_fifo[0]
            # we tried to send some actual data
            return

    def handle_timeout(self):
        """Called cyclically to check if data trasfer is stalling with
        no progress in which case the client is kicked off.
        """
        if self.get_transmitted_bytes() > self._lastdata:
            self._lastdata = self.get_transmitted_bytes()
            self.idler = CallLater(self.timeout, self.handle_timeout)
        else:
            msg = "Data connection timed out."
            self.cmd_channel.log(msg)
            self.cmd_channel.respond("421 " + msg)
            self.cmd_channel.close_when_done()
            self.close()

    def handle_expt(self):
        """Called on "exceptional" data events."""
        self.cmd_channel.respond("426 Connection error; transfer aborted.")
        self.close()

    def handle_error(self):
        """Called when an exception is raised and not otherwise handled."""
        try:
            raise
        except (KeyboardInterrupt, SystemExit, asyncore.ExitNow):
            raise
        except socket.error, err:
            # fix around asyncore bug (http://bugs.python.org/issue1736101)
            if err[0] in (errno.ECONNRESET, errno.ENOTCONN, errno.ESHUTDOWN, \
                          errno.ECONNABORTED):
                self.handle_close()
                return
            else:
                error = str(err[1])
        # an error could occur in case we fail reading / writing
        # from / to file (e.g. file system gets full)
        except EnvironmentError, err:
            error = _strerror(err)
        except:
            # some other exception occurred;  we don't want to provide
            # confidential error messages
            logerror(traceback.format_exc())
            error = "Internal error"
        self.cmd_channel.respond("426 %s; transfer aborted." %error)
        self.close()

    def handle_close(self):
        """Called when the socket is closed."""
        # If we used channel for receiving we assume that transfer is
        # finished when client close connection , if we used channel
        # for sending we have to check that all data has been sent
        # (responding with 226) or not (responding with 426).
        if self.receive:
            self.transfer_finished = True
            action = 'received'
        else:
            action = 'sent'
        if self.transfer_finished:
            self.cmd_channel.respond("226 Transfer complete.")
            if self.file_obj:
                fname = self.cmd_channel.fs.fs2ftp(self.file_obj.name)
                self.cmd_channel.log('"%s" %s.' %(fname, action))
        else:
            tot_bytes = self.get_transmitted_bytes()
            msg = "Transfer aborted; %d bytes transmitted." %tot_bytes
            self.cmd_channel.respond("426 " + msg)
            self.cmd_channel.log(msg)
        self.close()

    def close(self):
        """Close the data channel, first attempting to close any remaining
        file handles."""
        if not self._closed:
            self._closed = True
            if self.file_obj is not None and not self.file_obj.closed:
                self.file_obj.close()
            if self.idler is not None and not self.idler.cancelled:
                self.idler.cancel()
            asyncore.dispatcher.close(self)
            if self.file_obj is not None and self.transfer_finished:
                if self.receive:
                    self.cmd_channel.on_file_received(self.file_obj.name)
                else:
                    self.cmd_channel.on_file_sent(self.file_obj.name)
            self.cmd_channel.on_dtp_close()


# --- producers

class FileProducer:
    """Producer wrapper for file[-like] objects."""

    buffer_size = 65536

    def __init__(self, file, type):
        """Initialize the producer with a data_wrapper appropriate to TYPE.

         - (file) file: the file[-like] object.
         - (str) type: the current TYPE, 'a' (ASCII) or 'i' (binary).
        """
        self.done = False
        self.file = file
        if type == 'a':
            if os.linesep == '\r\n':
                self.data_wrapper = lambda x: x
            else:
                self.data_wrapper = lambda x: x.replace(os.linesep, '\r\n')
        elif type == 'i':
            self.data_wrapper = lambda x: x
        else:
            raise TypeError, "Unsupported type"

    def more(self):
        """Attempt a chunk of data of size self.buffer_size."""
        if self.done:
            return ''
        data = self.data_wrapper(self.file.read(self.buffer_size))
        if not data:
            self.done = True
            if not self.file.closed:
                self.file.close()
        return data


class BufferedIteratorProducer:
    """Producer for iterator objects with buffer capabilities."""
    # how many times iterator.next() will be called before
    # returning some data
    loops = 20

    def __init__(self, iterator):
        self.iterator = iterator

    def more(self):
        """Attempt a chunk of data from iterator by calling
        its next() method different times.
        """
        buffer = []
        for x in xrange(self.loops):
            try:
                buffer.append(self.iterator.next())
            except StopIteration:
                break
        return ''.join(buffer)


# --- filesystem

class AbstractedFS:
    """A class used to interact with the file system, providing a high
    level, cross-platform interface compatible with both Windows and
    UNIX style filesystems.

    It provides some utility methods and some wraps around operations
    involved in file creation and file system operations like moving
    files or removing directories.

    Instance attributes:
     - (str) root: the user home directory.
     - (str) cwd: the current working directory.
     - (str) rnfr: source file to be renamed.
    """

    def __init__(self):
        self.root = None
        self.cwd = '/'
        self.rnfr = None

    # --- Pathname / conversion utilities

    def ftpnorm(self, ftppath):
        """Normalize a "virtual" ftp pathname (tipically the raw string
        coming from client) depending on the current working directory.

        Example (having "/foo" as current working directory):
        'x' -> '/foo/x'

        Note: directory separators are system independent ("/").
        Pathname returned is always absolutized.
        """
        if os.path.isabs(ftppath):
            p = os.path.normpath(ftppath)
        else:
            p = os.path.normpath(os.path.join(self.cwd, ftppath))
        # normalize string in a standard web-path notation having '/'
        # as separator.
        p = p.replace("\\", "/")
        # os.path.normpath supports UNC paths (e.g. "//a/b/c") but we
        # don't need them.  In case we get an UNC path we collapse
        # redundant separators appearing at the beginning of the string
        while p[:2] == '//':
            p = p[1:]
        # Anti path traversal: don't trust user input, in the event
        # that self.cwd is not absolute, return "/" as a safety measure.
        # This is for extra protection, maybe not really necessary.
        if not os.path.isabs(p):
            p = "/"
        return p

    def ftp2fs(self, ftppath):
        """Translate a "virtual" ftp pathname (tipically the raw string
        coming from client) into equivalent absolute "real" filesystem
        pathname.

        Example (having "/home/user" as root directory):
        'x' -> '/home/user/x'

        Note: directory separators are system dependent.
        """
        # as far as I know, it should always be path traversal safe...
        if os.path.normpath(self.root) == os.sep:
            return os.path.normpath(self.ftpnorm(ftppath))
        else:
            p = self.ftpnorm(ftppath)[1:]
            return os.path.normpath(os.path.join(self.root, p))

    def fs2ftp(self, fspath):
        """Translate a "real" filesystem pathname into equivalent
        absolute "virtual" ftp pathname depending on the user's
        root directory.

        Example (having "/home/user" as root directory):
        '/home/user/x' -> '/x'

        As for ftpnorm, directory separators are system independent
        ("/") and pathname returned is always absolutized.

        On invalid pathnames escaping from user's root directory
        (e.g. "/home" when root is "/home/user") always return "/".
        """
        if os.path.isabs(fspath):
            p = os.path.normpath(fspath)
        else:
            p = os.path.normpath(os.path.join(self.root, fspath))
        if not self.validpath(p):
            return '/'
        p = p.replace(os.sep, "/")
        p = p[len(self.root):]
        if not p.startswith('/'):
            p = '/' + p
        return p

    # alias for backward compatibility with 0.2.0
    normalize = ftpnorm
    translate = ftp2fs

    def validpath(self, path):
        """Check whether the path belongs to user's home directory.
        Expected argument is a "real" filesystem pathname.

        If path is a symbolic link it is resolved to check its real
        destination.

        Pathnames escaping from user's root directory are considered
        not valid.
        """
        root = self.realpath(self.root)
        path = self.realpath(path)
        if not self.root.endswith(os.sep):
            root = self.root + os.sep
        if not path.endswith(os.sep):
            path = path + os.sep
        if path[0:len(root)] == root:
            return True
        return False

    # --- Wrapper methods around open() and tempfile.mkstemp

    def open(self, filename, mode):
        """Open a file returning its handler."""
        return open(filename, mode)

    def mkstemp(self, suffix='', prefix='', dir=None, mode='wb'):
        """A wrap around tempfile.mkstemp creating a file with a unique
        name.  Unlike mkstemp it returns an object with a file-like
        interface.
        """
        class FileWrapper:
            def __init__(self, fd, name):
                self.file = fd
                self.name = name
            def __getattr__(self, attr):
                return getattr(self.file, attr)

        text = not 'b' in mode
        # max number of tries to find out a unique file name
        tempfile.TMP_MAX = 50
        fd, name = tempfile.mkstemp(suffix, prefix, dir, text=text)
        file = os.fdopen(fd, mode)
        return FileWrapper(file, name)

    # --- Wrapper methods around os.*

    def chdir(self, path):
        """Change the current directory."""
        # temporarily join the specified directory to see if we have
        # permissions to do so
        basedir = os.getcwd()
        try:
            os.chdir(path)
        except os.error:
            raise
        else:
            os.chdir(basedir)
            self.cwd = self.fs2ftp(path)

    def mkdir(self, path):
        """Create the specified directory."""
        os.mkdir(path)

    def listdir(self, path):
        """List the content of a directory."""
        return os.listdir(path)

    def rmdir(self, path):
        """Remove the specified directory."""
        os.rmdir(path)

    def remove(self, path):
        """Remove the specified file."""
        os.remove(path)

    def rename(self, src, dst):
        """Rename the specified src file to the dst filename."""
        os.rename(src, dst)

    def stat(self, path):
        """Perform a stat() system call on the given path."""
        return os.stat(path)

    def lstat(self, path):
        """Like stat but does not follow symbolic links."""
        return os.lstat(path)

    if not hasattr(os, 'lstat'):
        lstat = stat

    # --- Wrapper methods around os.path.*

    def isfile(self, path):
        """Return True if path is a file."""
        return os.path.isfile(path)

    def islink(self, path):
        """Return True if path is a symbolic link."""
        return os.path.islink(path)

    def isdir(self, path):
        """Return True if path is a directory."""
        return os.path.isdir(path)

    def getsize(self, path):
        """Return the size of the specified file in bytes."""
        return os.path.getsize(path)

    def getmtime(self, path):
        """Return the last modified time as a number of seconds since
        the epoch."""
        return os.path.getmtime(path)

    def realpath(self, path):
        """Return the canonical version of path eliminating any
        symbolic links encountered in the path (if they are
        supported by the operating system).
        """
        return os.path.realpath(path)

    def lexists(self, path):
        """Return True if path refers to an existing path, including
        a broken or circular symbolic link.
        """
        if hasattr(os.path, 'lexists'):
            return os.path.lexists(path)
        # grant backward compatibility with python 2.3
        elif hasattr(os, 'lstat'):
            try:
                os.lstat(path)
            except os.error:
                return False
            return True
        # fallback
        else:
            return os.path.exists(path)

    exists = lexists  # alias for backward compatibility with 0.2.0

    # --- Listing utilities

    # note: the following operations are no more blocking

    def get_list_dir(self, path):
        """"Return an iterator object that yields a directory listing
        in a form suitable for LIST command.
        """
        if self.isdir(path):
            listing = self.listdir(path)
            listing.sort()
            return self.format_list(path, listing)
        # if path is a file or a symlink we return information about it
        else:
            basedir, filename = os.path.split(path)
            self.lstat(path)  # raise exc in case of problems
            return self.format_list(basedir, [filename])

    def format_list(self, basedir, listing, ignore_err=True):
        """Return an iterator object that yields the entries of given
        directory emulating the "/bin/ls -lA" UNIX command output.

         - (str) basedir: the absolute dirname.
         - (list) listing: the names of the entries in basedir
         - (bool) ignore_err: when False raise exception if os.lstat()
         call fails.

        On platforms which do not support the pwd and grp modules (such
        as Windows), ownership is printed as "owner" and "group" as a
        default, and number of hard links is always "1". On UNIX
        systems, the actual owner, group, and number of links are
        printed.

        This is how output appears to client:

        -rw-rw-rw-   1 owner   group    7045120 Sep 02  3:47 music.mp3
        drwxrwxrwx   1 owner   group          0 Aug 31 18:50 e-books
        -rw-rw-rw-   1 owner   group        380 Sep 02  3:40 module.py
        """
        for basename in listing:
            file = os.path.join(basedir, basename)
            try:
                st = self.lstat(file)
            except os.error:
                if ignore_err:
                    continue
                raise
            perms = filemode(st.st_mode)  # permissions
            nlinks = st.st_nlink  # number of links to inode
            if not nlinks:  # non-posix system, let's use a bogus value
                nlinks = 1
            size = st.st_size  # file size
            if pwd and grp:
                # get user and group name, else just use the raw uid/gid
                try:
                    uname = pwd.getpwuid(st.st_uid).pw_name
                except KeyError:
                    uname = st.st_uid
                try:
                    gname = grp.getgrgid(st.st_gid).gr_name
                except KeyError:
                    gname = st.st_gid
            else:
                # on non-posix systems the only chance we use default
                # bogus values for owner and group
                uname = "owner"
                gname = "group"
            try:
                mtime = time.strftime("%b %d %H:%M", time.localtime(st.st_mtime))
            except ValueError:
                # It could be raised if last mtime happens to be too
                # old (prior to year 1900) in which case we return
                # the current time as last mtime.
                mtime = time.strftime("%b %d %H:%M")
            # if the file is a symlink, resolve it, e.g. "symlink -> realfile"
            if stat.S_ISLNK(st.st_mode) and hasattr(os, 'readlink'):
                basename = basename + " -> " + os.readlink(file)

            # formatting is matched with proftpd ls output
            yield "%s %3s %-8s %-8s %8s %s %s\r\n" %(perms, nlinks, uname, gname,
                                                     size, mtime, basename)

    def format_mlsx(self, basedir, listing, perms, facts, ignore_err=True):
        """Return an iterator object that yields the entries of a given
        directory or of a single file in a form suitable with MLSD and
        MLST commands.

        Every entry includes a list of "facts" referring the listed
        element.  See RFC-3659, chapter 7, to see what every single
        fact stands for.

         - (str) basedir: the absolute dirname.
         - (list) listing: the names of the entries in basedir
         - (str) perms: the string referencing the user permissions.
         - (str) facts: the list of "facts" to be returned.
         - (bool) ignore_err: when False raise exception if os.stat()
         call fails.

        Note that "facts" returned may change depending on the platform
        and on what user specified by using the OPTS command.

        This is how output could appear to the client issuing
        a MLSD request:

        type=file;size=156;perm=r;modify=20071029155301;unique=801cd2; music.mp3
        type=dir;size=0;perm=el;modify=20071127230206;unique=801e33; ebooks
        type=file;size=211;perm=r;modify=20071103093626;unique=801e32; module.py
        """
        permdir = ''.join([x for x in perms if x not in 'arw'])
        permfile = ''.join([x for x in perms if x not in 'celmp'])
        if ('w' in perms) or ('a' in perms) or ('f' in perms):
            permdir += 'c'
        if 'd' in perms:
            permdir += 'p'
        type = size = perm = modify = create = unique = mode = uid = gid = ""
        for basename in listing:
            file = os.path.join(basedir, basename)
            try:
                st = self.stat(file)
            except OSError:
                if ignore_err:
                    continue
                raise
            # type + perm
            if stat.S_ISDIR(st.st_mode):
                if 'type' in facts:
                    if basename == '.':
                        type = 'type=cdir;'
                    elif basename == '..':
                        type = 'type=pdir;'
                    else:
                        type = 'type=dir;'
                if 'perm' in facts:
                    perm = 'perm=%s;' %permdir
            else:
                if 'type' in facts:
                    type = 'type=file;'
                if 'perm' in facts:
                    perm = 'perm=%s;' %permfile
            if 'size' in facts:
                size = 'size=%s;' %st.st_size  # file size
            # last modification time
            if 'modify' in facts:
                try:
                    modify = 'modify=%s;' %time.strftime("%Y%m%d%H%M%S",
                                           time.localtime(st.st_mtime))
                # it could be raised if last mtime happens to be too old
                # (prior to year 1900)
                except ValueError:
                    modify = ""
            if 'create' in facts:
                # on Windows we can provide also the creation time
                try:
                    create = 'create=%s;' %time.strftime("%Y%m%d%H%M%S",
                                           time.localtime(st.st_ctime))
                except ValueError:
                    create = ""
            # UNIX only
            if 'unix.mode' in facts:
                mode = 'unix.mode=%s;' %oct(st.st_mode & 0777)
            if 'unix.uid' in facts:
                uid = 'unix.uid=%s;' %st.st_uid
            if 'unix.gid' in facts:
                gid = 'unix.gid=%s;' %st.st_gid
            # We provide unique fact (see RFC-3659, chapter 7.5.2) on
            # posix platforms only; we get it by mixing st_dev and
            # st_ino values which should be enough for granting an
            # uniqueness for the file listed.
            # The same approach is used by pure-ftpd.
            # Implementors who want to provide unique fact on other
            # platforms should use some platform-specific method (e.g.
            # on Windows NTFS filesystems MTF records could be used).
            if 'unique' in facts:
                unique = "unique=%x%x;" %(st.st_dev, st.st_ino)

            yield "%s%s%s%s%s%s%s%s%s %s\r\n" %(type, size, perm, modify, create,
                                                mode, uid, gid, unique, basename)


# --- FTP

class FTPHandler(asynchat.async_chat):
    """Implements the FTP server Protocol Interpreter (see RFC-959),
    handling commands received from the client on the control channel.

    All relevant session information is stored in class attributes
    reproduced below and can be modified before instantiating this
    class.

     - (int) timeout:
       The timeout which is the maximum time a remote client may spend
       between FTP commands. If the timeout triggers, the remote client
       will be kicked off.  Defaults to 300 seconds.

     - (str) banner: the string sent when client connects.

     - (int) max_login_attempts:
        the maximum number of wrong authentications before disconnecting
        the client (default 3).

     - (bool)permit_foreign_addresses:
        FTP site-to-site transfer feature: also referenced as "FXP" it
        permits for transferring a file between two remote FTP servers
        without the transfer going through the client's host (not
        recommended for security reasons as described in RFC-2577).
        Having this attribute set to False means that all data
        connections from/to remote IP addresses which do not match the
        client's IP address will be dropped (defualt False).

     - (bool) permit_privileged_ports:
        set to True if you want to permit active data connections (PORT)
        over privileged ports (not recommended, defaulting to False).

     - (str) masquerade_address:
        the "masqueraded" IP address to provide along PASV reply when
        pyftpdlib is running behind a NAT or other types of gateways.
        When configured pyftpdlib will hide its local address and
        instead use the public address of your NAT (default None).

     - (list) passive_ports:
        what ports ftpd will use for its passive data transfers.
        Value expected is a list of integers (e.g. range(60000, 65535)).
        When configured pyftpdlib will no longer use kernel-assigned
        random ports (default None).


    All relevant instance attributes initialized when client connects
    are reproduced below.  You may be interested in them in case you
    want to subclass the original FTPHandler.

     - (bool) authenticated: True if client authenticated himself.
     - (str) username: the name of the connected user (if any).
     - (int) attempted_logins: number of currently attempted logins.
     - (str) current_type: the current transfer type (default "a")
     - (int) af: the address family (IPv4/IPv6)
     - (instance) server: the FTPServer class instance.
     - (instance) data_server: the data server instance (if any).
     - (instance) data_channel: the data channel instance (if any).
    """
    # these are overridable defaults

    # default classes
    authorizer = DummyAuthorizer()
    active_dtp = ActiveDTP
    passive_dtp = PassiveDTP
    dtp_handler = DTPHandler
    abstracted_fs = AbstractedFS

    # session attributes (explained in the docstring)
    timeout = 300
    banner = "pyftpdlib %s ready." %__ver__
    max_login_attempts = 3
    permit_foreign_addresses = False
    permit_privileged_ports = False
    masquerade_address = None
    passive_ports = None

    def __init__(self, conn, server):
        """Initialize the command channel.

         - (instance) conn: the socket object instance of the newly
            established connection.
         - (instance) server: the ftp server class instance.
        """
        asynchat.async_chat.__init__(self, conn)
        self.set_terminator("\r\n")
        # try to handle urgent data inline
        try:
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_OOBINLINE, 1)
        except socket.error:
            pass

        # public session attributes
        self.server = server
        self.remote_ip, self.remote_port = self.socket.getpeername()[:2]
        self.fs = self.abstracted_fs()
        self.authenticated = False
        self.username = ""
        self.password = ""
        self.attempted_logins = 0
        self.current_type = 'a'
        self.restart_position = 0
        self.quit_pending = False
        self.sleeping = False
        self.data_server = None
        self.data_channel = None
        if self.timeout:
            self.idler = CallLater(self.timeout, self.handle_timeout)
        else:
            self.idler = None
        if hasattr(self.socket, 'family'):
            self.af = self.socket.family
        else:  # python < 2.5
            ip, port = self.socket.getsockname()[:2]
            self.af = socket.getaddrinfo(ip, port, socket.AF_UNSPEC,
                                         socket.SOCK_STREAM)[0][0]

        # private session attributes
        self._in_buffer = []
        self._in_buffer_len = 0
        self._epsvall = False
        self._in_dtp_queue = None
        self._out_dtp_queue = None
        self._closed = False
        self._extra_feats = []
        self._current_facts = ['type', 'perm', 'size', 'modify']
        if os.name == 'posix':
            self._current_facts.append('unique')
        self._available_facts = self._current_facts[:]
        if pwd and grp:
            self._available_facts += ['unix.mode', 'unix.uid', 'unix.gid']
        if os.name == 'nt':
            self._available_facts.append('create')

    def handle(self):
        """Return a 220 'Ready' response to the client over the command
        channel.
        """
        if len(self.banner) <= 75:
            self.respond("220 %s" %str(self.banner))
        else:
            self.push('220-%s\r\n' %str(self.banner))
            self.respond('220 ')

    def handle_max_cons(self):
        """Called when limit for maximum number of connections is reached."""
        msg = "Too many connections. Service temporary unavailable."
        self.respond("421 %s" %msg)
        self.log(msg)
        # If self.push is used, data could not be sent immediately in
        # which case a new "loop" will occur exposing us to the risk of
        # accepting new connections.  Since this could cause asyncore to
        # run out of fds (...and exposes the server to DoS attacks), we
        # immediately close the channel by using close() instead of
        # close_when_done(). If data has not been sent yet client will
        # be silently disconnected.
        self.close()

    def handle_max_cons_per_ip(self):
        """Called when too many clients are connected from the same IP."""
        msg = "Too many connections from the same IP address."
        self.respond("421 %s" %msg)
        self.log(msg)
        self.close_when_done()

    def handle_timeout(self):
        """Called when client does not send any command within the time
        specified in <timeout> attribute."""
        msg = "Control connection timed out."
        self.log(msg)
        self.respond("421 " + msg)
        self.close_when_done()

    # --- asyncore / asynchat overridden methods

    def readable(self):
        # if there's a quit pending we stop reading data from socket
        return not self.sleeping

    def collect_incoming_data(self, data):
        """Read incoming data and append to the input buffer."""
        self._in_buffer.append(data)
        self._in_buffer_len += len(data)
        # Flush buffer if it gets too long (possible DoS attacks).
        # RFC-959 specifies that a 500 response could be given in
        # such cases
        buflimit = 2048
        if self._in_buffer_len > buflimit:
            self.respond('500 Command too long.')
            self.log('Command received exceeded buffer limit of %s.' %(buflimit))
            self._in_buffer = []
            self._in_buffer_len = 0

    def found_terminator(self):
        r"""Called when the incoming data stream matches the \r\n
        terminator.

        Depending on the command received it calls the command's
        corresponding method (e.g. for received command "MKD pathname",
        ftp_MKD() method is called with "pathname" as the argument).
        """
        if self.idler is not None and not self.idler.cancelled:
            self.idler.reset()

        line = ''.join(self._in_buffer)
        self._in_buffer = []
        self._in_buffer_len = 0

        cmd = line.split(' ')[0].upper()
        arg = line[len(cmd)+1:]
        if cmd == "SITE" and arg:
            cmd = "SITE %s" %arg.split(' ')[0].upper()
            arg = line[len(cmd)+1:]

        if cmd != 'PASS':
            self.logline("<== %s" %line)
        else:
            self.logline("<== %s %s" %(line.split(' ')[0], '*' * 6))

        # Recognize those commands having a "special semantic". They
        # should be sent by following the RFC-959 procedure of sending
        # Telnet IP/Synch sequence (chr 242 and 255) as OOB data but
        # since many ftp clients don't do it correctly we check the
        # last 4 characters only.
        if not cmd in proto_cmds:
            if cmd[-4:] in ('ABOR', 'STAT', 'QUIT'):
                cmd = cmd[-4:]
            else:
                self.respond('500 Command "%s" not understood.' %cmd)
                return

        if not arg and proto_cmds[cmd].arg_needed is True:
            self.respond("501 Syntax error: command needs an argument.")
            return
        if arg and proto_cmds[cmd].arg_needed is False:
            self.respond("501 Syntax error: command does not accept arguments.")
            return

        if not self.authenticated:
            if proto_cmds[cmd].auth_needed or (cmd == 'STAT' and arg):
                self.respond("530 Log in with USER and PASS first.")
            else:
                method = getattr(self, 'ftp_' + cmd.replace(' ', '_'))
                method(arg)  # call the proper ftp_* method
        else:
            if cmd == 'STAT' and not arg:
                self.ftp_STAT('')
                return

            # for file-system related commands check whether real path
            # destination is valid                
            if proto_cmds[cmd].check_path and cmd != 'STOU':
                if cmd in ('CWD', 'XCWD'):
                    arg = arg or '/'
                elif cmd in ('CDUP', 'XCUP'):
                    arg = '..'
                elif cmd == 'LIST':
                    if arg.lower() in ('-a', '-l', '-al', '-la'):
                        arg = self.fs.cwd
                    else:
                        arg = arg or self.fs.cwd
                elif cmd == 'STAT':
                    if glob.has_magic(arg):
                        self.respond('550 Globbing not supported.')
                        return
                    arg = arg or self.fs.cwd
                else:  # LIST, NLST, MLSD, MLST
                    arg = arg or self.fs.cwd                                                
                if not self.fs.validpath(arg or '/'):
                    line = self.fs.ftpnorm(arg)
                    err = '"%s" points to a path which is outside ' \
                          "the user's root directory" %line
                    self.respond("550 %s." %err)
                    self.log('FAIL %s "%s". %s.' %(cmd, line, err))                    
                    return                
            # check permission
            perm = proto_cmds[cmd].perm
            if perm is not None and cmd != 'STOU':                
                if not self.authorizer.has_perm(self.username, perm, arg or '/'):
                    self.log('FAIL %s "%s". Not enough privileges.' \
                             %(cmd, self.fs.fs2ftp(line)))
                    self.respond("550 Can't %s. Not enough privileges." %cmd)
                    return            
            # call the proper ftp_* method
            method = getattr(self, 'ftp_' + cmd.replace(' ', '_'))
            method(arg)

    def handle_expt(self):
        """Called when there is out of band (OOB) data to be read.
        This could happen in case of such clients strictly following
        the RFC-959 directives of sending Telnet IP and Synch as OOB
        data before issuing ABOR, STAT and QUIT commands.
        It should never be called since the SO_OOBINLINE option is
        enabled except on some systems like FreeBSD where it doesn't
        seem to have effect.
        """
        if hasattr(socket, 'MSG_OOB'):
            try:
                data = self.socket.recv(1024, socket.MSG_OOB)
            except socket.error, why:
                if why[0] == errno.EINVAL:
                    return
            else:
                self._in_buffer.append(data)
                return
        self.log("Can't handle OOB data.")
        self.close()

    def handle_error(self):
        try:
            raise
        except (KeyboardInterrupt, SystemExit, asyncore.ExitNow):
            raise
        except socket.error, err:
            # fix around asyncore bug (http://bugs.python.org/issue1736101)
            if err[0] in (errno.ECONNRESET, errno.ENOTCONN, errno.ESHUTDOWN, \
                          errno.ECONNABORTED):
                self.handle_close()
                return
            else:
                logerror(traceback.format_exc())
        except:
            logerror(traceback.format_exc())
        self.close()

    def handle_close(self):
        self.close()

    def close(self):
        """Close the current channel disconnecting the client."""
        if not self._closed:
            self._closed = True
            if self.data_server is not None:
                self.data_server.close()
                del self.data_server

            if self.data_channel is not None:
                self.data_channel.close()
                del self.data_channel

            del self._out_dtp_queue
            del self._in_dtp_queue

            if self.idler is not None and not self.idler.cancelled:
                self.idler.cancel()

            # remove client IP address from ip map
            self.server.ip_map.remove(self.remote_ip)
            asynchat.async_chat.close(self)
            self.log("Disconnected.")

    # --- callbacks

    def on_file_sent(self, file):
        """Called every time a file has been succesfully sent.
        'file' is the complete filename of the file being sent.
        """

    def on_file_received(self, file):
        """Called every time a file has been succesfully received.
        'file' is the complete filename of the file being received.
        """

    def on_dtp_connection(self):
        """Called every time data channel connects (either active or
        passive).

        Incoming and outgoing queues are checked for pending data.
        If outbound data is pending, it is pushed into the data channel.
        If awaiting inbound data, the data channel is enabled for
        receiving.
        """
        if self.data_server is not None:
            self.data_server.close()
        self.data_server = None

        # stop the idle timer as long as the data transfer is not finished
        if self.idler is not None and not self.idler.cancelled:
            self.idler.cancel()

        # check for data to send
        if self._out_dtp_queue is not None:
            data, isproducer, file = self._out_dtp_queue
            self._out_dtp_queue = None
            if file:
                self.data_channel.file_obj = file
            try:
                if not isproducer:
                    self.data_channel.push(data)
                else:
                    self.data_channel.push_with_producer(data)
                if self.data_channel is not None:
                    self.data_channel.close_when_done()
            except:
                # dealing with this exception is up to DTP (see bug #84)
                self.data_channel.handle_error()

        # check for data to receive
        elif self._in_dtp_queue is not None:
            self.data_channel.file_obj = self._in_dtp_queue
            self.data_channel.enable_receiving(self.current_type)
            self._in_dtp_queue = None

    def on_dtp_close(self):
        """Called every time the data channel is closed."""
        self.data_channel = None
        if self.quit_pending:
            self.close_when_done()
        elif self.timeout:
            # data transfer finished, restart the idle timer
            self.idler = CallLater(self.timeout, self.handle_timeout)

    # --- utility

    def respond(self, resp):
        """Send a response to the client using the command channel."""
        self.push(resp + '\r\n')
        self.logline('==> %s' % resp)

    def push_dtp_data(self, data, isproducer=False, file=None):
        """Pushes data into the data channel.

        It is usually called for those commands requiring some data to
        be sent over the data channel (e.g. RETR).
        If data channel does not exist yet, it queues the data to send
        later; data will then be pushed into data channel when
        on_dtp_connection() will be called.

         - (str/classobj) data: the data to send which may be a string
            or a producer object).
         - (bool) isproducer: whether treat data as a producer.
         - (file) file: the file[-like] object to send (if any).
        """
        if self.data_channel is not None:
            self.respond("125 Data connection already open. Transfer starting.")
            if file:
                self.data_channel.file_obj = file
            try:
                if not isproducer:
                    self.data_channel.push(data)
                else:
                    self.data_channel.push_with_producer(data)
                if self.data_channel is not None:
                    self.data_channel.close_when_done()
            except:
                # dealing with this exception is up to DTP (see bug #84)
                self.data_channel.handle_error()
        else:
            self.respond("150 File status okay. About to open data connection.")
            self._out_dtp_queue = (data, isproducer, file)

    def log(self, msg):
        """Log a message, including additional identifying session data."""
        log("[%s]@%s:%s %s" %(self.username, self.remote_ip,
                              self.remote_port, msg))

    def logline(self, msg):
        """Log a line including additional indentifying session data."""
        logline("%s:%s %s" %(self.remote_ip, self.remote_port, msg))

    def flush_account(self):
        """Flush account information by clearing attributes that need
        to be reset on a REIN or new USER command.
        """
        if self.data_channel is not None:
            if not self.data_channel.transfer_in_progress():
                self.data_channel.close()
                self.data_channel = None
        if self.data_server is not None:
            self.data_server.close()
            self.data_server = None

        self.fs.rnfr = None
        self.authenticated = False
        self.username = ""
        self.password = ""
        self.attempted_logins = 0
        self.current_type = 'a'
        self.restart_position = 0
        self.quit_pending = False
        self.sleeping = False
        self._in_dtp_queue = None
        self._out_dtp_queue = None

    def run_as_current_user(self, function, *args, **kwargs):
        """Execute a function impersonating the current logged-in user."""
        self.authorizer.impersonate_user(self.username, self.password)
        try:
            return function(*args, **kwargs)
        finally:
            self.authorizer.terminate_impersonation()

        # --- connection

    def _make_eport(self, ip, port):
        """Establish an active data channel with remote client which
        issued a PORT or EPRT command.
        """
        # FTP bounce attacks protection: according to RFC-2577 it's
        # recommended to reject PORT if IP address specified in it
        # does not match client IP address.
        if not self.permit_foreign_addresses and ip != self.remote_ip:
            self.log("Rejected data connection to foreign address %s:%s."
                     %(ip, port))
            self.respond("501 Can't connect to a foreign address.")
            return

        # ...another RFC-2577 recommendation is rejecting connections
        # to privileged ports (< 1024) for security reasons.
        if not self.permit_privileged_ports and port < 1024:
            self.log('PORT against the privileged port "%s" refused.' %port)
            self.respond("501 Can't connect over a privileged port.")
            return

        # close existent DTP-server instance, if any.
        if self.data_server is not None:
            self.data_server.close()
            self.data_server = None
        if self.data_channel is not None:
            self.data_channel.close()
            self.data_channel = None

        # make sure we are not hitting the max connections limit
        if self.server.max_cons and len(self._map) >= self.server.max_cons:
            msg = "Too many connections. Can't open data channel."
            self.respond("425 %s" %msg)
            self.log(msg)
            return

        # open data channel
        self.active_dtp(ip, port, self)

    def _make_epasv(self, extmode=False):
        """Initialize a passive data channel with remote client which
        issued a PASV or EPSV command.
        If extmode argument is False we assume that client issued EPSV in
        which case extended passive mode will be used (see RFC-2428).
        """
        # close existing DTP-server instance, if any
        if self.data_server is not None:
            self.data_server.close()
            self.data_server = None

        if self.data_channel is not None:
            self.data_channel.close()
            self.data_channel = None

        # make sure we are not hitting the max connections limit
        if self.server.max_cons and len(self._map) >= self.server.max_cons:
            msg = "Too many connections. Can't open data channel."
            self.respond("425 %s" %msg)
            self.log(msg)
            return

        # open data channel
        self.data_server = self.passive_dtp(self, extmode)

    def ftp_PORT(self, line):
        """Start an active data channel by using IPv4."""
        if self._epsvall:
            self.respond("501 PORT not allowed after EPSV ALL.")
            return
        if self.af != socket.AF_INET:
            self.respond("425 You cannot use PORT on IPv6 connections. "
                         "Use EPRT instead.")
            return
        # Parse PORT request for getting IP and PORT.
        # Request comes in as:
        # > h1,h2,h3,h4,p1,p2
        # ...where the client's IP address is h1.h2.h3.h4 and the TCP
        # port number is (p1 * 256) + p2.
        try:
            addr = map(int, line.split(','))
            assert len(addr) == 6
            for x in addr[:4]:
                assert 0 <= x <= 255
            ip = '%d.%d.%d.%d' %tuple(addr[:4])
            port = (addr[4] * 256) + addr[5]
            assert 0 <= port <= 65535
        except (AssertionError, ValueError, OverflowError):
            self.respond("501 Invalid PORT format.")
            return
        self._make_eport(ip, port)

    def ftp_EPRT(self, line):
        """Start an active data channel by choosing the network protocol
        to use (IPv4/IPv6) as defined in RFC-2428.
        """
        if self._epsvall:
            self.respond("501 EPRT not allowed after EPSV ALL.")
            return
        # Parse EPRT request for getting protocol, IP and PORT.
        # Request comes in as:
        # # <d>proto<d>ip<d>port<d>
        # ...where <d> is an arbitrary delimiter character (usually "|") and
        # <proto> is the network protocol to use (1 for IPv4, 2 for IPv6).
        try:
            af, ip, port = line.split(line[0])[1:-1]
            port = int(port)
            assert 0 <= port <= 65535
        except (AssertionError, ValueError, IndexError, OverflowError):
            self.respond("501 Invalid EPRT format.")
            return

        if af == "1":
            if self.af != socket.AF_INET:
                self.respond('522 Network protocol not supported (use 2).')
            else:
                try:
                    octs = map(int, ip.split('.'))
                    assert len(octs) == 4
                    for x in octs:
                        assert 0 <= x <= 255
                except (AssertionError, ValueError, OverflowError):
                    self.respond("501 Invalid EPRT format.")
                else:
                    self._make_eport(ip, port)
        elif af == "2":
            if self.af == socket.AF_INET:
                self.respond('522 Network protocol not supported (use 1).')
            else:
                self._make_eport(ip, port)
        else:
            if self.af == socket.AF_INET:
                self.respond('501 Unknown network protocol (use 1).')
            else:
                self.respond('501 Unknown network protocol (use 2).')

    def ftp_PASV(self, line):
        """Start a passive data channel by using IPv4."""
        if self._epsvall:
            self.respond("501 PASV not allowed after EPSV ALL.")
            return
        if self.af != socket.AF_INET:
            self.respond("425 You cannot use PASV on IPv6 connections. "
                         "Use EPSV instead.")
        else:
            self._make_epasv(extmode=False)

    def ftp_EPSV(self, line):
        """Start a passive data channel by using IPv4 or IPv6 as defined
        in RFC-2428.
        """
        # RFC-2428 specifies that if an optional parameter is given,
        # we have to determine the address family from that otherwise
        # use the same address family used on the control connection.
        # In such a scenario a client may use IPv4 on the control channel
        # and choose to use IPv6 for the data channel.
        # But how could we use IPv6 on the data channel without knowing
        # which IPv6 address to use for binding the socket?
        # Unfortunately RFC-2428 does not provide satisfing information
        # on how to do that.  The assumption is that we don't have any way
        # to know wich address to use, hence we just use the same address
        # family used on the control connection.
        if not line:
            self._make_epasv(extmode=True)
        elif line == "1":
            if self.af != socket.AF_INET:
                self.respond('522 Network protocol not supported (use 2).')
            else:
                self._make_epasv(extmode=True)
        elif line == "2":
            if self.af == socket.AF_INET:
                self.respond('522 Network protocol not supported (use 1).')
            else:
                self._make_epasv(extmode=True)
        elif line.lower() == 'all':
            self._epsvall = True
            self.respond('220 Other commands other than EPSV are now disabled.')
        else:
            if self.af == socket.AF_INET:
                self.respond('501 Unknown network protocol (use 1).')
            else:
                self.respond('501 Unknown network protocol (use 2).')

    def ftp_QUIT(self, line):
        """Quit the current session disconnecting the client."""
        if self.authenticated:
            msg_quit = self.authorizer.get_msg_quit(self.username)
        else:
            msg_quit = "Goodbye."
        if len(msg_quit) <= 75:
            self.respond("221 %s" %msg_quit)
        else:
            self.push("221-%s\r\n" %msg_quit)
            self.respond("221 ")

        # From RFC-959:
        # If file transfer is in progress, the connection will remain
        # open for result response and the server will then close it.
        # We also stop responding to any further command.
        if self.data_channel:
            self.quit_pending = True
            self.sleeping = True
        else:
            self.close_when_done()

        # --- data transferring

    def ftp_LIST(self, line):
        """Return a list of files in the specified directory to the
        client.
        """
        # - If no argument, fall back on cwd as default.
        # - Some older FTP clients erroneously issue /bin/ls-like LIST
        #   formats in which case we fall back on cwd as default.
        datacr = None
        try:            
            datacr = self.fs.get_cr(line)
            path = self.fs.ftp2fs(line, datacr)
            line = self.fs.ftpnorm(line)
            iterator = self.run_as_current_user(self.fs.get_list_dir, path)            
        except OSError, err:
            why = _strerror(err)
            self.log('FAIL LIST "%s". %s.' %(line, why))
            self.respond('550 %s.' %why)
        else:
            self.log('OK LIST "%s". Transfer starting.' %line)
            producer = BufferedIteratorProducer(iterator)
            self.push_dtp_data(producer, isproducer=True)
        self.fs.close_cr(datacr)

    def ftp_NLST(self, line):
        """Return a list of files in the specified directory in a
        compact form to the client.
        """
        datacr = None
        try:            
            datacr = self.fs.get_cr(line)
            path = self.fs.ftp2fs(line, datacr)
            line = self.fs.ftpnorm(line)
            if self.fs.isdir(path):
                listing = self.run_as_current_user(self.fs.listdir, path)
                listing = map(lambda x:os.path.split(x.path)[1], listing)
            else:
                # if path is a file we just list its name
                self.fs.lstat(path)  # raise exc in case of problems
                basedir, filename = os.path.split(line)
                listing = [filename]            
        except OSError, err:
            why = _strerror(err)
            self.log('FAIL NLST "%s". %s.' %(line, why))
            self.respond('550 %s.' %why)
        else:
            data = ''
            if listing:
                listing.sort()
                data = '\r\n'.join(listing) + '\r\n'
            self.log('OK NLST "%s". Transfer starting.' %line)
            self.push_dtp_data(data)
        self.fs.close_cr(datacr)
        # --- MLST and MLSD commands

    # The MLST and MLSD commands are intended to standardize the file and
    # directory information returned by the server-FTP process.  These
    # commands differ from the LIST command in that the format of the
    # replies is strictly defined although extensible.

    def ftp_MLST(self, line):
        """Return information about a pathname in a machine-processable
        form as defined in RFC-3659.
        """ 
        datacr = None       
        try:            
            datacr = self.fs.get_cr(line)
            path = self.fs.ftp2fs(line, datacr)
            line = self.fs.ftpnorm(line)
            basedir, basename = os.path.split(path)
            perms = self.authorizer.get_perms(self.username)
            iterator = self.run_as_current_user(self.fs.format_mlsx, basedir,
                       [basename], perms, self.current_facts, ignore_err=False)
            data = ''.join(iterator)            
        except OSError, err:
            self.fs.close_cr(datacr)
            why = _strerror(err)
            self.log('FAIL MLST "%s". %s.' %(line, why))
            self.respond('550 %s.' %why)
        else:
            self.fs.close_cr(datacr)
            # since TVFS is supported (see RFC-3659 chapter 6), a fully
            # qualified pathname should be returned
            data = data.split(' ')[0] + ' %s\r\n' %line
            # response is expected on the command channel
            self.push('250-Listing "%s":\r\n' %line)
            # the fact set must be preceded by a space
            self.push(' ' + data)
            self.respond('250 End MLST.')

    def ftp_MLSD(self, line):
        """Return contents of a directory in a machine-processable form
        as defined in RFC-3659.
        """
        datacr = None
        try:            
            datacr = self.fs.get_cr(line)
            path = self.fs.ftp2fs(line, datacr)
            line = self.fs.ftpnorm(line)
            # RFC-3659 requires 501 response code if path is not a directory
            if not self.fs.isdir(path):
                err = 'No such directory'
                self.log('FAIL MLSD "%s". %s.' %(line, err))
                self.respond("501 %s." %err)
                return
            listing = self.run_as_current_user(self.fs.listdir, path)            
        except OSError, err:
            self.fs.close_cr(datacr)
            why = _strerror(err)
            self.log('FAIL MLSD "%s". %s.' %(line, why))
            self.respond('550 %s.' %why)
        else:
            self.fs.close_cr(datacr)
            perms = self.authorizer.get_perms(self.username)
            iterator = self.fs.format_mlsx(path, listing, perms,
                       self._current_facts)
            producer = BufferedIteratorProducer(iterator)
            self.log('OK MLSD "%s". Transfer starting.' %line)
            self.push_dtp_data(producer, isproducer=True)

    def ftp_RETR(self, line):
        """Retrieve the specified file (transfer from the server to the
        client)
        """
        datacr = None        
        try:            
            datacr = self.fs.get_cr(line)
            file = self.fs.ftp2fs(line, datacr)
            line = self.fs.ftpnorm(line)
            rest_pos = self.restart_position
            self.restart_position = 0
            fd = self.run_as_current_user(self.fs.open, file, 'rb')            
        except IOError, err:
            self.fs.close_cr(datacr)
            why = _strerror(err)
            self.log('FAIL RETR "%s". %s.' %(line, why))
            self.respond('550 %s.' %why)
            return

        if rest_pos:
            # Make sure that the requested offset is valid (within the
            # size of the file being resumed).
            # According to RFC-1123 a 554 reply may result in case that
            # the existing file cannot be repositioned as specified in
            # the REST.
            ok = 0
            try:
                assert not rest_pos > self.fs.getsize(file)
                fd.seek(rest_pos)
                ok = 1
            except AssertionError:
                why = "Invalid REST parameter"
            except IOError, err:
                why = _strerror(err)
            if not ok:                
                self.respond('554 %s' %why)
                self.log('FAIL RETR "%s". %s.' %(line, why))
                self.fs.close_cr(datacr)
                return        
        self.log('OK RETR "%s". Download starting.' %line)
        producer = FileProducer(fd, self.current_type)
        self.push_dtp_data(producer, isproducer=True, file=fd)
        self.fs.close_cr(datacr)

    def ftp_STOR(self, line, mode='w'):
        """Store a file (transfer from the client to the server)."""
        # A resume could occur in case of APPE or REST commands.
        # In that case we have to open file object in different ways:
        # STOR: mode = 'w'
        # APPE: mode = 'a'
        # REST: mode = 'r+' (to permit seeking on file object)
        if 'a' in mode:
            cmd = 'APPE'
        else:
            cmd = 'STOR'
            
        line = self.fs.ftpnorm(line)
        basedir,basename = os.path.split(line)

        datacr = None
        try:
            datacr = self.fs.get_cr(line)
            file = self.fs.ftp2fs(basedir, datacr)

        except OSError, err:
            self.fs.close_cr(datacr)
            why = ftpserver._strerror(err)
            self.log('FAIL %s "%s". %s.' %(cmd, line, why))
            self.respond('550 %s.' %why)
            return
            
        rest_pos = self.restart_position
        self.restart_position = 0
        if rest_pos:
            mode = 'r+'
        try:
            fd = self.run_as_current_user(self.fs.create, file, basename, mode + 'b')
        except IOError, err:
            self.fs.close_cr(datacr)
            why = _strerror(err)
            self.log('FAIL %s "%s". %s.' %(cmd, line, why))
            self.respond('550 %s.' %why)
            return

        if rest_pos:
            # Make sure that the requested offset is valid (within the
            # size of the file being resumed).
            # According to RFC-1123 a 554 reply may result in case
            # that the existing file cannot be repositioned as
            # specified in the REST.
            ok = 0
            try:
                assert not rest_pos > self.fs.getsize(file)
                fd.seek(rest_pos)
                ok = 1
            except AssertionError:
                why = "Invalid REST parameter"
            except IOError, err:
                why = _strerror(err)
            if not ok:
                self.respond('554 %s' %why)
                self.log('FAIL %s "%s". %s.' %(cmd, line, why))
                self.fs.close_cr(datacr)
                return

        self.log('OK %s "%s". Upload starting.' %(cmd, line))
        if self.data_channel is not None:
            self.respond("125 Data connection already open. Transfer starting.")
            self.data_channel.file_obj = fd
            self.data_channel.enable_receiving(self.current_type)
        else:
            self.respond("150 File status okay. About to open data connection.")
            self._in_dtp_queue = fd
        self.fs.close_cr(datacr)

    def ftp_STOU(self, line):
        """Store a file on the server with a unique name."""
        # Note 1: RFC-959 prohibited STOU parameters, but this
        # prohibition is obsolete.
        # Note 2: 250 response wanted by RFC-959 has been declared
        # incorrect in RFC-1123 that wants 125/150 instead.
        # Note 3: RFC-1123 also provided an exact output format
        # defined to be as follow:
        # > 125 FILE: pppp
        # ...where pppp represents the unique path name of the
        # file that will be written.

        # watch for STOU preceded by REST, which makes no sense.
        if self.restart_position:
            self.respond("450 Can't STOU while REST request is pending.")
            return
            
        datacr = None
        datacr = self.fs.get_cr(line)

        if line:
            line = self.fs.ftpnorm(line)
            basedir,prefix = os.path.split(line)
            basedir = self.fs.ftp2fs(basedir, datacr)
            #prefix = prefix + '.'
        else:
            basedir = self.fs.ftp2fs(self.fs.cwd)
            prefix = 'ftpd.'
        try:
            fd = self.run_as_current_user(self.fs.mkstemp, prefix=prefix,
                                          dir=basedir)
        except IOError, err:
            # hitted the max number of tries to find out file with
            # unique name
            if err.errno == errno.EEXIST:
                why = 'No usable unique file name found'
            # something else happened
            else:
                why = _strerror(err)
            self.respond("450 %s." %why)
            self.log('FAIL STOU "%s". %s.' %(self.fs.ftpnorm(line), why))
            self.fs.close_cr(datacr)
            return

        if not self.authorizer.has_perm(self.username, 'w', fd.name):
            try:
                fd.close()
                self.run_as_current_user(self.fs.remove, fd.name)
            except os.error:
                pass
            self.log('FAIL STOU "%s". Not enough privileges'
                     %self.fs.ftpnorm(line))
            self.respond("550 Can't STOU: not enough privileges.")
            self.fs.close_cr(datacr)
            return

        # now just acts like STOR except that restarting isn't allowed
        filename = os.path.basename(fd.name)
        self.log('OK STOU "%s". Upload starting.' %filename)
        if self.data_channel is not None:
            self.respond("125 FILE: %s" %filename)
            self.data_channel.file_obj = fd
            self.data_channel.enable_receiving(self.current_type)
        else:
            self.respond("150 FILE: %s" %filename)
            self._in_dtp_queue = fd
        self.fs.close_cr(datacr)

    def ftp_APPE(self, file):
        """Append data to an existing file on the server."""
        # watch for APPE preceded by REST, which makes no sense.
        if self.restart_position:
            self.respond("450 Can't APPE while REST request is pending.")
        else:
            self.ftp_STOR(file, mode='a')

    def ftp_REST(self, line):
        """Restart a file transfer from a previous mark."""
        if self.current_type == 'a':
            self.respond('501 Resuming transfers not allowed in ASCII mode.')
            return
        try:
            marker = int(line)
            if marker < 0:
                raise ValueError
        except (ValueError, OverflowError):
            self.respond("501 Invalid parameter.")
        else:
            self.respond("350 Restarting at position %s." %marker)
            self.restart_position = marker

    def ftp_ABOR(self, line):
        """Abort the current data transfer."""

        # ABOR received while no data channel exists
        if (self.data_server is None) and (self.data_channel is None):
            resp = "225 No transfer to abort."
        else:
            # a PASV was received but connection wasn't made yet
            if self.data_server is not None:
                self.data_server.close()
                self.data_server = None
                resp = "225 ABOR command successful; data channel closed."

            # If a data transfer is in progress the server must first
            # close the data connection, returning a 426 reply to
            # indicate that the transfer terminated abnormally, then it
            # must send a 226 reply, indicating that the abort command
            # was successfully processed.
            # If no data has been transmitted we just respond with 225
            # indicating that no transfer was in progress.
            if self.data_channel is not None:
                if self.data_channel.transfer_in_progress():
                    self.data_channel.close()
                    self.data_channel = None
                    self.respond("426 Connection closed; transfer aborted.")
                    self.log("OK ABOR. Transfer aborted, data channel closed.")
                    resp = "226 ABOR command successful."
                else:
                    self.data_channel.close()
                    self.data_channel = None
                    self.log("OK ABOR. Data channel closed.")
                    resp = "225 ABOR command successful; data channel closed."
        self.respond(resp)


        # --- authentication

    def ftp_USER(self, line):
        """Set the username for the current session."""
        # RFC-959 specifies a 530 response to the USER command if the
        # username is not valid.  If the username is valid is required
        # ftpd returns a 331 response instead.  In order to prevent a
        # malicious client from determining valid usernames on a server,
        # it is suggested by RFC-2577 that a server always return 331 to
        # the USER command and then reject the combination of username
        # and password for an invalid username when PASS is provided later.
        if not self.authenticated:
            self.respond('331 Username ok, send password.')
        else:
            # a new USER command could be entered at any point in order
            # to change the access control flushing any user, password,
            # and account information already supplied and beginning the
            # login sequence again.
            self.flush_account()
            msg = 'Previous account information was flushed'
            self.log('OK USER "%s". %s.' %(line, msg))
            self.respond('331 %s, send password.' %msg)
        self.username = line

    _auth_failed_timeout = 5

    def ftp_PASS(self, line):
        """Check username's password against the authorizer."""
        if self.authenticated:
            self.respond("503 User already authenticated.")
            return
        if not self.username:
            self.respond("503 Login with USER first.")
            return

        def auth_failed(msg="Authentication failed."):
            if not self._closed:
                self.attempted_logins += 1
                if self.attempted_logins >= self.max_login_attempts:
                    msg = "530 " + msg + " Disconnecting."
                    self.respond(msg)
                    self.log(msg)
                    self.close_when_done()
                else:
                    self.respond("530 " + msg)
                    self.log(msg)
                    self.sleeping = False

        if self.authorizer.validate_authentication(self.username, line):
            msg_login = self.authorizer.get_msg_login(self.username)
            if len(msg_login) <= 75:
                self.respond('230 %s' %msg_login)
            else:
                self.push("230-%s\r\n" %msg_login)
                self.respond("230 ")
            self.authenticated = True
            self.password = line
            self.fs.username = self.username
            self.fs.password = line
            self.attempted_logins = 0
            self.fs.root = self.authorizer.get_home_dir(self.username)
            self.log("User %s logged in." %self.username)
        else:
            self.username = ""
            self.fs.username = ""
            self.sleeping = True
            if self.username == 'anonymous':
                CallLater(self._auth_failed_timeout, auth_failed,
                          "Anonymous access not allowed.")
            else:
                CallLater(self._auth_failed_timeout, auth_failed)

    def ftp_REIN(self, line):
        """Reinitialize user's current session."""
        # From RFC-959:
        # REIN command terminates a USER, flushing all I/O and account
        # information, except to allow any transfer in progress to be
        # completed.  All parameters are reset to the default settings
        # and the control connection is left open.  This is identical
        # to the state in which a user finds himself immediately after
        # the control connection is opened.
        self.log("OK REIN. Flushing account information.")
        self.flush_account()
        # Note: RFC-959 erroneously mention "220" as the correct response
        # code to be given in this case, but this is wrong...
        self.respond("230 Ready for new user.")


        # --- filesystem operations

    def ftp_PWD(self, line):
        """Return the name of the current working directory to the client."""
        self.respond('257 "%s" is the current directory.' %self.fs.cwd)

    def ftp_CWD(self, line):
        """Change the current working directory."""
        if not line:
            line = '/'
        datacr = None
        try:
            datacr = self.fs.get_cr(line)
            path = self.fs.ftp2fs(line, datacr)
            self.run_as_current_user(self.fs.chdir, path)
        except OSError, err:
            if err.errno==2:
                why = 'Authentication Required or Failed'
                self.log('FAIL CWD "%s". %s.' %(self.fs.ftpnorm(line), why))
                self.respond('530 %s.' %why)
            else:
                why = _strerror(err)
                self.log('FAIL CWD "%s". %s.' %(self.fs.ftpnorm(line), why))
                self.respond('550 %s.' %why)
        else:
            self.log('OK CWD "%s".' %self.fs.cwd)
            self.respond('250 "%s" is the current directory.' %self.fs.cwd)
        self.fs.close_cr(datacr)

    def ftp_CDUP(self, line):
        """Change into the parent directory."""
        # Note: RFC-959 says that code 200 is required but it also says
        # that CDUP uses the same codes as CWD.
        self.ftp_CWD('..')

    def ftp_SIZE(self, line):
        """Return size of file in a format suitable for using with
        RESTart as defined in RFC-3659."""

        # Implementation note: properly handling the SIZE command when
        # TYPE ASCII is used would require to scan the entire file to
        # perform the ASCII translation logic
        # (file.read().replace(os.linesep, '\r\n')) and then calculating
        # the len of such data which may be different than the actual
        # size of the file on the server.  Considering that calculating
        # such result could be very resource-intensive and also dangerous
        # (DoS) we reject SIZE when the current TYPE is ASCII.
        # However, clients in general should not be resuming downloads
        # in ASCII mode.  Resuming downloads in binary mode is the
        # recommended way as specified in RFC-3659.
        
        if self.current_type == 'a':
            why = "SIZE not allowed in ASCII mode"
            self.log('FAIL SIZE "%s". %s.' %(line, why))
            self.respond("550 %s." %why)
            return        
        datacr = False
        try:
            datacr = self.fs.get_cr(line)
            path = self.fs.ftp2fs(line, datacr)
            line = self.fs.ftpnorm(line)
            if not self.fs.isfile(self.fs.realpath(path)):
                why = "%s is not retrievable" %line
                self.log('FAIL SIZE "%s". %s.' %(line, why))
                self.respond("550 %s." %why)
                self.fs.close_cr(datacr)
                return
            size = self.run_as_current_user(self.fs.getsize, path)
            size = self.run_as_current_user(self.fs.getsize, path)
        except OSError, err:
            why = _strerror(err)
            self.log('FAIL SIZE "%s". %s.' %(line, why))
            self.respond('550 %s.' %why)
        else:
            self.respond("213 %s" %size)
            self.log('OK SIZE "%s".' %line)
        self.fs.close_cr(datacr)

    def ftp_MDTM(self, line):
        """Return last modification time of file to the client as an ISO
        3307 style timestamp (YYYYMMDDHHMMSS) as defined in RFC-3659.
        """
        datacr = None        
        try:
            datacr = self.fs.get_cr(line)
            path = self.fs.ftp2fs(line, datacr)
            line = self.fs.ftpnorm(line)
            if not self.fs.isfile(self.fs.realpath(path)):
                why = "%s is not retrievable" %line
                self.log('FAIL MDTM "%s". %s.' %(line, why))
                self.respond("550 %s." %why)
                self.fs.close_cr(datacr)
                return
            secs = self.run_as_current_user(self.fs.getmtime, path)    
            lmt = self.run_as_current_user(self.fs.getmtime, path)           
            
        except (OSError, ValueError), err:
            if isinstance(err, OSError):
                why = _strerror(err)
            else:
                # It could happen if file's last modification time
                # happens to be too old (prior to year 1900)
                why = "Can't determine file's last modification time"
            self.log('FAIL MDTM "%s". %s.' %(line, why))
            self.respond('550 %s.' %why)
        else:
            self.respond("213 %s" %lmt)
            self.log('OK MDTM "%s".' %line)
        self.fs.close_cr(datacr)
        
    def ftp_MKD(self, line):
        """Create the specified directory."""
        datacr = None
        line = self.fs.ftpnorm(line)
        basedir,basename = os.path.split(line)
        try:
            datacr = self.fs.get_cr(line)
            path = self.fs.ftp2fs(basedir, datacr)
            self.run_as_current_user(self.fs.mkdir, path, basename)
        except OSError, err:
            why = _strerror(err)
            self.log('FAIL MKD "%s". %s.' %(line, why))
            self.respond('550 %s.' %why)
        else:
            self.log('OK MKD "%s".' %line)
            # The 257 response is supposed to include the directory
            # name and in case it contains embedded double-quotes
            # they must be doubled (see RFC-959, chapter 7, appendix 2).
            self.respond('257 "%s" directory created.' %line.replace('"', '""'))
        self.fs.close_cr(datacr)

    def ftp_RMD(self, line):
        """Remove the specified directory."""
        datacr = False
        try:
            datacr = self.fs.get_cr(line)
            path = self.fs.ftp2fs(line, datacr)
            line = self.fs.ftpnorm(line)
            if self.fs.realpath(path) == self.fs.realpath(self.fs.root):
                msg = "Can't remove root directory."
                self.respond("550 %s" %msg)
                self.log('FAIL MKD "/". %s' %msg)
                self.fs.close_cr(datacr)
                return
            self.run_as_current_user(self.fs.rmdir, path)            
        except OSError, err:
            why = _strerror(err)
            self.log('FAIL RMD "%s". %s.' %(line, why))
            self.respond('550 %s.' %why)
        else:
            self.log('OK RMD "%s".' %line)
            self.respond("250 Directory removed.")
        self.fs.close_cr(datacr)
        
    def ftp_DELE(self, line):
        """Delete the specified file."""
        datacr = None
        try:
            datacr = self.fs.get_cr(line)
            path = self.fs.ftp2fs(line, datacr)
            line = self.fs.ftpnorm(line)
            self.run_as_current_user(self.fs.remove, path)
        except OSError, err:
            why = _strerror(err)
            self.log('FAIL DELE "%s". %s.' %(line, why))
            self.respond('550 %s.' %why)
        else:
            self.log('OK DELE "%s".' %line)
            self.respond("250 File removed.")
        self.fs.close_cr(datacr)
        
    def ftp_RNFR(self, line):
        """Rename the specified (only the source name is specified
        here, see RNTO command)"""
        
        datacr = None
        try:
            datacr = self.fs.get_cr(line)
            line = self.fs.ftpnorm(line)
            path = self.fs.ftp2fs(line, datacr)
            if not self.fs.lexists(path):
                self.respond("550 No such file or directory.")
            elif self.fs.realpath(path) == self.fs.realpath(self.fs.root):
                self.respond("550 Can't rename the home directory.")
            else:
                self.fs.rnfr = line
                self.respond("350 Ready for destination name.")
        except:
            self.respond("550 Can't find the file or directory.")
        self.fs.close_cr(datacr)

    def ftp_RNTO(self, line):
        """Rename file (destination name only, source is specified with
        RNFR).
        """
        if not self.fs.rnfr:
            self.respond("503 Bad sequence of commands: use RNFR first.")
            return
        datacr = None        
        try:
            try:
                datacr = self.fs.get_cr(line)
                src = self.fs.ftp2fs(self.fs.rnfr, datacr)
                line = self.fs.ftpnorm(line)
                basedir,basename = os.path.split(line)
                dst = self.fs.ftp2fs(basedir, datacr)
                self.run_as_current_user(self.fs.rename, src, dst,basename)
            except OSError, err:
                why = _strerror(err)
                self.log('FAIL RNFR/RNTO "%s ==> %s". %s.' \
                         %(self.fs.ftpnorm(self.fs.rnfr), line, why))
                self.respond('550 %s.' %why)
            else:
                self.log('OK RNFR/RNTO "%s ==> %s".' \
                         %(self.fs.ftpnorm(self.fs.rnfr), line))
                self.respond("250 Renaming ok.")
        finally:
            self.fs.rnfr = None
            self.fs.close_cr(datacr)



        # --- others

    def ftp_TYPE(self, line):
        """Set current type data type to binary/ascii"""
        type = line.upper().replace(' ', '')
        if type in ("A", "L7"):
            self.respond("200 Type set to: ASCII.")
            self.current_type = 'a'
        elif type in ("I", "L8"):
            self.respond("200 Type set to: Binary.")
            self.current_type = 'i'
        else:
            self.respond('504 Unsupported type "%s".' %line)

    def ftp_STRU(self, line):
        """Set file structure ("F" is the only one supported (noop))."""
        stru = line.upper()
        if stru == 'F':
            self.respond('200 File transfer structure set to: F.')
        elif stru in ('P', 'R'):
           # R is required in minimum implementations by RFC-959, 5.1.
           # RFC-1123, 4.1.2.13, amends this to only apply to servers
           # whose file systems support record structures, but also
           # suggests that such a server "may still accept files with
           # STRU R, recording the byte stream literally".
           # Should we accept R but with no operational difference from
           # F? proftpd and wu-ftpd don't accept STRU R. We just do
           # the same.
           #
           # RFC-1123 recommends against implementing P.
            self.respond('504 Unimplemented STRU type.')
        else:
            self.respond('501 Unrecognized STRU type.')

    def ftp_MODE(self, line):
        """Set data transfer mode ("S" is the only one supported (noop))."""
        mode = line.upper()
        if mode == 'S':
            self.respond('200 Transfer mode set to: S')
        elif mode in ('B', 'C'):
            self.respond('504 Unimplemented MODE type.')
        else:
            self.respond('501 Unrecognized MODE type.')

    def ftp_STAT(self, line):
        """Return statistics about current ftp session. If an argument
        is provided return directory listing over command channel.

        Implementation note:

        RFC-959 does not explicitly mention globbing but many FTP
        servers do support it as a measure of convenience for FTP
        clients and users.

        In order to search for and match the given globbing expression,
        the code has to search (possibly) many directories, examine
        each contained filename, and build a list of matching files in
        memory.  Since this operation can be quite intensive, both CPU-
        and memory-wise, we do not support globbing.
        """
        # return STATus information about ftpd
        if not line:
            s = []
            s.append('Connected to: %s:%s' %self.socket.getsockname()[:2])
            if self.authenticated:
                s.append('Logged in as: %s' %self.username)
            else:
                if not self.username:
                    s.append("Waiting for username.")
                else:
                    s.append("Waiting for password.")
            if self.current_type == 'a':
                type = 'ASCII'
            else:
                type = 'Binary'
            s.append("TYPE: %s; STRUcture: File; MODE: Stream" %type)
            if self.data_server is not None:
                s.append('Passive data channel waiting for connection.')
            elif self.data_channel is not None:
                bytes_sent = self.data_channel.tot_bytes_sent
                bytes_recv = self.data_channel.tot_bytes_received
                s.append('Data connection open:')
                s.append('Total bytes sent: %s' %bytes_sent)
                s.append('Total bytes received: %s' %bytes_recv)
            else:
                s.append('Data connection closed.')

            self.push('211-FTP server status:\r\n')
            self.push(''.join([' %s\r\n' %item for item in s]))
            self.respond('211 End of status.')
        # return directory LISTing over the command channel
        else:
            datacr = None
            try:
                datacr = self.fs.get_cr(line)
                iterator = self.run_as_current_user(self.fs.get_stat_dir, line, datacr)
            except OSError, err:
                why = _strerror(err)
                self.log('FAIL STAT "%s". %s.' %(line, why))
                self.respond('550 %s.' %why)
            else:
                self.push('213-Status of "%s":\r\n' %line)
                self.push_with_producer(BufferedIteratorProducer(iterator))
                self.respond('213 End of status.')
            self.fs.close_cr(datacr)
            
    def ftp_FEAT(self, line):
        """List all new features supported as defined in RFC-2398."""
        features = ['EPRT','EPSV','MDTM','MLSD','REST STREAM','SIZE','TVFS']
        features.extend(self._extra_feats)
        s = ''
        for fact in self._available_facts:
            if fact in self._current_facts:
                s += fact + '*;'
            else:
                s += fact + ';'
        features.append('MLST ' + s)
        features.sort()
        self.push("211-Features supported:\r\n")
        self.push("".join([" %s\r\n" %x for x in features]))
        self.respond('211 End FEAT.')

    def ftp_OPTS(self, line):
        """Specify options for FTP commands as specified in RFC-2389."""
        try:
            assert (not line.count(' ') > 1), 'Invalid number of arguments'
            if ' ' in line:
                cmd, arg = line.split(' ')
                assert (';' in arg), 'Invalid argument'
            else:
                cmd, arg = line, ''
            # actually the only command able to accept options is MLST
            assert (cmd.upper() == 'MLST'), 'Unsupported command "%s"' %cmd
        except AssertionError, err:
            self.respond('501 %s.' %err)
        else:
            facts = [x.lower() for x in arg.split(';')]
            self._current_facts = [x for x in facts if x in self._available_facts]
            f = ''.join([x + ';' for x in self._current_facts])
            self.respond('200 MLST OPTS ' + f)

    def ftp_NOOP(self, line):
        """Do nothing."""
        self.respond("200 I successfully done nothin'.")

    def ftp_SYST(self, line):
        """Return system type (always returns UNIX type: L8)."""
        # This command is used to find out the type of operating system
        # at the server.  The reply shall have as its first word one of
        # the system names listed in RFC-943.
        # Since that we always return a "/bin/ls -lA"-like output on
        # LIST we  prefer to respond as if we would on Unix in any case.
        self.respond("215 UNIX Type: L8")

    def ftp_ALLO(self, line):
        """Allocate bytes for storage (noop)."""
        # not necessary (always respond with 202)
        self.respond("202 No storage allocation necessary.")

    def ftp_HELP(self, line):
        """Return help text to the client."""
        if line:
            line = line.upper()
            if line in proto_cmds:
                self.respond("214 %s" %proto_cmds[line].help)
            else:
                self.respond("501 Unrecognized command.")
        else:
            # provide a compact list of recognized commands
            def formatted_help():
                cmds = []
                keys = [x for x in proto_cmds.keys() if not x.startswith('SITE ')]
                keys.sort()
                while keys:
                    elems = tuple((keys[0:8]))
                    cmds.append(' %-6s' * len(elems) %elems + '\r\n')
                    del keys[0:8]
                return ''.join(cmds)

            self.push("214-The following commands are recognized:\r\n")
            self.push(formatted_help())
            self.respond("214 Help command successful.")

        # --- site commands

    # No SITE commands aside from SITE HELP are implemented by default.
    # The user willing to add support for a specific SITE command has
    # to define a new ftp_SITE_%CMD% method in the subclass.

    def ftp_SITE_HELP(self, line):
        """Return help text to the client for a given SITE command."""
        if line:
            line = line.upper()
            if line in proto_cmds:
                self.respond("214 %s" %proto_cmds[line].help)
            else:
                self.respond("501 Unrecognized SITE command.")
        else:
            self.push("214-The following SITE commands are recognized:\r\n")
            site_cmds = []
            keys = proto_cmds.keys()
            keys.sort()
            for cmd in keys:
                if cmd.startswith('SITE '):
                    site_cmds.append(' %s\r\n' %cmd[5:])
            self.push(''.join(site_cmds))
            self.respond("214 Help SITE command successful.")

        # --- support for deprecated cmds

    # RFC-1123 requires that the server treat XCUP, XCWD, XMKD, XPWD
    # and XRMD commands as synonyms for CDUP, CWD, MKD, LIST and RMD.
    # Such commands are obsoleted but some ftp clients (e.g. Windows
    # ftp.exe) still use them.

    def ftp_XCUP(self, line):
        """Change to the parent directory. Synonym for CDUP. Deprecated."""
        self.ftp_CDUP(line)

    def ftp_XCWD(self, line):
        """Change the current working directory. Synonym for CWD. Deprecated."""
        self.ftp_CWD(line)

    def ftp_XMKD(self, line):
        """Create the specified directory. Synonym for MKD. Deprecated."""
        self.ftp_MKD(line)

    def ftp_XPWD(self, line):
        """Return the current working directory. Synonym for PWD. Deprecated."""
        self.ftp_PWD(line)

    def ftp_XRMD(self, line):
        """Remove the specified directory. Synonym for RMD. Deprecated."""
        self.ftp_RMD(line)


class FTPServer(asyncore.dispatcher):
    """This class is an asyncore.disptacher subclass.  It creates a FTP
    socket listening on <address>, dispatching the requests to a <handler>
    (typically FTPHandler class).

    Depending on the type of address specified IPv4 or IPv6 connections
    (or both, depending from the underlying system) will be accepted.

    All relevant session information is stored in class attributes
    described below.
    Overriding them is strongly recommended to avoid running out of
    file descriptors (DoS)!

     - (int) max_cons:
        number of maximum simultaneous connections accepted (defaults
        to 0 == unlimited).

     - (int) max_cons_per_ip:
        number of maximum connections accepted for the same IP address
        (defaults to 0 == unlimited).
    """

    max_cons = 0
    max_cons_per_ip = 0

    def __init__(self, address, handler):
        """Initiate the FTP server opening listening on address.

         - (tuple) address: the host:port pair on which the command
           channel will listen.

         - (classobj) handler: the handler class to use.
        """
        asyncore.dispatcher.__init__(self)
        self.handler = handler
        self.ip_map = []
        host, port = address

        # AF_INET or AF_INET6 socket
        # Get the correct address family for our host (allows IPv6 addresses)
        try:
            info = socket.getaddrinfo(host, port, socket.AF_UNSPEC,
                                      socket.SOCK_STREAM, 0, socket.AI_PASSIVE)
        except socket.gaierror:
            # Probably a DNS issue. Assume IPv4.
            self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
            self.set_reuse_addr()
            self.bind((host, port))
        else:
            for res in info:
                af, socktype, proto, canonname, sa = res
                try:
                    self.create_socket(af, socktype)
                    self.set_reuse_addr()
                    self.bind(sa)
                except socket.error, msg:
                    if self.socket:
                        self.socket.close()
                    self.socket = None
                    continue
                break
            if not self.socket:
                raise socket.error, msg
        self.listen(5)

    def set_reuse_addr(self):
        # Overridden for convenience. Avoid to reuse address on Windows.
        if (os.name in ('nt', 'ce')) or (sys.platform == 'cygwin'):
            return
        asyncore.dispatcher.set_reuse_addr(self)

    def serve_forever(self, timeout=1, use_poll=False, map=None, count=None):
        """A wrap around asyncore.loop(); starts the asyncore polling
        loop including running the scheduler.
        The arguments are the same expected by original asyncore.loop()
        function.
        """
        if map is None:
            map = asyncore.socket_map
        # backward compatibility for python versions < 2.4
        if not hasattr(self, '_map'):
            self._map = self.handler._map = map

        if use_poll and hasattr(asyncore.select, 'poll'):
            poll_fun = asyncore.poll2
        else:
            poll_fun = asyncore.poll

        if count is None:
            log("Serving FTP on %s:%s" %self.socket.getsockname()[:2])
            try:
                while map or _tasks:
                    if map:
                        poll_fun(timeout, map)
                    if _tasks:
                        _scheduler()
            except (KeyboardInterrupt, SystemExit, asyncore.ExitNow):
                log("Shutting down FTP server.")
                self.close_all()
        else:
            while (map or _tasks) and count > 0:
                if map:
                    poll_fun(timeout, map)
                if _tasks:
                    _scheduler()
                count = count - 1

    def handle_accept(self):
        """Called when remote client initiates a connection."""
        try:
            sock_obj, addr = self.accept()
        except TypeError:
            # for some reason sometimes accept() returns None instead
            # of a socket
            return
        log("[]%s:%s Connected." %addr[:2])

        handler = self.handler(sock_obj, self)
        ip = addr[0]
        self.ip_map.append(ip)

        # For performance and security reasons we should always set a
        # limit for the number of file descriptors that socket_map
        # should contain.  When we're running out of such limit we'll
        # use the last available channel for sending a 421 response
        # to the client before disconnecting it.
        if self.max_cons:
            if len(self._map) > self.max_cons:
                handler.handle_max_cons()
                return

        # accept only a limited number of connections from the same
        # source address.
        if self.max_cons_per_ip:
            if self.ip_map.count(ip) > self.max_cons_per_ip:
                handler.handle_max_cons_per_ip()
                return

        handler.handle()

    def writable(self):
        return 0

    def handle_error(self):
        """Called to handle any uncaught exceptions."""
        try:
            raise
        except (KeyboardInterrupt, SystemExit, asyncore.ExitNow):
            raise
        logerror(traceback.format_exc())
        self.close()

    def close_all(self, map=None, ignore_all=False):
        """Stop serving and also disconnects all currently connected
        clients.

         - (dict) map:
            A dictionary whose items are the channels to close.
            If map is omitted, the default asyncore.socket_map is used.

         - (bool) ignore_all:
            having it set to False results in raising exception in case
            of unexpected errors.

        Implementation note:

        This is how asyncore.close_all() is implemented starting from
        Python 2.6.
        The previous versions of close_all() instead of iteratating over
        all opened channels and calling close() method for each one
        of them only closed sockets generating memory leaks.
        """
        if map is None:
            map = self._map
        for x in map.values():
            try:
                x.close()
            except OSError, x:
                if x[0] == errno.EBADF:
                    pass
                elif not ignore_all:
                    raise
            except (asyncore.ExitNow, KeyboardInterrupt, SystemExit):
                raise
            except:
                if not ignore_all:
                    raise
        map.clear()


def test():
    # cmd line usage (provide a read-only anonymous ftp server):
    # python -m pyftpdlib.ftpserver
    authorizer = DummyAuthorizer()
    authorizer.add_anonymous(os.getcwd())
    FTPHandler.authorizer = authorizer
    address = ('', 21)
    ftpd = FTPServer(address, FTPHandler)
    ftpd.serve_forever()

if __name__ == '__main__':
    test()
