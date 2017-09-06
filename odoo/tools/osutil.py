# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""
Some functions related to the os and os.path module
"""

from contextlib import contextmanager
import os
from os.path import join as opj
import shutil
import tempfile
import zipfile

if os.name == 'nt':
    import ctypes
    import win32service as ws
    import win32serviceutil as wsu


def listdir(dir, recursive=False):
    """Allow to recursively get the file listing"""
    dir = os.path.normpath(dir)
    if not recursive:
        return os.listdir(dir)

    res = []
    for root, dirs, files in walksymlinks(dir):
        root = root[len(dir)+1:]
        res.extend([opj(root, f) for f in files])
    return res

def walksymlinks(top, topdown=True, onerror=None):
    """
    same as os.walk but follow symlinks
    attention: all symlinks are walked before all normals directories
    """
    for dirpath, dirnames, filenames in os.walk(top, topdown, onerror):
        if topdown:
            yield dirpath, dirnames, filenames

        symlinks = (dirname for dirname in dirnames if os.path.islink(os.path.join(dirpath, dirname)))
        for s in symlinks:
            for x in walksymlinks(os.path.join(dirpath, s), topdown, onerror):
                yield x

        if not topdown:
            yield dirpath, dirnames, filenames

@contextmanager
def tempdir():
    tmpdir = tempfile.mkdtemp()
    try:
        yield tmpdir
    finally:
        shutil.rmtree(tmpdir)

def zip_dir(path, stream, include_dir=True, fnct_sort=None):      # TODO add ignore list
    """
    : param fnct_sort : Function to be passed to "key" parameter of built-in
                        python sorted() to provide flexibility of sorting files
                        inside ZIP archive according to specific requirements.
    """
    path = os.path.normpath(path)
    len_prefix = len(os.path.dirname(path)) if include_dir else len(path)
    if len_prefix:
        len_prefix += 1

    with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED, allowZip64=True) as zipf:
        for dirpath, dirnames, filenames in os.walk(path):
            filenames = sorted(filenames, key=fnct_sort)
            for fname in filenames:
                bname, ext = os.path.splitext(fname)
                ext = ext or bname
                if ext not in ['.pyc', '.pyo', '.swp', '.DS_Store']:
                    path = os.path.normpath(os.path.join(dirpath, fname))
                    if os.path.isfile(path):
                        zipf.write(path, path[len_prefix:])


if os.name != 'nt':
    getppid = os.getppid
    is_running_as_nt_service = lambda: False
else:
    # based on http://mail.python.org/pipermail/python-win32/2007-June/006174.html
    _TH32CS_SNAPPROCESS = 0x00000002
    class _PROCESSENTRY32(ctypes.Structure):
        _fields_ = [("dwSize", ctypes.c_ulong),
                    ("cntUsage", ctypes.c_ulong),
                    ("th32ProcessID", ctypes.c_ulong),
                    ("th32DefaultHeapID", ctypes.c_ulong),
                    ("th32ModuleID", ctypes.c_ulong),
                    ("cntThreads", ctypes.c_ulong),
                    ("th32ParentProcessID", ctypes.c_ulong),
                    ("pcPriClassBase", ctypes.c_ulong),
                    ("dwFlags", ctypes.c_ulong),
                    ("szExeFile", ctypes.c_char * 260)]

    def getppid():
        CreateToolhelp32Snapshot = ctypes.windll.kernel32.CreateToolhelp32Snapshot
        Process32First = ctypes.windll.kernel32.Process32First
        Process32Next = ctypes.windll.kernel32.Process32Next
        CloseHandle = ctypes.windll.kernel32.CloseHandle
        hProcessSnap = CreateToolhelp32Snapshot(_TH32CS_SNAPPROCESS, 0)
        current_pid = os.getpid()
        try:
            pe32 = _PROCESSENTRY32()
            pe32.dwSize = ctypes.sizeof(_PROCESSENTRY32)
            if not Process32First(hProcessSnap, ctypes.byref(pe32)):
                raise OSError('Failed getting first process.')
            while True:
                if pe32.th32ProcessID == current_pid:
                    return pe32.th32ParentProcessID
                if not Process32Next(hProcessSnap, ctypes.byref(pe32)):
                    return None
        finally:
            CloseHandle(hProcessSnap)

    from contextlib import contextmanager
    from odoo.release import nt_service_name

    def is_running_as_nt_service():
        @contextmanager
        def close_srv(srv):
            try:
                yield srv
            finally:
                ws.CloseServiceHandle(srv)

        try:
            with close_srv(ws.OpenSCManager(None, None, ws.SC_MANAGER_ALL_ACCESS)) as hscm:
                with close_srv(wsu.SmartOpenService(hscm, nt_service_name, ws.SERVICE_ALL_ACCESS)) as hs:
                    info = ws.QueryServiceStatusEx(hs)
                    return info['ProcessId'] == getppid()
        except Exception:
            return False

if __name__ == '__main__':
    from pprint import pprint as pp
    pp(listdir('../report', True))
