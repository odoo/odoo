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
import tools

from base_module_quality import base_module_quality
import pooler
import re

class quality_test(base_module_quality.abstract_quality_check):

    def __init__(self):
        '''
        This test checks the quality of __terp__.py file in the selected module.
        '''
        super(quality_test, self).__init__()
        self.bool_installed_only = True
        return None

    def run_test(self, cr, uid, module_path, module_state):
        no_terp = False
        list_files = os.listdir(module_path)
        for i in list_files:
            path = os.path.join(module_path, i)
            if os.path.isdir(path):
                for j in os.listdir(path):
                    list_files.append(os.path.join(i, j))

        n = 0
        score = 0.0
        feel_good_factor = 0
        feel_bad_factor = 0
        detail = "\n===TERP Test===\n"
        summary = "\n===TERP Test===:\n"
        error = False
        
        if '__terp__.py' not in list_files:
            no_terp = True
        
        if no_terp:
            summary += """  
The module does not contain the __terp__.py file.\n\n """
            header_list = ""
            error = True
            self.result = self.format_table(test='terp', data_list=[summary, detail, error])
            return None
        
        terp_file = os.path.join(module_path,'__terp__.py')
        res = eval(tools.file_open(terp_file).read())

        terp_keys = ['category', 'name', 'description', 'author', 'website', 'update_xml', 'init_xml', 'depends', 'version', 'active', 'installable', 'demo_xml']
        
        for key in terp_keys:
            if key in res:
                feel_good_factor += 1
                if isinstance(res[key],(str,unicode)):
                    if not res[key]:
                        feel_bad_factor += 1
                    else:    
                        if key == 'description' and res[key] and len(str(res[key]))>=25:
                            feel_good_factor += 1
                            if res['description'].count('\n') >= 4:# description contains minimum 5 lines
                                feel_good_factor += 1
                        if key == 'website':
                            ptrn = re.compile('https?://[\w\.]*') # reg ex matching on temporary basis.
                            result = ptrn.search(str(res[key]))
                            if result:
                                feel_good_factor += 1
            else:
                feel_bad_factor += 1     
        
        self.score = str(round((feel_good_factor * 10) / float(feel_good_factor + feel_bad_factor),2))
#        if not self.bool_installed_only or module_state=="installed":
        summary += """
This test checks if the module satisfies the current coding standard for __terp__.py file used by OpenERP.

""" + "Score: " + str(self.score) + "/10\n"
            
#        else:
#            summary += """ 
#The module has to be installed before running this test.\n\n """
#            header_list = ""
#            error = True
        
        detail += "__terp__.py : "+ str(self.score) + "/10\n"     
        self.result = self.format_table(test='terp', data_list=[summary, detail, error])
        return None


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: