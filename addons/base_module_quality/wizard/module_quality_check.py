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

form_check = '''<?xml version="1.0"?>
<form string="Quality check">
    <field name="test" />
</form>'''

fields_check = {
    'test': {
        'string':'Tests', 'type':'selection', 'size':64, 'required':True,
        'selection': [('pylint', 'Pylint'), ('othertest','other')],
        'default': lambda *args: 'pylint'
    },
    }
view_form = """<?xml version="1.0"?>
<form string="Check quality">
    <group colspan="2" col="4">
        <field name="module_info" nolabel="1" colspan="4"/>
    </group>
</form>"""

view_field = {
    "module_info": {'type': 'text', 'string': 'check quality',
        'readonly': True,},
}

class wiz_quality_check(wizard.interface):

    def _check(self, cr, uid, data, context):
        if data['form']['test'] == 'pylint':
            pool=pooler.get_pool(cr.dbname)
            module_data = pool.get('ir.module.module').browse(cr, uid, data['ids'])
            from pylint_test import pylint_test
            ad = tools.config['addons_path']
            url = os.path.join(ad, module_data[0].name)
            result = pylint_test._test_pylint(self, url)
            string_ret = ''
            for i in result:
                string_ret = string_ret + i + ':\n' + result[i]

        return {'module_info':string_ret}
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

