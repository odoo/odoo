# -*- coding: utf-8 -*-
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

import wizard
import pooler
import module_zip
from base_module_publish import post_multipart
from urllib import urlopen
from tools.translate import _

intro_form = '''<?xml version="1.0"?>
<form string="Module publication">
    <separator string="Publication information" colspan="4"/>
    <field name="text" colspan="4" nolabel="1"/>
</form>'''

intro_fields = {
    'text': {'string': 'Introduction', 'type': 'text', 'readonly': True,
        'default': lambda *a: """
This system will automatically publish and upload the selected modules to the
Open ERP official website. You can use it to quickly update a set of
module (new version).

Make sure you read the publication manual and modules guidlines
before continuing:
  http://www.openerp.com/

Thanks you for contributing!
"""},
}

login_form = '''<?xml version="1.0"?>
<form string="Module publication">
    <separator string="User information" colspan="4"/>
    <label string="Please provide here your login on the Open ERP website."
    align="0.0" colspan="4"/>
    <label string="If you don't have an access, you can create one http://www.openerp.com/"
    align="0.0" colspan="4"/>
    <field name="login"/>
    <newline/>
    <field name="password"/>
    <newline/>
    <field name="email"/>
</form>'''

login_fields = {
    'login': {'string':'Login', 'type':'char', 'size':32, 'required':True},
    'email': {'string':'Email', 'type':'char', 'size':100, 'required':True},
    'password': {'string':'Password', 'type':'char', 'size':32, 'required':True,
        'invisible':True},
}

end_form = '''<?xml version="1.0"?>
<form string="Module publication">
    <separator string="Upload information" colspan="4"/>
    <field name="update" colspan="4"/>
    <field name="already" colspan="4"/>
    <field name="error" colspan="4"/>
</form>'''

end_fields= {
    'update': {'type': 'text', 'string': 'Modules updated', 'readonly': True},
    'already': {'type': 'text', 'string': 'Modules already updated',
        'readonly': True},
    'error': {'type': 'text', 'string': 'Modules in error', 'readonly': True},
}

def _upload(self, cr, uid, datas, context):
    pool = pooler.get_pool(cr.dbname)
    modules = pool.get('ir.module.module').browse(cr, uid, datas['ids'])
    log = [[], [], []] # [update, already, error]
    for mod in modules: # whoooouuuuffff update
        if mod.state != 'installed':
            result[2].append(mod.name)
            continue
        res = module_zip.createzip(cr, uid, mod.id, context, b64enc=False,
                src=(mod.license in ('GPL-2')))
        download = 'http://www.openerp.com/download/modules/'+res['module_filename']
        result = post_multipart('www.openerp.com', '/mtree_upload.php',
                [('login', datas['form']['login']),
                    ('password', datas['form']['password']),
                    ('module_name', mod.name)
                ], [('module', res['module_filename'],
                    res['module_file'])
                ])
        if result[0] == "1":
            raise wizard.except_wizard(_('Error'), _('Login failed!'))
        elif result[0] == "0":
            log[0].append(mod.name)
        elif result[0] == "2":
            log[1].append(mod.name)
        else:
            log[2].append(mod.name)
        updata = {
            'link_name': mod.shortdesc or '',
            'link_desc': (mod.description or '').replace('\n','<br/>\n'),
            'website': mod.website or '',
            'email': datas['form']['email'] or '',
            'cust_1': download,
            'cust_3': mod.url or '/',
            'cust_6': mod.installed_version or '0',
            'cust_7': mod.name,
            'option': 'com_mtree',
            'task': 'savelisting',
            'Itemid': '99999999',
            'cat_id': '0',
            'adminForm': '',
            'auto_login': datas['form']['login'],
            'auto_password': datas['form']['password']
        }
        a = urlopen('http://www.openerp.com/mtree_interface.php?module=%s' % (mod.name,))
        aa = a.read()
        if aa[0]<>'0':
            updata['link_id']=aa.split('\n')[0]
            updata['cat_id']=aa.split('\n')[1]
            updata['option'] = 'mtree'
        result = post_multipart('www.openerp.com', '/index.php', updata.items(), [])
    return {'update': '\n'.join(log[0]), 'already': '\n'.join(log[1]), 'error': '\n'.join(log[2])}

class base_module_publish_all(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {
                'type': 'form',
                'arch': intro_form,
                'fields': intro_fields,
                'state': [
                    ('end', 'Cancel'),
                    ('login', 'Ok'),
                ]
            }
        },
        'login': {
            'actions': [],
            'result': {
                'type': 'form',
                'arch': login_form,
                'fields': login_fields,
                'state': [
                    ('end', 'Cancel'),
                    ('publish', 'Publish')
                ]
            }
        },
        'publish': {
            'actions': [_upload],
            'result': {
                'type': 'form',
                'arch': end_form,
                'fields': end_fields,
                'state': [
                    ('end', 'Close')
                ]
            }
        },
    }
base_module_publish_all('base_module_publish.module_publish_all')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

