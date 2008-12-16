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
from base_module_quality import base_module_quality

#~ class _test_pylint(quality_check):

    #~ def __init__(self, url, add_folder=None):
        #~ print "dans le test"
        #~ list_files = os.listdir(url)
        #~ new_list = []
        #~ subfolder = {}
        #~ for i in list_files:
            #~ if os.path.isdir(i):
                #~ path = os.path.join(url, i)
                #~ new_list.append(os.listdir(path))
                #~ res = _test_pylint(self, path, add_folder=i)
                #~ subfolder.update(res)
        #~ dict_files = {}
        #~ for file in list_files:
            #~ if file.split('.')[-1] == 'py' and not file.startswith('__init__'):
                #~ file_path = os.path.join(url, file)
                #~ res = os.popen('pylint '+file_path+' | tail -4').read()
                #~ if res.startswith('Global'):
                    #~ if add_folder:
                        #~ dict_files[add_folder + '/' + file] = res
                    #~ else:
                        #~ dict_files[file] = res
        #~ dict_files.update(subfolder)
        #~ print "dict_files", dict_files
        #~ return dict_files

class _test_pylint(base_module_quality.quality_check):

    def __init__(self, module_path):
        self._result = """
Pylint Test:
------------

    This test checks if the module satisfy the current coding standard used by OpenERP.

 
"""
        list_files = os.listdir(module_path)
        new_list = []
        subfolder = {}
        for i in list_files:
            path = os.path.join(module_path, i)
            if os.path.isdir(path):
                for j in os.listdir(path):
                    list_files.append(os.path.join(i, j))

        dict_files = {}
        n =0 
        score = 0.0
        print list_files
        for file in list_files:
            if file.split('.')[-1] == 'py' and not file.endswith('__init__.py') and not file.endswith('__terp__.py'):
#--rcfile=<file>     Specify a configuration file.
                file_path = os.path.join(module_path, file)
                res = os.popen('pylint  --persistent=n '+file_path).read()
                n += 1
                leftchar = -1
                while res[leftchar:leftchar+1] != ' ' and leftchar-1 <= 0:
                    leftchar -=1
                rightchar = -10
                while res[rightchar:rightchar+1] != '/' and rightchar+1 <= 0:
                    rightchar +=1

                score += float(res[leftchar+1:rightchar])
                self._result_details += res
                self._result += file+": "+ res[leftchar+1:rightchar]+"/10\n" 
        self._score = score / n
        return None


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

