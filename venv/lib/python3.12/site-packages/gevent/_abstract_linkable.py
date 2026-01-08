# -*- coding: utf-8 -*-
# cython: auto_pickle=False,embedsignature=True,always_allow_keywords=False
"""
Internal module, support for the linkable protocol for "event" like objects.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import sys
from gc import get_objects

from greenlet import greenlet
from greenlet import error as greenlet_error

from gevent._compat import thread_mod_name
from gevent._hub_local import get_hub_noargs as get_hub
from gevent._hub_local import get_hub_if_exists

from gevent.exceptions import InvalidSwitchError
from gevent.exceptions import InvalidThreadUseError
from gevent.timeout import Timeout

locals()['getcurrent'] = __import__('greenlet').getcurrent
locals()['greenlet_init'] = lambda: None

__all__ = [
    'AbstractLinkable',
]

# Need the real get_ident. We're imported early enough during monkey-patching
# that we can be sure nothing is monkey patched yet.
_get_thread_ident = __import__(thread_mod_name).get_ident
_allocate_thread_lock = __import__(thread_mod_name).allocate_lock

class _FakeNotifier(object):
    __slots__ = (
        'pending',
    )

    def __init__(self):
        self.pending = False

def get_roots_and_hubs():
    from gevent.hub import Hub # delay import
    return {
        x.parent: x
        for x in get_objects()
        # Make sure to only find hubs that have a loop
        # and aren't destroyed. If we don't do that, we can
        # get an old hub that no longer works leading to issues in
        # combined test cases.
        if isinstance(x, Hub) and x.loop is not None
    }


class AbstractLinkable(object):
    # Encapsulates the standard parts of the linking and notifying
    # protocol common to both repeatable events (Event, Semaphore) and
    # one-time events (AsyncResult).
    #
    # With a few careful exceptions, instances of this object can only
    # be used from a single thread. The exception is that certain methods
    # may be used from multiple threads IFF:
    #
    # 1.  They are documented as safe for that purpose; AND
    # 2a. This object is compiled with Cython and thus is holding the GIL
    #     for the entire duration of the method; OR
    # 2b. A subclass ensures that a Python-level native thread lock is held
    #     for the duration of the method; this is necessary in pure-Python mode.
    #     The only known implementation of such
    #     a subclass is for Semaphore. AND
    # 3. The subclass that calls ``capture_hub`` catches
    #    and handles ``InvalidThreadUseError``
    #
    # TODO: As of gevent 1.5, we use the same datastructures and almost
    # the same algorithm as Greenlet. See about unifying them more.

    __slots__ = (
        'hub',
        '_links',
        '_notifier',
        '_notify_all',
        '__weakref__'
    )

    def __init__(self, hub=None):
        # Before this implementation, AsyncResult and Semaphore
        # maintained the order of notifications, but Event did not.

        # In gevent 1.3, before Semaphore extended this class, that
        # was changed to not maintain the order. It was done because
        # Event guaranteed to only call callbacks once (a set) but
        # AsyncResult had no such guarantees. When Semaphore was
        # changed to extend this class, it lost its ordering
        # guarantees. Unfortunately, that made it unfair. There are
        # rare cases that this can starve a greenlet
        # (https://github.com/gevent/gevent/issues/1487) and maybe
        # even lead to deadlock (not tested).

        # So in gevent 1.5 we go back to maintaining order. But it's
        # still important not to make duplicate calls, and it's also
        # important to avoid O(n^2) behaviour that can result from
        # naive use of a simple list due to the need to handle removed
        # links in the _notify_links loop. Cython has special support for
        # built-in sets, lists, and dicts, but not ordereddict. Rather than
        # use two data structures, or a dict({link: order}), we simply use a
        # list and remove objects as we go, keeping track of them so as not to
        # have duplicates called. This makes `unlink` O(n), but we can avoid
        # calling it in the common case in _wait_core (even so, the number of
        # waiters should usually be pretty small)
        self._links = []
        self._notifier = None
        # This is conceptually a class attribute, defined here for ease of access in
        # cython. If it's true, when notifiers fire, all existing callbacks are called.
        # If its false, we only call callbacks as long as ready() returns true.
        self._notify_all = True
        # we don't want to do get_hub() here to allow defining module-level objects
        # without initializing the hub. However, for multiple-thread safety, as soon
        # as a waiting method is entered, even if it won't have to wait, we
        # need to grab the hub and assign ownership. But we don't want to grab one prematurely.
        # The example is three threads, the main thread and two worker threads; if we create
        # a Semaphore in the main thread but only use it in the two threads, if we had grabbed
        # the main thread's hub, the two worker threads would have a dependency on it, meaning that
        # if the main event loop is blocked, the worker threads might get blocked too.
        self.hub = hub

    def linkcount(self):
        # For testing: how many objects are linked to this one?
        return len(self._links)

    def ready(self):
        # Instances must define this
        raise NotImplementedError

    def rawlink(self, callback):
        """
        Register a callback to call when this object is ready.

        *callback* will be called in the :class:`Hub
        <gevent.hub.Hub>`, so it must not use blocking gevent API.
        *callback* will be passed one argument: this instance.
        """
        if not callable(callback):
            raise TypeError('Expected callable: %r' % (callback, ))
        self._links.append(callback)
        self._check_and_notify()

    def unlink(self, callback):
        """Remove the callback set by :meth:`rawlink`"""
        try:
            self._links.remove(callback)
        except ValueError:
            pass

        if not self._links and self._notifier is not None and self._notifier.pending:
            # If we currently have one queued, but not running, de-queue it.
            # This will break a reference cycle.
            # (self._notifier -> self._notify_links -> self)
            # If it's actually running, though, (and we're here as a result of callbacks)
            # we don't want to change it; it needs to finish what its doing
            # so we don't attempt to start a fresh one or swap it out from underneath the
            # _notify_links method.
            self._notifier.stop()

    def _allocate_lock(self):
        return _allocate_thread_lock()

    def _getcurrent(self):
        return getcurrent() # pylint:disable=undefined-variable

    def _get_thread_ident(self):
        return _get_thread_ident()

    def _capture_hub(self, create):
        # Subclasses should call this as the first action from any
        # public method that could, in theory, block and switch
        # to the hub. This may release the GIL. It may
        # raise InvalidThreadUseError if the result would

        # First, detect a dead hub and drop it.
        while 1:
            my_hub = self.hub
            if my_hub is None:
                break
            if my_hub.dead: # dead is a property, could release GIL
                # back, holding GIL
                if self.hub is my_hub:
                    self.hub = None
                    my_hub = None
                    break
            else:
                break

        if self.hub is None:
            # This next line might release the GIL.
            current_hub = get_hub() if create else get_hub_if_exists()

            # We have the GIL again. Did anything change? If so,
            # we lost the race.
            if self.hub is None:
                self.hub = current_hub

        if self.hub is not None and self.hub.thread_ident != _get_thread_ident():
            raise InvalidThreadUseError(
                self.hub,
                get_hub_if_exists(),
                getcurrent() # pylint:disable=undefined-variable
            )
        return self.hub

    def _check_and_notify(self):
        # If this object is ready to be notified, begin the process.
        if self.ready() and self._links and not self._notifier:
            hub = None
            try:
                hub = self._capture_hub(False) # Must create, we need it.
            except InvalidThreadUseError:
                # The current hub doesn't match self.hub. That's OK,
                # we still want to start the notifier in the thread running
                # self.hub (because the links probably contains greenlet.switch
                # calls valid only in that hub)
                pass
            if hub is not None:
                self._notifier = hub.loop.run_callback(self._notify_links, [])
            else:
                # Hmm, no hub. We must be the only thing running. Then its OK
                # to just directly call the callbacks.
                self._notifier = 1
                try:
                    self._notify_links([])
                finally:
                    self._notifier = None

    def _notify_link_list(self, links):
        # The core of the _notify_links method to notify
        # links in order. Lets the ``links`` list be mutated,
        # and only notifies up to the last item in the list, in case
        # objects are added to it.
        if not links:
            # HMM. How did we get here? Running two threads at once?
            # Seen once on Py27/Win/Appveyor
            # https://ci.appveyor.com/project/jamadden/gevent/builds/36875645/job/9wahj9ft4h4qa170
            return []

        only_while_ready = not self._notify_all
        final_link = links[-1]
        done = set() # of ids
        hub = self.hub if self.hub is not None else get_hub_if_exists()
        unswitched = []
        while links: # remember this can be mutated
            if only_while_ready and not self.ready():
                break

            link = links.pop(0) # Cython optimizes using list internals
            id_link = id(link)
            if id_link not in done:
                # XXX: JAM: What was I thinking? This doesn't make much sense,
                # there's a good chance `link` will be deallocated, and its id() will
                # be free to be reused. This also makes looping difficult, you have to
                # create new functions inside a loop rather than just once outside the loop.
                done.add(id_link)
                try:
                    self._drop_lock_for_switch_out()
                    try:
                        link(self)
                    except greenlet_error:
                        # couldn't switch to a greenlet, we must be
                        # running in a different thread. back on the list it goes for next time.
                        unswitched.append(link)
                    finally:
                        self._acquire_lock_for_switch_in()

                except: # pylint:disable=bare-except
                    # We're running in the hub, errors must not escape.
                    if hub is not None:
                        hub.handle_error((link, self), *sys.exc_info())
                    else:
                        import traceback
                        traceback.print_exc()

            if link is final_link:
                break
        return unswitched

    def _notify_links(self, arrived_while_waiting):
        # This method must hold the GIL, or be guarded with the lock that guards
        # this object. Thus, while we are notifying objects, an object from another
        # thread simply cannot arrive and mutate ``_links`` or ``arrived_while_waiting``

        # ``arrived_while_waiting`` is a list of greenlet.switch methods
        # to call. These were objects that called wait() while we were processing,
        # and which would have run *before* those that had actually waited
        # and blocked. Instead of returning True immediately, we add them to this
        # list so they wait their turn.

        # We release self._notifier here when done invoking links.
        # The object itself becomes false in a boolean way as soon
        # as this method returns.
        notifier = self._notifier
        if notifier is None:
            # XXX: How did we get here?
            self._check_and_notify()
            return
        # Early links are allowed to remove later links, and links
        # are allowed to add more links, thus we must not
        # make a copy of our the ``_links`` list, we must traverse it and
        # mutate in place.
        #
        # We were ready() at the time this callback was scheduled; we
        # may not be anymore, and that status may change during
        # callback processing. Some of our subclasses (Event) will
        # want to notify everyone who was registered when the status
        # became true that it was once true, even though it may not be
        # any more. In that case, we must not keep notifying anyone that's
        # newly added after that, even if we go ready again.
        try:
            unswitched = self._notify_link_list(self._links)
            # Now, those that arrived after we had begun the notification
            # process. Follow the same rules, stop with those that are
            # added so far to prevent starvation.
            if arrived_while_waiting:
                un2 = self._notify_link_list(arrived_while_waiting)
                unswitched.extend(un2)

                # Anything left needs to go back on the main list.
                self._links.extend(arrived_while_waiting)
        finally:
            # We should not have created a new notifier even if callbacks
            # released us because we loop through *all* of our links on the
            # same callback while self._notifier is still true.
            assert self._notifier is notifier, (self._notifier, notifier)
            self._notifier = None
            # TODO: Maybe we should intelligently reset self.hub to
            # free up thread affinity? In case of a pathological situation where
            # one object was used from one thread once & first,  but usually is
            # used by another thread.
            #
            # BoundedSemaphore does this.
        # Now we may be ready or not ready. If we're ready, which
        # could have happened during the last link we called, then we
        # must have more links than we started with. We need to schedule the
        # wakeup.
        self._check_and_notify()
        if unswitched:
            self._handle_unswitched_notifications(unswitched)


    def _handle_unswitched_notifications(self, unswitched):
        # Given a list of callable objects that raised
        # ``greenlet.error`` when we called them: If we can determine
        # that it is a parked greenlet (the callablle is a
        # ``greenlet.switch`` method) and we can determine the hub
        # that the greenlet belongs to (either its parent, or, in the
        # case of a main greenlet, find a hub with the same parent as
        # this greenlet object) then:

        # Move this to be a callback in that thread.
        # (This relies on holding the GIL *or* ``Hub.loop.run_callback`` being
        # thread-safe! Note that the CFFI implementations are definitely
        # NOT thread-safe. TODO: Make them? Or an alternative?)
        #
        # Otherwise, print some error messages.

        # TODO: Inline this for individual links. That handles the
        # "only while ready" case automatically. Be careful about locking in that case.
        #
        # TODO: Add a 'strict' mode that prevents doing this dance, since it's
        # inherently not safe.
        root_greenlets = None
        printed_tb = False
        only_while_ready = not self._notify_all

        while unswitched:
            if only_while_ready and not self.ready():
                self.__print_unswitched_warning(unswitched, printed_tb)
                break

            link = unswitched.pop(0)

            hub = None # Also serves as a "handled?" flag
            # Is it a greenlet.switch method?
            if (getattr(link, '__name__', None) == 'switch'
                and isinstance(getattr(link, '__self__', None), greenlet)):
                glet = link.__self__
                parent = glet.parent

                while parent is not None:
                    if hasattr(parent, 'loop'): # Assuming the hub.
                        hub = glet.parent
                        break
                    parent = glet.parent

                if hub is None:
                    if root_greenlets is None:
                        root_greenlets = get_roots_and_hubs()
                    hub = root_greenlets.get(glet)

                if hub is not None and hub.loop is not None:
                    hub.loop.run_callback_threadsafe(link, self)
            if hub is None or hub.loop is None:
                # We couldn't handle it
                self.__print_unswitched_warning(link, printed_tb)
                printed_tb = True


    def __print_unswitched_warning(self, link, printed_tb):
        print('gevent: error: Unable to switch to greenlet', link,
              'from', self, '; crossing thread boundaries is not allowed.',
              file=sys.stderr)

        if not printed_tb:
            printed_tb = True
            print(
                'gevent: error: '
                'This is a result of using gevent objects from multiple threads,',
                'and is a bug in the calling code.', file=sys.stderr)

            import traceback
            traceback.print_stack()

    def _quiet_unlink_all(self, obj):
        if obj is None:
            return

        self.unlink(obj)
        if self._notifier is not None and self._notifier.args:
            try:
                self._notifier.args[0].remove(obj)
            except ValueError:
                pass

    def __wait_to_be_notified(self, rawlink): # pylint:disable=too-many-branches
        resume_this_greenlet = getcurrent().switch # pylint:disable=undefined-variable
        if rawlink:
            self.rawlink(resume_this_greenlet)
        else:
            self._notifier.args[0].append(resume_this_greenlet)

        try:
            self._switch_to_hub(self.hub)
            # If we got here, we were automatically unlinked already.
            resume_this_greenlet = None
        finally:
            self._quiet_unlink_all(resume_this_greenlet)

    def _switch_to_hub(self, the_hub):
        self._drop_lock_for_switch_out()
        try:
            result = the_hub.switch()
        finally:
            self._acquire_lock_for_switch_in()
        if result is not self: # pragma: no cover
            raise InvalidSwitchError(
                'Invalid switch into %s.wait(): %r' % (
                    self.__class__.__name__,
                    result,
                )
            )

    def _acquire_lock_for_switch_in(self):
        return

    def _drop_lock_for_switch_out(self):
        return

    def _wait_core(self, timeout, catch=Timeout):
        """
        The core of the wait implementation, handling switching and
        linking.

        This method is NOT safe to call from multiple threads.

        ``self.hub`` must be initialized before entering this method.
        The hub that is set is considered the owner and cannot be changed
        while this method is running. It must only be called from the thread
        where ``self.hub`` is the current hub.

        If *catch* is set to ``()``, a timeout that elapses will be
        allowed to be raised.

        :return: A true value if the wait succeeded without timing out.
          That is, a true return value means we were notified and control
          resumed in this greenlet.
        """
        with Timeout._start_new_or_dummy(timeout) as timer: # Might release
            # We already checked above (_wait()) if we're ready()
            try:
                self.__wait_to_be_notified(
                    True,# Use rawlink()
                )
                return True
            except catch as ex:
                if ex is not timer:
                    raise
                # test_set_and_clear and test_timeout in test_threading
                # rely on the exact return values, not just truthish-ness
                return False

    def _wait_return_value(self, waited, wait_success):
        # pylint:disable=unused-argument
        # Subclasses should override this to return a value from _wait.
        # By default we return None.
        return None # pragma: no cover all extent subclasses override

    def _wait(self, timeout=None):
        # Watch where we could potentially release the GIL.
        self._capture_hub(True) # Must create, we must have an owner. Might release

        if self.ready(): # *might* release, if overridden in Python.
            result = self._wait_return_value(False, False) # pylint:disable=assignment-from-none
            if self._notifier:
                # We're already notifying waiters; one of them must have run
                # and switched to this greenlet, which arrived here. Alternately,
                # we could be in a separate thread (but we're holding the GIL/object lock)
                self.__wait_to_be_notified(False) # Use self._notifier.args[0] instead of self.rawlink

            return result

        gotit = self._wait_core(timeout)
        return self._wait_return_value(True, gotit)

    def _at_fork_reinit(self):
        """
        This method was added in Python 3.9 and is called by logging.py
        ``_after_at_fork_child_reinit_locks`` on Lock objects.

        It is also called from threading.py, ``_after_fork`` in
        ``_reset_internal_locks``, and that can hit ``Event`` objects.

        Subclasses should reset themselves to an initial state. This
        includes unlocking/releasing, if possible. This method detaches from the
        previous hub and drops any existing notifier.
        """
        self.hub = None
        self._notifier = None

def _init():
    greenlet_init() # pylint:disable=undefined-variable

_init()


from gevent._util import import_c_accel
import_c_accel(globals(), 'gevent.__abstract_linkable')
