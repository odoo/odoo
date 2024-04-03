# Copyright (c) 2009-2012 Denis Bilenko. See LICENSE for details.
# copyright (c) 2018 gevent
# cython: auto_pickle=False,embedsignature=True,always_allow_keywords=False
"""
Synchronized queues.

The :mod:`gevent.queue` module implements multi-producer, multi-consumer queues
that work across greenlets, with the API similar to the classes found in the
standard :mod:`Queue` and :class:`multiprocessing <multiprocessing.Queue>` modules.

The classes in this module implement the iterator protocol. Iterating
over a queue means repeatedly calling :meth:`get <Queue.get>` until
:meth:`get <Queue.get>` returns ``StopIteration`` (specifically that
class, not an instance or subclass).

    >>> import gevent.queue
    >>> queue = gevent.queue.Queue()
    >>> queue.put(1)
    >>> queue.put(2)
    >>> queue.put(StopIteration)
    >>> for item in queue:
    ...    print(item)
    1
    2

.. versionchanged:: 1.0
       ``Queue(0)`` now means queue of infinite size, not a channel. A :exc:`DeprecationWarning`
       will be issued with this argument.
"""

from __future__ import absolute_import
import sys
from heapq import heappush as _heappush
from heapq import heappop as _heappop
from heapq import heapify as _heapify
import collections

if sys.version_info[0] == 2:
    import Queue as __queue__ # python 3: pylint:disable=import-error
else:
    import queue as __queue__ # python 2: pylint:disable=import-error
# We re-export these exceptions to client modules.
# But we also want fast access to them from Cython with a cdef,
# and we do that with the _ definition.
_Full = Full = __queue__.Full
_Empty = Empty = __queue__.Empty

from gevent.timeout import Timeout
from gevent._hub_local import get_hub_noargs as get_hub
from gevent.exceptions import InvalidSwitchError

__all__ = []
__implements__ = ['Queue', 'PriorityQueue', 'LifoQueue']
__extensions__ = ['JoinableQueue', 'Channel']
__imports__ = ['Empty', 'Full']
if hasattr(__queue__, 'SimpleQueue'):
    __all__.append('SimpleQueue') # New in 3.7
    # SimpleQueue is implemented in C and directly allocates locks
    # unaffected by monkey patching. We need the Python version.
    SimpleQueue = __queue__._PySimpleQueue # pylint:disable=no-member
__all__ += (__implements__ + __extensions__ + __imports__)


# pylint 2.0.dev2 things collections.dequeue.popleft() doesn't return
# pylint:disable=assignment-from-no-return

def _safe_remove(deq, item):
    # For when the item may have been removed by
    # Queue._unlock
    try:
        deq.remove(item)
    except ValueError:
        pass

import gevent._waiter
locals()['Waiter'] = gevent._waiter.Waiter
locals()['getcurrent'] = __import__('greenlet').getcurrent
locals()['greenlet_init'] = lambda: None

class ItemWaiter(Waiter): # pylint:disable=undefined-variable
    # pylint:disable=assigning-non-slot
    __slots__ = (
        'item',
        'queue',
    )

    def __init__(self, item, queue):
        Waiter.__init__(self) # pylint:disable=undefined-variable
        self.item = item
        self.queue = queue

    def put_and_switch(self):
        self.queue._put(self.item)
        self.queue = None
        self.item = None
        return self.switch(self)

