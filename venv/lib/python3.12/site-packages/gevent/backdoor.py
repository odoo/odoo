# Copyright (c) 2009-2014, gevent contributors
# Based on eventlet.backdoor Copyright (c) 2005-2006, Bob Ippolito
"""
Interactive greenlet-based network console that can be used in any process.

The :class:`BackdoorServer` provides a REPL inside a running process. As
long as the process is monkey-patched, the ``BackdoorServer`` can coexist
with other elements of the process.

.. seealso:: :class:`code.InteractiveConsole`
"""
from __future__ import print_function, absolute_import
import sys
import socket
from code import InteractiveConsole

from gevent.greenlet import Greenlet
from gevent.hub import getcurrent
from gevent.server import StreamServer
from gevent.pool import Pool


__all__ = [
    'BackdoorServer',
]

try:
    sys.ps1
except AttributeError:
    sys.ps1 = '>>> '
try:
    sys.ps2
except AttributeError:
    sys.ps2 = '... '

class _Greenlet_stdreplace(Greenlet):
    # A greenlet that replaces sys.std[in/out/err] while running.

    __slots__ = (
        'stdin',
        'stdout',
        'prev_stdin',
        'prev_stdout',
        'prev_stderr',
    )

    def __init__(self, *args, **kwargs):
        Greenlet.__init__(self, *args, **kwargs)
        self.stdin = None
        self.stdout = None
        self.prev_stdin = None
        self.prev_stdout = None
        self.prev_stderr = None

    def switch(self, *args, **kw):
        if self.stdin is not None:
            self.switch_in()
        Greenlet.switch(self, *args, **kw)

    def switch_in(self):
        self.prev_stdin = sys.stdin
        self.prev_stdout = sys.stdout
        self.prev_stderr = sys.stderr

        sys.stdin = self.stdin
        sys.stdout = self.stdout
        sys.stderr = self.stdout

    def switch_out(self):
        sys.stdin = self.prev_stdin
        sys.stdout = self.prev_stdout
        sys.stderr = self.prev_stderr

        self.prev_stdin = self.prev_stdout = self.prev_stderr = None

    def throw(self, *args, **kwargs):
        # pylint:disable=arguments-differ
        if self.prev_stdin is None and self.stdin is not None:
            self.switch_in()
        Greenlet.throw(self, *args, **kwargs)

    def run(self):
        try:
            return Greenlet.run(self)
        finally:
            # Make sure to restore the originals.
            self.switch_out()


