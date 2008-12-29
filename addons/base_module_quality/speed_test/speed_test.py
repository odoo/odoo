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
from tools import config
import pooler
import time


from base_module_quality import base_module_quality


class quality_test(base_module_quality.abstract_quality_check):

    def __init__(self):
        super(quality_test, self).__init__()
#        self.result = """
#===Speed Test===:
#
#This test checks the speed of the module.
#
#"""
        self.bool_installed_only = True
        return None
    def run_test(self, cr, uid, module_path, module_state):
        pool = pooler.get_pool(cr.dbname)
        module_name = module_path.split('/')[-1]
#        self.result+=('{| border="1" cellspacing="0" cellpadding="5" align="left" \n! %-40s \n! %-10s \n! %-10s \n! %-10s \n! %-10s \n! %-20s') % ('Object Name'.ljust(40), 'Size-Number of Records (S)'.ljust(10), '1'.ljust(10), 'S/2'.ljust(10), 'S'.ljust(10), 'Complexity using query'.ljust(20))
        header_list = ['Object Name', 'Size-Number of Records (S)', '1', 'S/2', 'S', 'Complexity using query']
        obj_list = self.get_objects(cr, uid, module_name)
        obj_counter = 0
        score = 0
        obj_ids = self.get_ids(cr, uid, obj_list)
        detail = ""
        list1 = []
        error = False
        for obj in obj_ids:
            obj_counter += 1
            ids = obj_ids[obj]
            ids = ids[:100]
            size = len(ids)
            if size:
                c1 = cr.count

                pool.get(obj).read(cr, uid, ids[0])
                pool.get(obj).read(cr, uid, ids[0])
                code_base_complexity = cr.count - c1

                pool.get(obj).read(cr, uid, ids[:size/2])
                pool.get(obj).read(cr, uid, ids[:size/2])
                code_half_complexity = cr.count - c1

                pool.get(obj).read(cr, uid, ids)
                pool.get(obj).read(cr, uid, ids)
                code_size_complexity = cr.count - c1

                if size < 5:
                    self.score += -2
#                    self.result += ('\n|-\n| %s \n| %s \n| %s \n| %s \n| %s \n| %s ') % (obj, size, code_base_complexity, code_half_complexity, code_size_complexity, "Warning! Not enough demo data")
                    list = [obj, size, code_base_complexity, code_half_complexity, code_size_complexity, "Warning! Not enough demo data"]
                    list1.append(list)
                else:
                    if code_size_complexity <= (code_base_complexity + size):
                        complexity = "O(1)"
                        score = 10
                    else:
                        complexity = "O(n) or worst"
                        score = 0
#                    self.result += ('\n|-\n| %s \n| %s \n| %s \n| %s \n| %s \n| %s ') % (obj, size, code_base_complexity, code_half_complexity, code_size_complexity, complexity)
                    list = [obj, size, code_base_complexity, code_half_complexity, code_size_complexity, complexity]
                    list1.append(list)
            else:
                score += -5
#                self.result += ('\n|-\n| %s \n| %s \n| %s \n| %s \n| %s \n| %s ') % (obj, size, "", "", "", "Warning! Object has no demo data")
                list = [obj, size, "", "", "", "Warning! Object has no demo data"]
                list1.append(list)
#        self.result += '\n|}\n'
        self.score = obj_counter and score/obj_counter or 0.0
        if not self.bool_installed_only or module_state=="installed":
            summary = """
===Speed Test===:

    This test checks the speed of the module.

"""+ "Score: " + str(self.score) + "/10\n"
        else:
            summary ="""  \n===Speed Test===:

The module has to be installed before running this test.\n\n """
            header_list = ""
            error = True
        self.result = self.format_table(test='speed', header=header_list, data_list=[summary,list1, error])
        return None

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

