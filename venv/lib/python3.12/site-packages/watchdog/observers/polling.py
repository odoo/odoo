""":module: watchdog.observers.polling
:synopsis: Polling emitter implementation.
:author: yesudeep@google.com (Yesudeep Mangalapilly)
:author: contact@tiger-222.fr (Mickaël Schoentgen)

Classes
-------
.. autoclass:: PollingObserver
   :members:
   :show-inheritance:

.. autoclass:: PollingObserverVFS
   :members:
   :show-inheritance:
   :special-members:
"""

from __future__ import annotations

import os
import threading
from functools import partial
from typing import TYPE_CHECKING

from watchdog.events import (
    DirCreatedEvent,
    DirDeletedEvent,
    DirModifiedEvent,
    DirMovedEvent,
    FileCreatedEvent,
    FileDeletedEvent,
    FileModifiedEvent,
    FileMovedEvent,
)
from watchdog.observers.api import DEFAULT_EMITTER_TIMEOUT, DEFAULT_OBSERVER_TIMEOUT, BaseObserver, EventEmitter
from watchdog.utils.dirsnapshot import DirectorySnapshot, DirectorySnapshotDiff, EmptyDirectorySnapshot

if TYPE_CHECKING:
    from collections.abc import Iterator
    from typing import Callable

    from watchdog.events import FileSystemEvent
    from watchdog.observers.api import EventQueue, ObservedWatch


class PollingEmitter(EventEmitter):
    """Platform-independent emitter that polls a directory to detect file
    system changes.
    """

    def __init__(
        self,
        event_queue: EventQueue,
        watch: ObservedWatch,
        *,
        timeout: float = DEFAULT_EMITTER_TIMEOUT,
        event_filter: list[type[FileSystemEvent]] | None = None,
        stat: Callable[[str], os.stat_result] = os.stat,
        listdir: Callable[[str | None], Iterator[os.DirEntry]] = os.scandir,
    ) -> None:
        super().__init__(event_queue, watch, timeout=timeout, event_filter=event_filter)
        self._snapshot: DirectorySnapshot = EmptyDirectorySnapshot()
        self._lock = threading.Lock()
        self._take_snapshot: Callable[[], DirectorySnapshot] = lambda: DirectorySnapshot(
            self.watch.path,
            recursive=self.watch.is_recursive,
            stat=stat,
            listdir=listdir,
        )

    def on_thread_start(self) -> None:
        self._snapshot = self._take_snapshot()

    def queue_events(self, timeout: float) -> None:
        # We don't want to hit the disk continuously.
        # timeout behaves like an interval for polling emitters.
        if self.stopped_event.wait(timeout):
            return

        with self._lock:
            if not self.should_keep_running():
                return

            # Get event diff between fresh snapshot and previous snapshot.
            # Update snapshot.
            try:
                new_snapshot = self._take_snapshot()
            except OSError:
                self.queue_event(DirDeletedEvent(self.watch.path))
                self.stop()
                return

            events = DirectorySnapshotDiff(self._snapshot, new_snapshot)
            self._snapshot = new_snapshot

            # Files.
            for src_path in events.files_deleted:
                self.queue_event(FileDeletedEvent(src_path))
            for src_path in events.files_modified:
                self.queue_event(FileModifiedEvent(src_path))
            for src_path in events.files_created:
                self.queue_event(FileCreatedEvent(src_path))
            for src_path, dest_path in events.files_moved:
                self.queue_event(FileMovedEvent(src_path, dest_path))

            # Directories.
            for src_path in events.dirs_deleted:
                self.queue_event(DirDeletedEvent(src_path))
            for src_path in events.dirs_modified:
                self.queue_event(DirModifiedEvent(src_path))
            for src_path in events.dirs_created:
                self.queue_event(DirCreatedEvent(src_path))
            for src_path, dest_path in events.dirs_moved:
                self.queue_event(DirMovedEvent(src_path, dest_path))


class PollingObserver(BaseObserver):
    """Platform-independent observer that polls a directory to detect file
    system changes.
    """

    def __init__(self, *, timeout: float = DEFAULT_OBSERVER_TIMEOUT) -> None:
        super().__init__(PollingEmitter, timeout=timeout)


class PollingObserverVFS(BaseObserver):
    """File system independent observer that polls a directory to detect changes."""

    def __init__(
        self,
        stat: Callable[[str], os.stat_result],
        listdir: Callable[[str | None], Iterator[os.DirEntry]],
        *,
        polling_interval: int = 1,
    ) -> None:
        """:param stat: stat function. See ``os.stat`` for details.
        :param listdir: listdir function. See ``os.scandir`` for details.
        :type polling_interval: int
        :param polling_interval: interval in seconds between polling the file system.
        """
        emitter_cls = partial(PollingEmitter, stat=stat, listdir=listdir)
        super().__init__(emitter_cls, timeout=polling_interval)  # type: ignore[arg-type]
