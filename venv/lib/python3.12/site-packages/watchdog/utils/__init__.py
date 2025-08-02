""":module: watchdog.utils
:synopsis: Utility classes and functions.
:author: yesudeep@google.com (Yesudeep Mangalapilly)
:author: contact@tiger-222.fr (Mickaël Schoentgen)

Classes
-------
.. autoclass:: BaseThread
   :members:
   :show-inheritance:
   :inherited-members:

"""

from __future__ import annotations

import sys
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import ModuleType

    from watchdog.tricks import Trick


class UnsupportedLibcError(Exception):
    pass


class WatchdogShutdownError(Exception):
    """Semantic exception used to signal an external shutdown event."""


class BaseThread(threading.Thread):
    """Convenience class for creating stoppable threads."""

    def __init__(self) -> None:
        threading.Thread.__init__(self)
        if hasattr(self, "daemon"):
            self.daemon = True
        else:
            self.setDaemon(True)
        self._stopped_event = threading.Event()

    @property
    def stopped_event(self) -> threading.Event:
        return self._stopped_event

    def should_keep_running(self) -> bool:
        """Determines whether the thread should continue running."""
        return not self._stopped_event.is_set()

    def on_thread_stop(self) -> None:
        """Override this method instead of :meth:`stop()`.
        :meth:`stop()` calls this method.

        This method is called immediately after the thread is signaled to stop.
        """

    def stop(self) -> None:
        """Signals the thread to stop."""
        self._stopped_event.set()
        self.on_thread_stop()

    def on_thread_start(self) -> None:
        """Override this method instead of :meth:`start()`. :meth:`start()`
        calls this method.

        This method is called right before this thread is started and this
        object's run() method is invoked.
        """

    def start(self) -> None:
        self.on_thread_start()
        threading.Thread.start(self)


def load_module(module_name: str) -> ModuleType:
    """Imports a module given its name and returns a handle to it."""
    try:
        __import__(module_name)
    except ImportError as e:
        error = f"No module named {module_name}"
        raise ImportError(error) from e
    return sys.modules[module_name]


def load_class(dotted_path: str) -> type[Trick]:
    """Loads and returns a class definition provided a dotted path
    specification the last part of the dotted path is the class name
    and there is at least one module name preceding the class name.

    Notes
    -----
    You will need to ensure that the module you are trying to load
    exists in the Python path.

    Examples
    --------
    - module.name.ClassName    # Provided module.name is in the Python path.
    - module.ClassName         # Provided module is in the Python path.

    What won't work:
    - ClassName
    - modle.name.ClassName     # Typo in module name.
    - module.name.ClasNam      # Typo in classname.

    """
    dotted_path_split = dotted_path.split(".")
    if len(dotted_path_split) <= 1:
        error = f"Dotted module path {dotted_path} must contain a module name and a classname"
        raise ValueError(error)
    klass_name = dotted_path_split[-1]
    module_name = ".".join(dotted_path_split[:-1])

    module = load_module(module_name)
    if hasattr(module, klass_name):
        return getattr(module, klass_name)

    error = f"Module {module_name} does not have class attribute {klass_name}"
    raise AttributeError(error)
