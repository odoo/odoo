# Copyright (c) 2018 gevent community
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
from __future__ import absolute_import, print_function, division

import os
import unittest
import re
import gc
import functools

from . import sysinfo

# Linux/OS X/BSD platforms /can/ implement this by calling out to lsof.
# However, if psutil is available (it is cross-platform) use that.
# It is *much* faster than shelling out to lsof each time
# (Running 14 tests takes 3.964s with lsof and 0.046 with psutil)
# However, it still doesn't completely solve the issue on Windows: fds are reported
# as -1 there, so we can't fully check those.

def _collects(func):
    # We've seen OSError: No such file or directory /proc/PID/fd/NUM.
    # This occurs in the loop that checks open files. It first does
    # listdir() and then tries readlink() on each file. But the file
    # went away. This must be because of async GC in PyPy running
    # destructors at arbitrary times. This became an issue in PyPy 7.2
    # but could theoretically be an issue with any objects caught in a
    # cycle. This is one reason we GC before we begin. (The other is
    # to clean up outstanding objects that will close files in
    # __del__.)
    #
    # Note that this can hide errors, though, by causing greenlets to get
    # collected and drop references and thus close files. We should be deterministic
    # and careful about closing things.
    @functools.wraps(func)
    def f(**kw):
        gc.collect()
        gc.collect()
        enabled = gc.isenabled()
        gc.disable()

        try:
            return func(**kw)
        finally:
            if enabled:
                gc.enable()
    return f


if sysinfo.WIN:
    def _run_lsof():
        raise unittest.SkipTest("lsof not expected on Windows")
else:
    @_collects
    def _run_lsof():
        import tempfile
        pid = os.getpid()
        fd, tmpname = tempfile.mkstemp('get_open_files')
        os.close(fd)
        lsof_command = 'lsof -p %s > %s' % (pid, tmpname)
        if os.system(lsof_command):
            # XXX: This prints to the console an annoying message: 'lsof is not recognized'
            raise unittest.SkipTest("lsof failed")

        with open(tmpname) as fobj: # pylint:disable=unspecified-encoding
            data = fobj.read().strip()
        os.remove(tmpname)
        return data

def default_get_open_files(pipes=False, **_kwargs):
    data = _run_lsof()
    results = {}
    for line in data.split('\n'):
        line = line.strip()
        if not line or line.startswith("COMMAND"):
            # Skip header and blank lines
            continue
        split = re.split(r'\s+', line)
        # Note that this needs the real lsof; it won't work with
        # the lsof that comes from BusyBox. You'll get parsing errors
        # here.
        _command, _pid, _user, fd = split[:4]
        # Pipes (on OS X, at least) get an fd like "3" while normal files get an fd like "1u"
        if fd[:-1].isdigit() or fd.isdigit():
            if not pipes and fd[-1].isdigit():
                continue
            fd = int(fd[:-1]) if not fd[-1].isdigit() else int(fd)
            if fd in results:
                params = (fd, line, split, results.get(fd), data)
                raise AssertionError('error when parsing lsof output: duplicate fd=%r\nline=%r\nsplit=%r\nprevious=%r\ndata:\n%s' % params)
            results[fd] = line
    if not results:
        raise AssertionError('failed to parse lsof:\n%s' % (data, ))
    results['data'] = data
    return results

@_collects
def default_get_number_open_files():
    if os.path.exists('/proc/'):
        # Linux only
        fd_directory = '/proc/%d/fd' % os.getpid()
        return len(os.listdir(fd_directory))

    try:
        return len(get_open_files(pipes=True)) - 1
    except (OSError, AssertionError, unittest.SkipTest):
        return 0

lsof_get_open_files = default_get_open_files

try:
    # psutil import subprocess which on Python 3 imports selectors.
    # This can expose issues with monkey-patching.
    import psutil
except ImportError:
    get_open_files = default_get_open_files
    get_number_open_files = default_get_number_open_files
else:
    class _TrivialOpenFile(object):
        __slots__ = ('fd',)
        def __init__(self, fd):
            self.fd = fd

    @_collects
    def get_open_files(count_closing_as_open=True, **_kw):
        """
        Return a list of popenfile and pconn objects.

        Note that other than `fd`, they have different attributes.

        .. important:: If you want to find open sockets, on Windows
           and linux, it is important that the socket at least be listening
           (socket.listen(1)). Unlike the lsof implementation, this will only
           return sockets in a state like that.
        """

        results = {}

        for _ in range(3):
            try:
                if count_closing_as_open and os.path.exists('/proc/'):
                    # Linux only.
                    # psutil doesn't always see all connections, even though
                    # they exist in the filesystem. It's not entirely clear why.
                    # It sees them on Travis (prior to Ubuntu Bionic, at least)
                    # but doesn't in the manylinux image or Fedora 33 Rawhide image.
                    # This happens in test__makefile_ref TestSSL.*; in particular, if a
                    # ``sslsock.makefile()`` is opened and used to read all data, and the sending
                    # side shuts down, psutil no longer finds the open file. So we add them
                    # back in.
                    #
                    # Of course, the flip side of this is that we sometimes find connections
                    # we're not expecting.
                    # I *think* this has to do with CLOSE_WAIT handling?
                    fd_directory = '/proc/%d/fd' % os.getpid()
                    fd_files = os.listdir(fd_directory)
                else:
                    fd_files = []
                process = psutil.Process()
                results['data'] = process.open_files()
                results['data'] += process.connections('all')
                break
            except OSError:
                pass
        else:
            # No break executed
            raise unittest.SkipTest("Unable to read open files")

        for x in results['data']:
            results[x.fd] = x
        for fd_str in fd_files:
            if fd_str not in results:
                fd = int(fd_str)
                results[fd] = _TrivialOpenFile(fd)
        results['data'] += [('From psutil', process)]
        results['data'] += [('fd files', fd_files)]
        return results

    @_collects
    def get_number_open_files():
        process = psutil.Process()
        try:
            return process.num_fds()
        except AttributeError:
            # num_fds is unix only. Is num_handles close enough on Windows?
            return 0



class DoesNotLeakFilesMixin(object): # pragma: no cover
    """
    A test case mixin that helps find a method that's leaking an
    open file.

    Only mix this in when needed to debug, it slows tests down.
    """
    def setUp(self):
        self.__open_files_count = get_number_open_files()
        super(DoesNotLeakFilesMixin, self).setUp()

    def tearDown(self):
        super(DoesNotLeakFilesMixin, self).tearDown()
        after = get_number_open_files()
        if after > self.__open_files_count:
            raise AssertionError(
                "Too many open files. Before: %s < After: %s.\n%s" % (
                    self.__open_files_count,
                    after,
                    get_open_files()
                )
            )
