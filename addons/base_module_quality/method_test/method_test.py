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
        self.result = """
Method Test:
------------

    This test checks if the class method has exception or not.


"""
        self.bool_installed_only = False
        return None

    def run_test(self, module_path, module_name=None, cr=None, uid=None):
        pool = pooler.get_pool(cr.dbname)
        ids2 = pool.get('ir.model.data').search(cr, uid, [('module','=', module_name), ('model','=','ir.model')])
        obj_list = []
        for mod in pool.get('ir.model.data').browse(cr, uid, ids2):
            object_name = mod.name.split('_')
            object_name.pop(0)
            object_name = '.'.join(object_name)
            obj_list.append(str(object_name))
        result={}
        self.result += "Module Name:" + module_name + '\n' + '===============\n'
        for obj in obj_list:
            temp=[]
            try:
                res = pool.get(obj).search(cr, uid, [])
                temp.append('Ok')
            except:
                temp.append('Exception')
            try:
                res1 = pool.get(obj).fields_view_get(cr, uid,)
                temp.append('Ok')
            except:
                temp.append('Exception')
            try:
                res2 = pool.get(obj).read(cr, uid, [])
                temp.append('Ok')
            except:
                temp.append('Exception')
            result[obj] = temp
        self.result+=("%-40s %-12s \t %-16s %-12s")%('Object Name'.ljust(40),'search','fields_view_get','read')
        self.result+='\n'
        for res in result:
            self.result+=("%-40s %-12s \t %-16s \t %-12s")%(res.ljust(40),result[res][0],result[res][1],result[res][2])
            self.result+="\n"
        return None


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

