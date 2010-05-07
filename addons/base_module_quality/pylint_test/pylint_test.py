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
        self.name = _("Pylint Test")
        self.note = _("""This test uses Pylint and checks if the module satisfies the coding standard of Python. See http://www.logilab.org/project/name/pylint for further info.\n """)
        self.bool_installed_only = False
        self.min_score = 30

    def run_test(self, cr, uid, module_path):
        config_file_path = config['addons_path']+'/base_module_quality/pylint_test/pylint_test_config.txt'
        list_files = os.listdir(module_path)
        for i in list_files:
            path = os.path.join(module_path, i)
            if os.path.isdir(path):
                for j in os.listdir(path):
                    list_files.append(os.path.join(i, j))

        count = 0
        score = 0.0
        dict_py = {}
        flag = False
        self.result_details += '''<html><body><head>%s</head>'''%(self.get_style())
        for file_py in list_files:
            if file_py.split('.')[-1] == 'py' and not file_py.endswith('__init__.py') and not file_py.endswith('__terp__.py'):
                if not flag:
                    flag = True
                file_path = os.path.join(module_path, file_py)
                try:
                    import pylint
                    res = os.popen('pylint --rcfile=' + config_file_path + ' ' + file_path).read()
                except:
                    self.error = True
                    import netsvc
                    netsvc.Logger().notifyChannel('Pylint:', netsvc.LOG_WARNING, "Is pylint correctly installed? (http://pypi.python.org/pypi/pylint)")
                    self.result += _("Error. Is pylint correctly installed? (http://pypi.python.org/pypi/pylint)")+"\n"
                    return None
                count += 1
#                leftchar = -1
#                while res[leftchar:leftchar+1] != ' ' and leftchar-1 <= 0:
#                    leftchar -= 1
#                rightchar = -10
#                while res[rightchar:rightchar+1] != '/' and rightchar+1 <= 0:
#                    rightchar += 1
                try:
#                    score += float(res[leftchar+1:rightchar])
                    scr = res.split("Your code has been rated at")[1].split("</div>")[0].split("/")[0]
                    score += float(scr)
                    #self.result += file + ": " + res[leftchar+1:rightchar] + "/10\n"
                    dict_py[file_py] = [file_py, scr]
                except:
                    score += 0
                    #self.result += file + ": "+_("Unable to parse the result. Check the details.")+"\n"
                    dict_py[file_py] = [file_py, _("Unable to parse the result. Check the details.")]
                replace_string = ''
                replace_string += res
                replace_string = replace_string.replace('''<div''', '''<div class="divstyle" ''')
                replace_string = replace_string.replace('''<h1''', '''<h1 style="font-size:188%" class="head" ''')
                replace_string = replace_string.replace('''<h2''', '''<h2 style="font-size:150%" class="head" ''')
                replace_string = replace_string.replace('''<h3''', '''<h3 style="font-size:132%" class="head" ''')
                replace_string = replace_string.replace('''<h4''', '''<h4 style="font-size:116%" class="head" ''')
                replace_string = replace_string.replace('''<h5''', '''<h5 style="font-size:100%" class="head" ''')
                replace_string = replace_string.replace('''<h6''', '''<h6 style="font-size:80%" class="head" ''')
                replace_string = replace_string.replace('''<table''', '''<table class="tablestyle" ''')
                replace_string = replace_string.replace('''<th''', '''<th class="tdatastyle" ''')
                replace_string = replace_string.replace('''<td''', '''<td class="tdatastyle" ''')
                self.result_details += replace_string

        if not flag:
            self.error = True
            self.result = _("No python file found")
            return None
        self.result_details += '</body></html>'
        average_score = count and score / count or score
        self.score = (max(average_score, 0)) / 10
        if self.score*100 < self.min_score:
            self.message = 'Score is below than minimal score(%s%%)' % self.min_score
        self.result = self.get_result(dict_py)
        return None

    def get_result(self, dict_py):
        header = ('{| border="1" cellspacing="0" cellpadding="5" align="left" \n! %-40s \n! %-10s \n', [_('File Name'), _('Result (/10)')])
        if not self.error:
            return self.format_table(header, data_list=dict_py)
        return ""

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
