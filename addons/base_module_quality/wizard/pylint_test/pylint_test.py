# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import netsvc
from osv import fields, osv
import os

def _test_pylint(self, url, add_folder=None):
    list_files = os.listdir(url)
    new_list = []
    subfolder = {}
    for i in list_files:
        if os.path.isdir(i):
            path = os.path.join(url, i)
            new_list.append(os.listdir(path))
            res = _test_pylint(self, path, add_folder=i)
            subfolder.update(res)
    dict_files = {}
    for file in list_files:
        if file.split('.')[-1] == 'py' and not file.startswith('__init__'):
            file_path = os.path.join(url, file)
            res = os.popen('pylint '+file_path+' | tail -4').read()
            if res.startswith('Global'):
                if add_folder:
                    dict_files[add_folder + '/' + file] = res
                else:
                    dict_files[file] = res
    dict_files.update(subfolder)
    return dict_files

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

