from __future__ import absolute_import
from __future__ import print_function

from zope.interface import implementer

from gevent._interfaces import ICallback

__all__ = [
    'callback',
]


@implementer(ICallback)
class callback(object):

    __slots__ = ('callback', 'args')

    def __init__(self, cb, args):
        self.callback = cb
        self.args = args

    def stop(self):
        self.callback = None
        self.args = None

    close = stop

    # Note that __nonzero__ and pending are different
    # bool() is used in contexts where we need to know whether to schedule another callback,
    # so it's true if it's pending or currently running
    # 'pending' has the same meaning as libev watchers: it is cleared before actually
    # running the callback

    def __nonzero__(self):
        # it's nonzero if it's pending or currently executing
        # NOTE: This depends on loop._run_callbacks setting the args property
        # to None.
        return self.args is not None
    __bool__ = __nonzero__

    @property
    def pending(self):
        return self.callback is not None

    def _format(self):
        return ''

    def __repr__(self):
        result = "<%s at 0x%x" % (self.__class__.__name__, id(self))
        if self.pending:
            result += " pending"
        if self.callback is not None:
            result += " callback=%r" % (self.callback, )
        if self.args is not None:
            result += " args=%r" % (self.args, )
        if self.callback is None and self.args is None:
            result += " stopped"
        return result + ">"
