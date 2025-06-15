""":module: watchdog.events
:synopsis: File system events and event handlers.
:author: yesudeep@google.com (Yesudeep Mangalapilly)
:author: contact@tiger-222.fr (Mickaël Schoentgen)

Event Classes
-------------
.. autoclass:: FileSystemEvent
   :members:
   :show-inheritance:
   :inherited-members:

.. autoclass:: FileSystemMovedEvent
   :members:
   :show-inheritance:

.. autoclass:: FileMovedEvent
   :members:
   :show-inheritance:

.. autoclass:: DirMovedEvent
   :members:
   :show-inheritance:

.. autoclass:: FileModifiedEvent
   :members:
   :show-inheritance:

.. autoclass:: DirModifiedEvent
   :members:
   :show-inheritance:

.. autoclass:: FileCreatedEvent
   :members:
   :show-inheritance:

.. autoclass:: FileClosedEvent
   :members:
   :show-inheritance:

.. autoclass:: FileClosedNoWriteEvent
   :members:
   :show-inheritance:

.. autoclass:: FileOpenedEvent
   :members:
   :show-inheritance:

.. autoclass:: DirCreatedEvent
   :members:
   :show-inheritance:

.. autoclass:: FileDeletedEvent
   :members:
   :show-inheritance:

.. autoclass:: DirDeletedEvent
   :members:
   :show-inheritance:


Event Handler Classes
---------------------
.. autoclass:: FileSystemEventHandler
   :members:
   :show-inheritance:

.. autoclass:: PatternMatchingEventHandler
   :members:
   :show-inheritance:

.. autoclass:: RegexMatchingEventHandler
   :members:
   :show-inheritance:

.. autoclass:: LoggingEventHandler
   :members:
   :show-inheritance:

"""

from __future__ import annotations

import logging
import os.path
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from watchdog.utils.patterns import match_any_paths

if TYPE_CHECKING:
    from collections.abc import Generator

EVENT_TYPE_MOVED = "moved"
EVENT_TYPE_DELETED = "deleted"
EVENT_TYPE_CREATED = "created"
EVENT_TYPE_MODIFIED = "modified"
EVENT_TYPE_CLOSED = "closed"
EVENT_TYPE_CLOSED_NO_WRITE = "closed_no_write"
EVENT_TYPE_OPENED = "opened"


@dataclass(unsafe_hash=True)
class FileSystemEvent:
    """Immutable type that represents a file system event that is triggered
    when a change occurs on the monitored file system.

    All FileSystemEvent objects are required to be immutable and hence
    can be used as keys in dictionaries or be added to sets.
    """

    src_path: bytes | str
    dest_path: bytes | str = ""
    event_type: str = field(default="", init=False)
    is_directory: bool = field(default=False, init=False)

    """
    True if event was synthesized; False otherwise.
    These are events that weren't actually broadcast by the OS, but
    are presumed to have happened based on other, actual events.
    """
    is_synthetic: bool = field(default=False)


class FileSystemMovedEvent(FileSystemEvent):
    """File system event representing any kind of file system movement."""

    event_type = EVENT_TYPE_MOVED


# File events.


class FileDeletedEvent(FileSystemEvent):
    """File system event representing file deletion on the file system."""

    event_type = EVENT_TYPE_DELETED


class FileModifiedEvent(FileSystemEvent):
    """File system event representing file modification on the file system."""

    event_type = EVENT_TYPE_MODIFIED


class FileCreatedEvent(FileSystemEvent):
    """File system event representing file creation on the file system."""

    event_type = EVENT_TYPE_CREATED


class FileMovedEvent(FileSystemMovedEvent):
    """File system event representing file movement on the file system."""


class FileClosedEvent(FileSystemEvent):
    """File system event representing file close on the file system."""

    event_type = EVENT_TYPE_CLOSED


class FileClosedNoWriteEvent(FileSystemEvent):
    """File system event representing an unmodified file close on the file system."""

    event_type = EVENT_TYPE_CLOSED_NO_WRITE


class FileOpenedEvent(FileSystemEvent):
    """File system event representing file close on the file system."""

    event_type = EVENT_TYPE_OPENED


# Directory events.


class DirDeletedEvent(FileSystemEvent):
    """File system event representing directory deletion on the file system."""

    event_type = EVENT_TYPE_DELETED
    is_directory = True


class DirModifiedEvent(FileSystemEvent):
    """File system event representing directory modification on the file system."""

    event_type = EVENT_TYPE_MODIFIED
    is_directory = True


class DirCreatedEvent(FileSystemEvent):
    """File system event representing directory creation on the file system."""

    event_type = EVENT_TYPE_CREATED
    is_directory = True


class DirMovedEvent(FileSystemMovedEvent):
    """File system event representing directory movement on the file system."""

    is_directory = True


