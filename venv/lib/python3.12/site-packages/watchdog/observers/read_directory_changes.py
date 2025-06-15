from __future__ import annotations

import os.path
import platform
import threading
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
    generate_sub_created_events,
    generate_sub_moved_events,
)
from watchdog.observers.api import DEFAULT_EMITTER_TIMEOUT, DEFAULT_OBSERVER_TIMEOUT, BaseObserver, EventEmitter
from watchdog.observers.winapi import close_directory_handle, get_directory_handle, read_events

if TYPE_CHECKING:
    from ctypes.wintypes import HANDLE

    from watchdog.events import FileSystemEvent
    from watchdog.observers.api import EventQueue, ObservedWatch
    from watchdog.observers.winapi import WinAPINativeEvent


class WindowsApiEmitter(EventEmitter):
    """Windows API-based emitter that uses ReadDirectoryChangesW
    to detect file system changes for a watch.
    """

    def __init__(
        self,
        event_queue: EventQueue,
        watch: ObservedWatch,
        *,
        timeout: float = DEFAULT_EMITTER_TIMEOUT,
        event_filter: list[type[FileSystemEvent]] | None = None,
    ) -> None:
        super().__init__(event_queue, watch, timeout=timeout, event_filter=event_filter)
        self._lock = threading.Lock()
        self._whandle: HANDLE | None = None

    def on_thread_start(self) -> None:
        self._whandle = get_directory_handle(self.watch.path)

    if platform.python_implementation() == "PyPy":

        def start(self) -> None:
            """PyPy needs some time before receiving events, see #792."""
            from time import sleep

            super().start()
            sleep(0.01)

    def on_thread_stop(self) -> None:
        if self._whandle:
            close_directory_handle(self._whandle)

    def _read_events(self) -> list[WinAPINativeEvent]:
        if not self._whandle:
            return []
        return read_events(self._whandle, self.watch.path, recursive=self.watch.is_recursive)

    def queue_events(self, timeout: float) -> None:
        winapi_events = self._read_events()
        with self._lock:
            last_renamed_src_path = ""
            for winapi_event in winapi_events:
                src_path = os.path.join(self.watch.path, winapi_event.src_path)

                if winapi_event.is_renamed_old:
                    last_renamed_src_path = src_path
                elif winapi_event.is_renamed_new:
                    dest_path = src_path
                    src_path = last_renamed_src_path
                    if os.path.isdir(dest_path):
                        self.queue_event(DirMovedEvent(src_path, dest_path))
                        if self.watch.is_recursive:
                            for sub_moved_event in generate_sub_moved_events(src_path, dest_path):
                                self.queue_event(sub_moved_event)
                    else:
                        self.queue_event(FileMovedEvent(src_path, dest_path))
                elif winapi_event.is_modified:
                    self.queue_event((DirModifiedEvent if os.path.isdir(src_path) else FileModifiedEvent)(src_path))
                elif winapi_event.is_added:
                    isdir = os.path.isdir(src_path)
                    self.queue_event((DirCreatedEvent if isdir else FileCreatedEvent)(src_path))
                    if isdir and self.watch.is_recursive:
                        for sub_created_event in generate_sub_created_events(src_path):
                            self.queue_event(sub_created_event)
                elif winapi_event.is_removed:
                    self.queue_event(FileDeletedEvent(src_path))
                elif winapi_event.is_removed_self:
                    self.queue_event(DirDeletedEvent(self.watch.path))
                    self.stop()


class WindowsApiObserver(BaseObserver):
    """Observer thread that schedules watching directories and dispatches
    calls to event handlers.
    """

    def __init__(self, *, timeout: float = DEFAULT_OBSERVER_TIMEOUT) -> None:
        super().__init__(WindowsApiEmitter, timeout=timeout)
