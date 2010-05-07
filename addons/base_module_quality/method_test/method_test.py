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

from tools.translate import _

from base_module_quality import base_module_quality
import pooler

class quality_test(base_module_quality.abstract_quality_check):

    def __init__(self):
        super(quality_test, self).__init__()
        self.name = _("Method Test")
        self.note = _("""
This test checks if the module classes are raising exception when calling basic methods or not.
""")
        self.bool_installed_only = True
        self.min_score = 60

    def run_test(self, cr, uid, module_path):
        pool = pooler.get_pool(cr.dbname)
        module_name = module_path.split('/')[-1]
        obj_list = self.get_objects(cr, uid, module_name)
        result_dict = {}
        if not obj_list:
            self.error = True
            self.result = _("Module has no objects")
            return None
        ok_count = 0
        ex_count = 0
        for obj in obj_list:
            temp = [obj]
            try:
                pool.get(obj).search(cr, uid, [])
                temp.append(_('Ok'))
                ok_count += 1
            except:
                temp.append(_('Exception'))
                ex_count += 1
            try:
                pool.get(obj).fields_view_get(cr, uid,)
                temp.append(_('Ok'))
                ok_count += 1
            except:
                temp.append(_('Exception'))
                ex_count += 1
            try:
                pool.get(obj).read(cr, uid, [])
                temp.append(_('Ok'))
                ok_count += 1
            except:
                temp.append(_('Exception'))
                ex_count += 1
            result_dict[obj] = temp
        self.score = (ok_count + ex_count) and float(ok_count)/float(ok_count + ex_count) or 0.0
        if self.score*100 < self.min_score:
            self.message = 'Score is below than minimal score(%s%%)' % self.min_score
        self.result = self.get_result(result_dict)
        return None

    def get_result(self, dict_method):
        header = ('{| border="1" cellspacing="0" cellpadding="5" align="left" \n! %-40s \n! %-16s \n! %-20s \n! %-16s ', [_('Object Name'), 'search()', 'fields_view_get()', 'read()'])
        detail = ""
        if not self.error:
            detail += self.format_table(header, dict_method)
        return detail

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
