# Copyright (c) 2009-2011 Denis Bilenko. See LICENSE for details.
"""
Managing greenlets in a group.

The :class:`Group` class in this module abstracts a group of running
greenlets. When a greenlet dies, it's automatically removed from the
group. All running greenlets in a group can be waited on with
:meth:`Group.join`, or all running greenlets can be killed with
:meth:`Group.kill`.

The :class:`Pool` class, which is a subclass of :class:`Group`,
provides a way to limit concurrency: its :meth:`spawn <Pool.spawn>`
method blocks if the number of greenlets in the pool has already
reached the limit, until there is a free slot.
"""
from __future__ import print_function, absolute_import, division


from gevent.hub import GreenletExit, getcurrent, kill as _kill
from gevent.greenlet import joinall, Greenlet
from gevent.queue import Full as QueueFull
from gevent.timeout import Timeout
from gevent.event import Event
from gevent.lock import Semaphore, DummySemaphore

from gevent._compat import izip
from gevent._imap import IMap
from gevent._imap import IMapUnordered

__all__ = [
    'Group',
    'Pool',
    'PoolFull',
]




class GroupMappingMixin(object):
    # Internal, non-public API class.
    # Provides mixin methods for implementing mapping pools. Subclasses must define:

    __slots__ = ()

    def spawn(self, func, *args, **kwargs):
        """
        A function that runs *func* with *args* and *kwargs*, potentially
        asynchronously. Return a value with a ``get`` method that blocks
        until the results of func are available, and a ``rawlink`` method
        that calls a callback when the results are available.

        If this object has an upper bound on how many asyncronously executing
        tasks can exist, this method may block until a slot becomes available.
        """
        raise NotImplementedError()

    def _apply_immediately(self):
        """
        should the function passed to apply be called immediately,
        synchronously?
        """
        raise NotImplementedError()

    def _apply_async_use_greenlet(self):
        """
        Should apply_async directly call Greenlet.spawn(), bypassing
        `spawn`?

        Return true when self.spawn would block.
        """
        raise NotImplementedError()

    def _apply_async_cb_spawn(self, callback, result):
        """
        Run the given callback function, possibly
        asynchronously, possibly synchronously.
        """
        raise NotImplementedError()

    def apply_cb(self, func, args=None, kwds=None, callback=None):
        """
        :meth:`apply` the given *func(\\*args, \\*\\*kwds)*, and, if a *callback* is given, run it with the
        results of *func* (unless an exception was raised.)

        The *callback* may be called synchronously or asynchronously. If called
        asynchronously, it will not be tracked by this group. (:class:`Group` and :class:`Pool`
        call it asynchronously in a new greenlet; :class:`~gevent.threadpool.ThreadPool` calls
        it synchronously in the current greenlet.)
        """
        result = self.apply(func, args, kwds)
        if callback is not None:
            self._apply_async_cb_spawn(callback, result)
        return result

    def apply_async(self, func, args=None, kwds=None, callback=None):
        """
        A variant of the :meth:`apply` method which returns a :class:`~.Greenlet` object.

        When the returned greenlet gets to run, it *will* call :meth:`apply`,
        passing in *func*, *args* and *kwds*.

        If *callback* is specified, then it should be a callable which
        accepts a single argument. When the result becomes ready
        callback is applied to it (unless the call failed).

        This method will never block, even if this group is full (that is,
        even if :meth:`spawn` would block, this method will not).

        .. caution:: The returned greenlet may or may not be tracked
           as part of this group, so :meth:`joining <join>` this group is
           not a reliable way to wait for the results to be available or
           for the returned greenlet to run; instead, join the returned
           greenlet.

        .. tip:: Because :class:`~.ThreadPool` objects do not track greenlets, the returned
           greenlet will never be a part of it. To reduce overhead and improve performance,
           :class:`Group` and :class:`Pool` may choose to track the returned
           greenlet. These are implementation details that may change.
        """
        if args is None:
            args = ()
        if kwds is None:
            kwds = {}
        if self._apply_async_use_greenlet():
            # cannot call self.spawn() directly because it will block
            # XXX: This is always the case for ThreadPool, but for Group/Pool
            # of greenlets, this is only the case when they are full...hence
            # the weasely language about "may or may not be tracked". Should we make
            # Group/Pool always return true as well so it's never tracked by any
            # implementation? That would simplify that logic, but could increase
            # the total number of greenlets in the system and add a layer of
            # overhead for the simple cases when the pool isn't full.
            return Greenlet.spawn(self.apply_cb, func, args, kwds, callback)

        greenlet = self.spawn(func, *args, **kwds)
        if callback is not None:
            greenlet.link(pass_value(callback))
        return greenlet

    def apply(self, func, args=None, kwds=None):
        """
        Rough quivalent of the :func:`apply()` builtin function blocking until
        the result is ready and returning it.

        The ``func`` will *usually*, but not *always*, be run in a way
        that allows the current greenlet to switch out (for example,
        in a new greenlet or thread, depending on implementation). But
        if the current greenlet or thread is already one that was
        spawned by this pool, the pool may choose to immediately run
        the `func` synchronously.

        Any exception ``func`` raises will be propagated to the caller of ``apply`` (that is,
        this method will raise the exception that ``func`` raised).
        """
        if args is None:
            args = ()
        if kwds is None:
            kwds = {}
        if self._apply_immediately():
            return func(*args, **kwds)
        return self.spawn(func, *args, **kwds).get()

    def __map(self, func, iterable):
        return [g.get() for g in
                [self.spawn(func, i) for i in iterable]]

    def map(self, func, iterable):
        """Return a list made by applying the *func* to each element of
        the iterable.

        .. seealso:: :meth:`imap`
        """
        # We can't return until they're all done and in order. It
        # wouldn't seem to much matter what order we wait on them in,
        # so the simple, fast (50% faster than imap) solution would be:

        # return [g.get() for g in
        #           [self.spawn(func, i) for i in iterable]]

        # If the pool size is unlimited (or more than the len(iterable)), this
        # is equivalent to imap (spawn() will never block, all of them run concurrently,
        # we call get() in the order the iterable was given).

        # Now lets imagine the pool if is limited size. Suppose the
        # func is time.sleep, our pool is limited to 3 threads, and
        # our input is [10, 1, 10, 1, 1] We would start three threads,
        # one to sleep for 10, one to sleep for 1, and the last to
        # sleep for 10. We would block starting the fourth thread. At
        # time 1, we would finish the second thread and start another
        # one for time 1. At time 2, we would finish that one and
        # start the last thread, and then begin executing get() on the first
        # thread.

        # Because it's spawn that blocks, this is *also* equivalent to what
        # imap would do.

        # The one remaining difference is that imap runs in its own
        # greenlet, potentially changing the way the event loop runs.
        # That's easy enough to do.

        g = Greenlet.spawn(self.__map, func, iterable)
        return g.get()

    def map_cb(self, func, iterable, callback=None):
        result = self.map(func, iterable)
        if callback is not None:
            callback(result) # pylint:disable=not-callable
        return result

    def map_async(self, func, iterable, callback=None):
        """
        A variant of the map() method which returns a Greenlet object that is executing
        the map function.

        If callback is specified then it should be a callable which accepts a
        single argument.
        """
        return Greenlet.spawn(self.map_cb, func, iterable, callback)

    def __imap(self, cls, func, *iterables, **kwargs):
        # Python 2 doesn't support the syntax that lets us mix varargs and
        # a named kwarg, so we have to unpack manually
        maxsize = kwargs.pop('maxsize', None)
        if kwargs:
            raise TypeError("Unsupported keyword arguments")
        return cls.spawn(func, izip(*iterables), spawn=self.spawn,
                         _zipped=True, maxsize=maxsize)

    def imap(self, func, *iterables, **kwargs):
        """
        imap(func, *iterables, maxsize=None) -> iterable

        An equivalent of :func:`itertools.imap`, operating in parallel.
        The *func* is applied to each element yielded from each
        iterable in *iterables* in turn, collecting the result.

        If this object has a bound on the number of active greenlets it can
        contain (such as :class:`Pool`), then at most that number of tasks will operate
        in parallel.

        :keyword int maxsize: If given and not-None, specifies the maximum number of
            finished results that will be allowed to accumulate awaiting the reader;
            more than that number of results will cause map function greenlets to begin
            to block. This is most useful if there is a great disparity in the speed of
            the mapping code and the consumer and the results consume a great deal of resources.

            .. note:: This is separate from any bound on the number of active parallel
               tasks, though they may have some interaction (for example, limiting the
               number of parallel tasks to the smallest bound).

            .. note:: Using a bound is slightly more computationally expensive than not using a bound.

            .. tip:: The :meth:`imap_unordered` method makes much better
                use of this parameter. Some additional, unspecified,
                number of objects may be required to be kept in memory
                to maintain order by this function.

        :return: An iterable object.

        .. versionchanged:: 1.1b3
            Added the *maxsize* keyword parameter.
        .. versionchanged:: 1.1a1
            Accept multiple *iterables* to iterate in parallel.
        """
        return self.__imap(IMap, func, *iterables, **kwargs)

    def imap_unordered(self, func, *iterables, **kwargs):
        """
        imap_unordered(func, *iterables, maxsize=None) -> iterable

        The same as :meth:`imap` except that the ordering of the results
        from the returned iterator should be considered in arbitrary
        order.

        This is lighter weight than :meth:`imap` and should be preferred if order
        doesn't matter.

        .. seealso:: :meth:`imap` for more details.
        """
        return self.__imap(IMapUnordered, func, *iterables, **kwargs)


