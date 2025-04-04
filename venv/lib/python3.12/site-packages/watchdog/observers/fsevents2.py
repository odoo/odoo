""":module: watchdog.observers.fsevents2
:synopsis: FSEvents based emitter implementation.
:author: thomas.amland@gmail.com (Thomas Amland)
:author: contact@tiger-222.fr (Mickaël Schoentgen)
:platforms: macOS
"""

from __future__ import annotations

import logging
import os
import queue
import unicodedata
import warnings
from threading import Thread
from typing import TYPE_CHECKING

# pyobjc
import AppKit
from FSEvents import (
    CFRunLoopGetCurrent,
    CFRunLoopRun,
    CFRunLoopStop,
    FSEventStreamCreate,
    FSEventStreamInvalidate,
    FSEventStreamRelease,
    FSEventStreamScheduleWithRunLoop,
    FSEventStreamStart,
    FSEventStreamStop,
    kCFAllocatorDefault,
    kCFRunLoopDefaultMode,
    kFSEventStreamCreateFlagFileEvents,
    kFSEventStreamCreateFlagNoDefer,
    kFSEventStreamEventFlagItemChangeOwner,
    kFSEventStreamEventFlagItemCreated,
    kFSEventStreamEventFlagItemFinderInfoMod,
    kFSEventStreamEventFlagItemInodeMetaMod,
    kFSEventStreamEventFlagItemIsDir,
    kFSEventStreamEventFlagItemIsSymlink,
    kFSEventStreamEventFlagItemModified,
    kFSEventStreamEventFlagItemRemoved,
    kFSEventStreamEventFlagItemRenamed,
    kFSEventStreamEventFlagItemXattrMod,
    kFSEventStreamEventIdSinceNow,
)

from watchdog.events import (
    DirCreatedEvent,
    DirDeletedEvent,
    DirModifiedEvent,
    DirMovedEvent,
    FileCreatedEvent,
    FileDeletedEvent,
    FileModifiedEvent,
    FileMovedEvent,
    FileSystemEvent,
)
from watchdog.observers.api import DEFAULT_EMITTER_TIMEOUT, DEFAULT_OBSERVER_TIMEOUT, BaseObserver, EventEmitter

if TYPE_CHECKING:
    from typing import Callable

    from watchdog.observers.api import EventQueue, ObservedWatch

logger = logging.getLogger(__name__)

message = "watchdog.observers.fsevents2 is deprecated and will be removed in a future release."
warnings.warn(message, category=DeprecationWarning, stacklevel=1)
logger.warning(message)


class FSEventsQueue(Thread):
    """Low level FSEvents client."""

    def __init__(self, path: bytes | str) -> None:
        Thread.__init__(self)
        self._queue: queue.Queue[list[NativeEvent] | None] = queue.Queue()
        self._run_loop = None

        if isinstance(path, bytes):
            path = os.fsdecode(path)
        self._path = unicodedata.normalize("NFC", path)

        context = None
        latency = 1.0
        self._stream_ref = FSEventStreamCreate(
            kCFAllocatorDefault,
            self._callback,
            context,
            [self._path],
            kFSEventStreamEventIdSinceNow,
            latency,
            kFSEventStreamCreateFlagNoDefer | kFSEventStreamCreateFlagFileEvents,
        )
        if self._stream_ref is None:
            error = "FSEvents. Could not create stream."
            raise OSError(error)

    def run(self) -> None:
        pool = AppKit.NSAutoreleasePool.alloc().init()
        self._run_loop = CFRunLoopGetCurrent()
        FSEventStreamScheduleWithRunLoop(self._stream_ref, self._run_loop, kCFRunLoopDefaultMode)
        if not FSEventStreamStart(self._stream_ref):
            FSEventStreamInvalidate(self._stream_ref)
            FSEventStreamRelease(self._stream_ref)
            error = "FSEvents. Could not start stream."
            raise OSError(error)

        CFRunLoopRun()
        FSEventStreamStop(self._stream_ref)
        FSEventStreamInvalidate(self._stream_ref)
        FSEventStreamRelease(self._stream_ref)
        del pool
        # Make sure waiting thread is notified
        self._queue.put(None)

    def stop(self) -> None:
        if self._run_loop is not None:
            CFRunLoopStop(self._run_loop)

    def _callback(
        self,
        stream_ref: int,
        client_callback_info: Callable,
        num_events: int,
        event_paths: list[bytes],
        event_flags: list[int],
        event_ids: list[int],
    ) -> None:
        events = [NativeEvent(path, flags, _id) for path, flags, _id in zip(event_paths, event_flags, event_ids)]
        logger.debug("FSEvents callback. Got %d events:", num_events)
        for e in events:
            logger.debug(e)
        self._queue.put(events)

    def read_events(self) -> list[NativeEvent] | None:
        """Returns a list or one or more events, or None if there are no more
        events to be read.
        """
        return self._queue.get() if self.is_alive() else None


