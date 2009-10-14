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
import tools
from tools.translate import _

intro_form = '''<?xml version="1.0"?>
<form string="Report designer">
    <separator string="Report designer introduction" colspan="4"/>
    <field name="text" colspan="4" nolabel="1"/>
</form>'''

intro_fields = {
    'text': {
        'string': 'Introduction',
        'type': 'text',
        'readonly': True,
        'default': lambda *args: """This system must be used with the Tiny OpenOffice plugin. If you
did not installed yet, you can find this package on:
    http://www.openerp.com

This wizard will provide you the .SXW report that you can modify
in OpenOffice. After having modified it, you will be able to reupload
it to the Open ERP server.
"""},
    'operation': {
        'string': 'Operation',
        'type': 'selection',
        'selection': [
            ('create','Create a new report'),
            ('modify','Modify an existing report')
            ],
        'size': 32,
        'required': True,
        'default': lambda *args: 'create',
    },
}

get_form = '''<?xml version="1.0"?>
<form string="Get a report">
    <separator string="Select your report" colspan="4"/>
    <field name="report_id"/>
</form>'''

get_fields = {
    'report_id': {
        'string': 'Report',
        'type': 'many2one',
        'relation': 'ir.actions.report.xml',
        'required': True,
        'domain': [('report_sxw_content','<>',False)],
    },
}

get_form_result = '''<?xml version="1.0"?>
<form string="Get a report">
    <separator string="The .SXW report" colspan="4"/>
    <field name="report_id"/>
    <newline/>
    <field name="file_sxw"/>
    <newline/>
    <label colspan="4" string="This is the template of your requested report.\nSave it as a .SXW file and open it with OpenOffice.\nDon't forget to install the Tiny OpenOffice package to modify it.\nOnce it is modified, re-upload it in Open ERP using this wizard." align="0.0"/>
</form>'''

get_form_fields = {
    'report_id': {
        'string': 'Report',
        'type': 'many2one',
        'relation': 'ir.actions.report.xml',
        'readonly': True,
    },
    'file_sxw': {
        'string': 'Your .SXW file',
        'type': 'binary',
        'readonly': True,
    }
}


send_form_result_arch = '''<?xml version="1.0"?>
<form string="Report modified">
    <separator string="Report modified" colspan="4"/>
    <label string="Your report has been modified."/>
</form>'''

send_form_result_fields = {
}


send_form_arch = '''<?xml version="1.0"?>
<form string="Get a report">
    <separator string="Upload your modified report" colspan="4"/>
    <field name="report_id"/>
    <newline/>
    <field name="file_sxw"/>
</form>'''

send_form_fields = {
    'report_id': {
        'string': 'Report',
        'type': 'many2one',
        'relation': 'ir.actions.report.xml',
        'required': True,
        'domain': [('report_sxw_content','<>',False)]
    },
    'file_sxw': {
        'string': 'Your .SXW file',
        'type': 'binary',
        'required': True
    }
}

def _get_default(obj, cursor, user, data, context):
    return {}


class base_report_designer_modify(wizard.interface):
    def _upload_report_clear(self, cr, uid, data, context):
        return {'file_sxw': False}

    def _upload_report(self, cr, uid, data, context):
        import tiny_sxw2rml
        import StringIO
        pool = pooler.get_pool(cr.dbname)
        sxwval = StringIO.StringIO(base64.decodestring(data['form']['file_sxw']))
        fp = tools.file_open('normalized_oo2rml.xsl',subdir='addons/base_report_designer/wizard/tiny_sxw2rml')
        report = pool.get('ir.actions.report.xml').write(cr, uid, [data['form']['report_id']], {
            'report_sxw_content': base64.decodestring(data['form']['file_sxw']),
            'report_rml_content': str(tiny_sxw2rml.sxw2rml(sxwval, xsl=fp.read()))
        })
        return {}

    def _get_report(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)
        report = pool.get('ir.actions.report.xml').browse(cr, uid, data['form']['report_id'], context)
        try:
            return {'file_sxw': base64.encodestring(report.report_sxw_content)}
        except:
            raise wizard.except_wizard(_('Error'), _('Report does not contain the sxw content!'))

    states = {
        'init': {
            'actions': [],
            'result': {
                'type': 'form',
                'arch': intro_form,
                'fields': intro_fields,
                'state': [
                    ('end','Cancel'),
                    ('get_form','Modify a report')
                ]
            }
        },
        'get_form': {
            'actions': [_get_default],
            'result': {
                'type': 'form',
                'arch': get_form,
                'fields': get_fields,
                'state': [
                    ('end','Cancel'),
                    ('get_form_result', 'Continue'),
                ]
            }
        },
        'get_form_result': {
            'actions': [_get_report],
            'result': {
                'type': 'form',
                'arch': get_form_result,
                'fields': get_form_fields,
                'state': [
                    ('end','Close'),
                    ('send_form', 'Upload the modified report'),
                ]
            }
        },
        'send_form': {
            'actions': [_upload_report_clear],
            'result': {
                'type': 'form',
                'arch': send_form_arch,
                'fields': send_form_fields,
                'state': [
                    ('end','Close'),
                    ('send_form_result', 'Update the report'),
                ]
            }
        },
        'send_form_result': {
            'actions': [_upload_report],
            'result': {
                'type': 'form',
                'arch': send_form_result_arch,
                'fields': send_form_result_fields,
                'state': [
                    ('end','Close'),
                ]
            }
        },
    }

base_report_designer_modify('base_report_designer.modify')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

