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
import re

from tools.translate import _
from base_module_quality import base_module_quality
import pooler

class quality_test(base_module_quality.abstract_quality_check):

    def __init__(self):
        super(quality_test, self).__init__()
        self.name = _("Object Test")
        self.note = _("""
Test checks for fields, views, security rules, dependancy level
""")
        self.bool_installed_only = True
        self.min_score = 40

    def run_test(self, cr, uid, module_path):
        pool = pooler.get_pool(cr.dbname)
        module_name = module_path.split('/')[-1]
        obj_list = self.get_objects(cr, uid, module_name)
        ids_model = self.get_model_ids(cr, uid, obj_list)
        result_security = {}

        if obj_list: # if module has no new created classes skipp fields, views, security tests
            field_obj = pool.get('ir.model.fields')
            view_obj = pool.get('ir.ui.view')
            access_obj = pool.get('ir.model.access')

            field_ids = field_obj.search(cr, uid, [('model', 'in', obj_list)])
            view_ids = view_obj.search(cr, uid, [('model', 'in', obj_list), ('type', 'in', ['tree', 'form'])])
            access_ids = access_obj.search(cr, uid, [('model_id', 'in', ids_model)])

            field_data = field_obj.browse(cr, uid, field_ids)
            view_data = view_obj.browse(cr, uid, view_ids)
            access_data = access_obj.browse(cr, uid, access_ids)

            result_dict = {}
            result_view = {}
            good_field = 0
            total_field = 0

            # field test .....
            for field in field_data:
                result_dict[field.model] = []
            for field in field_data:
                ttype = field.ttype
                name = field.name
                total_field += 1
                check_str = re.compile('[a-z]+[\w_]*$') #re.compile('[a-z]+[_]?[a-z]+$')
                if ttype == 'many2one':
                    if name.split('_')[-1] == 'id':
                        good_field += 1
                    else:
                        data = 'many2one field should end with _id'
                        result_dict[field.model].append([field.model, name, data])
                elif ttype in ['many2many', 'one2many']:
                    if name.split('_')[-1] == 'ids':
                        good_field += 1
                    else:
                        data = '%s field should end with _ids'% (ttype)
                        result_dict[field.model].append([field.model, name, data])
                elif check_str.match(name):
                    good_field += 1
                else:
                    data = 'Field name should be in lower case or it should follow python standard'
                    result_dict[field.model].append([field.model, name, data])

            #views tests
            for res in result_dict.keys():
                if not result_dict[res]:
                    del result_dict[res]
            view_dict = {}
            total_views = len(obj_list) * 2
            model_views = 0
            for view in view_data:
                view_dict[view.model] = []
                model_views += 1
            for view in view_data:
                ttype = view.type
                view_dict[view.model].append(ttype)
            for view in view_dict:
                if len(view_dict[view]) < 2:
                    model_views -= 1
                    result_view[view] = [view, 'You should have atleast form/tree view of an object']
            if model_views > total_views:
                model_views = total_views

            #security rules test...
            list_files = os.listdir(module_path)
            security_folder = False
            for file_sec in list_files:
                if file_sec == 'security':
                    path = os.path.join(module_path, file_sec)
                    if os.path.isdir(path):
                        security_folder = True
            if not security_folder:
                result_security[module_name] = [module_name, 'Security folder is not available (All security rules and groups should define in security folder)']
            access_list = []
            good_sec = len(obj_list)
            bad_sec = 0
            for access in access_data:
                access_list.append(access.model_id.model)
                if not access.group_id:
                    result_security[access.model_id.model] = [access.model_id.model, 'Specified object has no related group define on access rules']
                    bad_sec += 1 # to be check
            not_avail_access = filter(lambda x: not x in access_list, obj_list)
            for obj in not_avail_access:
                bad_sec += 1
                result_security[obj] = [obj, 'Object should have at least one security rule defined on it']

        #  Dependacy test of module
        module_obj = pool.get('ir.module.module')
        module_ids = module_obj.search(cr, uid, [('name', '=', module_name)])
        module_data = module_obj.browse(cr, uid, module_ids)
        depend_list = []
        depend_check = []
        remove_list = []
        for depend in module_data[0].dependencies_id:
            depend_list.append(depend.name)
        module_ids = module_obj.search(cr, uid, [('name', 'in', depend_list)])
        module_data = module_obj.browse(cr, uid, module_ids)
        for data in module_data:
            for check in data.dependencies_id:
                depend_check.append(check.name)
            for dep in depend_list:
                if dep in depend_check and not dep in remove_list:
                    remove_list.append(str(dep))
        if remove_list:
            result_security[module_name] = [remove_list, 'Unnecessary dependacy should be removed please Provide only highest requirement level']
        bad_depend = len(remove_list)

        if not obj_list:
            score_depend = (100 - (bad_depend * 5)) / 100.0 #  note : score is calculated based on if you have for e.g. two module extra in dependancy it will score -10 out of 100
            self.score = score_depend
            self.result = self.get_result({ module_name: ['No object found', 'No object found', 'No object found', int(score_depend * 100)]})
            self.result_details += self.get_result_general(result_security, name="General")
            return None

        score_view = total_views and float(model_views) / float(total_views)
        score_field = total_field and float(good_field) / float(total_field)
        score_depend = (100 - (bad_depend * 5)) / 100.0 #  note : score is calculated based on if you have for e.g. two module extra in dependancy it will score -10 out of 100
        score_security = good_sec and float(good_sec - bad_sec) / float(good_sec)
        self.score = (score_view + score_field + score_security + score_depend) / 4
        if self.score*100 < self.min_score:
            self.message = 'Score is below than minimal score(%s%%)' % self.min_score
        self.result = self.get_result({ module_name: [int(score_field * 100), int(score_view * 100), int(score_security * 100), int(score_depend * 100)]})
        self.result_details += self.get_result_details(result_dict)
        self.result_details += self.get_result_general(result_view, name="View")
        self.result_details += self.get_result_general(result_security, name="General")
        return None

    def get_result(self, dict_obj):
        header = ('{| border="1" cellspacing="0" cellpadding="5" align="left" \n! %-40s \n! %-40s \n! %-40s \n! %-10s \n', [_('Result of fields in %'), _('Result of views in %'), _('Result of Security in %'), _('Result of dependancy in %')])
        if not self.error:
            return self.format_table(header, data_list=dict_obj)
        return ""

    def get_result_details(self, dict_obj):
        res = ""
        if dict_obj != {}:
            str_html = '''<html><strong> Fields Result</strong><head>%s</head><body>'''%(self.get_style())
            res += str_html
            header = ('<tr><th class="tdatastyle">%s</th><th class="tdatastyle">%s</th><th class="tdatastyle">%s</th></tr>', [_('Object Name'), _('Field name'), _('Suggestion')])
            if not self.error:
                for key in dict_obj.keys():
                    data_list = []
                    final_dict = {}
                    data_list = dict_obj[key]
                    count = 0
                    for i in data_list:
                        count = count + 1
                        final_dict[key + str(count)] = i
                    res_str = '<table class="tablestyle">' + self.format_html_table(header, data_list=final_dict) + '</table><br>'
                    res += res_str.replace('''<td''', '''<td class="tdatastyle" ''')
            return res + '</body></html>'
        return ""

    def get_result_general(self, dict_obj, name=''):
        str_html = '''<html><strong> %s Result</strong><head>%s</head><body><table class="tablestyle">'''% (name, self.get_style())
        header = ('<tr><th class="tdatastyle">%s</th><th class="tdatastyle">%s</th></tr>', [_('Object Name'), _('Suggestion')])
        if not self.error:
            res = str_html + self.format_html_table(header, data_list=dict_obj) + '</table></body></html>'
            res = res.replace('''<td''', '''<td class="tdatastyle" ''')
            return res
        return ""

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
