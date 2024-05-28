# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""
Some functions related to the os and os.path module
"""
import os
import re
import zipfile


WINDOWS_RESERVED = re.compile(r'''
    ^
    # forbidden stems: reserved keywords
    (:?CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])
    # even with an extension this is recommended against
    (:?\..*)?
    $
''', flags=re.IGNORECASE | re.VERBOSE)
def clean_filename(name, replacement=''):
    """ Strips or replaces possibly problematic or annoying characters our of
    the input string, in order to make it a valid filename in most operating
    systems (including dropping reserved Windows filenames).

    If this results in an empty string, results in "Untitled" (localized).

    Allows:

    * any alphanumeric character (unicode)
    * underscore (_) as that's innocuous
    * dot (.) except in leading position to avoid creating dotfiles
    * dash (-) except in leading position to avoid annoyance / confusion with
      command options
    * brackets ([ and ]), while they correspond to shell *character class*
      they're a common way to mark / tag files especially on windows
    * parenthesis ("(" and ")"), a more natural though less common version of
      the former
    * space (" ")

    :param str name: file name to clean up
    :param str replacement:
        replacement string to use for sequences of problematic input, by default
        an empty string to remove them entirely, each contiguous sequence of
        problems is replaced by a single replacement
    :rtype: str
    """
    if WINDOWS_RESERVED.match(name):
        return "Untitled"
    return re.sub(r'[^\w_.()\[\] -]+', replacement, name).lstrip('.-') or "Untitled"

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
    is_running_as_nt_service = lambda: False
else:
    import win32service as ws
    import win32serviceutil as wsu

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
                    return info['ProcessId'] == os.getppid()
        except Exception:
            return False
