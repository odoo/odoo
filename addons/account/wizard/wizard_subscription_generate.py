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

import time
import wizard
import pooler

#
# TODO: add an intermediate screen for checks
#

_subscription_form = '''<?xml version="1.0"?>
<form string="%s">
    <seperator string="Generate entries before:" colspan="4"/>
    <field name="date"/>
</form>''' % ('Subscription Compute',)

_subscription_fields = {
    'date': {'string':'Date', 'type':'date', 'default':lambda *a: time.strftime('%Y-%m-%d'), 'required':True},
}

class wiz_subscription(wizard.interface):
    def _action_generate(self, cr, uid, data, context):
        cr.execute('select id from account_subscription_line where date<%s and move_id is null', (data['form']['date'],))
        ids = map(lambda x: x[0], cr.fetchall())
        pooler.get_pool(cr.dbname).get('account.subscription.line').move_create(cr, uid, ids)
        return {}

    states = {
        'init': {
            'actions': [],
            'result': {'type': 'form', 'arch':_subscription_form, 'fields':_subscription_fields, 'state':[('end','Cancel'),('generate','Compute Entry Dates')]}
        },
        'generate': {
            'actions': [_action_generate],
            'result': {'type': 'state', 'state':'end'}
        }
    }
wiz_subscription('account.subscription.generate')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