class Group(GroupMappingMixin):
    """
    Maintain a group of greenlets that are still running, without
    limiting their number.

    Links to each item and removes it upon notification.

    Groups can be iterated to discover what greenlets they are tracking,
    they can be tested to see if they contain a greenlet, and they know the
    number (len) of greenlets they are tracking. If they are not tracking any
    greenlets, they are False in a boolean context.

    .. attribute:: greenlet_class

        Either :class:`gevent.Greenlet` (the default) or a subclass.
        These are the type of
        object we will :meth:`spawn`. This can be
        changed on an instance or in a subclass.
    """

    greenlet_class = Greenlet

    def __init__(self, *args):
        assert len(args) <= 1, args
        self.greenlets = set(*args)
        if args:
            for greenlet in args[0]:
                greenlet.rawlink(self._discard)
        # each item we kill we place in dying, to avoid killing the same greenlet twice
        self.dying = set()
        self._empty_event = Event()
        self._empty_event.set()

    def __repr__(self):
        return '<%s at 0x%x %s>' % (self.__class__.__name__, id(self), self.greenlets)

    def __len__(self):
        """
        Answer how many greenlets we are tracking. Note that if we are empty,
        we are False in a boolean context.
        """
        return len(self.greenlets)

    def __contains__(self, item):
        """
        Answer if we are tracking the given greenlet.
        """
        return item in self.greenlets

    def __iter__(self):
        """
        Iterate across all the greenlets we are tracking, in no particular order.
        """
        return iter(self.greenlets)

    def add(self, greenlet):
        """
        Begin tracking the *greenlet*.

        If this group is :meth:`full`, then this method may block
        until it is possible to track the greenlet.

        Typically the *greenlet* should **not** be started when
        it is added because if this object blocks in this method,
        then the *greenlet* may run to completion before it is tracked.
        """
        try:
            rawlink = greenlet.rawlink
        except AttributeError:
            pass  # non-Greenlet greenlet, like MAIN
        else:
            rawlink(self._discard)
        self.greenlets.add(greenlet)
        self._empty_event.clear()

    def _discard(self, greenlet):
        self.greenlets.discard(greenlet)
        self.dying.discard(greenlet)
        if not self.greenlets:
            self._empty_event.set()

    def discard(self, greenlet):
        """
        Stop tracking the greenlet.
        """
        self._discard(greenlet)
        try:
            unlink = greenlet.unlink
        except AttributeError:
            pass  # non-Greenlet greenlet, like MAIN
        else:
            unlink(self._discard)

    def start(self, greenlet):
        """
        Add the **unstarted** *greenlet* to the collection of greenlets
        this group is monitoring, and then start it.
        """
        self.add(greenlet)
        greenlet.start()

    def spawn(self, *args, **kwargs): # pylint:disable=arguments-differ
        """
        Begin a new greenlet with the given arguments (which are passed
        to the greenlet constructor) and add it to the collection of greenlets
        this group is monitoring.

        :return: The newly started greenlet.
        """
        greenlet = self.greenlet_class(*args, **kwargs)
        self.start(greenlet)
        return greenlet

