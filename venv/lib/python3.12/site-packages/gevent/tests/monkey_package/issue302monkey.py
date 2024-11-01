from __future__ import print_function
import socket
import sys
import os.path
if sys.argv[1] == 'patched':
    print('gevent' in repr(socket.socket))
else:
    assert sys.argv[1] == 'stdlib'
    print('gevent' not in repr(socket.socket))
print(os.path.abspath(__file__))



if sys.argv[1] == 'patched':
    # __package__ is handled differently, for some reason, and
    # runpy doesn't let us override it. When we call it, it
    # becomes ''. This appears to be against the documentation for
    # runpy, which says specifically "If the supplied path
    # directly references a script file (whether as source or as
    # precompiled byte code), then __file__ will be set to the
    # supplied path, and __spec__, __cached__, __loader__ and
    # __package__ will all be set to None."
    print(__package__ == '') # pylint:disable=compare-to-empty-string
else:
    # but the interpreter sets it to None
    print(__package__ is None)
