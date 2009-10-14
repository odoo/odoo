# -*- coding: utf-8 -*-
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

from osv import fields, osv
from tools.translate import _
import pooler
from tools import config
from base_module_quality import base_module_quality

class quality_test(base_module_quality.abstract_quality_check):

    def __init__(self):
        super(quality_test, self).__init__()
        self.bool_installed_only = True
        self.name = _("Unit Test")
        self.note = _("""
This test checks the Unit Test(PyUnit) Cases of the module. Note that 'unit_test/test.py' is needed in module.

""")
        self.min_score = 0
        self.message = 'This test does not calculate score'
        self.bool_count_score = False
        return None

    def run_test(self, cr, uid, module_path):
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
            self.result += _("Error! Module is not properly loaded/installed")
            return None
        module = module[0]
        test = module.name + '.' + 'unit_test.test'
        test_module = __import__(test)
        test_file = getattr(test_module, 'unit_test')
        test_obj = getattr(test_file, 'test')

        test_result = test_obj.runTest(cr,uid)
        self.result = self.get_result(test_result)
        self.result_details += self.get_result_details(test_result)
        return None

    def get_result(self, data_list):
        header = ('{| border="1" cellspacing="0" cellpadding="5" align="left" \n! %-40s \n! %-40s \n', [_('Summary'), _('Status')])
        result_unit = {}
        res_list = []
        if data_list[0]:
            res = data_list[1].split('\n')
            res_list.append(res[-4:][0])
            res_list.append(res[-4:][2])
            result_unit['unit_test'] = res_list
            return self.format_table(header, data_list=result_unit)
        return "Unit Test Fail"

    def get_result_details(self, data_list):
        detail = '''<html><head>%s</head><body><table class="tablestyle">
           <tr><th class="tdatastyle">Test Cases</th ><th class="tdatastyle">Result</th>'''%(self.get_style())
        html = ''

        if data_list[0] == True:
            data = data_list[1].split('... ok')
            for case in map(lambda x:x[0].replace('\n',''),map(lambda x: x.split(' ('),data)):
                if case.find('Ran') != -1:
                    case = case[case.index('Ran'):-2]
                    html += '<tr><th class="tdatastyle">%s</th><th class="tdatastyle">OK</th></tr>'%(case)
                else:
                    html += '<tr><td class="tdatastyle">%s</td><td class="tdatastyle">OK</td></tr>'%(case)
            res = detail + html + '</table></body></html>'
            return res
        else:
            detail_lst = []
            cnt = 0
            detail += '''<th class="tdatastyle">Details</th></tr>'''
            data = data_list[1].split("======================================================================")
            test = data[0].split('\n')
            for err in (data_list[0].failures,data_list[0].errors):
                for value in err:
                    detail_lst.append(value[1])

            for case in map(lambda x:x.split('...'), test):
                if len(case[0]) < 2:
                    continue
                test_name = case[0].split(' (')[0]
                html += '<tr><th class="tdatastyle">%s</th><th class="tdatastyle">%s</th><td class="tdatastyle">%s</td></tr>'%(test_name,case[1],detail_lst[cnt])
                cnt += 1
            return detail + html +'</tr></table></body></html>'
        return ''

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: