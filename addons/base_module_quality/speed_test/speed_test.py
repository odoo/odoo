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
import pooler

from base_module_quality import base_module_quality

class CounterCursor(object):
    def __init__(self, real_cursor):
        self.cr = real_cursor
        self.count = 0

    def reset(self):
        self.count = 0

    def execute(self, query, params=None):
        if query.lower().startswith('select '):
            self.count += 1
        return self.cr.execute(query, params)

    def __getattr__(self, attr):
        return getattr(self.cr, attr)


class quality_test(base_module_quality.abstract_quality_check):

    def __init__(self):
        super(quality_test, self).__init__()
        self.bool_installed_only = True
        self.name = _("Speed Test")
        self.note = _("""
This test checks the speed of the module. Note that at least 5 demo data is needed in order to run it.

""")
        self.min_score = 30

    def run_test(self, cr, uid, module_path):
        pool = pooler.get_pool(cr.dbname)
        module_name = module_path.split('/')[-1]
        obj_list = self.get_objects(cr, uid, module_name)

        # remove osv_memory class becaz it does not have demo data
        if obj_list:
            cr.execute("SELECT w.res_model FROM ir_actions_todo AS t "\
                       "LEFT JOIN ir_act_window AS w ON t.action_id=w.id "\
                       "WHERE w.res_model IN %s", (tuple(obj_list),))
            res = cr.fetchall()
            for remove_obj in res:
                if remove_obj and (remove_obj[0] in obj_list):
                    obj_list.remove(remove_obj[0])

        result_dict2 = {}
        if not obj_list:
            self.error = True
            self.result += _("Given module has no objects.Speed test can work only when new objects are created in the module along with demo data")
            return None
        obj_counter = 0
        score = 0.0
        obj_ids = self.get_ids(cr, uid, obj_list)
        result_dict = {}
        result_dict2 = {}
        self.result_details += _("<html>O(1) means that the number of SQL requests to read the object does not depand on the number of objects we are reading. This feature is hardly wished.\n</html>")
        ccr = CounterCursor(cr)
        for obj, ids in obj_ids.items():
            code_base_complexity = 0
            code_half_complexity = 0
            code_size_complexity = 0
            obj_counter += 1
            ids = ids[:100]
            size = len(ids)
            list2 = []
            if size:
                speed_list = []
                try:
                    # perform the operation once to put data in cache
                    pool.get(obj).read(cr, uid, ids)

                    ccr.reset()
                    pool.get(obj).read(ccr, uid, [ids[0]])
                    code_base_complexity = ccr.count

                    ccr.reset()
                    pool.get(obj).read(ccr, uid, ids[:size/2])
                    code_half_complexity = ccr.count

                    ccr.reset()
                    pool.get(obj).read(ccr, uid, ids)
                    code_size_complexity = ccr.count

                except Exception, e:
                    list2 = [obj, _("Error in Read method")]
                    speed_list = [obj, size, code_base_complexity, code_half_complexity, code_size_complexity, _("Error in Read method:" + str(e))]
                else:
                    if size < 5:
                        speed_list = [obj, size, code_base_complexity, code_half_complexity, code_size_complexity, _("Warning! Not enough demo data")]
                        list2 = [obj, _("No enough data")]
                    else:
                        if code_size_complexity <= (code_base_complexity + size):
                            complexity = _("O(1)")
                            score += 1
                            list2 = [obj, _("Efficient")]
                        else:
                            complexity = _("O(n) or worst")
                            list2 = [obj, _("Not Efficient")]

                        speed_list = [obj, size, code_base_complexity, code_half_complexity, code_size_complexity, complexity]
            else:
                speed_list = [obj, size, "", "", "", _("Warning! Object has no demo data")]
                list2 = [obj, _("No data")]
            result_dict[obj] = speed_list
            result_dict2[obj] = list2
        self.score = obj_counter and score / obj_counter or 0.0
        if self.score*100 < self.min_score:
            self.message = 'Score is below than minimal score(%s%%)' % self.min_score
        self.result_details += self.get_result_details(result_dict)
        self.result += self.get_result(result_dict2)
        return None

    def get_result(self, dict_speed):
        header = ('{| border="1" cellspacing="0" cellpadding="5" align="left" \n! %-40s \n! %-10s', [_('Object Name'), _('Result')])
        if not self.error:
            return self.format_table(header, data_list=dict_speed)
        return ""

    def get_result_details(self, dict_speed):
        str_html = '''<html><head>%s</head><body><table class="tablestyle">'''%(self.get_style())
        header = ('<tr><th class="tdatastyle" >%s</th><th class="tdatastyle">%s</th><th class="tdatastyle">%s</th><th class="tdatastyle">%s</th><th class="tdatastyle">%s</th><th class="tdatastyle">%s</th></tr>', [_('Object Name'), _('N (Number of Records)'), _('1'), _('N/2'), _('N'), _('Reading Complexity')])
        if not self.error:
            res = str_html + self.format_html_table(header, data_list=dict_speed) + '</table></body></html>'
            res = res.replace('''<td''', '''<td class="tdatastyle" ''')
            return res
        return ""

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
