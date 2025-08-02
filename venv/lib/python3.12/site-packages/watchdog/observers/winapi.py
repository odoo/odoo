""":module: watchdog.observers.winapi
:synopsis: Windows API-Python interface (removes dependency on ``pywin32``).
:author: theller@ctypes.org (Thomas Heller)
:author: will@willmcgugan.com (Will McGugan)
:author: ryan@rfk.id.au (Ryan Kelly)
:author: yesudeep@gmail.com (Yesudeep Mangalapilly)
:author: thomas.amland@gmail.com (Thomas Amland)
:author: contact@tiger-222.fr (Mickaël Schoentgen)
:platforms: windows
"""

from __future__ import annotations

import contextlib
import ctypes
from ctypes.wintypes import BOOL, DWORD, HANDLE, LPCWSTR, LPVOID, LPWSTR
from dataclasses import dataclass
from functools import reduce
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

# Invalid handle value.
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

# File notification constants.
FILE_NOTIFY_CHANGE_FILE_NAME = 0x01
FILE_NOTIFY_CHANGE_DIR_NAME = 0x02
FILE_NOTIFY_CHANGE_ATTRIBUTES = 0x04
FILE_NOTIFY_CHANGE_SIZE = 0x08
FILE_NOTIFY_CHANGE_LAST_WRITE = 0x010
FILE_NOTIFY_CHANGE_LAST_ACCESS = 0x020
FILE_NOTIFY_CHANGE_CREATION = 0x040
FILE_NOTIFY_CHANGE_SECURITY = 0x0100

FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
FILE_FLAG_OVERLAPPED = 0x40000000
FILE_LIST_DIRECTORY = 1
FILE_SHARE_READ = 0x01
FILE_SHARE_WRITE = 0x02
FILE_SHARE_DELETE = 0x04
OPEN_EXISTING = 3

VOLUME_NAME_NT = 0x02

# File action constants.
FILE_ACTION_CREATED = 1
FILE_ACTION_DELETED = 2
FILE_ACTION_MODIFIED = 3
FILE_ACTION_RENAMED_OLD_NAME = 4
FILE_ACTION_RENAMED_NEW_NAME = 5
FILE_ACTION_DELETED_SELF = 0xFFFE
FILE_ACTION_OVERFLOW = 0xFFFF

# Aliases
FILE_ACTION_ADDED = FILE_ACTION_CREATED
FILE_ACTION_REMOVED = FILE_ACTION_DELETED
FILE_ACTION_REMOVED_SELF = FILE_ACTION_DELETED_SELF

THREAD_TERMINATE = 0x0001

# IO waiting constants.
WAIT_ABANDONED = 0x00000080
WAIT_IO_COMPLETION = 0x000000C0
WAIT_OBJECT_0 = 0x00000000
WAIT_TIMEOUT = 0x00000102

# Error codes
ERROR_OPERATION_ABORTED = 995


class OVERLAPPED(ctypes.Structure):
    _fields_ = (
        ("Internal", LPVOID),
        ("InternalHigh", LPVOID),
        ("Offset", DWORD),
        ("OffsetHigh", DWORD),
        ("Pointer", LPVOID),
        ("hEvent", HANDLE),
    )


def _errcheck_bool(value: Any | None, func: Any, args: Any) -> Any:
    if not value:
        raise ctypes.WinError()  # type: ignore[attr-defined]
    return args


def _errcheck_handle(value: Any | None, func: Any, args: Any) -> Any:
    if not value:
        raise ctypes.WinError()  # type: ignore[attr-defined]
    if value == INVALID_HANDLE_VALUE:
        raise ctypes.WinError()  # type: ignore[attr-defined]
    return args


def _errcheck_dword(value: Any | None, func: Any, args: Any) -> Any:
    if value == 0xFFFFFFFF:
        raise ctypes.WinError()  # type: ignore[attr-defined]
    return args


kernel32 = ctypes.WinDLL("kernel32")  # type: ignore[attr-defined]

ReadDirectoryChangesW = kernel32.ReadDirectoryChangesW
ReadDirectoryChangesW.restype = BOOL
ReadDirectoryChangesW.errcheck = _errcheck_bool
ReadDirectoryChangesW.argtypes = (
    HANDLE,  # hDirectory
    LPVOID,  # lpBuffer
    DWORD,  # nBufferLength
    BOOL,  # bWatchSubtree
    DWORD,  # dwNotifyFilter
    ctypes.POINTER(DWORD),  # lpBytesReturned
    ctypes.POINTER(OVERLAPPED),  # lpOverlapped
    LPVOID,  # FileIOCompletionRoutine # lpCompletionRoutine
)

CreateFileW = kernel32.CreateFileW
CreateFileW.restype = HANDLE
CreateFileW.errcheck = _errcheck_handle
CreateFileW.argtypes = (
    LPCWSTR,  # lpFileName
    DWORD,  # dwDesiredAccess
    DWORD,  # dwShareMode
    LPVOID,  # lpSecurityAttributes
    DWORD,  # dwCreationDisposition
    DWORD,  # dwFlagsAndAttributes
    HANDLE,  # hTemplateFile
)

CloseHandle = kernel32.CloseHandle
CloseHandle.restype = BOOL
CloseHandle.argtypes = (HANDLE,)  # hObject

CancelIoEx = kernel32.CancelIoEx
CancelIoEx.restype = BOOL
CancelIoEx.errcheck = _errcheck_bool
CancelIoEx.argtypes = (
    HANDLE,  # hObject
    ctypes.POINTER(OVERLAPPED),  # lpOverlapped
)

CreateEvent = kernel32.CreateEventW
CreateEvent.restype = HANDLE
CreateEvent.errcheck = _errcheck_handle
CreateEvent.argtypes = (
    LPVOID,  # lpEventAttributes
    BOOL,  # bManualReset
    BOOL,  # bInitialState
    LPCWSTR,  # lpName
)

SetEvent = kernel32.SetEvent
SetEvent.restype = BOOL
SetEvent.errcheck = _errcheck_bool
SetEvent.argtypes = (HANDLE,)  # hEvent

WaitForSingleObjectEx = kernel32.WaitForSingleObjectEx
WaitForSingleObjectEx.restype = DWORD
WaitForSingleObjectEx.errcheck = _errcheck_dword
WaitForSingleObjectEx.argtypes = (
    HANDLE,  # hObject
    DWORD,  # dwMilliseconds
    BOOL,  # bAlertable
)

CreateIoCompletionPort = kernel32.CreateIoCompletionPort
CreateIoCompletionPort.restype = HANDLE
CreateIoCompletionPort.errcheck = _errcheck_handle
CreateIoCompletionPort.argtypes = (
    HANDLE,  # FileHandle
    HANDLE,  # ExistingCompletionPort
    LPVOID,  # CompletionKey
    DWORD,  # NumberOfConcurrentThreads
)

GetQueuedCompletionStatus = kernel32.GetQueuedCompletionStatus
GetQueuedCompletionStatus.restype = BOOL
GetQueuedCompletionStatus.errcheck = _errcheck_bool
GetQueuedCompletionStatus.argtypes = (
    HANDLE,  # CompletionPort
    LPVOID,  # lpNumberOfBytesTransferred
    LPVOID,  # lpCompletionKey
    ctypes.POINTER(OVERLAPPED),  # lpOverlapped
    DWORD,  # dwMilliseconds
)

PostQueuedCompletionStatus = kernel32.PostQueuedCompletionStatus
PostQueuedCompletionStatus.restype = BOOL
PostQueuedCompletionStatus.errcheck = _errcheck_bool
PostQueuedCompletionStatus.argtypes = (
    HANDLE,  # CompletionPort
    DWORD,  # lpNumberOfBytesTransferred
    DWORD,  # lpCompletionKey
    ctypes.POINTER(OVERLAPPED),  # lpOverlapped
)


GetFinalPathNameByHandleW = kernel32.GetFinalPathNameByHandleW
GetFinalPathNameByHandleW.restype = DWORD
GetFinalPathNameByHandleW.errcheck = _errcheck_dword
GetFinalPathNameByHandleW.argtypes = (
    HANDLE,  # hFile
    LPWSTR,  # lpszFilePath
    DWORD,  # cchFilePath
    DWORD,  # DWORD
)


class FileNotifyInformation(ctypes.Structure):
    _fields_ = (
        ("NextEntryOffset", DWORD),
        ("Action", DWORD),
        ("FileNameLength", DWORD),
        ("FileName", (ctypes.c_char * 1)),
    )


LPFNI = ctypes.POINTER(FileNotifyInformation)


# We don't need to recalculate these flags every time a call is made to
# the win32 API functions.
WATCHDOG_FILE_FLAGS = FILE_FLAG_BACKUP_SEMANTICS
WATCHDOG_FILE_SHARE_FLAGS = reduce(
    lambda x, y: x | y,
    [
        FILE_SHARE_READ,
        FILE_SHARE_WRITE,
        FILE_SHARE_DELETE,
    ],
)
WATCHDOG_FILE_NOTIFY_FLAGS = reduce(
    lambda x, y: x | y,
    [
        FILE_NOTIFY_CHANGE_FILE_NAME,
        FILE_NOTIFY_CHANGE_DIR_NAME,
        FILE_NOTIFY_CHANGE_ATTRIBUTES,
        FILE_NOTIFY_CHANGE_SIZE,
        FILE_NOTIFY_CHANGE_LAST_WRITE,
        FILE_NOTIFY_CHANGE_SECURITY,
        FILE_NOTIFY_CHANGE_LAST_ACCESS,
        FILE_NOTIFY_CHANGE_CREATION,
    ],
)