#     def close(self):
#         """Prevents any more tasks from being submitted to the pool"""
#         self.add = RaiseException("This %s has been closed" % self.__class__.__name__)

    def join(self, timeout=None, raise_error=False):
        """
        Wait for this group to become empty *at least once*.

        If there are no greenlets in the group, returns immediately.

        .. note:: By the time the waiting code (the caller of this
           method) regains control, a greenlet may have been added to
           this group, and so this object may no longer be empty. (That
           is, ``group.join(); assert len(group) == 0`` is not
           guaranteed to hold.) This method only guarantees that the group
           reached a ``len`` of 0 at some point.

        :keyword bool raise_error: If True (*not* the default), if any
            greenlet that finished while the join was in progress raised
            an exception, that exception will be raised to the caller of
            this method. If multiple greenlets raised exceptions, which
            one gets re-raised is not determined. Only greenlets currently
            in the group when this method is called are guaranteed to
            be checked for exceptions.

        :return bool: A value indicating whether this group became empty.
           If the timeout is specified and the group did not become empty
           during that timeout, then this will be a false value. Otherwise
           it will be a true value.

        .. versionchanged:: 1.2a1
           Add the return value.
        """
        greenlets = list(self.greenlets) if raise_error else ()
        result = self._empty_event.wait(timeout=timeout)

        for greenlet in greenlets:
            if greenlet.exception is not None:
                if hasattr(greenlet, '_raise_exception'):
                    greenlet._raise_exception()
                raise greenlet.exception

        return result

    def kill(self, exception=GreenletExit, block=True, timeout=None):
        """
        Kill all greenlets being tracked by this group.
        """
        timer = Timeout._start_new_or_dummy(timeout)
        try:
            while self.greenlets:
                for greenlet in list(self.greenlets):
                    if greenlet in self.dying:
                        continue
                    try:
                        kill = greenlet.kill
                    except AttributeError:
                        _kill(greenlet, exception)
                    else:
                        kill(exception, block=False)
                    self.dying.add(greenlet)
                if not block:
                    break
                joinall(self.greenlets)
        except Timeout as ex:
            if ex is not timer:
                raise
        finally:
            timer.cancel()

    def killone(self, greenlet, exception=GreenletExit, block=True, timeout=None):
        """
        If the given *greenlet* is running and being tracked by this group,
        kill it.
        """
        if greenlet not in self.dying and greenlet in self.greenlets:
            greenlet.kill(exception, block=False)
            self.dying.add(greenlet)
            if block:
                greenlet.join(timeout)

    def full(self):
        """
        Return a value indicating whether this group can track more greenlets.

        In this implementation, because there are no limits on the number of
        tracked greenlets, this will always return a ``False`` value.
        """
        return False

    def wait_available(self, timeout=None):
        """
        Block until it is possible to :meth:`spawn` a new greenlet.

        In this implementation, because there are no limits on the number
        of tracked greenlets, this will always return immediately.
        """

    # MappingMixin methods

    def _apply_immediately(self):
        # If apply() is called from one of our own
        # worker greenlets, don't spawn a new one---if we're full, that
        # could deadlock.
        return getcurrent() in self

    def _apply_async_cb_spawn(self, callback, result):
        Greenlet.spawn(callback, result)

    def _apply_async_use_greenlet(self):
        # cannot call self.spawn() because it will block, so
        # use a fresh, untracked greenlet that when run will
        # (indirectly) call self.spawn() for us.
        return self.full()



