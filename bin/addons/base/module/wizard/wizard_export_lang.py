# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2008 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id$
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

import wizard
import tools
import base64
import StringIO
import csv
import pooler

from osv import fields,osv

'''
view_form_init="""<?xml version="1.0"?>
<form string="Export language">
    <image name="gtk-dialog-info" colspan="2"/>
    <group colspan="2" col="4">
        <separator string="Export translation file" colspan="4"/>
        <label align="0.0" string="Choose a language to export:" colspan="4"/>
        <field name="lang" colspan="4"/>
    </group>
</form>"""

view_form_finish="""<?xml version="1.0"?>
<form string="Export language">
    <image name="gtk-dialog-info" colspan="2"/>
    <group colspan="2" col="4">
        <separator string="Export done" colspan="4"/>
        <field name="data" readonly="1" colspan="3"/>
        <label align="0.0" string="Save this document to a .CSV file and open it with\n your favourite spreadsheet software. The file\n encoding is UTF-8. You have to translate the latest\n column before reimporting it." colspan="4"/>
    </group>
</form>"""

class wizard_export_lang(wizard.interface):
    def _get_language(self, cr, uid, context):
        lang_obj=pooler.get_pool(cr.dbname).get('res.lang')
        ids=lang_obj.search(cr, uid, [('active', '=', True),])
        langs=lang_obj.browse(cr, uid, ids)
        return [(lang.code, lang.translatable and lang.name or _('New language')) for lang in langs]

    def _get_file(self, cr, uid, data, context):
        file=tools.trans_generate(data['form']['lang'], 'all', dbname=cr.dbname)
        buf=StringIO.StringIO()
        writer=csv.writer(buf, 'UNIX')
        for row in file:
            writer.writerow(row)
        del file
        out=base64.encodestring(buf.getvalue())
        buf.close()
        return {'data': out}

    fields_form={
        'lang': {'string':'Language', 'type':'selection', 'selection':_get_language,},
    }
    fields_form_finish={
        'data': {'string':'File', 'type':'binary', 'readonly': True,},
    }
    states={
        'init':{
            'actions': [],
            'result': {'type': 'form', 'arch': view_form_init, 'fields': fields_form,
                'state': [
                    ('end', 'Cancel', 'gtk-cancel'),
                    ('finish', 'Ok', 'gtk-ok', True)
                ]
            }
        },
        'finish':{
            'actions': [_get_file],
            'result': {'type': 'form', 'arch': view_form_finish, 
                'fields': fields_form_finish,
                'state': [
                    ('end', 'Close', 'gtk-cancel', True)
                ]
            }
        },
    }
wizard_export_lang('module.lang.export')
'''

class wizard_export_lang(osv.osv_memory):

    def _get_languages(self, cr, uid, context):
        lang_obj=pooler.get_pool(cr.dbname).get('res.lang')
        ids=lang_obj.search(cr, uid, [('active', '=', True),])
        langs=lang_obj.browse(cr, uid, ids)
        return [(lang.code, lang.translatable and lang.name or _('New language')) for lang in langs]
    

    def act_cancel(self, cr, uid, ids, context=None):
        #self.unlink(cr, uid, ids, context)
        return {'type':'ir.actions.act_window_close' }

    def act_destroy(self, *args):
        return {'type':'ir.actions.act_window_close' }

    def act_getfile(self, cr, uid, ids, context=None):
        this = self.browse(cr, uid, ids)[0]
        mods = map(lambda m: m.name, this.modules)
        mods.sort()
        buf=StringIO.StringIO()
    
        tools.trans_export(this.lang, mods, buf, this.format, dbname=cr.dbname)

        if this.format == 'csv':
            this.advice = _("Save this document to a .CSV file and open it with your favourite spreadsheet software. The file encoding is UTF-8. You have to translate the latest column before reimporting it.")
        elif this.format == 'po':
            this.advice = _("Save this document to a .po file and edit it with a specific software or a text editor. The file encoding is UTF-8.")
        
        out=base64.encodestring(buf.getvalue())
        buf.close()
        return self.write(cr, uid, ids, {'state':'get', 'data':out, 'advice':this.advice}, context=context)

    _name = "wizard.module.lang.export"
    _columns = {
            'lang': fields.selection(_get_languages, 'Language',required=True),
            'format': fields.selection( ( ('csv','CSV File'), ('po','PO File') ), 'File Format', required=True),
            'modules': fields.many2many('ir.module.module', 'rel_modules_langexport', 'wiz_id', 'module_id', 'Modules', domain=[('state','=','installed')]),
            'data': fields.binary('File', readonly=True),
            'advice': fields.text('', readonly=True),
            'state': fields.selection( ( ('choose','choose'),   # choose language
                                         ('get','get'),         # get the file
                                       ) ),
            }
    _defaults = { 'state': lambda *a: 'choose', }
wizard_export_lang()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

