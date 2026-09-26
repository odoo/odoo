# pylint: disable=no-member

# This module is only used to create and compile the gevent.libuv._corecffi module;
# nothing should be directly imported from it except `ffi`, which should only be
# used for `ffi.compile()`; programs should import gevent._corecfffi.
# However, because we are using "out-of-line" mode, it is necessary to examine
# this file to know what functions are created and available on the generated
# module.
from __future__ import absolute_import, print_function
import os
import os.path # pylint:disable=no-name-in-module
import platform
import sys

from cffi import FFI

sys.path.append(".")

try:
    import _setuputils
except ImportError:
    print("This file must be imported with setup.py in the current working dir.")
    raise


__all__ = []

WIN = sys.platform.startswith('win32')
LIBUV_EMBED = _setuputils.should_embed('libuv')
PY2 = sys.version_info[0] == 2


ffi = FFI()

thisdir = os.path.dirname(os.path.abspath(__file__))
parentdir = os.path.abspath(os.path.join(thisdir, '..'))
setup_py_dir = os.path.abspath(os.path.join(thisdir, '..', '..', '..'))
libuv_dir = os.path.abspath(os.path.join(setup_py_dir, 'deps', 'libuv'))

def read_source(name):
    # pylint:disable=unspecified-encoding
    with open(os.path.join(thisdir, name), 'r') as f:
        return f.read()

_cdef = read_source('_corecffi_cdef.c')
_source = read_source('_corecffi_source.c')

# These defines and uses help keep the C file readable and lintable by
# C tools.
_cdef = _cdef.replace('#define GEVENT_STRUCT_DONE int', '')
_cdef = _cdef.replace("GEVENT_STRUCT_DONE _;", '...;')

# nlink_t is not used in libuv.
_cdef = _cdef.replace('#define GEVENT_ST_NLINK_T int',
                      '')
_cdef = _cdef.replace('GEVENT_ST_NLINK_T', 'nlink_t')


_cdef = _cdef.replace('#define GEVENT_UV_OS_SOCK_T int', '')
# uv_os_sock_t is int on POSIX and SOCKET on Win32, but socket is
# just another name for handle, which is just another name for 'void*'
# which we will treat as an 'unsigned long' or 'unsigned long long'
# since it comes through 'fileno()' where it has been cast as an int.
# See class watcher.io
_void_pointer_as_integer = 'intptr_t'
_cdef = _cdef.replace("GEVENT_UV_OS_SOCK_T", 'int' if not WIN else _void_pointer_as_integer)




LIBUV_INCLUDE_DIRS = [
    os.path.join(libuv_dir, 'include'),
    os.path.join(libuv_dir, 'src'),
]

# Initially based on https://github.com/saghul/pyuv/blob/v1.x/setup_libuv.py

def _libuv_source(rel_path):
    # Certain versions of setuptools, notably on windows, are *very*
    # picky about what we feed to sources= "setup() arguments must
    # *always* be /-separated paths relative to the setup.py
    # directory, *never* absolute paths." POSIX doesn't have that issue.
    path = os.path.join('deps', 'libuv', 'src', rel_path)
    return path

LIBUV_SOURCES = [
    _libuv_source('fs-poll.c'),
    _libuv_source('inet.c'),
    _libuv_source('threadpool.c'),
    _libuv_source('uv-common.c'),
    _libuv_source('version.c'),
    _libuv_source('uv-data-getter-setters.c'),
    _libuv_source('timer.c'),
    _libuv_source('idna.c'),
    _libuv_source('strscpy.c'),
    # Added between 1.42.0 and 1.44.2; only used
    # on unix in that release, but generic
    _libuv_source('strtok.c'),
]

if WIN:
    LIBUV_SOURCES += [
        _libuv_source('win/async.c'),
        _libuv_source('win/core.c'),
        _libuv_source('win/detect-wakeup.c'),
        _libuv_source('win/dl.c'),
        _libuv_source('win/error.c'),
        _libuv_source('win/fs-event.c'),
        _libuv_source('win/fs.c'),
        # getaddrinfo.c refers to ConvertInterfaceIndexToLuid
        # and ConvertInterfaceLuidToNameA, which are supposedly in iphlpapi.h
        # and iphlpapi.lib/dll. But on Windows 10 with Python 3.5 and VC 14 (Visual Studio 2015),
        # I get an undefined warning from the compiler for those functions and
        # a link error from the linker, so this file can't be included.
        # This is possibly because the functions are defined for Windows Vista, and
        # Python 3.5 builds with at earlier SDK?
        # Fortunately we don't use those functions.
        #_libuv_source('win/getaddrinfo.c'),
        # getnameinfo.c refers to uv__getaddrinfo_translate_error from
        # getaddrinfo.c, which we don't have.
        #_libuv_source('win/getnameinfo.c'),
        _libuv_source('win/handle.c'),
        _libuv_source('win/loop-watcher.c'),
        _libuv_source('win/pipe.c'),
        _libuv_source('win/poll.c'),
        _libuv_source('win/process-stdio.c'),
        _libuv_source('win/process.c'),
        _libuv_source('win/signal.c'),
        _libuv_source('win/snprintf.c'),
        _libuv_source('win/stream.c'),
        _libuv_source('win/tcp.c'),
        _libuv_source('win/thread.c'),
        _libuv_source('win/tty.c'),
        _libuv_source('win/udp.c'),
        _libuv_source('win/util.c'),
        _libuv_source('win/winapi.c'),
        _libuv_source('win/winsock.c'),
    ]
