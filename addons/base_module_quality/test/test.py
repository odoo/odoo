import os

from osv import fields, osv
from tools.translate import _
import pooler
from tools import config
from base_module_quality import base_module_quality

class quality_test(base_module_quality.abstract_quality_check):

    def __init__(self):
        super(quality_test, self).__init__()
        self.name = _("Test")
        self.note = _("""
This test checks the YML of the module
""")
        self.bool_installed_only = False
        self.bad_standard = 0
        self.good_standard = 0
        self.result_py = {}
        self.min_score = 0
        return None

    def run_test(self, cr, uid, module_path):
        pool = pooler.get_pool(cr.dbname)
        module_name = module_path.split('/')[-1]
        test_file = config['addons_path'] +'/' + module_name +'/test'

        if not os.path.exists(test_file):
            self.result += _("Module does not have Proper Path")
            return None
        else:
            list_files = os.listdir(test_file)
            for i in list_files:
                    path = os.path.join(module_path, i)
                    if os.path.isdir(path):
                        for j in os.listdir(path):
                            list_files.append(os.path.join(i, j))
            py_list = []
            for file_py in list_files:
                if file_py.split('.')[-1] == 'yml':
                    file_path = os.path.join(module_path, file_py)
                    py_list.append(file_path)

            if not py_list:
                self.error = True
                self.result = _("No YML file found")
                return None

            self.score = self.good_standard and float(self.good_standard) / float(self.good_standard + self.bad_standard)
            if self.score*100 < self.min_score:
                self.message = 'Score is below than minimal score(%s%%)' % self.min_score
            self.result = self.get_result({ module_path: [int(self.score * 100)]})
            self.result_details += self.get_result_general(self.result_py)

    def get_result(self, dict_obj):
        header = ('{| border="1" cellspacing="0" cellpadding="5" align="left" \n! %-40s \n', [_('Result of test in %')])
        if not self.error:
            return self.format_table(header, data_list=dict_obj)
        return

    def get_result_general(self, dict_obj):
        str_html = '''<html><strong>Result</strong><head>%s</head><body><table class="tablestyle">'''%(self.get_style())
        header = ('<tr><th class="tdatastyle">%s</th><th class="tdatastyle">%s</th><th class="tdatastyle">%s</th></tr>', [_('Object Name'), _('Line number'), _('Suggestion')])
        if not self.error:
            res = str_html + self.format_html_table(header, data_list=dict_obj) + '</table></body></html>'
            res = res.replace('''<td''', '''<td class="tdatastyle" ''')
            return res
        return ""
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
