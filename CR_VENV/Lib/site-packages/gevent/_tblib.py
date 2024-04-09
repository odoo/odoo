# -*- coding: utf-8 -*-
# A vendored version of part of https://github.com/ionelmc/python-tblib
# pylint:disable=redefined-outer-name,reimported,function-redefined,bare-except,no-else-return,broad-except
####
# Copyright (c) 2013-2016, Ionel Cristian Mărieș
# All rights reserved.

# Redistribution and use in source and binary forms, with or without modification, are permitted provided that the
# following conditions are met:

# 1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following
# disclaimer.

# 2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following
# disclaimer in the documentation and/or other materials provided with the distribution.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
# THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
####

# cpython.py

"""
Taken verbatim from Jinja2.

https://github.com/mitsuhiko/jinja2/blob/master/jinja2/debug.py#L267
"""
# pylint:disable=consider-using-dict-comprehension
#import platform # XXX: gevent cannot import platform at the top level; interferes with monkey patching
import sys


def _init_ugly_crap():
    """This function implements a few ugly things so that we can patch the
    traceback objects.  The function returned allows resetting `tb_next` on
    any python traceback object.  Do not attempt to use this on non cpython
    interpreters
    """
    import ctypes
    from types import TracebackType

    # figure out side of _Py_ssize_t
    if hasattr(ctypes.pythonapi, 'Py_InitModule4_64'):
        _Py_ssize_t = ctypes.c_int64
    else:
        _Py_ssize_t = ctypes.c_int

    # regular python
    class _PyObject(ctypes.Structure):
        pass

    _PyObject._fields_ = [
        ('ob_refcnt', _Py_ssize_t),
        ('ob_type', ctypes.POINTER(_PyObject))
    ]

    # python with trace
    if hasattr(sys, 'getobjects'):
        class _PyObject(ctypes.Structure):
            pass

        _PyObject._fields_ = [
            ('_ob_next', ctypes.POINTER(_PyObject)),
            ('_ob_prev', ctypes.POINTER(_PyObject)),
            ('ob_refcnt', _Py_ssize_t),
            ('ob_type', ctypes.POINTER(_PyObject))
        ]

    class _Traceback(_PyObject):
        pass

    _Traceback._fields_ = [
        ('tb_next', ctypes.POINTER(_Traceback)),
        ('tb_frame', ctypes.POINTER(_PyObject)),
        ('tb_lasti', ctypes.c_int),
        ('tb_lineno', ctypes.c_int)
    ]

    def tb_set_next(tb, next):
        """Set the tb_next attribute of a traceback object."""
        if not (isinstance(tb, TracebackType) and (next is None or isinstance(next, TracebackType))):
            raise TypeError('tb_set_next arguments must be traceback objects')
        obj = _Traceback.from_address(id(tb))
        if tb.tb_next is not None:
            old = _Traceback.from_address(id(tb.tb_next))
            old.ob_refcnt -= 1
        if next is None:
            obj.tb_next = ctypes.POINTER(_Traceback)()
        else:
            next = _Traceback.from_address(id(next))
            next.ob_refcnt += 1
            obj.tb_next = ctypes.pointer(next)

    return tb_set_next


tb_set_next = None
#try:
#    if platform.python_implementation() == 'CPython':
#        tb_set_next = _init_ugly_crap()
#except Exception as exc:
#    sys.stderr.write("Failed to initialize cpython support: {!r}".format(exc))
#del _init_ugly_crap

# __init__.py
import re
from types import CodeType
from types import FrameType
from types import TracebackType

try:
    from __pypy__ import tproxy
except ImportError:
    tproxy = None

__version__ = '1.3.0'
__all__ = ('Traceback',)

PY3 = sys.version_info[0] >= 3
FRAME_RE = re.compile(r'^\s*File "(?P<co_filename>.+)", line (?P<tb_lineno>\d+)(, in (?P<co_name>.+))?$')


class _AttrDict(dict):
    __slots__ = ()

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)


# noinspection PyPep8Naming
class __traceback_maker(Exception):
    pass


class TracebackParseError(Exception):
    pass


class Code(object):
    def __init__(self, code):
        self.co_filename = code.co_filename
        self.co_name = code.co_name
        self.co_argcount = 0
        self.co_kwonlyargcount = 0
        self.co_varnames = ()
        # gevent: copy more attributes
        self.co_nlocals = code.co_nlocals
        self.co_stacksize = code.co_stacksize
        self.co_flags = code.co_flags
        self.co_firstlineno = code.co_firstlineno

    def __reduce__(self):
        return Code, (_AttrDict(self.__dict__),)

    # noinspection SpellCheckingInspection
    def __tproxy__(self, operation, *args, **kwargs):
        if operation in ('__getattribute__', '__getattr__'):
            return getattr(self, args[0])
        else:
            return getattr(self, operation)(*args, **kwargs)