# ReadDirectoryChangesW buffer length.
# To handle cases with lot of changes, this seems the highest safest value we can use.
# Note: it will fail with ERROR_INVALID_PARAMETER when it is greater than 64 KB and
#       the application is monitoring a directory over the network.
#       This is due to a packet size limitation with the underlying file sharing protocols.
#       https://docs.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-readdirectorychangesw#remarks
BUFFER_SIZE = 64000

# Buffer length for path-related stuff.
# Introduced to keep the old behavior when we bumped BUFFER_SIZE from 2048 to 64000 in v1.0.0.
PATH_BUFFER_SIZE = 2048


def _parse_event_buffer(read_buffer: bytes, n_bytes: int) -> list[tuple[int, str]]:
    results = []
    while n_bytes > 0:
        fni = ctypes.cast(read_buffer, LPFNI)[0]  # type: ignore[arg-type]
        ptr = ctypes.addressof(fni) + FileNotifyInformation.FileName.offset
        filename = ctypes.string_at(ptr, fni.FileNameLength)
        results.append((fni.Action, filename.decode("utf-16")))
        num_to_skip = fni.NextEntryOffset
        if num_to_skip <= 0:
            break
        read_buffer = read_buffer[num_to_skip:]
        n_bytes -= num_to_skip  # num_to_skip is long. n_bytes should be long too.
    return results


def _is_observed_path_deleted(handle: HANDLE, path: str) -> bool:
    # Comparison of observed path and actual path, returned by
    # GetFinalPathNameByHandleW. If directory moved to the trash bin, or
    # deleted, actual path will not be equal to observed path.
    buff = ctypes.create_unicode_buffer(PATH_BUFFER_SIZE)
    GetFinalPathNameByHandleW(handle, buff, PATH_BUFFER_SIZE, VOLUME_NAME_NT)
    return buff.value != path


def _generate_observed_path_deleted_event() -> tuple[bytes, int]:
    # Create synthetic event for notify that observed directory is deleted
    path = ctypes.create_unicode_buffer(".")
    event = FileNotifyInformation(0, FILE_ACTION_DELETED_SELF, len(path), path.value.encode("utf-8"))
    event_size = ctypes.sizeof(event)
    buff = ctypes.create_string_buffer(PATH_BUFFER_SIZE)
    ctypes.memmove(buff, ctypes.addressof(event), event_size)
    return buff.raw, event_size


def get_directory_handle(path: str) -> HANDLE:
    """Returns a Windows handle to the specified directory path."""
    return CreateFileW(
        path,
        FILE_LIST_DIRECTORY,
        WATCHDOG_FILE_SHARE_FLAGS,
        None,
        OPEN_EXISTING,
        WATCHDOG_FILE_FLAGS,
        None,
    )


def close_directory_handle(handle: HANDLE) -> None:
    try:
        CancelIoEx(handle, None)  # force ReadDirectoryChangesW to return
        CloseHandle(handle)
    except OSError:
        with contextlib.suppress(Exception):
            CloseHandle(handle)


def read_directory_changes(handle: HANDLE, path: str, *, recursive: bool) -> tuple[bytes, int]:
    """Read changes to the directory using the specified directory handle.

    https://timgolden.me.uk/pywin32-docs/win32file__ReadDirectoryChangesW_meth.html
    """
    event_buffer = ctypes.create_string_buffer(BUFFER_SIZE)
    nbytes = DWORD()
    try:
        ReadDirectoryChangesW(
            handle,
            ctypes.byref(event_buffer),
            len(event_buffer),
            recursive,
            WATCHDOG_FILE_NOTIFY_FLAGS,
            ctypes.byref(nbytes),
            None,
            None,
        )
    except OSError as e:
        if e.winerror == ERROR_OPERATION_ABORTED:  # type: ignore[attr-defined]
            return event_buffer.raw, 0

        # Handle the case when the root path is deleted
        if _is_observed_path_deleted(handle, path):
            return _generate_observed_path_deleted_event()

        raise

    return event_buffer.raw, int(nbytes.value)


@dataclass(unsafe_hash=True)
class WinAPINativeEvent:
    action: int
    src_path: str

    @property
    def is_added(self) -> bool:
        return self.action == FILE_ACTION_CREATED

    @property
    def is_removed(self) -> bool:
        return self.action == FILE_ACTION_REMOVED

    @property
    def is_modified(self) -> bool:
        return self.action == FILE_ACTION_MODIFIED

    @property
    def is_renamed_old(self) -> bool:
        return self.action == FILE_ACTION_RENAMED_OLD_NAME

    @property
    def is_renamed_new(self) -> bool:
        return self.action == FILE_ACTION_RENAMED_NEW_NAME

    @property
    def is_removed_self(self) -> bool:
        return self.action == FILE_ACTION_REMOVED_SELF


def read_events(handle: HANDLE, path: str, *, recursive: bool) -> list[WinAPINativeEvent]:
    buf, nbytes = read_directory_changes(handle, path, recursive=recursive)
    events = _parse_event_buffer(buf, nbytes)
    return [WinAPINativeEvent(action, src_path) for action, src_path in events]
