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
import pooler


def _get_default_journal_selection(self, cr, uid, context):
    pool = pooler.get_pool(cr.dbname)
    obj = pool.get('account.journal')
    ids = obj.search(cr, uid, [('type', '=', 'cash')])
    res = obj.read(cr, uid, ids, ['id', 'name'], context)
    res = [(r['id'], r['name']) for r in res]
    res.insert(0, ('', ''))
    return res

default_journal_form = '''<?xml version="1.0"?>
<form string="Select default journals">
    <field name="default_journal" />
    <newline />
    <field name="default_journal_rebate" />
    <newline />
    <field name="default_journal_gift" />
    <newline />
</form>'''

default_journal_fields = {
    'default_journal': {'string': 'Default journal', 'type': 'selection',
        'selection': _get_default_journal_selection,
    },
    'default_journal_rebate': {'string': 'Default rebate journal', 'type': 'selection',
        'selection': _get_default_journal_selection,
    },
    'default_journal_gift': {'string': 'Default gift journal', 'type': 'selection',
        'selection': _get_default_journal_selection,
    },
}


class wizard_default_journal(wizard.interface):

    def _set_default_journal(self, cr, uid, data, context):

        def _update_default_journal_config(journal_type, journal_code, journal_descr, journal_codes, data):
            default_journal_id = data.get('form', {}).get(journal_type) or None
            dico = dict(name=journal_descr, code=journal_code, journal_id=default_journal_id)
            if default_journal_id:
                if journal_code in journal_codes:
                    ids = [obj.id for obj in objs if obj.code == journal_code]
                    pos_config_journal.write(cr, uid, ids, dico, context)
                else:
                    pos_config_journal.create(cr, uid, dico, context)
            else:
                ids = [obj.id for obj in objs if obj.code == journal_code]
                pos_config_journal.write(cr, uid, ids, dico, context)

        pool = pooler.get_pool(cr.dbname)
        pos_config_journal = pool.get('pos.config.journal')
        ids = pos_config_journal.search(cr, uid, [])
        objs = pos_config_journal.browse(cr, uid, ids)
        journal_codes = [str(obj.code) for obj in objs]

        _update_default_journal_config('default_journal', 'DEFAULT', 'Default journal', journal_codes, data)
        _update_default_journal_config('default_journal_rebate', 'REBATE', 'Default rebate journal', journal_codes, data)
        _update_default_journal_config('default_journal_gift', 'GIFT', 'Default gift journal', journal_codes, data)

        return {}

    def _get_defaults(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)
        pos_config_journal = pool.get('pos.config.journal')
        ids = pos_config_journal.search(cr, uid, [])
        objs = pos_config_journal.browse(cr, uid, ids)
        journal_codes = {}
        for obj in objs:
            journal_codes[obj.code] = int(obj.journal_id.id)

        form = data['form']
        form['default_journal'] = journal_codes.get('DEFAULT') or False
        form['default_journal_rebate'] = journal_codes.get('REBATE') or False
        form['default_journal_gift'] = journal_codes.get('GIFT') or False

        return form

    states = {
        'init': {
            'actions': [_get_defaults],
            'result': {
                'type': 'form',
                'arch': default_journal_form,
                'fields': default_journal_fields,
                'state': [
                    ('end', 'Cancel'),
                    ('set_default_journal', 'Define default journals')
                ]
            }
        },
        'set_default_journal': {
            'actions': [_set_default_journal],
            'result': {
                'type': 'state',
                'state': "end",
            }
        },
    }

wizard_default_journal('pos.config.journal')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