else:
    LIBUV_SOURCES += [
        _libuv_source('unix/async.c'),
        _libuv_source('unix/core.c'),
        _libuv_source('unix/dl.c'),
        _libuv_source('unix/fs.c'),
        _libuv_source('unix/getaddrinfo.c'),
        _libuv_source('unix/getnameinfo.c'),
        _libuv_source('unix/loop-watcher.c'),
        _libuv_source('unix/loop.c'),
        _libuv_source('unix/pipe.c'),
        _libuv_source('unix/poll.c'),
        _libuv_source('unix/process.c'),
        _libuv_source('unix/signal.c'),
        _libuv_source('unix/stream.c'),
        _libuv_source('unix/tcp.c'),
        _libuv_source('unix/thread.c'),
        _libuv_source('unix/tty.c'),
        _libuv_source('unix/udp.c'),
    ]


if sys.platform.startswith('linux'):
    LIBUV_SOURCES += [
        _libuv_source('unix/linux-core.c'),
        _libuv_source('unix/linux-inotify.c'),
        _libuv_source('unix/linux-syscalls.c'),
        _libuv_source('unix/procfs-exepath.c'),
        _libuv_source('unix/proctitle.c'),
        _libuv_source('unix/random-sysctl-linux.c'),
        _libuv_source('unix/epoll.c'),
    ]
elif sys.platform == 'darwin':
    LIBUV_SOURCES += [
        _libuv_source('unix/bsd-ifaddrs.c'),
        _libuv_source('unix/darwin.c'),
        _libuv_source('unix/darwin-proctitle.c'),
        _libuv_source('unix/fsevents.c'),
        _libuv_source('unix/kqueue.c'),
        _libuv_source('unix/proctitle.c'),
    ]
elif sys.platform.startswith(('freebsd', 'dragonfly')): # pragma: no cover
    # Not tested
    LIBUV_SOURCES += [
        _libuv_source('unix/bsd-ifaddrs.c'),
        _libuv_source('unix/freebsd.c'),
        _libuv_source('unix/kqueue.c'),
        _libuv_source('unix/posix-hrtime.c'),
        _libuv_source('unix/bsd-proctitle.c'),
    ]
elif sys.platform.startswith('openbsd'): # pragma: no cover
    # Not tested
    LIBUV_SOURCES += [
        _libuv_source('unix/bsd-ifaddrs.c'),
        _libuv_source('unix/kqueue.c'),
        _libuv_source('unix/openbsd.c'),
        _libuv_source('unix/posix-hrtime.c'),
        _libuv_source('unix/bsd-proctitle.c'),
    ]
elif sys.platform.startswith('netbsd'): # pragma: no cover
    # Not tested
    LIBUV_SOURCES += [
        _libuv_source('unix/bsd-ifaddrs.c'),
        _libuv_source('unix/kqueue.c'),
        _libuv_source('unix/netbsd.c'),
        _libuv_source('unix/posix-hrtime.c'),
        _libuv_source('unix/bsd-proctitle.c'),
    ]
elif sys.platform.startswith('sunos'): # pragma: no cover
    # Not tested.
    LIBUV_SOURCES += [
        _libuv_source('unix/no-proctitle.c'),
        _libuv_source('unix/sunos.c'),
    ]
elif sys.platform.startswith('aix'): # pragma: no cover
    # Not tested.
    LIBUV_SOURCES += [
        _libuv_source('unix/aix.c'),
        _libuv_source('unix/aix-common.c'),
    ]
elif sys.platform.startswith('haiku'): # pragma: no cover
    # Not tested
    LIBUV_SOURCES += [
        _libuv_source('unix/haiku.c')
    ]
elif sys.platform.startswith('cygwin'): # pragma: no cover
    # Not tested.

    # Based on Cygwin package sources /usr/src/libuv-1.32.0-1.src/libuv-1.32.0/Makefile.am
    # Apparently the same upstream at https://github.com/libuv/libuv/blob/v1.x/Makefile.am
    LIBUV_SOURCES += [
        _libuv_source('unix/cygwin.c'),
        _libuv_source('unix/bsd-ifaddrs.c'),
        _libuv_source('unix/no-fsevents.c'),
        _libuv_source('unix/no-proctitle.c'),
        _libuv_source('unix/posix-hrtime.c'),
        _libuv_source('unix/posix-poll.c'),
        _libuv_source('unix/procfs-exepath.c'),
        _libuv_source('unix/sysinfo-loadavg.c'),
        _libuv_source('unix/sysinfo-memory.c'),
    ]


