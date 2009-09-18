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

from osv import fields, osv
from tools.translate import _
import pooler
import os
import unittest
from tools import config
from base_module_quality import base_module_quality

class quality_test(base_module_quality.abstract_quality_check):

    def __init__(self):
        super(quality_test, self).__init__()
        self.bool_installed_only = True
        self.name = _("Unit Test")
        self.note = _("""
This test checks the Unit Test Cases of the module. Note that 'unit_test/test.py' is needed in module.

""")
        self.min_score = 0
        return None

    def run_test(self, cr, uid, module_path):
        self.score = 0.0
        pool = pooler.get_pool(cr.dbname)
        module_name = module_path.split('/')[-1]
        test_file = config['addons_path'] +'/' + module_name +'/unit_test/test.py'
        if not os.path.isfile(test_file):
            self.result += _("Module does not have 'unit_test/test.py' file")
            return None
        module_obj = pool.get('ir.module.module')
        module_ids = module_obj.search(cr, uid, [('name', '=', module_name)])
        module = module_obj.browse(cr, uid, module_ids)
        if not len(module):
            self.result += _("Sorry  does not load this module properly")
            return None
        module = module[0]
        if not module.state == "installed":
            self.result += _('Module has to be installed before running Unit test')
            return None

        test = module.name + '.' + 'unit_test.test'
        test_module = __import__(test)
        test_file = getattr(test_module, 'unit_test')
        test_obj = getattr(test_file, 'test')
        self.get_result(test_obj.runTest(cr,uid))
        return None

    def get_result(self, dict_unit):
        if not self.error:
            return self.format_html_table(data_list=dict_unit)
        return ""

    def format_html_table(self, data_list=None):
        detail = '''<html><head></head><body><table>
                   <tr><th>Test Cases</th><th>Result</th>'''
        html = ''

        if data_list[0] == True:
            self.result = data_list[1]
            data = data_list[1].split('... ok')
            for case in map(lambda x:x[0].replace('\n',''),map(lambda x: x.split(' ('),data)):
                if case.find('Ran') != -1:
                    case = case[case.index('Ran'):-2]
                    html += '<tr><th>%s</th><th>OK</th></tr>'%(case)
                else:
                    html += '<tr><td>%s</td><td>OK</td></tr>'%(case)
            self.result_details = detail + html + '</table></body></html>'
            return True

        detail_lst = []
        cnt = 0
        detail += '''<th>Details</th></tr>'''
        data = data_list[1].split("======================================================================")
        test = data[0].split('\n')
        self.result += '\n'.join(test)
        for err in (data_list[0].failures,data_list[0].errors):
            for value in err:
                detail_lst.append(value[1])
                self.result += value[1] + '\n'
        for case in map(lambda x:x.split('...'),test):
            if len(case[0]) < 2:
                continue
            test_name = case[0].split(' (')[0]
            html += '<tr><th>%s</th><th>%s</th><td>%s</td></tr>'%(test_name,case[1],detail_lst[cnt])
            cnt += 1
        self.result_details = detail + html +'</tr></table></body></html>'
        return True




# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