class Queue(object):
    """
    Create a queue object with a given maximum size.

    If *maxsize* is less than or equal to zero or ``None``, the queue
    size is infinite.

    Queues have a ``len`` equal to the number of items in them (the :meth:`qsize`),
    but in a boolean context they are always True.

    .. versionchanged:: 1.1b3
       Queues now support :func:`len`; it behaves the same as :meth:`qsize`.
    .. versionchanged:: 1.1b3
       Multiple greenlets that block on a call to :meth:`put` for a full queue
       will now be awakened to put their items into the queue in the order in which
       they arrived. Likewise, multiple greenlets that block on a call to :meth:`get` for
       an empty queue will now receive items in the order in which they blocked. An
       implementation quirk under CPython *usually* ensured this was roughly the case
       previously anyway, but that wasn't the case for PyPy.
    """

    __slots__ = (
        '_maxsize',
        'getters',
        'putters',
        'hub',
        '_event_unlock',
        'queue',
        '__weakref__',
    )

    def __init__(self, maxsize=None, items=(), _warn_depth=2):
        if maxsize is not None and maxsize <= 0:
            if maxsize == 0:
                import warnings
                warnings.warn(
                    'Queue(0) now equivalent to Queue(None); if you want a channel, use Channel',
                    DeprecationWarning,
                    stacklevel=_warn_depth)
            maxsize = None

        self._maxsize = maxsize if maxsize is not None else -1
        # Explicitly maintain order for getters and putters that block
        # so that callers can consistently rely on getting things out
        # in the apparent order they went in. This was once required by
        # imap_unordered. Previously these were set() objects, and the
        # items put in the set have default hash() and eq() methods;
        # under CPython, since new objects tend to have increasing
        # hash values, this tended to roughly maintain order anyway,
        # but that's not true under PyPy. An alternative to a deque
        # (to avoid the linear scan of remove()) might be an
        # OrderedDict, but it's 2.7 only; we don't expect to have so
        # many waiters that removing an arbitrary element is a
        # bottleneck, though.
        self.getters = collections.deque()
        self.putters = collections.deque()
        self.hub = get_hub()
        self._event_unlock = None
        self.queue = self._create_queue(items)

    @property
    def maxsize(self):
        return self._maxsize if self._maxsize > 0 else None

    @maxsize.setter
    def maxsize(self, nv):
        # QQQ make maxsize into a property with setter that schedules unlock if necessary
        if nv is None or nv <= 0:
            self._maxsize = -1
        else:
            self._maxsize = nv

    def copy(self):
        return type(self)(self.maxsize, self.queue)

    def _create_queue(self, items=()):
        return collections.deque(items)

    def _get(self):
        return self.queue.popleft()

    def _peek(self):
        return self.queue[0]

    def _put(self, item):
        self.queue.append(item)

    def __repr__(self):
        return '<%s at %s%s>' % (type(self).__name__, hex(id(self)), self._format())

    def __str__(self):
        return '<%s%s>' % (type(self).__name__, self._format())

    def _format(self):
        result = []
        if self.maxsize is not None:
            result.append('maxsize=%r' % (self.maxsize, ))
        if getattr(self, 'queue', None):
            result.append('queue=%r' % (self.queue, ))
        if self.getters:
            result.append('getters[%s]' % len(self.getters))
        if self.putters:
            result.append('putters[%s]' % len(self.putters))
        if result:
            return ' ' + ' '.join(result)
        return ''

    def qsize(self):
        """Return the size of the queue."""
        return len(self.queue)

    def __len__(self):
        """
        Return the size of the queue. This is the same as :meth:`qsize`.

        .. versionadded: 1.1b3

            Previously, getting len() of a queue would raise a TypeError.
        """

        return self.qsize()

    def __bool__(self):
        """
        A queue object is always True.

        .. versionadded: 1.1b3

           Now that queues support len(), they need to implement ``__bool__``
           to return True for backwards compatibility.
        """
        return True

    def __nonzero__(self):
        # Py2.
        # For Cython; __bool__ becomes a special method that we can't
        # get by name.
        return True

    def empty(self):
        """Return ``True`` if the queue is empty, ``False`` otherwise."""
        return not self.qsize()

    def full(self):
        """Return ``True`` if the queue is full, ``False`` otherwise.

        ``Queue(None)`` is never full.
        """
        return self._maxsize > 0 and self.qsize() >= self._maxsize

    def put(self, item, block=True, timeout=None):
        """Put an item into the queue.

        If optional arg *block* is true and *timeout* is ``None`` (the default),
        block if necessary until a free slot is available. If *timeout* is
        a positive number, it blocks at most *timeout* seconds and raises
        the :class:`Full` exception if no free slot was available within that time.
        Otherwise (*block* is false), put an item on the queue if a free slot
        is immediately available, else raise the :class:`Full` exception (*timeout*
        is ignored in that case).
        """
        if self._maxsize == -1 or self.qsize() < self._maxsize:
            # there's a free slot, put an item right away
            self._put(item)
            if self.getters:
                self._schedule_unlock()
        elif self.hub is getcurrent(): # pylint:disable=undefined-variable
            # We're in the mainloop, so we cannot wait; we can switch to other greenlets though.
            # Check if possible to get a free slot in the queue.
            while self.getters and self.qsize() and self.qsize() >= self._maxsize:
                getter = self.getters.popleft()
                getter.switch(getter)
            if self.qsize() < self._maxsize:
                self._put(item)
                return
            raise Full
        elif block:
            waiter = ItemWaiter(item, self)
            self.putters.append(waiter)
            timeout = Timeout._start_new_or_dummy(timeout, Full)
            try:
                if self.getters:
                    self._schedule_unlock()
                result = waiter.get()
                if result is not waiter:
                    raise InvalidSwitchError("Invalid switch into Queue.put: %r" % (result, ))
            finally:
                timeout.cancel()
                _safe_remove(self.putters, waiter)
        else:
            raise Full

    def put_nowait(self, item):
        """Put an item into the queue without blocking.

        Only enqueue the item if a free slot is immediately available.
        Otherwise raise the :class:`Full` exception.
        """
        self.put(item, False)


    def __get_or_peek(self, method, block, timeout):
        # Internal helper method. The `method` should be either
        # self._get when called from self.get() or self._peek when
        # called from self.peek(). Call this after the initial check
        # to see if there are items in the queue.

        if self.hub is getcurrent(): # pylint:disable=undefined-variable
            # special case to make get_nowait() or peek_nowait() runnable in the mainloop greenlet
            # there are no items in the queue; try to fix the situation by unlocking putters
            while self.putters:
                # Note: get() used popleft(), peek used pop(); popleft
                # is almost certainly correct.
                self.putters.popleft().put_and_switch()
                if self.qsize():
                    return method()
            raise Empty

        if not block:
            # We can't block, we're not the hub, and we have nothing
            # to return. No choice...
            raise Empty

        waiter = Waiter() # pylint:disable=undefined-variable
        timeout = Timeout._start_new_or_dummy(timeout, Empty)
        try:
            self.getters.append(waiter)
            if self.putters:
                self._schedule_unlock()
            result = waiter.get()
            if result is not waiter:
                raise InvalidSwitchError('Invalid switch into Queue.get: %r' % (result, ))
            return method()
        finally:
            timeout.cancel()
            _safe_remove(self.getters, waiter)

    def get(self, block=True, timeout=None):
        """Remove and return an item from the queue.

        If optional args *block* is true and *timeout* is ``None`` (the default),
        block if necessary until an item is available. If *timeout* is a positive number,
        it blocks at most *timeout* seconds and raises the :class:`Empty` exception
        if no item was available within that time. Otherwise (*block* is false), return
        an item if one is immediately available, else raise the :class:`Empty` exception
        (*timeout* is ignored in that case).
        """
        if self.qsize():
            if self.putters:
                self._schedule_unlock()
            return self._get()

        return self.__get_or_peek(self._get, block, timeout)

    def get_nowait(self):
        """Remove and return an item from the queue without blocking.

        Only get an item if one is immediately available. Otherwise
        raise the :class:`Empty` exception.
        """
        return self.get(False)

    def peek(self, block=True, timeout=None):
        """Return an item from the queue without removing it.

        If optional args *block* is true and *timeout* is ``None`` (the default),
        block if necessary until an item is available. If *timeout* is a positive number,
        it blocks at most *timeout* seconds and raises the :class:`Empty` exception
        if no item was available within that time. Otherwise (*block* is false), return
        an item if one is immediately available, else raise the :class:`Empty` exception
        (*timeout* is ignored in that case).
        """
        if self.qsize():
            # This doesn't schedule an unlock like get() does because we're not
            # actually making any space.
            return self._peek()

        return self.__get_or_peek(self._peek, block, timeout)

    def peek_nowait(self):
        """Return an item from the queue without blocking.

        Only return an item if one is immediately available. Otherwise
        raise the :class:`Empty` exception.
        """
        return self.peek(False)

    def _unlock(self):
        while True:
            repeat = False
            if self.putters and (self._maxsize == -1 or self.qsize() < self._maxsize):
                repeat = True
                try:
                    putter = self.putters.popleft()
                    self._put(putter.item)
                except: # pylint:disable=bare-except
                    putter.throw(*sys.exc_info())
                else:
                    putter.switch(putter)
            if self.getters and self.qsize():
                repeat = True
                getter = self.getters.popleft()
                getter.switch(getter)
            if not repeat:
                return

    def _schedule_unlock(self):
        if not self._event_unlock:
            self._event_unlock = self.hub.loop.run_callback(self._unlock)

    def __iter__(self):
        return self

    def __next__(self):
        result = self.get()
        if result is StopIteration:
            raise result
        return result

    next = __next__ # Py2


