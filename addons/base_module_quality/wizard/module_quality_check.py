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

import tools
import os


#TODO: (utiliser les nouveaux wizards pour heriter la vue et rajouter un onglet par test?)
#TODO: configure pylint
#TODO: implement the speed test
#TODO: implement the simple test
#TODO: add cheks: do the class quality_check inherits the class abstract_quality_check? 
#TODO: improve translability


#To keep or not? to be discussed...
#~ form_check = '''<?xml version="1.0"?>
#~ <form string="Quality check">
    #~ <field name="test" />
#~ </form>'''

#~ fields_check = {
    #~ 'test': {
        #~ 'string':'Tests', 'type':'selection',  'required':True,
        #~ 'selection': [('pylint', 'Pylint'), ('othertest','other')],
        #~ 'default': lambda *args: 'pylint'
    #~ },
    #~ }

view_form = """<?xml version="1.0"?>
<form string="Check quality">
    <notebook>
        <page string="Summary">
            <field name="general_info" nolabel="1" colspan="4" height="350" width="400"/>
        </page>
    </notebook>
</form>"""


view_field = {
    "general_info": {'type': 'text', 'string': 'General Info',  'readonly':True},
}


class wiz_quality_check(wizard.interface):


    def _check(self, cr, uid, data, context={}):
        string_ret = ""
        from tools import config
        pool = pooler.get_pool(cr.dbname)
        module_data = pool.get('ir.module.module').browse(cr, uid, data['ids'])

        list_folders = os.listdir(config['addons_path']+'/base_module_quality/')
        for item in list_folders:
            path = config['addons_path']+'/base_module_quality/'+item
            if os.path.exists(path+'/'+item+'.py') and item not in ['report', 'wizard', 'security']:
                ad = tools.config['addons_path']
                module_path = os.path.join(ad, module_data[0].name)
                item2 = 'base_module_quality.'+item+'.'+item
                x = __import__(item2)
                x2 = getattr(x, item)
                x3 = getattr(x2, item)
                val = x3.quality_test()
                if not val.bool_installed_only or module_data[0].state == "installed":
                    val.run_test(str(module_path))
                else:
                    val.result += "The module has to be installed before running this test."

                string_ret += val.result
                print val.result_details

        return {'general_info':string_ret}



    states = {

#To keep or not? to be discussed...

        #~ 'init': {
            #~ 'actions': [],
            #~ 'result': {'type':'form', 'arch':form_check, 'fields':fields_check, 'state':[('end','Cancel'),('do','Do Test')]}
        #~ },
        'init': {
            'actions': [_check],
            'result': {'type':'form', 'arch':view_form, 'fields':view_field, 'state':[('end','Ok')]},
        },

    }
wiz_quality_check('base.module.quality')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

