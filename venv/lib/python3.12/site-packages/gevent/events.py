# -*- coding: utf-8 -*-
# Copyright 2018 gevent. See LICENSE for details.
"""
Publish/subscribe event infrastructure.

When certain "interesting" things happen during the lifetime of the
process, gevent will "publish" an event (an object). That event is
delivered to interested "subscribers" (functions that take one
parameter, the event object).

Higher level frameworks may take this foundation and build richer
models on it.

:mod:`zope.event` will be used to provide the functionality of
`notify` and `subscribers`. See :mod:`zope.event.classhandler` for a
simple class-based approach to subscribing to a filtered list of
events, and see `zope.component
<https://zopecomponent.readthedocs.io/en/latest/event.html>`_ for a
much higher-level, flexible system. If you are using one of these
systems, you generally will not want to directly modify `subscribers`.

.. versionadded:: 1.3b1

.. versionchanged:: 23.7.0
   Now uses :mod:`importlib.metadata` instead of :mod:`pkg_resources`
   to locate entry points.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


__all__ = [
    'subscribers',

    # monitor thread
    'IEventLoopBlocked',
    'EventLoopBlocked',
    'IMemoryUsageThresholdExceeded',
    'MemoryUsageThresholdExceeded',
    'IMemoryUsageUnderThreshold',
    'MemoryUsageUnderThreshold',

    # Hub
    'IPeriodicMonitorThread',
    'IPeriodicMonitorThreadStartedEvent',
    'PeriodicMonitorThreadStartedEvent',

    # monkey
    'IGeventPatchEvent',
    'GeventPatchEvent',
    'IGeventWillPatchEvent',
    'DoNotPatch',
    'GeventWillPatchEvent',
    'IGeventDidPatchEvent',
    'IGeventWillPatchModuleEvent',
    'GeventWillPatchModuleEvent',
    'IGeventDidPatchModuleEvent',
    'GeventDidPatchModuleEvent',
    'IGeventWillPatchAllEvent',
    'GeventWillPatchAllEvent',
    'IGeventDidPatchBuiltinModulesEvent',
    'GeventDidPatchBuiltinModulesEvent',
    'IGeventDidPatchAllEvent',
    'GeventDidPatchAllEvent',
]

# pylint:disable=no-self-argument,inherit-non-class
import platform

from zope.interface import Interface
from zope.interface import Attribute
from zope.interface import implementer

from zope.event import subscribers
from zope.event import notify



#: Applications may register for notification of events by appending a
#: callable to the ``subscribers`` list.
#:
#: Each subscriber takes a single argument, which is the event object
#: being published.
#:
#: Exceptions raised by subscribers will be propagated *without* running
#: any remaining subscribers.
#:
#: This is an alias for `zope.event.subscribers`; prefer to use
#: that attribute directly.
subscribers = subscribers

try:
    # Cache the platform info. pkg_resources uses
    # platform.machine() for environment markers, and
    # platform.machine() wants to call os.popen('uname'), which is
    # broken on Py2 when the gevent child signal handler is
    # installed. (see test__monkey_sigchild_2.py)
    platform.uname()
except: # pylint:disable=bare-except
    pass
finally:
    del platform

def notify_and_call_entry_points(event):
    notify(event)
    from importlib import metadata
    import sys
    # This used to use the  old ``pkg_resources.iter_entry_points(group,name=None)``
    # API, passing it just the first argument, ``group=event.ENTRY_POINT_NAME``.
    # In other words, we don't care about the ``name``.
    if sys.version_info[:2] >= (3, 10):
        # pylint:disable-next=unexpected-keyword-arg
        # The only thing you can do with this is iterate it to get
        # EntryPoint objects. (e.g., accessing by index raises a warning)
        entry_points = metadata.entry_points(group=event.ENTRY_POINT_NAME)
    else:
        # Prior to 3.10, we have to do this all manually (keyword selection
        # was introduced in 3.10; in 3.9 and before, entry_points returns a plain
        # ``dict``). Using it like this is deprecated in 3.10, so to avoid warnings
        # we have to write it twice.
        #
        # Prior to 3.9, there is no ``.module`` attribute, so if we
        # needed that we'd have to look at the complete ``.value``
        # attribute.
        ep_dict = metadata.entry_points()
        __traceback_info__ = ep_dict
        # On Python 3.8, we can get duplicate EntryPoint objects; it is unclear
        # why. Drop them into a set to make sure we only get one.
        entry_points = set(
            ep
            for ep
            in ep_dict.get(event.ENTRY_POINT_NAME, ())
        )

    for plugin in entry_points:
        subscriber = plugin.load()
        subscriber(event)


class IPeriodicMonitorThread(Interface):
    """
    The contract for the periodic monitoring thread that is started
    by the hub.
    """

    def add_monitoring_function(function, period):
        """
        Schedule the *function* to be called approximately every *period* fractional seconds.

        The *function* receives one argument, the hub being monitored. It is called
        in the monitoring thread, *not* the hub thread. It **must not** attempt to
        use the gevent asynchronous API.

        If the *function* is already a monitoring function, then its *period*
        will be updated for future runs.

        If the *period* is ``None``, then the function will be removed.

        A *period* less than or equal to zero is not allowed.
        """

class IPeriodicMonitorThreadStartedEvent(Interface):
    """
    The event emitted when a hub starts a periodic monitoring thread.

    You can use this event to add additional monitoring functions.
    """

    monitor = Attribute("The instance of `IPeriodicMonitorThread` that was started.")

class PeriodicMonitorThreadStartedEvent(object):
    """
    The implementation of :class:`IPeriodicMonitorThreadStartedEvent`.
    """

    #: The name of the setuptools entry point that is called when this
    #: event is emitted.
    ENTRY_POINT_NAME = 'gevent.plugins.hub.periodic_monitor_thread_started'

    def __init__(self, monitor):
        self.monitor = monitor

class IEventLoopBlocked(Interface):
    """
    The event emitted when the event loop is blocked.

    This event is emitted in the monitor thread.
    """

    greenlet = Attribute("The greenlet that appeared to be blocking the loop.")
    blocking_time = Attribute("The approximate time in seconds the loop has been blocked.")
    info = Attribute("A sequence of string lines providing extra info.")

@implementer(IEventLoopBlocked)
class EventLoopBlocked(object):
    """
    The event emitted when the event loop is blocked.

    Implements `IEventLoopBlocked`.
    """

    def __init__(self, greenlet, blocking_time, info):
        self.greenlet = greenlet
        self.blocking_time = blocking_time
        self.info = info

class IMemoryUsageThresholdExceeded(Interface):
    """
    The event emitted when the memory usage threshold is exceeded.

    This event is emitted only while memory continues to grow
    above the threshold. Only if the condition or stabilized is corrected (memory
    usage drops) will the event be emitted in the future.

    This event is emitted in the monitor thread.
    """

    mem_usage = Attribute("The current process memory usage, in bytes.")
    max_allowed = Attribute("The maximum allowed memory usage, in bytes.")
    memory_info = Attribute("The tuple of memory usage stats return by psutil.")

class _AbstractMemoryEvent(object):

    def __init__(self, mem_usage, max_allowed, memory_info):
        self.mem_usage = mem_usage
        self.max_allowed = max_allowed
        self.memory_info = memory_info

    def __repr__(self):
        return "<%s used=%d max=%d details=%r>" % (
            self.__class__.__name__,
            self.mem_usage,
            self.max_allowed,
            self.memory_info,
        )

@implementer(IMemoryUsageThresholdExceeded)
class MemoryUsageThresholdExceeded(_AbstractMemoryEvent):
    """
    Implementation of `IMemoryUsageThresholdExceeded`.
    """


class IMemoryUsageUnderThreshold(Interface):
    """
    The event emitted when the memory usage drops below the
    threshold after having previously been above it.

    This event is emitted only the first time memory usage is detected
    to be below the threshold after having previously been above it.
    If memory usage climbs again, a `IMemoryUsageThresholdExceeded`
    event will be broadcast, and then this event could be broadcast again.

    This event is emitted in the monitor thread.
    """

    mem_usage = Attribute("The current process memory usage, in bytes.")
    max_allowed = Attribute("The maximum allowed memory usage, in bytes.")
    max_memory_usage = Attribute("The memory usage that caused the previous "
                                 "IMemoryUsageThresholdExceeded event.")
    memory_info = Attribute("The tuple of memory usage stats return by psutil.")


@implementer(IMemoryUsageUnderThreshold)
class MemoryUsageUnderThreshold(_AbstractMemoryEvent):
    """
    Implementation of `IMemoryUsageUnderThreshold`.
    """

    def __init__(self, mem_usage, max_allowed, memory_info, max_usage):
        super(MemoryUsageUnderThreshold, self).__init__(mem_usage, max_allowed, memory_info)
        self.max_memory_usage = max_usage


class IGeventPatchEvent(Interface):
    """
    The root for all monkey-patch events gevent emits.
    """

    source = Attribute("The source object containing the patches.")
    target = Attribute("The destination object to be patched.")

@implementer(IGeventPatchEvent)
class GeventPatchEvent(object):
    """
    Implementation of `IGeventPatchEvent`.
    """

    def __init__(self, source, target):
        self.source = source
        self.target = target

    def __repr__(self):
        return '<%s source=%r target=%r at %x>' % (self.__class__.__name__,
                                                   self.source,
                                                   self.target,
                                                   id(self))

class IGeventWillPatchEvent(IGeventPatchEvent):
    """
    An event emitted *before* gevent monkey-patches something.

    If a subscriber raises `DoNotPatch`, then patching this particular
    item will not take place.
    """


class DoNotPatch(BaseException):
    """
    Subscribers to will-patch events can raise instances
    of this class to tell gevent not to patch that particular item.
    """


@implementer(IGeventWillPatchEvent)
class GeventWillPatchEvent(GeventPatchEvent):
    """
    Implementation of `IGeventWillPatchEvent`.
    """

class IGeventDidPatchEvent(IGeventPatchEvent):
    """
    An event emitted *after* gevent has patched something.
    """

@implementer(IGeventDidPatchEvent)
class GeventDidPatchEvent(GeventPatchEvent):
    """
    Implementation of `IGeventDidPatchEvent`.
    """

class IGeventWillPatchModuleEvent(IGeventWillPatchEvent):
    """
    An event emitted *before* gevent begins patching a specific module.

    Both *source* and *target* attributes are module objects.
    """

    module_name = Attribute("The name of the module being patched. "
                            "This is the same as ``target.__name__``.")

    target_item_names = Attribute("The list of item names to patch. "
                                  "This can be modified in place with caution.")

@implementer(IGeventWillPatchModuleEvent)
class GeventWillPatchModuleEvent(GeventWillPatchEvent):
    """
    Implementation of `IGeventWillPatchModuleEvent`.
    """

    #: The name of the setuptools entry point that is called when this
    #: event is emitted.
    ENTRY_POINT_NAME = 'gevent.plugins.monkey.will_patch_module'

    def __init__(self, module_name, source, target, items):
        super(GeventWillPatchModuleEvent, self).__init__(source, target)
        self.module_name = module_name
        self.target_item_names = items


class IGeventDidPatchModuleEvent(IGeventDidPatchEvent):
    """
    An event emitted *after* gevent has completed patching a specific
    module.
    """

    module_name = Attribute("The name of the module being patched. "
                            "This is the same as ``target.__name__``.")


@implementer(IGeventDidPatchModuleEvent)
class GeventDidPatchModuleEvent(GeventDidPatchEvent):
    """
    Implementation of `IGeventDidPatchModuleEvent`.
    """

    #: The name of the setuptools entry point that is called when this
    #: event is emitted.
    ENTRY_POINT_NAME = 'gevent.plugins.monkey.did_patch_module'

    def __init__(self, module_name, source, target):
        super(GeventDidPatchModuleEvent, self).__init__(source, target)
        self.module_name = module_name

# TODO: Maybe it would be useful for the the module patch events
# to have an attribute telling if they're being done during patch_all?

class IGeventWillPatchAllEvent(IGeventWillPatchEvent):
    """
    An event emitted *before* gevent begins patching the system.

    Following this event will be a series of
    `IGeventWillPatchModuleEvent` and `IGeventDidPatchModuleEvent` for
    each patched module.

    Once the gevent builtin modules have been processed,
    `IGeventDidPatchBuiltinModulesEvent` will be emitted. Processing
    this event is an ideal time for third-party modules to be imported
    and patched (which may trigger its own will/did patch module
    events).

    Finally, a `IGeventDidPatchAllEvent` will be sent.

    If a subscriber to this event raises `DoNotPatch`, no patching
    will be done.

    The *source* and *target* attributes have undefined values.
    """

    patch_all_arguments = Attribute(
        "A dictionary of all the arguments to `gevent.monkey.patch_all`. "
        "This dictionary should not be modified. "
    )

    patch_all_kwargs = Attribute(
        "A dictionary of the extra arguments to `gevent.monkey.patch_all`. "
        "This dictionary should not be modified. "
    )

    def will_patch_module(module_name):
        """
        Return whether the module named *module_name* will be patched.
        """

class _PatchAllMixin(object):
    def __init__(self, patch_all_arguments, patch_all_kwargs):
        super(_PatchAllMixin, self).__init__(None, None)
        self._patch_all_arguments = patch_all_arguments
        self._patch_all_kwargs = patch_all_kwargs

    @property
    def patch_all_arguments(self):
        return self._patch_all_arguments.copy()

    @property
    def patch_all_kwargs(self):
        return self._patch_all_kwargs.copy()

    def __repr__(self):
        return '<%s %r at %x>' % (self.__class__.__name__,
                                  self._patch_all_arguments,
                                  id(self))

@implementer(IGeventWillPatchAllEvent)
class GeventWillPatchAllEvent(_PatchAllMixin, GeventWillPatchEvent):
    """
    Implementation of `IGeventWillPatchAllEvent`.
    """

    #: The name of the setuptools entry point that is called when this
    #: event is emitted.
    ENTRY_POINT_NAME = 'gevent.plugins.monkey.will_patch_all'

    def will_patch_module(self, module_name):
        return self.patch_all_arguments.get(module_name)

class IGeventDidPatchBuiltinModulesEvent(IGeventDidPatchEvent):
    """
    Event emitted *after* the builtin modules have been patched.

    If you're going to monkey-patch a third-party library, this is
    usually the event to listen for.

    The values of the *source* and *target* attributes are undefined.
    """

    patch_all_arguments = Attribute(
        "A dictionary of all the arguments to `gevent.monkey.patch_all`. "
        "This dictionary should not be modified. "
    )

    patch_all_kwargs = Attribute(
        "A dictionary of the extra arguments to `gevent.monkey.patch_all`. "
        "This dictionary should not be modified. "
    )

@implementer(IGeventDidPatchBuiltinModulesEvent)
class GeventDidPatchBuiltinModulesEvent(_PatchAllMixin, GeventDidPatchEvent):
    """
    Implementation of `IGeventDidPatchBuiltinModulesEvent`.
    """

    #: The name of the setuptools entry point that is called when this
    #: event is emitted.
    ENTRY_POINT_NAME = 'gevent.plugins.monkey.did_patch_builtins'

class IGeventDidPatchAllEvent(IGeventDidPatchEvent):
    """
    Event emitted after gevent has patched all modules, both builtin
    and those provided by plugins/subscribers.

    The values of the *source* and *target* attributes are undefined.
    """

@implementer(IGeventDidPatchAllEvent)
class GeventDidPatchAllEvent(_PatchAllMixin, GeventDidPatchEvent):
    """
    Implementation of `IGeventDidPatchAllEvent`.
    """

    #: The name of the setuptools entry point that is called when this
    #: event is emitted.
    ENTRY_POINT_NAME = 'gevent.plugins.monkey.did_patch_all'
