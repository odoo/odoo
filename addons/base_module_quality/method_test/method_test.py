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
import pooler

class quality_test(base_module_quality.abstract_quality_check):

    def __init__(self):
        super(quality_test, self).__init__()
#        self.result = """
#===Method Test===:
#
#This test checks if the module classes are raising exception when calling basic methods or no.
#
#"""
        self.bool_installed_only = True
        return None

    def run_test(self, cr, uid, module_path):
        pool = pooler.get_pool(cr.dbname)
        module_name = module_path.split('/')[-1]
        obj_list = self.get_objects(cr, uid, module_name)
        result = {}
        ok_count = 0
        ex_count = 0
        for obj in obj_list:
            temp = []
            try:
                res = pool.get(obj).search(cr, uid, [])
                temp.append('Ok')
                ok_count += 1
            except:
                temp.append('Exception')
                ex_count += 1
            try:
                res1 = pool.get(obj).fields_view_get(cr, uid,)
                temp.append('Ok')
                ok_count += 1
            except:
                temp.append('Exception')
                ex_count += 1
            try:
                res2 = pool.get(obj).read(cr, uid, [])
                temp.append('Ok')
                ok_count += 1
            except:
                temp.append('Exception')
                ex_count += 1
            result[obj] = temp
#        self.result += ('{| border="1" cellspacing="0" cellpadding="5" align="left" \n! %-40s \n! %-16s \n! %-20s \n! %-16s ') % ('Object Name'.ljust(40), 'search()'.ljust(16), 'fields_view_get()'.ljust(20), 'read()'.ljust(16))
        header_list = ['Object Name', 'search()', 'fields_view_get', 'read']
#        for res in result:
#            self.result += ('\n|-\n| %s \n| %s \n| %s \n| %s ') % (res, result[res][0],result[res][1], result[res][2])
#        self.result += '\n|}'
        self.score = (ok_count + ex_count) and float(ok_count)/float(ok_count + ex_count) or 0.0
        summary = """\n ===Method Test===:

This test checks if the module classes are raising exception when calling basic methods or no.

""" + "Score: " + str(self.score) + "/10\n"
        self.result = self.format_table(test='method', header=header_list, data_list=[summary,result])
        return None


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