class UnboundQueue(Queue):
    # A specialization of Queue that knows it can never
    # be bound. Changing its maxsize has no effect.

    __slots__ = ()

    def __init__(self, maxsize=None, items=()):
        if maxsize is not None:
            raise ValueError("UnboundQueue has no maxsize")
        Queue.__init__(self, maxsize, items)
        self.putters = None # Will never be used.

    def put(self, item, block=True, timeout=None):
        self._put(item)
        if self.getters:
            self._schedule_unlock()


class PriorityQueue(Queue):
    '''A subclass of :class:`Queue` that retrieves entries in priority order (lowest first).

    Entries are typically tuples of the form: ``(priority number, data)``.

    .. versionchanged:: 1.2a1
       Any *items* given to the constructor will now be passed through
       :func:`heapq.heapify` to ensure the invariants of this class hold.
       Previously it was just assumed that they were already a heap.
    '''

    __slots__ = ()

    def _create_queue(self, items=()):
        q = list(items)
        _heapify(q)
        return q

    def _put(self, item):
        _heappush(self.queue, item)

    def _get(self):
        return _heappop(self.queue)


class LifoQueue(Queue):
    '''A subclass of :class:`Queue` that retrieves most recently added entries first.'''

    __slots__ = ()

    def _create_queue(self, items=()):
        return list(items)

    def _put(self, item):
        self.queue.append(item)

    def _get(self):
        return self.queue.pop()

    def _peek(self):
        return self.queue[-1]


