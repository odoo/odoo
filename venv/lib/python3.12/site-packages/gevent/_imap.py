# -*- coding: utf-8 -*-
# Copyright (c) 2018 gevent
# cython: auto_pickle=False,embedsignature=True,always_allow_keywords=False,infer_types=True

"""
Iterators across greenlets or AsyncResult objects.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


from gevent import lock
from gevent import queue


__all__ = [
    'IMapUnordered',
    'IMap',
]

locals()['Greenlet'] = __import__('gevent').Greenlet
locals()['Semaphore'] = lock.Semaphore
locals()['UnboundQueue'] = queue.UnboundQueue


class Failure(object):
    __slots__ = ('exc', 'raise_exception')

    def __init__(self, exc, raise_exception=None):
        self.exc = exc
        self.raise_exception = raise_exception


def _raise_exc(failure):
    # For cython.
    if failure.raise_exception:
        failure.raise_exception()
    else:
        raise failure.exc

class IMapUnordered(Greenlet): # pylint:disable=undefined-variable
    """
    At iterator of map results.
    """

    def __init__(self, func, iterable, spawn, maxsize=None, _zipped=False):
        """
        An iterator that.

        :param callable spawn: The function we use to create new greenlets.
        :keyword int maxsize: If given and not-None, specifies the maximum number of
            finished results that will be allowed to accumulated awaiting the reader;
            more than that number of results will cause map function greenlets to begin
            to block. This is most useful is there is a great disparity in the speed of
            the mapping code and the consumer and the results consume a great deal of resources.
            Using a bound is more computationally expensive than not using a bound.

        .. versionchanged:: 1.1b3
            Added the *maxsize* parameter.
        """
        Greenlet.__init__(self) # pylint:disable=undefined-variable
        self.spawn = spawn
        self._zipped = _zipped
        self.func = func
        self.iterable = iterable
        self.queue = UnboundQueue() # pylint:disable=undefined-variable


        if maxsize:
            # Bounding the queue is not enough if we want to keep from
            # accumulating objects; the result value will be around as
            # the greenlet's result, blocked on self.queue.put(), and
            # we'll go on to spawn another greenlet, which in turn can
            # create the result. So we need a semaphore to prevent a
            # greenlet from exiting while the queue is full so that we
            # don't spawn the next greenlet (assuming that self.spawn
            # is of course bounded). (Alternatively we could have the
            # greenlet itself do the insert into the pool, but that
            # takes some rework).
            #
            # Given the use of a semaphore at this level, sizing the queue becomes
            # redundant, and that lets us avoid having to use self.link() instead
            # of self.rawlink() to avoid having blocking methods called in the
            # hub greenlet.
            self._result_semaphore = Semaphore(maxsize) # pylint:disable=undefined-variable
        else:
            self._result_semaphore = None

        self._outstanding_tasks = 0
        # The index (zero based) of the maximum number of
        # results we will have.
        self._max_index = -1
        self.finished = False


    # We're iterating in a different greenlet than we're running.
    def __iter__(self):
        return self

    def __next__(self):
        if self._result_semaphore is not None:
            self._result_semaphore.release()
        value = self._inext()
        if isinstance(value, Failure):
            _raise_exc(value)
        return value

    next = __next__ # Py2

    def _inext(self):
        return self.queue.get()

    def _ispawn(self, func, item, item_index):
        if self._result_semaphore is not None:
            self._result_semaphore.acquire()
        self._outstanding_tasks += 1
        g = self.spawn(func, item) if not self._zipped else self.spawn(func, *item)
        g._imap_task_index = item_index
        g.rawlink(self._on_result)
        return g

    def _run(self): # pylint:disable=method-hidden
        try:
            func = self.func
            for item in self.iterable:
                self._max_index += 1
                self._ispawn(func, item, self._max_index)
            self._on_finish(None)
        except BaseException as e:
            self._on_finish(e)
            raise
        finally:
            self.spawn = None
            self.func = None
            self.iterable = None
            self._result_semaphore = None

    def _on_result(self, greenlet):
        # This method will be called in the hub greenlet (we rawlink)
        self._outstanding_tasks -= 1
        count = self._outstanding_tasks
        finished = self.finished
        ready = self.ready()
        put_finished = False

        if ready and count <= 0 and not finished:
            finished = self.finished = True
            put_finished = True

        if greenlet.successful():
            self.queue.put(self._iqueue_value_for_success(greenlet))
        else:
            self.queue.put(self._iqueue_value_for_failure(greenlet))

        if put_finished:
            self.queue.put(self._iqueue_value_for_self_finished())

    def _on_finish(self, exception):
        # Called in this greenlet.
        if self.finished:
            return

        if exception is not None:
            self.finished = True
            self.queue.put(self._iqueue_value_for_self_failure(exception))
            return

        if self._outstanding_tasks <= 0:
            self.finished = True
            self.queue.put(self._iqueue_value_for_self_finished())

    def _iqueue_value_for_success(self, greenlet):
        return greenlet.value

    def _iqueue_value_for_failure(self, greenlet):
        return Failure(greenlet.exception, getattr(greenlet, '_raise_exception'))

    def _iqueue_value_for_self_finished(self):
        return Failure(StopIteration())

    def _iqueue_value_for_self_failure(self, exception):
        return Failure(exception, self._raise_exception)


class IMap(IMapUnordered):
    # A specialization of IMapUnordered that returns items
    # in the order in which they were generated, not
    # the order in which they finish.

    def __init__(self, *args, **kwargs):
        # The result dictionary: {index: value}
        self._results = {}

        # The index of the result to return next.
        self.index = 0
        IMapUnordered.__init__(self, *args, **kwargs)

    def _inext(self):
        try:
            value = self._results.pop(self.index)
        except KeyError:
            # Wait for our index to finish.
            while 1:
                index, value = self.queue.get()
                if index == self.index:
                    break
                self._results[index] = value
        self.index += 1
        return value

    def _iqueue_value_for_success(self, greenlet):
        return (greenlet._imap_task_index, IMapUnordered._iqueue_value_for_success(self, greenlet))

    def _iqueue_value_for_failure(self, greenlet):
        return (greenlet._imap_task_index, IMapUnordered._iqueue_value_for_failure(self, greenlet))

    def _iqueue_value_for_self_finished(self):
        return (self._max_index + 1, IMapUnordered._iqueue_value_for_self_finished(self))

    def _iqueue_value_for_self_failure(self, exception):
        return (self._max_index + 1, IMapUnordered._iqueue_value_for_self_failure(self, exception))

from gevent._util import import_c_accel
import_c_accel(globals(), 'gevent.__imap')
