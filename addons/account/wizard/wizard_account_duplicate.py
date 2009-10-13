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

duplicate_form = '''<?xml version="1.0"?>
<form string="Duplicate account charts">
    <field name="company_id"/>
</form>'''

duplicate_fields = {
    'company_id': {'string': 'Company', 'type': 'many2one', 'relation': 'res.company', 'required': True},
}

def _do_duplicate(self, cr, uid, data, context):
    account_obj = pooler.get_pool(cr.dbname).get('account.account')
    account_obj.copy(cr, uid, data['id'], data['form'], context=context)
    return {}

class wizard_account_duplicate(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {'type': 'form', 'arch': duplicate_form, 'fields': duplicate_fields, 'state': (('end', 'Cancel'), ('duplicate', 'Duplicate'))},
        },
        'duplicate': {
            'actions': [_do_duplicate],
            'result': {'type': 'state', 'state': 'end'},
        },
    }
wizard_account_duplicate('account.wizard.account.duplicate')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