class Frame(object):
    def __init__(self, frame):
        self.f_locals = {}
        self.f_globals = dict([
            (k, v)
            for k, v in frame.f_globals.items()
            if k in ("__file__", "__name__")
        ])
        self.f_code = Code(frame.f_code)
        self.f_lineno = frame.f_lineno

    def clear(self):
        # For compatibility with PyPy 3.5;
        # clear was added to frame in Python 3.4
        # and is called by traceback.clear_frames(), which
        # in turn is called by unittest.TestCase.assertRaises
        pass

    # noinspection SpellCheckingInspection
    def __tproxy__(self, operation, *args, **kwargs):
        if operation in ('__getattribute__', '__getattr__'):
            if args[0] == 'f_code':
                return tproxy(CodeType, self.f_code.__tproxy__)
            else:
                return getattr(self, args[0])
        else:
            return getattr(self, operation)(*args, **kwargs)


class Traceback(object):

    tb_next = None

    def __init__(self, tb):
        self.tb_frame = Frame(tb.tb_frame)
        # noinspection SpellCheckingInspection
        self.tb_lineno = int(tb.tb_lineno)

        # Build in place to avoid exceeding the recursion limit
        tb = tb.tb_next
        prev_traceback = self
        cls = type(self)
        while tb is not None:
            traceback = object.__new__(cls)
            traceback.tb_frame = Frame(tb.tb_frame)
            traceback.tb_lineno = int(tb.tb_lineno)
            prev_traceback.tb_next = traceback
            prev_traceback = traceback
            tb = tb.tb_next

    def as_traceback(self):
        if tproxy:
            return tproxy(TracebackType, self.__tproxy__)
        if not tb_set_next:
            raise RuntimeError("Cannot re-create traceback !")

        current = self
        top_tb = None
        tb = None
        while current:
            f_code = current.tb_frame.f_code
            code = compile('\n' * (current.tb_lineno - 1) + 'raise __traceback_maker', current.tb_frame.f_code.co_filename, 'exec')
            if hasattr(code, "replace"):
                # Python 3.8 and newer
                code = code.replace(co_argcount=0,
                                    co_filename=f_code.co_filename, co_name=f_code.co_name,
                                    co_freevars=(), co_cellvars=())
            elif PY3:
                code = CodeType(
                    0, code.co_kwonlyargcount,
                    code.co_nlocals, code.co_stacksize, code.co_flags,
                    code.co_code, code.co_consts, code.co_names, code.co_varnames,
                    f_code.co_filename, f_code.co_name,
                    code.co_firstlineno, code.co_lnotab, (), ()
                )
            else:
                code = CodeType(
                    0,
                    code.co_nlocals, code.co_stacksize, code.co_flags,
                    code.co_code, code.co_consts, code.co_names, code.co_varnames,
                    f_code.co_filename.encode(), f_code.co_name.encode(),
                    code.co_firstlineno, code.co_lnotab, (), ()
                )

            # noinspection PyBroadException
            try:
                exec(code, dict(current.tb_frame.f_globals), {})
            except:
                next_tb = sys.exc_info()[2].tb_next
                if top_tb is None:
                    top_tb = next_tb
                if tb is not None:
                    tb_set_next(tb, next_tb)
                tb = next_tb
                del next_tb

            current = current.tb_next
        try:
            return top_tb
        finally:
            del top_tb
            del tb
    to_traceback = as_traceback


    # noinspection SpellCheckingInspection
    def __tproxy__(self, operation, *args, **kwargs):
        if operation in ('__getattribute__', '__getattr__'):
            if args[0] == 'tb_next':
                return self.tb_next and self.tb_next.as_traceback()
            elif args[0] == 'tb_frame':
                return tproxy(FrameType, self.tb_frame.__tproxy__)
            else:
                return getattr(self, args[0])
        else:
            return getattr(self, operation)(*args, **kwargs)

    def as_dict(self):
        """Convert a Traceback into a dictionary representation"""
        if self.tb_next is None:
            tb_next = None
        else:
            tb_next = self.tb_next.to_dict()

        code = {
            'co_filename': self.tb_frame.f_code.co_filename,
            'co_name': self.tb_frame.f_code.co_name,
        }
        frame = {
            'f_globals': self.tb_frame.f_globals,
            'f_code': code,
            'f_lineno': self.tb_frame.f_lineno,
        }
        return {
            'tb_frame': frame,
            'tb_lineno': self.tb_lineno,
            'tb_next': tb_next,
        }
    to_dict = as_dict

    @classmethod
    def from_dict(cls, dct):
        if dct['tb_next']:
            tb_next = cls.from_dict(dct['tb_next'])
        else:
            tb_next = None

        code = _AttrDict(
            co_filename=dct['tb_frame']['f_code']['co_filename'],
            co_name=dct['tb_frame']['f_code']['co_name'],
        )
        frame = _AttrDict(
            f_globals=dct['tb_frame']['f_globals'],
            f_code=code,
            f_lineno=dct['tb_frame']['f_lineno'],
        )
        tb = _AttrDict(
            tb_frame=frame,
            tb_lineno=dct['tb_lineno'],
            tb_next=tb_next,
        )
        return cls(tb)

    @classmethod
    def from_string(cls, string, strict=True):
        frames = []
        header = strict

        for line in string.splitlines():
            line = line.rstrip()
            if header:
                if line == 'Traceback (most recent call last):':
                    header = False
                continue
            frame_match = FRAME_RE.match(line)
            if frame_match:
                frames.append(frame_match.groupdict())
            elif line.startswith('  '):
                pass
            elif strict:
                break  # traceback ended

        if frames:
            previous = None
            for frame in reversed(frames):
                previous = _AttrDict(
                    frame,
                    tb_frame=_AttrDict(
                        frame,
                        f_globals=_AttrDict(
                            __file__=frame['co_filename'],
                            __name__='?',
                        ),
                        f_code=_AttrDict(frame),
                        f_lineno=int(frame['tb_lineno']),
                    ),
                    tb_next=previous,
                )
            return cls(previous)
        else:
            raise TracebackParseError("Could not find any frames in %r." % string)