class JoinableQueue(Queue):
    """
    A subclass of :class:`Queue` that additionally has
    :meth:`task_done` and :meth:`join` methods.
    """

    __slots__ = (
        '_cond',
        'unfinished_tasks',
    )

    def __init__(self, maxsize=None, items=(), unfinished_tasks=None):
        """

        .. versionchanged:: 1.1a1
           If *unfinished_tasks* is not given, then all the given *items*
           (if any) will be considered unfinished.

        """
        Queue.__init__(self, maxsize, items, _warn_depth=3)

        from gevent.event import Event
        self._cond = Event()
        self._cond.set()

        if unfinished_tasks:
            self.unfinished_tasks = unfinished_tasks
        elif items:
            self.unfinished_tasks = len(items)
        else:
            self.unfinished_tasks = 0

        if self.unfinished_tasks:
            self._cond.clear()

    def copy(self):
        return type(self)(self.maxsize, self.queue, self.unfinished_tasks)

    def _format(self):
        result = Queue._format(self)
        if self.unfinished_tasks:
            result += ' tasks=%s _cond=%s' % (self.unfinished_tasks, self._cond)
        return result

    def _put(self, item):
        Queue._put(self, item)
        self.unfinished_tasks += 1
        self._cond.clear()

    def task_done(self):
        '''Indicate that a formerly enqueued task is complete. Used by queue consumer threads.
        For each :meth:`get <Queue.get>` used to fetch a task, a subsequent call to :meth:`task_done` tells the queue
        that the processing on the task is complete.

        If a :meth:`join` is currently blocking, it will resume when all items have been processed
        (meaning that a :meth:`task_done` call was received for every item that had been
        :meth:`put <Queue.put>` into the queue).

        Raises a :exc:`ValueError` if called more times than there were items placed in the queue.
        '''
        if self.unfinished_tasks <= 0:
            raise ValueError('task_done() called too many times')
        self.unfinished_tasks -= 1
        if self.unfinished_tasks == 0:
            self._cond.set()

    def join(self, timeout=None):
        '''
        Block until all items in the queue have been gotten and processed.

        The count of unfinished tasks goes up whenever an item is added to the queue.
        The count goes down whenever a consumer thread calls :meth:`task_done` to indicate
        that the item was retrieved and all work on it is complete. When the count of
        unfinished tasks drops to zero, :meth:`join` unblocks.

        :param float timeout: If not ``None``, then wait no more than this time in seconds
            for all tasks to finish.
        :return: ``True`` if all tasks have finished; if ``timeout`` was given and expired before
            all tasks finished, ``False``.

        .. versionchanged:: 1.1a1
           Add the *timeout* parameter.
        '''
        return self._cond.wait(timeout=timeout)


