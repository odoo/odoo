import gevent

# For reproducing #728: We spawn a greenlet at import time,
# that itself wants to import, and wait on it at import time.
# If we're the only greenlet running, and locks aren't granular
# enough, this results in a LoopExit (and also a lock deadlock)


def f():
    __import__('_imports_at_top_level')

g = gevent.spawn(f)
g.get()
