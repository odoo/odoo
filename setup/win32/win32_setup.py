# -*- coding: utf-8 -*-

import os
import glob
import py2exe
from distutils.core import setup


execfile(os.path.join(os.path.dirname(__file__), '..', '..', 'odoo', 'release.py'))


def generate_files():
    actions = {
        'start': ['stop', 'start'],
        'stop': ['stop'],
    }

    files = []
    if os.name == 'nt':
        files.append(("Microsoft.VC90.CRT", glob.glob('C:\Microsoft.VC90.CRT\*.*')))
    for action, steps in actions.items():
        fname = action + '.bat'
        files.append(fname)
        with open(fname, 'w') as fp:
            fp.write('@PATH=%WINDIR%\system32;%WINDIR%;%WINDIR%\System32\Wbem;.\n')
            for step in steps:
                fp.write('@net %s %s\n' % (step, nt_service_name))
    return files

setup(
    service=["win32_service"],
    version=version,
    license=license,
    url=url,
    author=author,
    author_email=author_email,
    data_files=generate_files(),
    options={
        "py2exe": {
            "excludes": [
                'Tkconstants',
                'Tkinter',
                'tcl',
                '_imagingtk',
                'PIL._imagingtk',
                'ImageTk',
                'PIL.ImageTk',
                'FixTk'
            ],
            "skip_archive": 1,
            "optimize": 2,
        }
    },
)
