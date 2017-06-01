# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.     
#
##############################################################################

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

        symlinks = filter(lambda dirname: os.path.islink(os.path.join(dirpath, dirname)), dirnames)
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

def _get_copy_function(src, dst):
    # try hardlinking file, to see if filesystem supports it
    with tempfile.NamedTemporaryFile(dir=src) as src_file:
        try:
            os.link(src_file.name, os.path.join(dst, '__test_link__'))
            os.unlink(os.path.join(dst, '__test_link__'))
            copy_function = os.link
        except OSError as e:
            copy_function = shutil.copy2
    return copy_function

def clonetree(src, dst, ignore=None):
    """Same as shutil.copytree(), except it hardlinks the files instead of
    copying them if the two paths belong to the same filesystem.

    WARNING: Hardlinks are not copies, if the new files are modified, so are
    the old ones. Don't use this if you need independent copies that can be
    modified independently!"""
    names = os.listdir(src)
    if ignore is not None:
        ignored_names = ignore(src, names)
    else:
        ignored_names = set()

    os.makedirs(dst)
    copy_function = _get_copy_function(src, dst)
    errors = []
    for name in names:
        if name in ignored_names:
            continue
        srcname = os.path.join(src, name)
        dstname = os.path.join(dst, name)
        try:
            if os.path.isdir(srcname):
                clonetree(srcname, dstname, ignore)
            else:
                copy_function(srcname, dstname)
            # XXX What about devices, sockets etc.?
        except (IOError, os.error) as why:
            errors.append((srcname, dstname, str(why)))
        # catch the Error from the recursive clonetree so that we can
        # continue with other files
        except Error as err:
            errors.extend(err.args[0])
    try:
        shutil.copystat(src, dst)
    except shutil.WindowsError:
        # can't copy file access times on Windows
        pass
    except OSError as why:
        errors.extend((src, dst, str(why)))
    if errors:
        raise Error(errors)

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
    from openerp.release import nt_service_name

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

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
