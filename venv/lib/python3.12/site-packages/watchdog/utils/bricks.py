"""Utility collections or "bricks".

:module: watchdog.utils.bricks
:author: yesudeep@google.com (Yesudeep Mangalapilly)
:author: lalinsky@gmail.com (Lukáš Lalinský)
:author: python@rcn.com (Raymond Hettinger)
:author: contact@tiger-222.fr (Mickaël Schoentgen)

Classes
=======
.. autoclass:: OrderedSetQueue
   :members:
   :show-inheritance:
   :inherited-members:

.. autoclass:: OrderedSet

"""

from __future__ import annotations

import queue
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any


class SkipRepeatsQueue(queue.Queue):
    """Thread-safe implementation of an special queue where a
    put of the last-item put'd will be dropped.

    The implementation leverages locking already implemented in the base class
    redefining only the primitives.

    Queued items must be immutable and hashable so that they can be used
    as dictionary keys. You must implement **only read-only properties** and
    the :meth:`Item.__hash__()`, :meth:`Item.__eq__()`, and
    :meth:`Item.__ne__()` methods for items to be hashable.

    An example implementation follows::

        class Item:
            def __init__(self, a, b):
                self._a = a
                self._b = b

            @property
            def a(self):
                return self._a

            @property
            def b(self):
                return self._b

            def _key(self):
                return (self._a, self._b)

            def __eq__(self, item):
                return self._key() == item._key()

            def __ne__(self, item):
                return self._key() != item._key()

            def __hash__(self):
                return hash(self._key())

    based on the OrderedSetQueue below
    """

    def _init(self, maxsize: int) -> None:
        super()._init(maxsize)
        self._last_item = None

    def put(self, item: Any, block: bool = True, timeout: float | None = None) -> None:  # noqa: FBT001,FBT002
        """This method will be used by `eventlet`, when enabled, so we cannot use force proper keyword-only
        arguments nor touch the signature. Also, the `timeout` argument will be ignored in that case.
        """
        if self._last_item is None or item != self._last_item:
            super().put(item, block, timeout)

    def _put(self, item: Any) -> None:
        super()._put(item)
        self._last_item = item

    def _get(self) -> Any:
        item = super()._get()
        if item is self._last_item:
            self._last_item = None
        return item
