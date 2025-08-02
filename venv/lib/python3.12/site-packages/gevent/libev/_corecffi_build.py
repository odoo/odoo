# pylint: disable=no-member

# This module is only used to create and compile the gevent._corecffi module;
# nothing should be directly imported from it except `ffi`, which should only be
# used for `ffi.compile()`; programs should import gevent._corecfffi.
# However, because we are using "out-of-line" mode, it is necessary to examine
# this file to know what functions are created and available on the generated
# module.
from __future__ import absolute_import, print_function
import sys
import os
import os.path # pylint:disable=no-name-in-module
from cffi import FFI

sys.path.append(".")
try:
    import _setuplibev
    import _setuputils
except ImportError:
    print("This file must be imported with setup.py in the current working dir.")
    raise

thisdir = os.path.dirname(os.path.abspath(__file__))
parentdir = os.path.abspath(os.path.join(thisdir, '..'))
setup_dir = os.path.abspath(os.path.join(thisdir, '..', '..', '..'))


__all__ = []


ffi = FFI()
distutils_ext = _setuplibev.build_extension()

def read_source(name):
    # pylint:disable=unspecified-encoding
    with open(os.path.join(thisdir, name), 'r') as f:
        return f.read()

# cdef goes to the cffi library and determines what can be used in
# Python.
_cdef = read_source('_corecffi_cdef.c')

# These defines and uses help keep the C file readable and lintable by
# C tools.
_cdef = _cdef.replace('#define GEVENT_STRUCT_DONE int', '')
_cdef = _cdef.replace("GEVENT_STRUCT_DONE _;", '...;')

_cdef = _cdef.replace('#define GEVENT_ST_NLINK_T int',
                      'typedef int... nlink_t;')
_cdef = _cdef.replace('GEVENT_ST_NLINK_T', 'nlink_t')

if _setuplibev.LIBEV_EMBED:
    # Arrange access to the loop internals
    _cdef += """
struct ev_loop {
    int backend_fd;
    int activecnt;
    ...;
};
    """

# arrange to be configured.
_setuputils.ConfiguringBuildExt.gevent_add_pre_run_action(distutils_ext.configure)


if sys.platform.startswith('win'):
    # We must have the vfd_open, etc, functions on
    # Windows. But on other platforms, going through
    # CFFI to just return the file-descriptor is slower
    # than just doing it in Python, so we check for and
    # workaround their absence in corecffi.py
    _cdef += """
typedef int... vfd_socket_t;
int vfd_open(vfd_socket_t);
vfd_socket_t vfd_get(int);
void vfd_free(int);
"""

# source goes to the C compiler
_source = read_source('_corecffi_source.c')

macros = list(distutils_ext.define_macros)
try:
    # We need the data pointer.
    macros.remove(('EV_COMMON', ''))
except ValueError:
    pass

ffi.cdef(_cdef)
ffi.set_source(
    'gevent.libev._corecffi',
    _source,
    include_dirs=distutils_ext.include_dirs + [
        thisdir, # "libev.h"
        parentdir, # _ffi/alloc.c
    ],
    define_macros=macros,
    undef_macros=distutils_ext.undef_macros,
    libraries=distutils_ext.libraries,
)

if __name__ == '__main__':
    # XXX: Note, on Windows, we would need to specify the external libraries
    # that should be linked in, such as ws2_32 and (because libev_vfd.h makes
    # Python.h calls) the proper Python library---at least for PyPy. I never got
    # that to work though, and calling python functions is strongly discouraged
    # from CFFI code.

    # On macOS to make the non-embedded case work correctly, against
    # our local copy of libev:
    #
    # 1) configure and make libev
    # 2) CPPFLAGS=-Ideps/libev/ LDFLAGS=-Ldeps/libev/.libs GEVENTSETUP_EMBED_LIBEV=0 \
    #     python setup.py build_ext -i
    # 3) export DYLD_LIBRARY_PATH=`pwd`/deps/libev/.libs
    #
    # The DYLD_LIBRARY_PATH is because the linker hard-codes
    # /usr/local/lib/libev.4.dylib in the corecffi.so dylib, because
    # that's the "install name" of the libev dylib that was built.
    # Adding a -rpath to the LDFLAGS doesn't change things.
    # This can be fixed with `install_name_tool`:
    #
    # 3) install_name_tool -change /usr/local/lib/libev.4.dylib \
    #    `pwd`/deps/libev/.libs/libev.4.dylib \
    #     src/gevent/libev/_corecffi.abi3.so
    ffi.compile(verbose=True)
