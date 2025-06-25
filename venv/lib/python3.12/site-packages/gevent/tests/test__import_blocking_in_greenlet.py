#!/usr/bin/python
# See https://github.com/gevent/gevent/issues/108
import gevent
from gevent import monkey

monkey.patch_all()

import_errors = []


def some_func():
    try:
        from _blocks_at_top_level import x
        assert x == 'done'
    except ImportError as e:
        import_errors.append(e)
        raise

gs = [gevent.spawn(some_func) for i in range(2)]
gevent.joinall(gs)

assert not import_errors, import_errors
