"""
Wrappers to make file-like objects cooperative.

.. class:: FileObject(fobj, mode='r', buffering=-1, closefd=True, encoding=None, errors=None, newline=None)

    The main entry point to the file-like gevent-compatible behaviour. It
    will be defined to be the best available implementation.

    All the parameters are as for :func:`io.open`.

    :param fobj: Usually a file descriptor of a socket. Can also be
        another object with a ``fileno()`` method, or an object that can
        be passed to ``io.open()`` (e.g., a file system path). If the object
        is not a socket, the results will vary based on the platform and the
        type of object being opened.

        All supported versions of Python allow :class:`os.PathLike` objects.

    .. versionchanged:: 1.5
       Accept str and ``PathLike`` objects for *fobj* on all versions of Python.
    .. versionchanged:: 1.5
       Add *encoding*, *errors* and *newline* arguments.
    .. versionchanged:: 1.5
       Accept *closefd* and *buffering* instead of *close* and *bufsize* arguments.
       The latter remain for backwards compatibility.

There are two main implementations of ``FileObject``. On all systems,
there is :class:`FileObjectThread` which uses the built-in native
threadpool to avoid blocking the entire interpreter. On UNIX systems
(those that support the :mod:`fcntl` module), there is also
:class:`FileObjectPosix` which uses native non-blocking semantics.

A third class, :class:`FileObjectBlock`, is simply a wrapper that
executes everything synchronously (and so is not gevent-compatible).
It is provided for testing and debugging purposes.

All classes have the same signature; some may accept extra keyword arguments.

Configuration
=============

You may change the default value for ``FileObject`` using the
``GEVENT_FILE`` environment variable. Set it to ``posix``, ``thread``,
or ``block`` to choose from :class:`FileObjectPosix`,
:class:`FileObjectThread` and :class:`FileObjectBlock`, respectively.
You may also set it to the fully qualified class name of another
object that implements the file interface to use one of your own
objects.

.. note::

    The environment variable must be set at the time this module
    is first imported.

Classes
=======
"""
from __future__ import absolute_import

from gevent._config import config

__all__ = [
    'FileObjectPosix',
    'FileObjectThread',
    'FileObjectBlock',
    'FileObject',
]

try:
    from fcntl import fcntl
except ImportError:
    __all__.remove("FileObjectPosix")
else:
    del fcntl
    from gevent._fileobjectposix import FileObjectPosix

from gevent._fileobjectcommon import FileObjectThread
from gevent._fileobjectcommon import FileObjectBlock


# None of the possible objects can live in this module because
# we would get an import cycle and the config couldn't be set from code.
# TODO: zope.hookable would be great for allowing this to be imported
# without requiring configuration but still being very fast.
FileObject = config.fileobject
