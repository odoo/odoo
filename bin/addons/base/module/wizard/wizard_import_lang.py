# -*- encoding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.     
#
##############################################################################

import wizard
import tools
import base64
import pooler
from tempfile import TemporaryFile

view_form="""<?xml version="1.0"?>
<form string="Import language">
    <image name="gtk-dialog-info" colspan="2"/>
    <group colspan="2" col="4">
        <separator string="Import New Language" colspan="4"/>
        <field name="name" width="200"/>
        <field name="code"/>
        <field name="data" colspan="4"/>
        <label string="You have to import a .CSV file wich is encoded in UTF-8.\n
Please check that the first line of your file is one of the following:" colspan="4" align="0.0"/>
        <label string="type,name,res_id,src,value" colspan="4"/>
        <label string="module,type,name,res_id,src,value" colspan="4"/>
        <label string="You can also import .po files." colspan="4" align="0.0"/>
    </group>
</form>"""

fields_form={
    'name':{'string':'Language name', 'type':'char', 'size':64, 'required':True},
    'code':{'string':'Code (eg:en__US)', 'type':'char', 'size':5, 'required':True},
    'data':{'string':'File', 'type':'binary', 'required':True},
}

class wizard_import_lang(wizard.interface):

    def _import_lang(self, cr, uid, data, context):
        form=data['form']
        fileobj = TemporaryFile('w+')
        fileobj.write( base64.decodestring(form['data']) )

        # now we determine the file format
        fileobj.seek(0)
        first_line = fileobj.readline().strip().replace('"', '').replace(' ', '')
        fileformat = first_line.endswith("type,name,res_id,src,value") and 'csv' or 'po'
        fileobj.seek(0)

        tools.trans_load_data(cr.dbname, fileobj, fileformat, form['code'], lang_name=form['name'])
        fileobj.close()
        return {}

    states={
        'init':{
            'actions': [],
            'result': {'type': 'form', 'arch': view_form, 'fields': fields_form,
                'state':[
                    ('end', 'Cancel', 'gtk-cancel'),
                    ('finish', 'Ok', 'gtk-ok', True)
                ]
            }
        },
        'finish':{
            'actions':[],
            'result':{'type':'action', 'action':_import_lang, 'state':'end'}
        },
    }
wizard_import_lang('module.lang.import')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

