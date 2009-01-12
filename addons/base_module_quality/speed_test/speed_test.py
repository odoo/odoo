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
from tools.translate import _
import pooler
import time


from base_module_quality import base_module_quality


class quality_test(base_module_quality.abstract_quality_check):

    def __init__(self):
        super(quality_test, self).__init__()
        self.bool_installed_only = True
        self.ponderation = 1.0
        self.name = _("Speed Test")
        self.note = _("""
This test checks the speed of the module. Note that at least 5 demo data is needed in order to run it.

""")
        return None

    def run_test(self, cr, uid, module_path):
        pool = pooler.get_pool(cr.dbname)
        module_name = module_path.split('/')[-1]
        obj_list = self.get_objects(cr, uid, module_name)
        obj_counter = 0
        score = 0.0
        obj_ids = self.get_ids(cr, uid, obj_list)
        result_dict = {}
        result_dict2 = {}
        self.result_details += _("O(1) means that the number of SQL requests to read the object does not depand on the number of objects we are reading. This feature is hardly wished.\n")
        for obj, ids in obj_ids.items():
            obj_counter += 1
            ids = ids[:100]
            size = len(ids)
            list2 = []
            if size:
                list = []

                #we perform the operation twice, and count the number of queries in the second run. This allows to avoid the cache effect. (like translated terms that asks for more queries)
                pool.get(obj).read(cr, uid, [ids[0]])
                c = cr.count
                pool.get(obj).read(cr, uid, [ids[0]])
                code_base_complexity = cr.count - c

                pool.get(obj).read(cr, uid, ids[:size/2])
                c = cr.count
                pool.get(obj).read(cr, uid, ids[:size/2])
                code_half_complexity = cr.count - c

                pool.get(obj).read(cr, uid, ids)
                c = cr.count
                pool.get(obj).read(cr, uid, ids)
                code_size_complexity = cr.count - c

                if size < 5:
                    list = [obj, size, code_base_complexity, code_half_complexity, code_size_complexity, _("Warning! Not enough demo data")]
                    list2 = [obj, _("No enough data")]
                else:
                    if code_size_complexity <= (code_base_complexity + size):
                        complexity = _("O(1)")
                        score += 1
                        list2 = [obj, _("Efficient")]
                    else:
                        complexity = _("O(n) or worst")
                        list2 = [obj, _("Not Efficient")]

                    list = [obj, size, code_base_complexity, code_half_complexity, code_size_complexity, complexity]

            else:
                list = [obj, size, "", "", "", _("Warning! Object has no demo data")]
                list2 = [obj, _("No data")]
            result_dict[obj] = list
            result_dict2[obj] = list2
        self.score = obj_counter and score / obj_counter or 0.0
        self.result_details += self.get_result_details(result_dict)
        self.result += self.get_result(result_dict2)
        return None

    def get_result(self, dict):
        header = ('{| border="1" cellspacing="0" cellpadding="5" align="left" \n! %-40s \n! %-10s', [_('Object Name'), _('Result')])
        if not self.error:
            return self.format_table(header, data_list=dict)
        return ""

    def get_result_details(self, dict):
        header = ('{| border="1" cellspacing="0" cellpadding="5" align="left" \n! %-40s \n! %-10s \n! %-10s \n! %-10s \n! %-10s \n! %-20s', [_('Object Name'), _('N (Number of Records)'), _('1'), _('N/2'), _('N'), _('Reading Complexity')])
        if not self.error:
            return self.format_table(header, data_list=dict)
        return ""

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

