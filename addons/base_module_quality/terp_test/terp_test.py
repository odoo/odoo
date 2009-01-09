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
import tools

from base_module_quality import base_module_quality
import pooler
import re

class quality_test(base_module_quality.abstract_quality_check):

    def __init__(self):
#        '''
#        This test checks the quality of __terp__.py file in the selected module.
#        '''
        super(quality_test, self).__init__()
        self.name = _("Terp Test")
        self.note = _("This test checks if the module satisfies the current coding standard used by OpenERP.")
        self.bool_installed_only = False
        self.no_terp = False
        self.ponderation = 2

        return None

    def run_test_terp(self, cr, uid, module_path):
        list_files = os.listdir(module_path)
        
        current_module = module_path.split('/')[-1]
        
        for i in list_files:
            path = os.path.join(module_path, i)
            if os.path.isdir(path):
                for j in os.listdir(path):
                    list_files.append(os.path.join(i, j))

        n = 0
        score = 0.0
        feel_good_factor = 0
        feel_bad_factor = 0
        if '__terp__.py' not in list_files:
            self.no_terp = True
            self.result += _("The module does not contain the __terp__.py file")
            return None

        terp_file = os.path.join(module_path,'__terp__.py')
        res = eval(tools.file_open(terp_file).read())

        terp_keys = ['category', 'name', 'description', 'author', 'website', 'update_xml', 'init_xml', 'depends', 'version', 'active', 'installable', 'demo_xml', 'certificate']

        for key in terp_keys:
            if key in res:
                feel_good_factor += 1 # each tag should appear
                if isinstance(res[key],(str,unicode)):
                    if not res[key]:
                        feel_bad_factor += 1
                    else:
                       
                        if key == 'description' and res[key] and len(str(res[key])) >= 150: # no. of chars should be >=150
                            feel_good_factor += 1
                            if res['description'].count('\n') >= 4:# description contains minimum 5 lines
                                feel_good_factor += 1
                        if key == 'website':
                            ptrn = re.compile('https?://[\w\.]*') # reg ex matching on temporary basis.Website is correctly formatted
                            result = ptrn.search(str(res[key]))
                            if result:
                                feel_good_factor += 1
                            else:
                                feel_bad_factor += 1
                
                if isinstance(res[key],bool):
                    if key == 'active':
                        if current_module != 'base':
                            if res[key]:
                                feel_bad_factor += 1
                        else:
                            if not res[key]:
                                feel_bad_factor += 1       
                        
                    if key == 'installable' and not res[key]: # installable tag is provided and True
                        feel_bad_factor +=1
            else:
                feel_bad_factor += 1

        score = round((feel_good_factor) / float(feel_good_factor + feel_bad_factor),2)

#        self.result += "__terp__.py : "+ str(self.score) + "/10\n"
        return [_('__terp__.py file'), score]


    def run_test(self, cr, uid, module_path):
        terp_score = self.run_test_terp(cr, uid, module_path)
        self.score = terp_score[1]
        self.result = self.get_result({'__terp__.py': terp_score})
        return None

    def get_result(self, dict):
        header = ('{| border="1" cellspacing="0" cellpadding="5" align="left" \n! %-40s \n! %-10s \n', [_('Object Name'), _('Result (/1)'),])
        if not self.error:
            return self.format_table(header, data_list=dict)
        return ""

    #~ def get_result(self, cr, uid, module_path, module_state):
#~ #        self.run_test(cr, uid, module_path)
#~ #        summary = "\n===TERP Test===:\n"
        #~ if self.no_terp:
           #~ summary += """
#~ The module does not contain the __terp__.py file.\n\n """
#~ #        else:
#~ #            summary += """
#~ #    This test checks if the module satisfies the current coding standard for __terp__.py file used by OpenERP.
#~ #    """ + "Score: " + str(self.score) + "/10\n"
        #~ return summary

    #~ def get_result_details(self):
        #~ detail = "\n===TERP Test===\n" + self.result
        #~ return detail



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
