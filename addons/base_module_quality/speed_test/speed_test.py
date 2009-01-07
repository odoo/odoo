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
        self.name = _("Speed Test")
        self.bool_installed_only = True
        self.ponderation = 1.0
        self.listdata = []
        return None
    def run_test(self, cr, uid, module_path):
        pool = pooler.get_pool(cr.dbname)
        module_name = module_path.split('/')[-1]
        obj_list = self.get_objects(cr, uid, module_name)
        obj_counter = 0
        score = 0
        obj_ids = self.get_ids(cr, uid, obj_list)
        for obj in obj_ids:
            obj_counter += 1
            ids = obj_ids[obj]
            ids = ids[:100]
            size = len(ids)
            if size:
                c1 = cr.count

                pool.get(obj).read(cr, uid, [ids[0]])
                pool.get(obj).read(cr, uid, [ids[0]])
                code_base_complexity = cr.count - c1

                pool.get(obj).read(cr, uid, ids[:size/2])
                pool.get(obj).read(cr, uid, ids[:size/2])
                code_half_complexity = cr.count - c1

                pool.get(obj).read(cr, uid, ids)
                pool.get(obj).read(cr, uid, ids)
                code_size_complexity = cr.count - c1

                if size < 5:
                    self.score += -2
                    list = [obj, size, code_base_complexity, code_half_complexity, code_size_complexity, "Warning! Not enough demo data"]
                    self.listdata.append(list)
                else:
                    if code_size_complexity <= (code_base_complexity + size):
                        complexity = "O(1)"
                        score = 10
                    else:
                        complexity = "O(n) or worst"
                        score = 0
                    list = [obj, size, code_base_complexity, code_half_complexity, code_size_complexity, complexity]
                    self.listdata.append(list)
            else:
                score += -5
                list = [obj, size, "", "", "", "Warning! Object has no demo data"]
                self.listdata.append(list)
        self.score = obj_counter and score/obj_counter or 0.0
        self.result = self.get_result()
        self.result_details = self.get_result_details()

        return None

    def get_result(self):
##        self.run_test(cr, uid, module_path)
#        if not self.bool_installed_only or module_state=="installed":
        summary = """
This test checks the speed of the module.

"""
#        else:
#            summary ="""  \n===Speed Test===:
#
#The module has to be installed before running this test.\n\n """
#            header_list = ""
#            self.error = True
        return summary

    def get_result_details(self):
        header_list = ['speed', 'Object Name', 'Size-Number of Records (S)', '1', 'S/2', 'S', 'Complexity using query']
        detail = ""
#        detail += "\n===Speed Test===\n"
        if not self.error:
            detail += self.format_table(header=header_list, data_list=[self.listdata])
        return detail

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

