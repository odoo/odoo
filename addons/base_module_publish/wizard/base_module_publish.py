# -*- coding: utf-8 -*-
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

import time
import wizard
import osv
import pooler
import urllib
import base64

import module_zip
import tools
from tools.translate import _

intro_form = '''<?xml version="1.0"?>
<form string="Module publication">
    <separator string="Publication information" colspan="4"/>
    <field name="text" colspan="4" nolabel="1" width="300" height="200"/>
</form>'''

intro_fields = {
    'text': {'string':'Introduction', 'type':'text', 'readonly':True,
        'default': lambda *args: """
This system will automatically publish the selected module to the
Open ERP official website. You can use it to quickly publish a new
module or update an existing one (new version).

Make sure you read the publication manual and modules guidelines
before continuing:
  http://www.openerp.com

Thank you for contributing!
"""},
}

def _get_selection(self, cr, uid, datas, *args):
    a = urllib.urlopen('http://www.openerp.com/mtree_interface.php')
    contents = a.read()
    content = filter(None, contents.split('\n'))
    result = map(lambda x:x.split('='), content)

    return result


check_form = '''<?xml version="1.0"?>
<form string="Module publication">
    <separator string="Verify your module information" colspan="4"/>
    <notebook>
        <page string="General">
            <field name="name"/>
            <field name="version"/>
            <field name="author"/>
            <field name="website" widget="url"/>
            <field name="shortdesc"/>
            <field name="operation"/>
            <field name="category" colspan="4"/>
            <newline/>
            <field name="license"/>
            <field name="include_src"/>
            <newline/>
            <field name="url_download" colspan="4" widget="url"/>
            <field name="docurl" colspan="4" widget="url"/>
            <field name="demourl" colspan="4" widget="url"/>
            <field name="image"/>
        </page>
        <page string="Description">
            <field name="description" colspan="4" nolabel="1"/>
        </page>
    </notebook>
</form>'''

check_fields = {
    'name': {'string':'Name', 'type':'char', 'size':64, 'readonly':True},
    'shortdesc': {'string':'Small description', 'type':'char', 'size':200,
        'readonly':True},
    'author': {'string':'Author', 'type':'char', 'size':128, 'readonly':True},
    'website': {'string':'Website', 'type':'char', 'size':200, 'readonly':True},
    'url': {'string':'Download URL', 'type':'char', 'size':200, 'readonly':True},
    'image': {'string':'Image file', 'type':'image', 'help': 'support only .png files'},
    'description': {'string':'Description', 'type':'text', 'readonly':True},
    'version': {'string':'Version', 'type':'char', 'readonly':True},
    'demourl': {'string':'Demo URL', 'type':'char', 'size':128,
        'help': 'empty to keep existing value'},
    'docurl': {'string':'Documentation URL', 'type':'char', 'size':128,
        'help': 'Empty to keep existing value'},
    'category': {'string':'Category', 'type':'selection', 'size':64, 'required':True,
        'selection': _get_selection},
    'license': {
        'string':'Licence', 'type':'selection', 'size':64, 'required':True,
        'selection': [('GPL-2', 'GPL-2'), ('Other proprietary','Other proprietary')],
        'default': lambda *args: 'GPL-2'
    },
    'include_src': {'string': 'Include source', 'type': 'boolean',
        'default': lambda *a: True},
    'operation': {
        'string':'Operation', 
        'type':'selection', 
        'readonly':True, 
        'selection':[('0','Creation'),('1','Modification')],
    },
    'url_download': {'string':'Download URL', 'type':'char', 'size':128,
        'help': 'Keep empty for an auto upload of the module'},
}

upload_info_form = '''<?xml version="1.0"?>
<form string="Module publication">
    <separator string="User information" colspan="4"/>
    <label string="Please provide here your login on the Open ERP website."
    align="0.0" colspan="4"/>
    <label string="If you don't have an access, you can create one http://www.openerp.com/"
    align="0.0" colspan="4"/>
    <field name="login"/>
    <newline/>
    <field name="password" password="True"/>
    <newline/>
    <field name="email"/>
</form>'''

def _get_edit(self, cr, uid, datas, *args):
    pool = pooler.get_pool(cr.dbname)
    name = pool.get('ir.module.module').read(cr, uid, [datas['id']], ['name'])[0]['name']
    a = urllib.urlopen('http://www.openerp.com/mtree_interface.php?module=%s' % (name,))
    content = a.read()
    try:
        email = self.pool.get('res.users').browse(cr, uid, uid).address.email or ''
    except:
        email =''
    result = {'operation': ((content[0]=='0') and '0') or '1', 'email':email}
    if (content[0]<>'0'):
        result['category'] =  content.split('\n')[1]
    return result


upload_info_fields = {
    'login': {'string':'Login', 'type':'char', 'size':32, 'required':True},
    'email': {'string':'Email', 'type':'char', 'size':100, 'required':True},
    'password': {'string':'Password', 'type':'char', 'size':32, 'required':True,
        'invisible':True},
}

end_form = '''<?xml version="1.0"?>
<form string="Module publication">
    <notebook>
        <page string="Information">
            <field name="text_end" colspan="4" nolabel="1" width="300" height="200"/>
        </page>
        <page string="Result">
            <field name="result" colspan="4" nolabel="1"/>
        </page>
    </notebook>
</form>'''

