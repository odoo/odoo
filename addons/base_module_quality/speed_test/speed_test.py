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
        self.result = """
===Speed Test===:

This test checks the speed of the module.

"""
        self.bool_installed_only = True
        return None

    def run_test(self, cr, uid, module_path):
        pool = pooler.get_pool(cr.dbname)
        module_name = module_path.split('/')[-1]
        self.result+=('{| border="1" cellspacing="0" cellpadding="5" align="left" \n! %-40s \n! %-10s \n! %-10s \n! %-10s \n! %-10s \n! %-20s') % ('Object Name'.ljust(40), 'Size (S)'.ljust(10), '1'.ljust(10), 'S/2'.ljust(10), 'S'.ljust(10), 'Complexity'.ljust(20))
        ids2 = pool.get('ir.model.data').search(cr, uid, [('module','=', module_name), ('model','=','ir.model')])
        model_data = pool.get('ir.model.data').browse(cr, uid, ids2)
        model_list = []
        for model in model_data:
            model_list.append(model.res_id)
        obj_list = []
        for mod in pool.get('ir.model').browse(cr, uid, model_list):
            obj_list.append(str(mod.model))

        obj_counter = 0
        score = 0
        for obj in obj_list:
            obj_counter += 1
            ids = pool.get(obj).search(cr, uid, [])
            ids = ids[:100]
            size = len(ids)
            if size:
                c1 = time.time()
                pool.get(obj).read(cr, uid, ids[0])
                c2 = time.time()
                base_time = c2 - c1

                c1 = time.time()
                pool.get(obj).read(cr, uid, ids[:size/2])
                c2 = time.time()
                halfsize_time = c2 - c1

                c1 = time.time()
                pool.get(obj).read(cr, uid, ids)
                c2 = time.time()
                size_time = c2 - c1
                if size < 5:
                    self.score += -2
                    self.result += ('\n|-\n| %s \n| %s \n| %s \n| %s \n| %s \n| %s ') % (obj, size, base_time, halfsize_time, size_time, "Warning! Not enough demo data")
                else:
                    tolerated_margin = 5/100
                    complexity = "not recognized"
                    if min(size_time,base_time,halfsize_time) != base_time:
                        complexity = "O(1)"
                        score += 10

                    else:
                        k1 = (halfsize_time - base_time)*1000 / ((size/2) - 1)
                        k2 = (size_time - base_time)*1000 / ((size) - 1)
                        tmp = k1 * tolerated_margin
                        if (k1 - tmp) < k2 and k2 <  (k1 + tmp):
                            complexity = "O(n)"
                            if round(tmp) == 0:
                                complexity = "O(1)"
                                score += 10
                            else:
                                score += 5
                        else:
                            complexity = "O(n²) or worst"
                            score += 0

                    self.result += ('\n|-\n| %s \n| %s \n| %s \n| %s \n| %s \n| %s ') % (obj, size, base_time, halfsize_time, size_time, complexity)
            else:
                score += -5
                self.result += ('\n|-\n| %s \n| %s \n| %s \n| %s \n| %s \n| %s ') % (obj, size, "", "", "", "Warning! Object has no demo data")


        self.result += '\n|}\n'
        self.score = obj_counter and score/obj_counter or 0.0
        return None

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

