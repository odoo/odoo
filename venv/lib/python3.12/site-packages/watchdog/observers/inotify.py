""":module: watchdog.observers.inotify
:synopsis: ``inotify(7)`` based emitter implementation.
:author: Sebastien Martini <seb@dbzteam.org>
:author: Luke McCarthy <luke@iogopro.co.uk>
:author: yesudeep@google.com (Yesudeep Mangalapilly)
:author: Tim Cuthbertson <tim+github@gfxmonk.net>
:author: contact@tiger-222.fr (Mickaël Schoentgen)
:platforms: Linux 2.6.13+.

.. ADMONITION:: About system requirements

    Recommended minimum kernel version: 2.6.25.

    Quote from the inotify(7) man page:

        "Inotify was merged into the 2.6.13 Linux kernel. The required library
        interfaces were added to glibc in version 2.4. (IN_DONT_FOLLOW,
        IN_MASK_ADD, and IN_ONLYDIR were only added in version 2.5.)"

    Therefore, you must ensure the system is running at least these versions
    appropriate libraries and the kernel.

.. ADMONITION:: About recursiveness, event order, and event coalescing

    Quote from the inotify(7) man page:

        If successive output inotify events produced on the inotify file
        descriptor are identical (same wd, mask, cookie, and name) then they
        are coalesced into a single event if the older event has not yet been
        read (but see BUGS).

        The events returned by reading from an inotify file descriptor form
        an ordered queue. Thus, for example, it is guaranteed that when
        renaming from one directory to another, events will be produced in
        the correct order on the inotify file descriptor.

        ...

        Inotify monitoring of directories is not recursive: to monitor
        subdirectories under a directory, additional watches must be created.

    This emitter implementation therefore automatically adds watches for
    sub-directories if running in recursive mode.

Some extremely useful articles and documentation:

.. _inotify FAQ: http://inotify.aiken.cz/?section=inotify&page=faq&lang=en
.. _intro to inotify: http://www.linuxjournal.com/article/8478

"""

from __future__ import annotations

import logging
import os
import threading
from typing import TYPE_CHECKING

from watchdog.events import (
    DirCreatedEvent,
    DirDeletedEvent,
    DirModifiedEvent,
    DirMovedEvent,
    FileClosedEvent,
    FileClosedNoWriteEvent,
    FileCreatedEvent,
    FileDeletedEvent,
    FileModifiedEvent,
    FileMovedEvent,
    FileOpenedEvent,
    FileSystemEvent,
    generate_sub_created_events,
    generate_sub_moved_events,
)
from watchdog.observers.api import DEFAULT_EMITTER_TIMEOUT, DEFAULT_OBSERVER_TIMEOUT, BaseObserver, EventEmitter
from watchdog.observers.inotify_buffer import InotifyBuffer
from watchdog.observers.inotify_c import InotifyConstants

if TYPE_CHECKING:
    from watchdog.observers.api import EventQueue, ObservedWatch

logger = logging.getLogger(__name__)