# pickling_support.py


def unpickle_traceback(tb_frame, tb_lineno, tb_next):
    ret = object.__new__(Traceback)
    ret.tb_frame = tb_frame
    ret.tb_lineno = tb_lineno
    ret.tb_next = tb_next
    return ret.as_traceback()


def pickle_traceback(tb):
    return unpickle_traceback, (Frame(tb.tb_frame), tb.tb_lineno, tb.tb_next and Traceback(tb.tb_next))


def install():
    try:
        import copy_reg
    except ImportError:
        import copyreg as copy_reg

    copy_reg.pickle(TracebackType, pickle_traceback)

# Added by gevent

# We have to defer the initialization, and especially the import of platform,
# until runtime. If we're monkey patched, we need to be sure to use
# the original __import__ to avoid switching through the hub due to
# import locks on Python 2. See also builtins.py for details.


def _unlocked_imports(f):
    def g(a):
        if sys is None: # pragma: no cover
            # interpreter shutdown on Py2
            return

        gb = None
        if 'gevent.builtins' in sys.modules:
            gb = sys.modules['gevent.builtins']
            gb._unlock_imports()
        try:
            return f(a)
        finally:
            if gb is not None:
                gb._lock_imports()
    g.__name__ = f.__name__
    g.__module__ = f.__module__
    return g


def _import_dump_load():
    global dumps
    global loads
    try:
        import cPickle as pickle
    except ImportError:
        import pickle
    dumps = pickle.dumps
    loads = pickle.loads

dumps = loads = None

_installed = False


def _init():
    global _installed
    global tb_set_next
    if _installed:
        return

    _installed = True
    import platform
    try:
        if platform.python_implementation() == 'CPython':
            tb_set_next = _init_ugly_crap()
    except Exception as exc:
        sys.stderr.write("Failed to initialize cpython support: {!r}".format(exc))

    try:
        from __pypy__ import tproxy
    except ImportError:
        tproxy = None

    if not tb_set_next and not tproxy:
        raise ImportError("Cannot use tblib. Runtime not supported.")
    _import_dump_load()
    install()


@_unlocked_imports
def dump_traceback(tb):
    # Both _init and dump/load have to be unlocked, because
    # copy_reg and pickle can do imports to resolve class names; those
    # class names are in this module and greenlet safe though
    _init()
    return dumps(tb)


@_unlocked_imports
def load_traceback(s):
    _init()
    return loads(s)