class FileSystemEventHandler:
    """Base file system event handler that you can override methods from."""

    def dispatch(self, event: FileSystemEvent) -> None:
        """Dispatches events to the appropriate methods.

        :param event:
            The event object representing the file system event.
        :type event:
            :class:`FileSystemEvent`
        """
        self.on_any_event(event)
        getattr(self, f"on_{event.event_type}")(event)

    def on_any_event(self, event: FileSystemEvent) -> None:
        """Catch-all event handler.

        :param event:
            The event object representing the file system event.
        :type event:
            :class:`FileSystemEvent`
        """

    def on_moved(self, event: DirMovedEvent | FileMovedEvent) -> None:
        """Called when a file or a directory is moved or renamed.

        :param event:
            Event representing file/directory movement.
        :type event:
            :class:`DirMovedEvent` or :class:`FileMovedEvent`
        """

    def on_created(self, event: DirCreatedEvent | FileCreatedEvent) -> None:
        """Called when a file or directory is created.

        :param event:
            Event representing file/directory creation.
        :type event:
            :class:`DirCreatedEvent` or :class:`FileCreatedEvent`
        """

    def on_deleted(self, event: DirDeletedEvent | FileDeletedEvent) -> None:
        """Called when a file or directory is deleted.

        :param event:
            Event representing file/directory deletion.
        :type event:
            :class:`DirDeletedEvent` or :class:`FileDeletedEvent`
        """

    def on_modified(self, event: DirModifiedEvent | FileModifiedEvent) -> None:
        """Called when a file or directory is modified.

        :param event:
            Event representing file/directory modification.
        :type event:
            :class:`DirModifiedEvent` or :class:`FileModifiedEvent`
        """

    def on_closed(self, event: FileClosedEvent) -> None:
        """Called when a file opened for writing is closed.

        :param event:
            Event representing file closing.
        :type event:
            :class:`FileClosedEvent`
        """

    def on_closed_no_write(self, event: FileClosedNoWriteEvent) -> None:
        """Called when a file opened for reading is closed.

        :param event:
            Event representing file closing.
        :type event:
            :class:`FileClosedNoWriteEvent`
        """

    def on_opened(self, event: FileOpenedEvent) -> None:
        """Called when a file is opened.

        :param event:
            Event representing file opening.
        :type event:
            :class:`FileOpenedEvent`
        """


class PatternMatchingEventHandler(FileSystemEventHandler):
    """Matches given patterns with file paths associated with occurring events.
    Uses pathlib's `PurePath.match()` method. `patterns` and `ignore_patterns`
    are expected to be a list of strings.
    """

    def __init__(
        self,
        *,
        patterns: list[str] | None = None,
        ignore_patterns: list[str] | None = None,
        ignore_directories: bool = False,
        case_sensitive: bool = False,
    ):
        super().__init__()

        self._patterns = patterns
        self._ignore_patterns = ignore_patterns
        self._ignore_directories = ignore_directories
        self._case_sensitive = case_sensitive

    @property
    def patterns(self) -> list[str] | None:
        """(Read-only)
        Patterns to allow matching event paths.
        """
        return self._patterns

    @property
    def ignore_patterns(self) -> list[str] | None:
        """(Read-only)
        Patterns to ignore matching event paths.
        """
        return self._ignore_patterns

    @property
    def ignore_directories(self) -> bool:
        """(Read-only)
        ``True`` if directories should be ignored; ``False`` otherwise.
        """
        return self._ignore_directories

    @property
    def case_sensitive(self) -> bool:
        """(Read-only)
        ``True`` if path names should be matched sensitive to case; ``False``
        otherwise.
        """
        return self._case_sensitive

    def dispatch(self, event: FileSystemEvent) -> None:
        """Dispatches events to the appropriate methods.

        :param event:
            The event object representing the file system event.
        :type event:
            :class:`FileSystemEvent`
        """
        if self.ignore_directories and event.is_directory:
            return

        paths = []
        if hasattr(event, "dest_path"):
            paths.append(os.fsdecode(event.dest_path))
        if event.src_path:
            paths.append(os.fsdecode(event.src_path))

        if match_any_paths(
            paths,
            included_patterns=self.patterns,
            excluded_patterns=self.ignore_patterns,
            case_sensitive=self.case_sensitive,
        ):
            super().dispatch(event)