class InotifyEmitter(EventEmitter):
    """inotify(7)-based event emitter.

    :param event_queue:
        The event queue to fill with events.
    :param watch:
        A watch object representing the directory to monitor.
    :type watch:
        :class:`watchdog.observers.api.ObservedWatch`
    :param timeout:
        Read events blocking timeout (in seconds).
    :type timeout:
        ``float``
    :param event_filter:
        Collection of event types to emit, or None for no filtering (default).
    :type event_filter:
        Iterable[:class:`watchdog.events.FileSystemEvent`] | None
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
        self._inotify: InotifyBuffer | None = None

    def on_thread_start(self) -> None:
        path = os.fsencode(self.watch.path)
        event_mask = self.get_event_mask_from_filter()
        self._inotify = InotifyBuffer(path, recursive=self.watch.is_recursive, event_mask=event_mask)

    def on_thread_stop(self) -> None:
        if self._inotify:
            self._inotify.close()
            self._inotify = None

    def queue_events(self, timeout: float, *, full_events: bool = False) -> None:
        # If "full_events" is true, then the method will report unmatched move events as separate events
        # This behavior is by default only called by a InotifyFullEmitter
        if self._inotify is None:
            logger.error("InotifyEmitter.queue_events() called when the thread is inactive")
            return
        with self._lock:
            if self._inotify is None:
                logger.error("InotifyEmitter.queue_events() called when the thread is inactive")
                return
            event = self._inotify.read_event()
            if event is None:
                return

            cls: type[FileSystemEvent]
            if isinstance(event, tuple):
                move_from, move_to = event
                src_path = self._decode_path(move_from.src_path)
                dest_path = self._decode_path(move_to.src_path)
                cls = DirMovedEvent if move_from.is_directory else FileMovedEvent
                self.queue_event(cls(src_path, dest_path))
                self.queue_event(DirModifiedEvent(os.path.dirname(src_path)))
                self.queue_event(DirModifiedEvent(os.path.dirname(dest_path)))
                if move_from.is_directory and self.watch.is_recursive:
                    for sub_moved_event in generate_sub_moved_events(src_path, dest_path):
                        self.queue_event(sub_moved_event)
                return

            src_path = self._decode_path(event.src_path)
            if event.is_moved_to:
                if full_events:
                    cls = DirMovedEvent if event.is_directory else FileMovedEvent
                    self.queue_event(cls("", src_path))
                else:
                    cls = DirCreatedEvent if event.is_directory else FileCreatedEvent
                    self.queue_event(cls(src_path))
                self.queue_event(DirModifiedEvent(os.path.dirname(src_path)))
                if event.is_directory and self.watch.is_recursive:
                    for sub_created_event in generate_sub_created_events(src_path):
                        self.queue_event(sub_created_event)
            elif event.is_attrib or event.is_modify:
                cls = DirModifiedEvent if event.is_directory else FileModifiedEvent
                self.queue_event(cls(src_path))
            elif event.is_delete or (event.is_moved_from and not full_events):
                cls = DirDeletedEvent if event.is_directory else FileDeletedEvent
                self.queue_event(cls(src_path))
                self.queue_event(DirModifiedEvent(os.path.dirname(src_path)))
            elif event.is_moved_from and full_events:
                cls = DirMovedEvent if event.is_directory else FileMovedEvent
                self.queue_event(cls(src_path, ""))
                self.queue_event(DirModifiedEvent(os.path.dirname(src_path)))
            elif event.is_create:
                cls = DirCreatedEvent if event.is_directory else FileCreatedEvent
                self.queue_event(cls(src_path))
                self.queue_event(DirModifiedEvent(os.path.dirname(src_path)))
            elif event.is_delete_self and src_path == self.watch.path:
                cls = DirDeletedEvent if event.is_directory else FileDeletedEvent
                self.queue_event(cls(src_path))
                self.stop()
            elif not event.is_directory:
                if event.is_open:
                    cls = FileOpenedEvent
                    self.queue_event(cls(src_path))
                elif event.is_close_write:
                    cls = FileClosedEvent
                    self.queue_event(cls(src_path))
                    self.queue_event(DirModifiedEvent(os.path.dirname(src_path)))
                elif event.is_close_nowrite:
                    cls = FileClosedNoWriteEvent
                    self.queue_event(cls(src_path))

    def _decode_path(self, path: bytes | str) -> bytes | str:
        """Decode path only if unicode string was passed to this emitter."""
        return path if isinstance(self.watch.path, bytes) else os.fsdecode(path)

    def get_event_mask_from_filter(self) -> int | None:
        """Optimization: Only include events we are filtering in inotify call."""
        if self._event_filter is None:
            return None

        # Always listen to delete self
        event_mask = InotifyConstants.IN_DELETE_SELF

        for cls in self._event_filter:
            if cls in {DirMovedEvent, FileMovedEvent}:
                event_mask |= InotifyConstants.IN_MOVE
            elif cls in {DirCreatedEvent, FileCreatedEvent}:
                event_mask |= InotifyConstants.IN_MOVE | InotifyConstants.IN_CREATE
            elif cls is DirModifiedEvent:
                event_mask |= (
                    InotifyConstants.IN_MOVE
                    | InotifyConstants.IN_ATTRIB
                    | InotifyConstants.IN_MODIFY
                    | InotifyConstants.IN_CREATE
                    | InotifyConstants.IN_CLOSE_WRITE
                )
            elif cls is FileModifiedEvent:
                event_mask |= InotifyConstants.IN_ATTRIB | InotifyConstants.IN_MODIFY
            elif cls in {DirDeletedEvent, FileDeletedEvent}:
                event_mask |= InotifyConstants.IN_DELETE
            elif cls is FileClosedEvent:
                event_mask |= InotifyConstants.IN_CLOSE_WRITE
            elif cls is FileClosedNoWriteEvent:
                event_mask |= InotifyConstants.IN_CLOSE_NOWRITE
            elif cls is FileOpenedEvent:
                event_mask |= InotifyConstants.IN_OPEN

        return event_mask


class InotifyFullEmitter(InotifyEmitter):
    """inotify(7)-based event emitter. By default this class produces move events even if they are not matched
    Such move events will have a ``None`` value for the unmatched part.
    """

    def queue_events(self, timeout: float, *, events: bool = True) -> None:  # type: ignore[override]
        super().queue_events(timeout, full_events=events)


class InotifyObserver(BaseObserver):
    """Observer thread that schedules watching directories and dispatches
    calls to event handlers.
    """

    def __init__(self, *, timeout: float = DEFAULT_OBSERVER_TIMEOUT, generate_full_events: bool = False) -> None:
        cls = InotifyFullEmitter if generate_full_events else InotifyEmitter
        super().__init__(cls, timeout=timeout)