class Channel(object):

    __slots__ = (
        'getters',
        'putters',
        'hub',
        '_event_unlock',
        '__weakref__',
    )

    def __init__(self, maxsize=1):
        # We take maxsize to simplify certain kinds of code
        if maxsize != 1:
            raise ValueError("Channels have a maxsize of 1")
        self.getters = collections.deque()
        self.putters = collections.deque()
        self.hub = get_hub()
        self._event_unlock = None

    def __repr__(self):
        return '<%s at %s %s>' % (type(self).__name__, hex(id(self)), self._format())

    def __str__(self):
        return '<%s %s>' % (type(self).__name__, self._format())

    def _format(self):
        result = ''
        if self.getters:
            result += ' getters[%s]' % len(self.getters)
        if self.putters:
            result += ' putters[%s]' % len(self.putters)
        return result

    @property
    def balance(self):
        return len(self.putters) - len(self.getters)

    def qsize(self):
        return 0

    def empty(self):
        return True

    def full(self):
        return True

    def put(self, item, block=True, timeout=None):
        if self.hub is getcurrent(): # pylint:disable=undefined-variable
            if self.getters:
                getter = self.getters.popleft()
                getter.switch(item)
                return
            raise Full

        if not block:
            timeout = 0

        waiter = Waiter() # pylint:disable=undefined-variable
        item = (item, waiter)
        self.putters.append(item)
        timeout = Timeout._start_new_or_dummy(timeout, Full)
        try:
            if self.getters:
                self._schedule_unlock()
            result = waiter.get()
            if result is not waiter:
                raise InvalidSwitchError("Invalid switch into Channel.put: %r" % (result, ))
        except:
            _safe_remove(self.putters, item)
            raise
        finally:
            timeout.cancel()

    def put_nowait(self, item):
        self.put(item, False)

    def get(self, block=True, timeout=None):
        if self.hub is getcurrent(): # pylint:disable=undefined-variable
            if self.putters:
                item, putter = self.putters.popleft()
                self.hub.loop.run_callback(putter.switch, putter)
                return item

        if not block:
            timeout = 0

        waiter = Waiter() # pylint:disable=undefined-variable
        timeout = Timeout._start_new_or_dummy(timeout, Empty)
        try:
            self.getters.append(waiter)
            if self.putters:
                self._schedule_unlock()
            return waiter.get()
        except:
            self.getters.remove(waiter)
            raise
        finally:
            timeout.close()

    def get_nowait(self):
        return self.get(False)

    def _unlock(self):
        while self.putters and self.getters:
            getter = self.getters.popleft()
            item, putter = self.putters.popleft()
            getter.switch(item)
            putter.switch(putter)

    def _schedule_unlock(self):
        if not self._event_unlock:
            self._event_unlock = self.hub.loop.run_callback(self._unlock)

    def __iter__(self):
        return self

    def __next__(self):
        result = self.get()
        if result is StopIteration:
            raise result
        return result

    next = __next__ # Py2

def _init():
    greenlet_init() # pylint:disable=undefined-variable

_init()


from gevent._util import import_c_accel
import_c_accel(globals(), 'gevent._queue')