class RegexMatchingEventHandler(FileSystemEventHandler):
    """Matches given regexes with file paths associated with occurring events.
    Uses the `re` module.
    """

    def __init__(
        self,
        *,
        regexes: list[str] | None = None,
        ignore_regexes: list[str] | None = None,
        ignore_directories: bool = False,
        case_sensitive: bool = False,
    ):
        super().__init__()

        if regexes is None:
            regexes = [r".*"]
        elif isinstance(regexes, str):
            regexes = [regexes]
        if ignore_regexes is None:
            ignore_regexes = []
        if case_sensitive:
            self._regexes = [re.compile(r) for r in regexes]
            self._ignore_regexes = [re.compile(r) for r in ignore_regexes]
        else:
            self._regexes = [re.compile(r, re.IGNORECASE) for r in regexes]
            self._ignore_regexes = [re.compile(r, re.IGNORECASE) for r in ignore_regexes]
        self._ignore_directories = ignore_directories
        self._case_sensitive = case_sensitive

    @property
    def regexes(self) -> list[re.Pattern[str]]:
        """(Read-only)
        Regexes to allow matching event paths.
        """
        return self._regexes

    @property
    def ignore_regexes(self) -> list[re.Pattern[str]]:
        """(Read-only)
        Regexes to ignore matching event paths.
        """
        return self._ignore_regexes

    @property
    def ignore_directories(self) -> bool:
        """(Read-only)
        ``True`` if directories should be ignored; ``False`` otherwise.
        """
        return self._ignore_directories

    @property
    def case_sensitive(self) -> bool:
        """(Read-only)
        ``True`` if path names should be matched sensitive to case; ``False``
        otherwise.
        """
        return self._case_sensitive

    def dispatch(self, event: FileSystemEvent) -> None:
        """Dispatches events to the appropriate methods.

        :param event:
            The event object representing the file system event.
        :type event:
            :class:`FileSystemEvent`
        """
        if self.ignore_directories and event.is_directory:
            return

        paths = []
        if hasattr(event, "dest_path"):
            paths.append(os.fsdecode(event.dest_path))
        if event.src_path:
            paths.append(os.fsdecode(event.src_path))

        if any(r.match(p) for r in self.ignore_regexes for p in paths):
            return

        if any(r.match(p) for r in self.regexes for p in paths):
            super().dispatch(event)


class LoggingEventHandler(FileSystemEventHandler):
    """Logs all the events captured."""

    def __init__(self, *, logger: logging.Logger | None = None) -> None:
        super().__init__()
        self.logger = logger or logging.root

    def on_moved(self, event: DirMovedEvent | FileMovedEvent) -> None:
        super().on_moved(event)

        what = "directory" if event.is_directory else "file"
        self.logger.info("Moved %s: from %s to %s", what, event.src_path, event.dest_path)

    def on_created(self, event: DirCreatedEvent | FileCreatedEvent) -> None:
        super().on_created(event)

        what = "directory" if event.is_directory else "file"
        self.logger.info("Created %s: %s", what, event.src_path)

    def on_deleted(self, event: DirDeletedEvent | FileDeletedEvent) -> None:
        super().on_deleted(event)

        what = "directory" if event.is_directory else "file"
        self.logger.info("Deleted %s: %s", what, event.src_path)

    def on_modified(self, event: DirModifiedEvent | FileModifiedEvent) -> None:
        super().on_modified(event)

        what = "directory" if event.is_directory else "file"
        self.logger.info("Modified %s: %s", what, event.src_path)

    def on_closed(self, event: FileClosedEvent) -> None:
        super().on_closed(event)

        self.logger.info("Closed modified file: %s", event.src_path)

    def on_closed_no_write(self, event: FileClosedNoWriteEvent) -> None:
        super().on_closed_no_write(event)

        self.logger.info("Closed read file: %s", event.src_path)

    def on_opened(self, event: FileOpenedEvent) -> None:
        super().on_opened(event)

        self.logger.info("Opened file: %s", event.src_path)


def generate_sub_moved_events(
    src_dir_path: bytes | str,
    dest_dir_path: bytes | str,
) -> Generator[DirMovedEvent | FileMovedEvent]:
    """Generates an event list of :class:`DirMovedEvent` and
    :class:`FileMovedEvent` objects for all the files and directories within
    the given moved directory that were moved along with the directory.

    :param src_dir_path:
        The source path of the moved directory.
    :param dest_dir_path:
        The destination path of the moved directory.
    :returns:
        An iterable of file system events of type :class:`DirMovedEvent` and
        :class:`FileMovedEvent`.
    """
    for root, directories, filenames in os.walk(dest_dir_path):  # type: ignore[type-var]
        for directory in directories:
            full_path = os.path.join(root, directory)  # type: ignore[call-overload]
            renamed_path = full_path.replace(dest_dir_path, src_dir_path) if src_dir_path else ""
            yield DirMovedEvent(renamed_path, full_path, is_synthetic=True)
        for filename in filenames:
            full_path = os.path.join(root, filename)  # type: ignore[call-overload]
            renamed_path = full_path.replace(dest_dir_path, src_dir_path) if src_dir_path else ""
            yield FileMovedEvent(renamed_path, full_path, is_synthetic=True)


def generate_sub_created_events(src_dir_path: bytes | str) -> Generator[DirCreatedEvent | FileCreatedEvent]:
    """Generates an event list of :class:`DirCreatedEvent` and
    :class:`FileCreatedEvent` objects for all the files and directories within
    the given moved directory that were moved along with the directory.

    :param src_dir_path:
        The source path of the created directory.
    :returns:
        An iterable of file system events of type :class:`DirCreatedEvent` and
        :class:`FileCreatedEvent`.
    """
    for root, directories, filenames in os.walk(src_dir_path):  # type: ignore[type-var]
        for directory in directories:
            full_path = os.path.join(root, directory)  # type: ignore[call-overload]
            yield DirCreatedEvent(full_path, is_synthetic=True)
        for filename in filenames:
            full_path = os.path.join(root, filename)  # type: ignore[call-overload]
            yield FileCreatedEvent(full_path, is_synthetic=True)