class NativeEvent:
    def __init__(self, path: bytes, flags: int, event_id: int) -> None:
        self.path = path
        self.flags = flags
        self.event_id = event_id
        self.is_created = bool(flags & kFSEventStreamEventFlagItemCreated)
        self.is_removed = bool(flags & kFSEventStreamEventFlagItemRemoved)
        self.is_renamed = bool(flags & kFSEventStreamEventFlagItemRenamed)
        self.is_modified = bool(flags & kFSEventStreamEventFlagItemModified)
        self.is_change_owner = bool(flags & kFSEventStreamEventFlagItemChangeOwner)
        self.is_inode_meta_mod = bool(flags & kFSEventStreamEventFlagItemInodeMetaMod)
        self.is_finder_info_mod = bool(flags & kFSEventStreamEventFlagItemFinderInfoMod)
        self.is_xattr_mod = bool(flags & kFSEventStreamEventFlagItemXattrMod)
        self.is_symlink = bool(flags & kFSEventStreamEventFlagItemIsSymlink)
        self.is_directory = bool(flags & kFSEventStreamEventFlagItemIsDir)

    @property
    def _event_type(self) -> str:
        if self.is_created:
            return "Created"
        if self.is_removed:
            return "Removed"
        if self.is_renamed:
            return "Renamed"
        if self.is_modified:
            return "Modified"
        if self.is_inode_meta_mod:
            return "InodeMetaMod"
        if self.is_xattr_mod:
            return "XattrMod"
        return "Unknown"

    def __repr__(self) -> str:
        return (
            f"<{type(self).__name__}: path={self.path!r}, type={self._event_type},"
            f" is_dir={self.is_directory}, flags={hex(self.flags)}, id={self.event_id}>"
        )


class FSEventsEmitter(EventEmitter):
    """FSEvents based event emitter. Handles conversion of native events."""

    def __init__(
        self,
        event_queue: EventQueue,
        watch: ObservedWatch,
        *,
        timeout: float = DEFAULT_EMITTER_TIMEOUT,
        event_filter: list[type[FileSystemEvent]] | None = None,
    ):
        super().__init__(event_queue, watch, timeout=timeout, event_filter=event_filter)
        self._fsevents = FSEventsQueue(watch.path)
        self._fsevents.start()

    def on_thread_stop(self) -> None:
        self._fsevents.stop()

    def queue_events(self, timeout: float) -> None:
        events = self._fsevents.read_events()
        if events is None:
            return
        i = 0
        while i < len(events):
            event = events[i]

            cls: type[FileSystemEvent]
            # For some reason the create and remove flags are sometimes also
            # set for rename and modify type events, so let those take
            # precedence.
            if event.is_renamed:
                # Internal moves appears to always be consecutive in the same
                # buffer and have IDs differ by exactly one (while others
                # don't) making it possible to pair up the two events coming
                # from a single move operation. (None of this is documented!)
                # Otherwise, guess whether file was moved in or out.
                # TODO: handle id wrapping
                if i + 1 < len(events) and events[i + 1].is_renamed and events[i + 1].event_id == event.event_id + 1:
                    cls = DirMovedEvent if event.is_directory else FileMovedEvent
                    self.queue_event(cls(event.path, events[i + 1].path))
                    self.queue_event(DirModifiedEvent(os.path.dirname(event.path)))
                    self.queue_event(DirModifiedEvent(os.path.dirname(events[i + 1].path)))
                    i += 1
                elif os.path.exists(event.path):
                    cls = DirCreatedEvent if event.is_directory else FileCreatedEvent
                    self.queue_event(cls(event.path))
                    self.queue_event(DirModifiedEvent(os.path.dirname(event.path)))
                else:
                    cls = DirDeletedEvent if event.is_directory else FileDeletedEvent
                    self.queue_event(cls(event.path))
                    self.queue_event(DirModifiedEvent(os.path.dirname(event.path)))
                # TODO: generate events for tree

            elif event.is_modified or event.is_inode_meta_mod or event.is_xattr_mod:
                cls = DirModifiedEvent if event.is_directory else FileModifiedEvent
                self.queue_event(cls(event.path))

            elif event.is_created:
                cls = DirCreatedEvent if event.is_directory else FileCreatedEvent
                self.queue_event(cls(event.path))
                self.queue_event(DirModifiedEvent(os.path.dirname(event.path)))

            elif event.is_removed:
                cls = DirDeletedEvent if event.is_directory else FileDeletedEvent
                self.queue_event(cls(event.path))
                self.queue_event(DirModifiedEvent(os.path.dirname(event.path)))
            i += 1


class FSEventsObserver2(BaseObserver):
    def __init__(self, *, timeout: float = DEFAULT_OBSERVER_TIMEOUT) -> None:
        super().__init__(FSEventsEmitter, timeout=timeout)