end_fields = {
    'text_end': {'string':'Summary', 'type':'text', 'readonly':True,
        'default': lambda *args: """
Thank you for contributing !

Your module has been successfully uploaded to the official website.
You must wait a few hours/days so that the Open ERP core team review
your module for approval on the website.
"""},
    'result': {'string':'Result page', 'type':'text', 'readonly':True}
}

import httplib, mimetypes

def post_multipart(host, selector, fields, files):
    def encode_multipart_formdata(fields, files):
        BOUNDARY = '----------ThIs_Is_tHe_bouNdaRY_$'
        CRLF = '\r\n'
        L = []
        for (key, value) in fields:
            L.append('--' + BOUNDARY)
            L.append('Content-Disposition: form-data; name="%s"' % key)
            L.append('')
            L.append(value)
        for (key,fname,value) in files:
            L.append('--' + BOUNDARY)
            L.append('Content-Disposition: form-data; name="%s"; filename="%s"'
                    % (key, fname))
            L.append('Content-Type: application/octet-stream')
            L.append('')
            L.append(value)
        L.append('--' + BOUNDARY + '--')
        L.append('')
        body = CRLF.join(L)
        content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
        return content_type, body
    content_type, body = encode_multipart_formdata(fields, files)
    import httplib

    headers = {"Content-type": content_type, "Accept": "*/*"}
    conn = httplib.HTTPConnection(host)
    conn.request("POST", selector, body, headers = headers)
    response = conn.getresponse()
    val = response.status
    res = response.read()
    conn.close()
    return res


def _upload(self, cr, uid, datas, context):
    pool = pooler.get_pool(cr.dbname)
    mod = pool.get('ir.module.module').browse(cr, uid, datas['id'])
    download = datas['form']['url_download'] or ''
    if not download:
        res = module_zip.createzip(cr, uid, datas['id'], context,
                b64enc=False, src=datas['form']['include_src'])
        download = 'http://www.openerp.com/download/modules/'+res['module_filename']
        result = post_multipart('www.openerp.com', '/mtree_upload.php',
            [
                ('login', datas['form']['login']),
                ('password', datas['form']['password']),
                ('module_name', str(mod.name))
            ], [
                ('module', res['module_filename'], res['module_file'])
            ])
        if result and result[0] == "1":
            raise wizard.except_wizard(_('Error'), _('Login failed!'))
        elif result and result[0] == "2":
            raise wizard.except_wizard(_('Error'),
                    _('This version of the module is already exist on the server'))
        elif result and result[0] != "0":
            raise wizard.except_wizard(_('Error'), _('Failed to upload the file'))

    updata = {
        'link_name': mod.shortdesc or '',
        'new_cat_id': datas['form']['category'],
        'link_desc': (mod.description or '').replace('\n','<br/>\n'),
        'website': mod.website or '',
        'price': '0.0',
        'email': datas['form']['email'] or '',
        'cust_1': download,
        'cust_2': datas['form']['demourl'] or '',   # Put here the download url
        'cust_3': mod.url or '/',
        'cust_4': datas['form']['docurl'] or '',
        'cust_5': datas['form']['license'] or '',
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
    name = mod.name
    a = urllib.urlopen('http://www.openerp.com/mtree_interface.php?module=%s' % (name,))
    aa = a.read()
    if aa[0]<>'0':
        updata['link_id']=aa.split('\n')[0]
        updata['option'] = 'mtree'

    files = []
    if datas['form']['image']:
        files.append(('link_image', 'link_image.png',
            base64.decodestring(datas['form']['image'])))
    result = post_multipart('www.openerp.com', '/index.php', updata.items(), files)
    return {'result': result}

def module_check(self, cr, uid, data, context):
    pool = pooler.get_pool(cr.dbname)
    module = pool.get('ir.module.module').browse(cr, uid, data['id'], context)
    if module.state != 'installed':
        raise wizard.except_wizard(_('Error'), _('You could not publish a module that is not installed!'))
    return {
        'name': module.name,
        'shortdesc': module.shortdesc,
        'author': module.author,
        'website': module.website,
        'url': module.url,
        'description': module.description,
        'version': module.installed_version,
        'license': module.license,
    }

class base_module_publish(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {
                'type':'form',
                'arch':intro_form,
                'fields':intro_fields,
                'state':[
                    ('end', 'Cancel', 'gtk-cancel'),
                    ('step1', 'Continue', 'gtk-go-forward', True)
                ]
            }
        },
        'step1': {
            'actions': [module_check, _get_edit],
            'result': {
                'type':'form',
                'arch':check_form,
                'fields':check_fields,
                'state':[
                    ('end','Cancel', 'gtk-cancel'),
                    ('init', 'Previous', 'gtk-go-back'),
                    ('step2','Continue', 'gtk-go-forward', True)
                ]
            }
        },
        'step2': {
            'actions': [],
            'result': {
                'type':'form',
                'arch':upload_info_form,
                'fields':upload_info_fields,
                'state':[
                    ('end','Cancel', 'gtk-cancel'),
                    ('step1', 'Previous', 'gtk-go-back'),
                    ('publish','Publish', 'gtk-ok', True)
                ]
            }
        },
        'publish': {
            'actions': [_upload], # Action to develop: upload method
            'result': {
                'type':'form',
                'arch':end_form,
                'fields':end_fields,
                'state':[
                    ('end','Close', 'gtk-ok', True)
                ]
            }
        }
    }
base_module_publish('base_module_publish.module_publish')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

