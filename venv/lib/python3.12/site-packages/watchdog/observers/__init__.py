""":module: watchdog.observers
:synopsis: Observer that picks a native implementation if available.
:author: yesudeep@google.com (Yesudeep Mangalapilly)
:author: contact@tiger-222.fr (Mickaël Schoentgen)

Classes
=======
.. autoclass:: Observer
   :members:
   :show-inheritance:
   :inherited-members:

Observer thread that schedules watching directories and dispatches
calls to event handlers.

You can also import platform specific classes directly and use it instead
of :class:`Observer`.  Here is a list of implemented observer classes.:

============== ================================ ==============================
Class          Platforms                        Note
============== ================================ ==============================
|Inotify|      Linux 2.6.13+                    ``inotify(7)`` based observer
|FSEvents|     macOS                            FSEvents based observer
|Kqueue|       macOS and BSD with kqueue(2)     ``kqueue(2)`` based observer
|WinApi|       Microsoft Windows                Windows API-based observer
|Polling|      Any                              fallback implementation
============== ================================ ==============================

.. |Inotify|     replace:: :class:`.inotify.InotifyObserver`
.. |FSEvents|    replace:: :class:`.fsevents.FSEventsObserver`
.. |Kqueue|      replace:: :class:`.kqueue.KqueueObserver`
.. |WinApi|      replace:: :class:`.read_directory_changes.WindowsApiObserver`
.. |Polling|     replace:: :class:`.polling.PollingObserver`

"""

from __future__ import annotations

import contextlib
import warnings
from typing import TYPE_CHECKING, Protocol

from watchdog.utils import UnsupportedLibcError, platform

if TYPE_CHECKING:
    from watchdog.observers.api import BaseObserver


class ObserverType(Protocol):
    def __call__(self, *, timeout: float = ...) -> BaseObserver: ...


def _get_observer_cls() -> ObserverType:
    if platform.is_linux():
        with contextlib.suppress(UnsupportedLibcError):
            from watchdog.observers.inotify import InotifyObserver

            return InotifyObserver
    elif platform.is_darwin():
        try:
            from watchdog.observers.fsevents import FSEventsObserver
        except Exception:
            try:
                from watchdog.observers.kqueue import KqueueObserver
            except Exception:
                warnings.warn("Failed to import fsevents and kqueue. Fall back to polling.", stacklevel=1)
            else:
                warnings.warn("Failed to import fsevents. Fall back to kqueue", stacklevel=1)
                return KqueueObserver
        else:
            return FSEventsObserver
    elif platform.is_windows():
        try:
            from watchdog.observers.read_directory_changes import WindowsApiObserver
        except Exception:
            warnings.warn("Failed to import `read_directory_changes`. Fall back to polling.", stacklevel=1)
        else:
            return WindowsApiObserver
    elif platform.is_bsd():
        from watchdog.observers.kqueue import KqueueObserver

        return KqueueObserver

    from watchdog.observers.polling import PollingObserver

    return PollingObserver


Observer = _get_observer_cls()

__all__ = ["Observer"]
