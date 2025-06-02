""" Garbage collector tools

## Reference
https://github.com/python/cpython/blob/main/InternalDocs/garbage_collector.md

## TLDR cpython

Objects have reference counts, but we need garbage collection for cyclic
references.  All allocated objects are split into collections (aka generations).
There is also one permanent generation that is never collected (see
``gc.freeze``).

The GC is triggered by the number of created objects. For the first collection,
at every allocation and deallocation, a counter is respectively increased and
decreased. Once it reaches a threshold, that collection is automatically
collected. Other thresolds indicate that every X collections, the next
collection is collected.

Default thresolds are 700, 10, 10.
"""
import contextlib
import gc
import logging

_logger = logging.getLogger('gc')


@contextlib.contextmanager
def disabling_gc():
    """Disable gc in the context manager."""
    if not gc.isenabled():
        yield False
        return
    gc.disable()
    _logger.debug('disabled, counts %s', gc.get_count())
    yield True
    counts = gc.get_count()
    gc.enable()
    _logger.debug('enabled, counts %s', counts)
