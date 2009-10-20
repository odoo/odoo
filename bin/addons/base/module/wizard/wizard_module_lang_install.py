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

import wizard
import tools
import pooler

view_form_end = """<?xml version="1.0"?>
<form string="Language file loaded.">
    <image name="gtk-dialog-info" colspan="2"/>
    <group colspan="2" col="4">
        <separator string="Installation Done" colspan="4"/>
        <label align="0.0" string="The selected language has been successfully installed.\nYou must change the preferences of the user and open a new menu to view changes." colspan="4"/>
    </group>
</form>"""

view_form = """<?xml version="1.0"?>
<form string="System Upgrade">
    <image name="gtk-dialog-info" colspan="2"/>
    <group colspan="2" col="4">
    <separator string="System Upgrade" colspan="4"/>
        <label align="0.0" string="Choose a language to install:" colspan="4"/>
        <field name="lang" colspan="4" required="1"/>
        <label align="0.0" string="Note that this operation may take a few minutes." colspan="4"/>
    </group>
</form>"""


class wizard_lang_install(wizard.interface):
    def _lang_install(self, cr, uid, data, context):
        lang = data['form']['lang']
        if lang:
            modobj = pooler.get_pool(cr.dbname).get('ir.module.module')
            mids = modobj.search(cr, uid, [('state', '=', 'installed')])
            modobj.update_translations(cr, uid, mids, lang)
        return {}

    fields_form = {
        'lang': {'string':'Language', 'type':'selection', 'selection':tools.scan_languages(),
        },
    }

    states = {
        'init': {
            'actions': [],
            'result': {'type': 'form', 'arch': view_form, 'fields': fields_form,
                'state': [
                    ('end', 'Cancel', 'gtk-cancel'),
                    ('start', 'Start installation', 'gtk-ok', True)
                ]
            }
        },
        'start': {
            'actions': [_lang_install],
            'result': {'type': 'form', 'arch': view_form_end, 'fields': {},
                'state': [
                    ('end', 'Ok', 'gtk-ok', True)
                ]
            }
        },
    }
wizard_lang_install('module.lang.install')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

