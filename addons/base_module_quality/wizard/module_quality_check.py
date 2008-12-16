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
import wizard
import pooler
import osv
import netsvc

import sys
import tools
import os
import pylint
import base_module_quality

form_check = '''<?xml version="1.0"?>
<form string="Quality check">
    <field name="test" />
</form>'''

fields_check = {
    'test': {
        'string':'Tests', 'type':'selection',  'required':True,
        'selection': [('pylint', 'Pylint'), ('othertest','other')],
        'default': lambda *args: 'pylint'
    },
    }

view_form = """<?xml version="1.0"?>
<form string="Check quality">
    <notebook>
        <page string="Summary">
            <field name="general_info" nolabel="1" colspan="4" height="350" width="400"/>
        </page>
    </notebook>
</form>"""
#TODO: utiliser les nouveaux wizards pour heriter la vue et rajouter un onglet par test?
#TODO: remove the first screen which is unused

view_field = {
    "general_info": {'type': 'text', 'string': 'General Info',  'readonly':True},
}




class wiz_quality_check(wizard.interface):


    def _check(self, cr, uid, data, context):
        string_ret = ""
        from tools import config
        list_folders=os.listdir(config['addons_path']+'/base_module_quality/')
        for item in list_folders:
            path = config['addons_path']+'/base_module_quality/wizard/'+item
            if os.path.exists(path+'/'+item+'.py') and item not in ['report','wizard', 'security']:
                pool=pooler.get_pool(cr.dbname)
                module_data = pool.get('ir.module.module').browse(cr, uid, data['ids'])

                ad = tools.config['addons_path']
                module_path = os.path.join(ad, module_data[0].name)
                #import pylint_test
                item='base_module_quality.'+item
                x = __import__(item)
                val = x.__init__(str(module_path))
                print "VALL",x._result
                string_ret += val._result

        return {'general_info':string_ret}


            #mra version
            #~ result = pylint_test._test_pylint(self, url)
            #~ string_ret = ''
            #~ for i in result:
                #~ string_ret = string_ret + i + ':\n' + result[i]
        #~ string_ret = ""
        #~ if data['form']['test'] == 'pylint':
            #~ pool=pooler.get_pool(cr.dbname)
            #~ module_data = pool.get('ir.module.module').browse(cr, uid, data['ids'])
            #~ from pylint_test import pylint_test
            #~ ad = tools.config['addons_path']
            #~ url = os.path.join(ad, module_data[0].name)
            #~ result = pylint_test._test_pylint(self, url)
            #~ string_ret = ''
            #~ for i in result:
                #~ string_ret = string_ret + i + ':\n' + result[i]

    states = {
        'init': {
            'actions': [],
            'result': {'type':'form', 'arch':form_check, 'fields':fields_check, 'state':[('end','Cancel'),('do','Do Test')]}
        },
        'do': {
            'actions': [_check],
            'result': {'type':'form', 'arch':view_form, 'fields':view_field, 'state':[('end','Ok')]},
        },

    }
wiz_quality_check('base.module.quality')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

