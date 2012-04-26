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

def datas():
    r = []
    if os.name == 'nt':
        r.append(("Microsoft.VC90.CRT", glob.glob('C:\Microsoft.VC90.CRT\*.*')))
    return r

setup(service=["OpenERPServerService"],
      options={"py2exe":{"excludes":["Tkconstants","Tkinter","tcl",
                                     "_imagingtk","PIL._imagingtk",
                                     "ImageTk", "PIL.ImageTk",
                                     "FixTk"],
                         "skip_archive": 1,
                         "optimize": 2,}},
      data_files=datas(),
      )

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

