# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

import os
import glob
from distutils.core import setup
import py2exe


meta = {}
execfile(os.path.join(os.path.dirname(__file__), '..', 'openerp', 'release.py'), meta)

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
                fp.write('@net %s %s\n' % (step, meta['nt_service_name']))

    files.append('meta.py')
    with open('meta.py', 'w') as fp:
        for m in 'description serie nt_service_name'.split():
            fp.write("%s = %r\n" % (m, meta[m],))

    return files

excludes = "Tkconstants Tkinter tcl _imagingtk PIL._imagingtk ImageTk PIL.ImageTk FixTk".split()

setup(service      = ["OpenERPServerService"],
      version      = meta['version'],
      license      = meta['license'],
      url          = meta['url'],
      author       = meta['author'],
      author_email = meta['author_email'],
      data_files   = generate_files(),
      options      = {"py2exe": {
                        "excludes": excludes,
                        "skip_archive": 1,
                        "optimize": 2,
                     }},
      )

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