class PoolFull(QueueFull):
    """
    Raised when a Pool is full and an attempt was made to
    add a new greenlet to it in non-blocking mode.
    """


class Pool(Group):

    def __init__(self, size=None, greenlet_class=None):
        """
        Create a new pool.

        A pool is like a group, but the maximum number of members
        is governed by the *size* parameter.

        :keyword int size: If given, this non-negative integer is the
            maximum count of active greenlets that will be allowed in
            this pool. A few values have special significance:

            * `None` (the default) places no limit on the number of
              greenlets. This is useful when you want to track, but not limit,
              greenlets. In general, a :class:`Group`
              may be a more efficient way to achieve the same effect, but some things
              need the additional abilities of this class (one example being the *spawn*
              parameter of :class:`gevent.baseserver.BaseServer` and
              its subclass :class:`gevent.pywsgi.WSGIServer`).

            * ``0`` creates a pool that can never have any active greenlets. Attempting
              to spawn in this pool will block forever. This is only useful
              if an application uses :meth:`wait_available` with a timeout and checks
              :meth:`free_count` before attempting to spawn.
        """
        if size is not None and size < 0:
            raise ValueError('size must not be negative: %r' % (size, ))
        Group.__init__(self)
        self.size = size
        if greenlet_class is not None:
            self.greenlet_class = greenlet_class
        if size is None:
            factory = DummySemaphore
        else:
            factory = Semaphore
        self._semaphore = factory(size)

    def wait_available(self, timeout=None):
        """
        Wait until it's possible to spawn a greenlet in this pool.

        :param float timeout: If given, only wait the specified number
            of seconds.

        .. warning:: If the pool was initialized with a size of 0, this
           method will block forever unless a timeout is given.

        :return: A number indicating how many new greenlets can be put into
           the pool without blocking.

        .. versionchanged:: 1.1a3
            Added the ``timeout`` parameter.
        """
        return self._semaphore.wait(timeout=timeout)

    def full(self):
        """
        Return a boolean indicating whether this pool is full, e.g. if
        :meth:`add` would block.

        :return: False if there is room for new members, True if there isn't.
        """
        return self.free_count() <= 0

    def free_count(self):
        """
        Return a number indicating *approximately* how many more members
        can be added to this pool.
        """
        if self.size is None:
            return 1
        return max(0, self.size - len(self))

    def start(self, greenlet, *args, **kwargs): # pylint:disable=arguments-differ
        """
        start(greenlet, blocking=True, timeout=None) -> None

        Add the **unstarted** *greenlet* to the collection of greenlets
        this group is monitoring and then start it.

        Parameters are as for :meth:`add`.
        """
        self.add(greenlet, *args, **kwargs)
        greenlet.start()

    def add(self, greenlet, blocking=True, timeout=None): # pylint:disable=arguments-differ
        """
        Begin tracking the given **unstarted** greenlet, possibly blocking
        until space is available.

        Usually you should call :meth:`start` to track and start the greenlet
        instead of using this lower-level method, or :meth:`spawn` to
        also create the greenlet.

        :keyword bool blocking: If True (the default), this function
            will block until the pool has space or a timeout occurs.  If
            False, this function will immediately raise a Timeout if the
            pool is currently full.
        :keyword float timeout: The maximum number of seconds this
            method will block, if ``blocking`` is True.  (Ignored if
            ``blocking`` is False.)
        :raises PoolFull: if either ``blocking`` is False and the pool
            was full, or if ``blocking`` is True and ``timeout`` was
            exceeded.

        ..  caution:: If the *greenlet* has already been started and
            *blocking* is true, then the greenlet may run to completion
            while the current greenlet blocks waiting to track it. This would
            enable higher concurrency than desired.

        ..  seealso:: :meth:`Group.add`

        ..  versionchanged:: 1.3.0 Added the ``blocking`` and
            ``timeout`` parameters.
        """
        if not self._semaphore.acquire(blocking=blocking, timeout=timeout):
            # We failed to acquire the semaphore.
            # If blocking was True, then there was a timeout. If blocking was
            # False, then there was no capacity. Either way, raise PoolFull.
            raise PoolFull()

        try:
            Group.add(self, greenlet)
        except:
            self._semaphore.release()
            raise

    def _discard(self, greenlet):
        Group._discard(self, greenlet)
        self._semaphore.release()


class pass_value(object):
    __slots__ = ['callback']

    def __init__(self, callback):
        self.callback = callback

    def __call__(self, source):
        if source.successful():
            self.callback(source.value)

    def __hash__(self):
        return hash(self.callback)

    def __eq__(self, other):
        return self.callback == getattr(other, 'callback', other)

    def __str__(self):
        return str(self.callback)

    def __repr__(self):
        return repr(self.callback)

    def __getattr__(self, item):
        assert item != 'callback'
        return getattr(self.callback, item)
