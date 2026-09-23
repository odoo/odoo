__all__ = [
    "site_data_dir",
    "user_data_dir",
]

import os
import sys
from pathlib import Path


def _xdg_dirs(variable: str, default: str) -> list[str]:
    # the XDG base-directory spec: an unset or empty variable takes the
    # default, and a relative entry is invalid and ignored
    entries = [
        entry.rstrip(os.sep) or os.sep
        for entry in (os.getenv(variable) or "").split(os.pathsep)
        if Path(entry).is_absolute()
    ]
    return entries or [default]


def user_data_dir(appname: str, appauthor: str | None = None) -> str:
    if sys.platform == "win32":
        path = Path(_get_win_folder("CSIDL_LOCAL_APPDATA"), appauthor or appname)
    elif sys.platform == "darwin":
        path = Path("~/Library/Application Support/").expanduser()
    else:
        path = Path(
            _xdg_dirs("XDG_DATA_HOME", str(Path("~/.local/share").expanduser()))[0]
        )
    return str(path / appname)


def site_data_dir(appname: str, appauthor: str | None = None) -> str:
    if sys.platform == "win32":
        path = Path(_get_win_folder("CSIDL_COMMON_APPDATA"), appauthor or appname)
    elif sys.platform == "darwin":
        path = Path("/Library/Application Support")
    else:
        path = Path(_xdg_dirs("XDG_DATA_DIRS", "/usr/local/share")[0]).expanduser()
    return str(path / appname)


def _get_win_folder_from_registry(csidl_name: str) -> str:
    import winreg as _winreg

    shell_folder_name = {
        "CSIDL_COMMON_APPDATA": "Common AppData",
        "CSIDL_LOCAL_APPDATA": "Local AppData",
    }[csidl_name]

    key = _winreg.OpenKey(  # type: ignore[attr-defined]
        _winreg.HKEY_CURRENT_USER,  # type: ignore[attr-defined]
        r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders",
    )
    folder, _type = _winreg.QueryValueEx(key, shell_folder_name)  # type: ignore[attr-defined]
    return folder


def _get_win_folder_with_pywin32(csidl_name: str) -> str:
    from win32com.shell import shell, shellcon

    folder = shell.SHGetFolderPath(0, getattr(shellcon, csidl_name), 0, 0)
    try:
        folder = str(folder)

        has_high_char = False
        for c in folder:
            if ord(c) > 255:
                has_high_char = True
                break
        if has_high_char:
            try:
                import win32api

                folder = win32api.GetShortPathName(folder)
            except ImportError:
                pass
    except UnicodeError:
        pass
    return folder


def _get_win_folder_with_ctypes(csidl_name: str) -> str:
    import ctypes

    csidl_const = {
        "CSIDL_COMMON_APPDATA": 35,
        "CSIDL_LOCAL_APPDATA": 28,
    }[csidl_name]

    buf = ctypes.create_unicode_buffer(1024)
    ctypes.windll.shell32.SHGetFolderPathW(None, csidl_const, None, 0, buf)  # type: ignore[attr-defined]

    has_high_char = False
    for c in buf:
        if ord(c) > 255:
            has_high_char = True
            break
    if has_high_char:
        buf2 = ctypes.create_unicode_buffer(1024)
        if ctypes.windll.kernel32.GetShortPathNameW(buf.value, buf2, 1024):  # type: ignore[attr-defined]
            buf = buf2

    return buf.value


if sys.platform == "win32":
    try:
        import win32com.shell  # noqa: F401  availability probe: the ImportError picks the fallback

        _get_win_folder = _get_win_folder_with_pywin32
    except ImportError:
        try:
            import ctypes  # noqa: F401  availability probe, as above

            _get_win_folder = _get_win_folder_with_ctypes
        except ImportError:
            _get_win_folder = _get_win_folder_from_registry
