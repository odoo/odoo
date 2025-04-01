"""
A pure-python re-implementation of methods used by win32verstamp.
This is to avoid a bootstraping problem where win32verstamp is used during build,
but requires an installation of pywin32 to be present.
We used to work around this by ignoring failure to verstamp, but that's easy to miss.

Implementations adapted, simplified and typed from:
- https://github.com/enthought/pywin32-ctypes/blob/main/win32ctypes/core/ctypes/_util.py
- https://github.com/enthought/pywin32-ctypes/blob/main/win32ctypes/core/cffi/_resource.py
- https://github.com/enthought/pywin32-ctypes/blob/main/win32ctypes/pywin32/win32api.py

---

(C) Copyright 2014 Enthought, Inc., Austin, TX
All right reserved.

This file is open source software distributed according to the terms in
https://github.com/enthought/pywin32-ctypes/blob/main/LICENSE.txt
"""

from __future__ import annotations

from collections.abc import Iterable
from ctypes import FormatError, WinDLL, get_last_error
from ctypes.wintypes import (
    BOOL,
    DWORD,
    HANDLE,
    LPCWSTR,
    LPVOID,
    WORD,
)
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ctypes import _NamedFuncPointer

    from _typeshed import ReadableBuffer
    from typing_extensions import Literal, SupportsBytes, SupportsIndex

kernel32 = WinDLL("kernel32", use_last_error=True)

###
# https://github.com/enthought/pywin32-ctypes/blob/main/win32ctypes/core/ctypes/_util.py
###


def make_error(function: _NamedFuncPointer) -> OSError:
    code = get_last_error()
    exception = OSError()
    exception.winerror = code
    exception.function = function.__name__
    exception.strerror = FormatError(code).strip()
    return exception


def check_null(result: int | None, function: _NamedFuncPointer, *_) -> int:
    if result is None:
        raise make_error(function)
    return result


def check_false(result: int | None, function: _NamedFuncPointer, *_) -> Literal[True]:
    if not bool(result):
        raise make_error(function)
    else:
        return True


###
# https://github.com/enthought/pywin32-ctypes/blob/main/win32ctypes/core/cffi/_resource.py
###

_BeginUpdateResource = kernel32.BeginUpdateResourceW
_BeginUpdateResource.argtypes = [LPCWSTR, BOOL]
_BeginUpdateResource.restype = HANDLE
_BeginUpdateResource.errcheck = check_null  # type: ignore[assignment] # ctypes is badly typed


_EndUpdateResource = kernel32.EndUpdateResourceW
_EndUpdateResource.argtypes = [HANDLE, BOOL]
_EndUpdateResource.restype = BOOL
_EndUpdateResource.errcheck = check_false  # type: ignore[assignment] # ctypes is badly typed

_UpdateResource = kernel32.UpdateResourceW
_UpdateResource.argtypes = [HANDLE, LPCWSTR, LPCWSTR, WORD, LPVOID, DWORD]
_UpdateResource.restype = BOOL
_UpdateResource.errcheck = check_false  # type: ignore[assignment] # ctypes is badly typed


###
# https://github.com/enthought/pywin32-ctypes/blob/main/win32ctypes/pywin32/win32api.py
###

LANG_NEUTRAL = 0x00


def BeginUpdateResource(filename: str, delete: bool):
    """Get a handle that can be used by the :func:`UpdateResource`.

    Parameters
    ----------
    fileName : str
        The filename of the module to load.
    delete : bool
        When true all existing resources are deleted

    Returns
    -------
    result : hModule
        Handle of the resource.

    """
    return _BeginUpdateResource(filename, delete)


def EndUpdateResource(handle: int, discard: bool) -> None:
    """End the update resource of the handle.

    Parameters
    ----------
    handle : hModule
        The handle of the resource as it is returned
        by :func:`BeginUpdateResource`

    discard : bool
        When True all writes are discarded.

    """
    _EndUpdateResource(handle, discard)


def UpdateResource(
    handle: int,
    type: str | int,
    name: str | int,
    data: Iterable[SupportsIndex] | SupportsIndex | SupportsBytes | ReadableBuffer,
    language: int = LANG_NEUTRAL,
) -> None:
    """Update a resource.

    Parameters
    ----------
    handle : hModule
        The handle of the resource file as returned by
        :func:`BeginUpdateResource`.

    type : str | int
        The type of resource to update.

    name : str | int
        The name or Id of the resource to update.

    data : bytes-like
        A bytes like object is expected.

    language : int
        Language to use, default is LANG_NEUTRAL.

    """
    lp_data = bytes(data)
    _UpdateResource(
        handle, LPCWSTR(type), LPCWSTR(name), language, lp_data, len(lp_data)
    )
