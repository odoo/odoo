# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
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
from tools.translate import _
from base_module_quality import base_module_quality

class quality_test(base_module_quality.abstract_quality_check):

    def __init__(self):
        super(quality_test, self).__init__()
        self.name = _("Pyflakes Test")
        self.note = _("""This test uses Pyflakes to analyze Python programs and detect various errors. It works by parsing the source file, not importing it. See http://www.divmod.org/trac/wiki/DivmodPyflakes for further info.\n (This test score does not effect final score) """)
        self.bool_installed_only = False
        self.bool_count_score = False #This test display on report (summary/detail) does not count score
        return None

    def run_test(self, cr, uid, module_path):
        list_files = os.listdir(module_path)
        for i in list_files:
            path = os.path.join(module_path, i)
            if os.path.isdir(path):
                for j in os.listdir(path):
                    list_files.append(os.path.join(i, j))

        dict_py = {}
        flag = False
        self.result_details += '''<html>
                              <head>
                              <link rel="stylesheet" type="text/css" href="/tg_widgets/openerp/css/wiki.css" media="all">
                              </head>
                              <body><table><tr><b>Report</b>'''
        for file_py in list_files:
            if file_py.split('.')[-1] == 'py' and not file_py.endswith('__init__.py') and not file_py.endswith('__terp__.py'):
                if not flag:
                    flag = True
                file_path = os.path.join(module_path, file_py)
                try:
                    res = os.popen('pyflakes' + ' ' + file_path).read()
                    if not res:
                        continue
                    self.result_details += '''<table border="2" bordercolor="black" width="100%" align="center"><tr><td width="30%"> ''' + file_py + '</td><td width="70%"><table border=2 bordercolor=black >'
                    list_res = res.split('\n')
                    temp_dict = {}
                    keys = ['imported but unused statements', 'unable to detect undefined names', \
                            'undefined name', 'redefinition of unused from line', \
                            'import shadowed by loop variable', 'local variables referenced before assignment', \
                            'duplicate argument in function definition', 'redefinition of function from line', \
                            'future import after other statements']
                    map(lambda key:temp_dict.setdefault(key, 0), keys)
                    detail_str = ''
                    for line in list_res:
                        self.result_details += '''<tr><td width="100%"> ''' + line + '</td></tr>'
                        detail_str += line + '\n'
                        if line.find("imported but unused") != -1:
                            temp_dict['imported but unused statements'] += 1
                        elif line.find("*' used; unable to detect undefined names") != -1:
                            temp_dict['unable to detect undefined names'] += 1
                        elif line.find("undefined name") != -1:
                            temp_dict['undefined name'] += 1
                        elif line.find("redefinition of unused") != -1:
                            temp_dict['redefinition of unused from line'] += 1
                        elif line.find("shadowed by loop variable") != -1:
                            temp_dict['import shadowed by loop variable'] += 1
                        elif line.find("referenced before assignment") != -1:
                            temp_dict['local variables referenced before assignment'] += 1
                        elif line.find("in function definition") != -1:
                            temp_dict['duplicate argument in function definition'] += 1
                        elif line.find("redefinition of function") != -1:
                            temp_dict['redefinition of function from line'] += 1
                        elif line.find("after other statements") != -1:
                            temp_dict['future import after other statements'] += 1
                    final_str = '\n'
                    for t in temp_dict:
                        if str(temp_dict[t]) != '0':
                            final_str += '\n' + str(t) + ' : ' + str(temp_dict[t]) + '\n'
                except:
                    self.result += _("Error! Is pyflakes correctly installed? (http://pypi.python.org/pypi/pyflakes/0.3.0)")+"\n"
                    break
                try:
                    dict_py[file_py] = [file_py, final_str]
                except:
                    dict_py[file_py] = [file_py, _("Unable to parse the result. Check the details.")]
                self.result_details += '</table></td>'
        if not flag:
            self.error = True
            self.result = _("No python file found")
            return None
        self.result_details += '</tr></table></body></html>'
        self.score = 0
        self.result = self.get_result(dict_py)
        return None

    def get_result(self, dict_py):
        header = ('{| border="1" cellspacing="0" cellpadding="5" align="left" \n! %-40s \n! %-10s \n', [_('File Name'), _('Result')])
        if not self.error:
            return self.format_table(header, data_list=dict_py)
        return ""

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: