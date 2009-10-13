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

_transaction_form = '''<?xml version="1.0"?>
<form string="Close Period">
    <separator string="Are you sure ?" colspan="4"/>
    <field name="sure"/>
</form>'''

_transaction_fields = {
    'sure': {'string':'Check this box', 'type':'boolean'},
}

def _data_save(self, cr, uid, data, context):
    mode = 'done'
    if data['form']['sure']:
        for id in data['ids']:
            cr.execute('update account_journal_period set state=%s where period_id=%s', (mode, id))
            cr.execute('update account_period set state=%s where id=%s', (mode, id))
    return {}

class wiz_journal_close(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {'type': 'form', 'arch':_transaction_form, 'fields':_transaction_fields, 'state':[('end','Cancel'),('close','Close Period')]}
        },
        'close': {
            'actions': [_data_save],
            'result': {'type': 'state', 'state':'end'}
        }
    }
wiz_journal_close('account.period.close')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

