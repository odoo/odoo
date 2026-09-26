"""Class-based event handlers


A light-weight event-handler framework based on event classes.

Handlers are registered for event classes:

    >>> import zope.event.classhandler

    >>> class MyEvent(object):
    ...     pass

    >>> def handler1(event):
    ...     print("handler1 %r" % event.__class__.__name__)

    >>> zope.event.classhandler.handler(MyEvent, handler1)

Descriptor syntax:

    >>> @zope.event.classhandler.handler(MyEvent)
    ... def handler2(event):
    ...     print("handler2 %r" % event.__class__.__name__)

    >>> class MySubEvent(MyEvent):
    ...     pass

    >>> @zope.event.classhandler.handler(MySubEvent)
    ... def handler3(event):
    ...     print("handler3 %r" % event.__class__.__name__)


Subscribers are called in class method-resolution order, so only
new-style event classes are supported, and then by order of registry.

    >>> import zope.event
    >>> zope.event.notify(MySubEvent())
    handler3 'MySubEvent'
    handler1 'MySubEvent'
    handler2 'MySubEvent'

"""
import zope.event


__all__ = [
    'handler',
]

registry = {}


def handler(event_class, handler_=None, _decorator=False):
    """ Define an event handler for a (new-style) class.

    This can be called with a class and a handler, or with just a
    class and the result used as a handler decorator.
    """
    if handler_ is None:
        return lambda func: handler(event_class, func, True)

    if not registry:
        zope.event.subscribers.append(dispatch)

    if event_class not in registry:
        registry[event_class] = [handler_]
    else:
        registry[event_class].append(handler_)

    if _decorator:
        return handler


def dispatch(event):
    for event_class in event.__class__.__mro__:
        for handler in registry.get(event_class, ()):
            handler(event)
