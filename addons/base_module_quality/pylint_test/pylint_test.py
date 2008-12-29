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


import os
from tools import config

from base_module_quality import base_module_quality


class quality_test(base_module_quality.abstract_quality_check):

    def __init__(self):
        super(quality_test, self).__init__()
#        self.result = """
#===Pylint Test===:
#
#    This test checks if the module satisfy the current coding standard used by OpenERP.
#
#"""
        self.bool_installed_only = False
        return None

    def run_test(self, cr, uid, module_path, module_state):
        config_file_path = config['addons_path']+'/base_module_quality/pylint_test/pylint_test_config.txt'
        list_files = os.listdir(module_path)
        for i in list_files:
            path = os.path.join(module_path, i)
            if os.path.isdir(path):
                for j in os.listdir(path):
                    list_files.append(os.path.join(i, j))

        n = 0
        score = 0.0
        detail = ""
        detail  = "\n===Pylint Test===\n"
        error = False
        for file in list_files:
            if file.split('.')[-1] == 'py' and not file.endswith('__init__.py') and not file.endswith('__terp__.py'):
                file_path = os.path.join(module_path, file)
                res = os.popen('pylint --rcfile=' + config_file_path + ' ' + file_path).read()
                n += 1
                leftchar = -1
                while res[leftchar:leftchar+1] != ' ' and leftchar-1 <= 0:
                    leftchar -= 1
                rightchar = -10
                while res[rightchar:rightchar+1] != '/' and rightchar+1 <= 0:
                    rightchar += 1

                try:
                    score += float(res[leftchar+1:rightchar])
#                    self.result += file + ": " + res[leftchar+1:rightchar] + "/10\n"
                    detail += file + ": " + res[leftchar+1:rightchar] + "/10\n"
                except:
                    score += 0
#                    self.result += file + ": Unable to parse the result. Check the details.\n"
                    detail += file + ": Unable to parse the result. Check the details.\n"
                self.result_details += res
        self.score = n and score / n or score
        if not self.bool_installed_only or module_state=="installed":
            summary ="""
===Pylint Test===:

This test checks if the module satisfy the current coding standard used by OpenERP.

""" + "Score: " + str(self.score) + "/10\n"
        else:
            summary ="""  \n===Pylint Test===:

The module has to be installed before running this test.\n\n """
            header_list = ""
            error = True
        self.result = self.format_table(test='pylint', data_list=[summary,detail,error])
        return None


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