class BackdoorServer(StreamServer):
    """
    Provide a backdoor to a program for debugging purposes.

    .. warning:: This backdoor provides no authentication and makes no
          attempt to limit what remote users can do. Anyone that
          can access the server can take any action that the running
          python process can. Thus, while you may bind to any interface, for
          security purposes it is recommended that you bind to one
          only accessible to the local machine, e.g.,
          127.0.0.1/localhost.

    Basic usage::

        from gevent.backdoor import BackdoorServer
        server = BackdoorServer(('127.0.0.1', 5001),
                                banner="Hello from gevent backdoor!",
                                locals={'foo': "From defined scope!"})
        server.serve_forever()

    In a another terminal, connect with...::

        $ telnet 127.0.0.1 5001
        Trying 127.0.0.1...
        Connected to 127.0.0.1.
        Escape character is '^]'.
        Hello from gevent backdoor!
        >> print(foo)
        From defined scope!

    .. versionchanged:: 1.2a1
       Spawned greenlets are now tracked in a pool and killed when the server
       is stopped.
    """

    def __init__(self, listener, locals=None, banner=None, **server_args):
        """
        :keyword locals: If given, a dictionary of "builtin" values that will be available
            at the top-level.
        :keyword banner: If geven, a string that will be printed to each connecting user.
        """
        group = Pool(greenlet_class=_Greenlet_stdreplace) # no limit on number
        StreamServer.__init__(self, listener, spawn=group, **server_args)
        _locals = {'__doc__': None, '__name__': '__console__'}
        if locals:
            _locals.update(locals)
        self.locals = _locals

        self.banner = banner
        self.stderr = sys.stderr

    def _create_interactive_locals(self):
        # Create and return a *new* locals dictionary based on self.locals,
        # and set any new entries in it. (InteractiveConsole does not
        # copy its locals value)
        _locals = self.locals.copy()
        # __builtins__ may either be the __builtin__ module or
        # __builtin__.__dict__; in the latter case typing
        # locals() at the backdoor prompt spews out lots of
        # useless stuff
        try:
            import __builtin__
            _locals["__builtins__"] = __builtin__
        except ImportError:
            import builtins # pylint:disable=import-error
            _locals["builtins"] = builtins
            _locals['__builtins__'] = builtins
        return _locals

    def handle(self, conn, _address): # pylint: disable=method-hidden
        """
        Interact with one remote user.

        .. versionchanged:: 1.1b2 Each connection gets its own
            ``locals`` dictionary. Previously they were shared in a
            potentially unsafe manner.
        """
        conn.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, True) # pylint:disable=no-member
        raw_file = conn.makefile(mode="r")
        getcurrent().stdin = _StdIn(conn, raw_file)
        getcurrent().stdout = _StdErr(conn, raw_file)

        # Swizzle the inputs
        getcurrent().switch_in()
        try:
            console = InteractiveConsole(self._create_interactive_locals())
            # Beginning in 3.6, the console likes to print "now exiting <class>"
            # but probably our socket is already closed, so this just causes problems.
            console.interact(banner=self.banner, exitmsg='') # pylint:disable=unexpected-keyword-arg

        except SystemExit:
            # raised by quit(); obviously this cannot propagate.
            pass
        finally:
            raw_file.close()
            conn.close()

class _BaseFileLike(object):

    # Python 2 likes to test for this before writing to stderr.
    softspace = None
    encoding = 'utf-8'

    __slots__ = (
        'sock',
        'fobj',
        'fileno',
    )

    def __init__(self, sock, stdin):
        self.sock = sock
        self.fobj = stdin
        # On Python 3, The builtin input() function (used by the
        # default InteractiveConsole) calls fileno() on
        # sys.stdin. If it's the same as the C stdin's fileno,
        # and isatty(fd) (C function call) returns true,
        # and all of that is also true for stdout, then input() will use
        # PyOS_Readline to get the input.
        #
        # On Python 2, the sys.stdin object has to extend the file()
        # class, and return true from isatty(fileno(sys.stdin.f_fp))
        # (where f_fp is a C-level FILE* member) to use PyOS_Readline.
        #
        # If that doesn't hold, both versions fall back to reading and writing
        # using sys.stdout.write() and sys.stdin.readline().
        self.fileno = sock.fileno

    def __getattr__(self, name):
        return getattr(self.fobj, name)

    def close(self):
        pass


class _StdErr(_BaseFileLike):
    """
    A file-like object that wraps the result of socket.makefile (composition
    instead of inheritance lets us work identically under CPython and PyPy).

    We write directly to the socket, avoiding the buffering that the text-oriented
    makefile would want to do (otherwise we'd be at the mercy of waiting on a
    flush() to get called for the remote user to see data); this beats putting
    the file in binary mode and translating everywhere with a non-default
    encoding.
    """

    def flush(self):
        "Does nothing. raw_input() calls this, only on Python 3."

    def write(self, data):
        if not isinstance(data, bytes):
            data = data.encode(self.encoding)
        self.sock.sendall(data)

class _StdIn(_BaseFileLike):
    # Like _StdErr, but for stdin.

    def readline(self, *a):
        try:
            return self.fobj.readline(*a).replace("\r\n", "\n")
        except UnicodeError:
            # Typically, under python 3, a ^C on the other end
            return ''

if __name__ == '__main__':
    if not sys.argv[1:]:
        print('USAGE: %s PORT [banner]' % sys.argv[0])
    else:
        BackdoorServer(('127.0.0.1', int(sys.argv[1])),
                       banner=(sys.argv[2] if len(sys.argv) > 2 else None),
                       locals={'hello': 'world'}).serve_forever()
