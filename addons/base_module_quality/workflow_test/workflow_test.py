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
import xml.dom.minidom

import tools
from tools.translate import _
from base_module_quality import base_module_quality
import pooler

class quality_test(base_module_quality.abstract_quality_check):

    def __init__(self):
        super(quality_test, self).__init__()
        self.name = _("Workflow Test")
        self.note = _("This test checks where object has workflow or not on it if there is a state field and several buttons on it and also checks validity of workflow xml file")
        self.bool_installed_only = True
        self.min_score = 40

    def run_test(self, cr, uid, module_path):
        pool = pooler.get_pool(cr.dbname)
        module_name = module_path.split('/')[-1]
        obj_list = self.get_objects(cr, uid, module_name)
        view_obj = pool.get('ir.ui.view')
        view_ids = view_obj.search(cr, uid, [('model', 'in', obj_list), ('type', 'in', ['form'])])
        view_data = view_obj.browse(cr, uid, view_ids)
        field_obj = pool.get('ir.model.fields')
        field_ids = field_obj.search(cr, uid, [('model', 'in', obj_list)])
        field_data = field_obj.browse(cr, uid, field_ids)
        wkf_obj = pool.get('workflow')
        wkf_activity_obj = pool.get('workflow.activity')

        state_check = []
        wkf_avail = []
        result_dict = {}
        activity_chk = {}
        bad_view = 0
        good_view = 0
        act_ok = 0
        not_ok = 0
        wkfs = []

        if obj_list:
            wkf_ids = wkf_obj.search(cr, uid, [('osv', 'in', obj_list)])
            wkfs = wkf_obj.read(cr, uid, wkf_ids, ['osv'])
            for i in wkfs:
                activity_chk[i['osv']] = {'start': 'not_ok', 'stop': 'not_ok'}
                wkf_avail.append(i['osv'])
                model_ids = self.get_ids(cr, uid, [i['osv']])
                if len(model_ids[i['osv']]) < 2: # to be modified..
                    bad_view += 1
                    result_dict[i['osv']] = [i['osv'], 'You should have enough demo data which allows testing of integrity of module and ensures the proper functioning of workflows']
                else:
                    good_view += 1
        wkf_ids = map(lambda x:x['id'], wkfs)
        if not wkf_ids:
            result_dict[module_name] = [module_name, 'No workflow defined on module']
        #Activity of workflow checking...
        activity_ids = wkf_activity_obj.search(cr, uid, [('wkf_id', 'in', wkf_ids)])
        activities = wkf_activity_obj.browse(cr, uid, activity_ids)
        for activity in activities:
            if activity.flow_start:
                activity_chk[activity.wkf_id.osv]['start'] = 'ok'
            if activity.flow_stop:
                activity_chk[activity.wkf_id.osv]['stop'] = 'ok'
            activity_chk[activity.wkf_id.osv]['model'] = activity.wkf_id.osv
            if activity.in_transitions and activity.out_transitions:
                act_ok += 1
            if not activity.in_transitions and not activity.out_transitions:
                not_ok += 1
                result_dict[activity.id] = [activity.name, 'Use less activity (improves readability and protects server resources)']
        for act in activity_chk:
            if activity_chk[act]['start'] == 'ok':
                act_ok += 1
            else:
                not_ok +=  1
                result_dict[activity_chk[act]['model']] = [activity_chk[act]['model'], 'Workflow activities should have atleast one starting node']
            if activity_chk[act]['stop'] == 'ok':
                act_ok += 1
            else:
                not_ok +=  1
                result_dict[activity_chk[act]['model']] = [activity_chk[act]['model'], 'Workflow activities should have atleast one ending node']

        score_general = act_ok and float(act_ok) / float(act_ok + not_ok)
        # workflow defined on object or not checking..
        for field in field_data:
            if field.name == 'state':
                state_check.append(field.model)
        for view in view_data:
            if view.model in state_check:
                dom = xml.dom.minidom.parseString(view.arch)
                node = dom.childNodes
                count = self.count_button(node[0], count=0)
                if count > 3 and not view.model in wkf_avail:
                    bad_view +=  1
                    result_dict[view.model] = [view.model, 'The presence of a field state in object often indicative of a need for workflow behind. And connect them to ensure consistency in this field.']
                elif count > 0 and view.model in wkf_avail:
                    good_view += 1
        score_avail = good_view and float(good_view) / float(bad_view + good_view)
        self.score = (score_general + score_avail) / 2
        if self.score*100 < self.min_score:
            self.message = 'Score is below than minimal score(%s%%)' % self.min_score
        if not wkf_ids and not bad_view:
            self.error = True
            self.result = _("No Workflow define")
            return None
        self.result = self.get_result({module_name: [module_name, int(self.score * 100)]})
        self.result_details += self.get_result_details(result_dict)
        return None

    def get_result(self, dict_wf):
        header = ('{| border="1" cellspacing="0" cellpadding="5" align="left" \n! %-40s \n! %-10s \n', [_('Module Name'), _('Result of views in %')])
        if not self.error:
            return self.format_table(header, data_list=dict_wf)
        return ""

    def get_result_details(self, dict_wf):
        str_html = '''<html><head>%s</head><body><table class="tablestyle">'''%(self.get_style())
        header = ('<tr><th class="tdatastyle">%s</th><th class="tdatastyle">%s</th></tr>', [_('Object Name'), _('Feed back About Workflow of Module')])
        if not self.error:
            res = str_html + self.format_html_table(header, data_list=dict_wf) + '</table><newline/></body></html>'
            res = res.replace('''<td''', '''<td class="tdatastyle" ''')
            return res
        return ""

    def count_button(self, node, count):
        for node in node.childNodes:
            if node.localName == 'button':
                count += 1
            if node.childNodes:
                count = self.count_button(node, count)
        return count

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