LIBUV_MACROS = [
    ('LIBUV_EMBED', int(LIBUV_EMBED)),
]

def _define_macro(name, value):
    LIBUV_MACROS.append((name, value))

LIBUV_LIBRARIES = []

def _add_library(name):
    LIBUV_LIBRARIES.append(name)

if sys.platform != 'win32':
    _define_macro('_LARGEFILE_SOURCE', 1)
    _define_macro('_FILE_OFFSET_BITS', 64)

if sys.platform.startswith('linux'):
    _add_library('dl')
    _add_library('rt')
    _define_macro('_GNU_SOURCE', 1)
    _define_macro('_POSIX_C_SOURCE', '200112')
elif sys.platform == 'darwin':
    _define_macro('_DARWIN_USE_64_BIT_INODE', 1)
    _define_macro('_DARWIN_UNLIMITED_SELECT', 1)
elif sys.platform.startswith('netbsd'): # pragma: no cover
    _add_library('kvm')
elif sys.platform.startswith('sunos'): # pragma: no cover
    _define_macro('__EXTENSIONS__', 1)
    _define_macro('_XOPEN_SOURCE', 500)
    _define_macro('_REENTRANT', 1)
    _add_library('kstat')
    _add_library('nsl')
    _add_library('sendfile')
    _add_library('socket')
    if platform.release() == '5.10':
        # https://github.com/libuv/libuv/issues/1458
        # https://github.com/giampaolo/psutil/blob/4d6a086411c77b7909cce8f4f141bbdecfc0d354/setup.py#L298-L300
        _define_macro('SUNOS_NO_IFADDRS', '')
elif sys.platform.startswith('aix'): # pragma: no cover
    _define_macro('_LINUX_SOURCE_COMPAT', 1)
    if os.uname().sysname != 'OS400':
        _add_library('perfstat')
elif WIN:
    # All other gevent .pyd files link to the specific minor-version Python
    # DLL, so we should do the same here. In virtual environments that don't
    # contain the major-version python?.dll stub, _corecffi.pyd would otherwise
    # cause the Windows DLL loader to search the entire PATH for a DLL with
    # that name. This might end up bringing a second, ABI-incompatible Python
    # version into the process, which can easily lead to crashes.
    # See https://github.com/gevent/gevent/pull/1814/files
    _define_macro('_CFFI_NO_LIMITED_API', 1)

    _define_macro('_GNU_SOURCE', 1)
    _define_macro('WIN32', 1)
    _define_macro('_CRT_SECURE_NO_DEPRECATE', 1)
    _define_macro('_CRT_NONSTDC_NO_DEPRECATE', 1)
    _define_macro('_CRT_SECURE_NO_WARNINGS', 1)
    _define_macro('_WIN32_WINNT', '0x0602')
    _define_macro('WIN32_LEAN_AND_MEAN', 1)
    # This value isn't available on the platform that we build and
    # test Python 2.7 on. It's used for getting power management
    # suspend/resume notifications, maybe for keeping timers accurate?
    #
    # TODO: This should be a more targeted check based on the platform
    # version, but that's complicated because it depends on having a
    # particular patch installed to the OS, and I don't know how to
    # check for that...but we're dropping Python 2 support soon, so
    # I suspect it really doesn't matter.
    if PY2:
        _define_macro('LOAD_LIBRARY_SEARCH_SYSTEM32', 0)
    _add_library('advapi32')
    _add_library('iphlpapi')
    _add_library('psapi')
    _add_library('shell32')
    _add_library('user32')
    _add_library('userenv')
    _add_library('ws2_32')

if not LIBUV_EMBED:
    del LIBUV_SOURCES[:]
    del LIBUV_INCLUDE_DIRS[:]
    _add_library('uv')

LIBUV_INCLUDE_DIRS.append(parentdir)

ffi.cdef(_cdef)
ffi.set_source(
    'gevent.libuv._corecffi',
    _source,
    sources=LIBUV_SOURCES,
    depends=LIBUV_SOURCES,
    include_dirs=LIBUV_INCLUDE_DIRS,
    libraries=list(LIBUV_LIBRARIES),
    define_macros=list(LIBUV_MACROS),
    extra_compile_args=list(_setuputils.IGNORE_THIRD_PARTY_WARNINGS),
)

if __name__ == '__main__':
    # See notes in libev/_corecffi_build.py for how to test this.
    #
    # Other than the obvious directory changes, the changes are:
    #
    # CPPFLAGS=-Ideps/libuv/include/ -Isrc/gevent/
    ffi.compile(verbose=True)
