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
import time
import netsvc
import pooler
from tools.translate import _

info = '''<?xml version="1.0"?>
<form string="Distribution Model Saved">
    <label string="This distribution model has been saved.\nYou will be able to reuse it later."/>
</form>'''


def activate(self, cr, uid, data, context):
    plan_obj = pooler.get_pool(cr.dbname).get('account.analytic.plan.instance')
    if data['id']:
        plan = plan_obj.browse(cr, uid, data['id'], context)
        if (not plan.name) or (not plan.code):
            raise wizard.except_wizard(_('Error'), _('Please put a name and a code before saving the model !'))
        pids  =  pooler.get_pool(cr.dbname).get('account.analytic.plan').search(cr, uid, [], context=context)
        if (not pids):
            raise wizard.except_wizard(_('Error'), _('No analytic plan defined !'))
        plan_obj.write(cr,uid,[data['id']],{'plan_id':pids[0]})
        return 'info'
    else:
        return 'endit'

def _do_nothing(self, cr, uid, data, context):
    return 1

class create_model(wizard.interface):

    states = {
        'init': {
            'actions': [],
            'result': {'type':'choice','next_state':activate}
        },
        'info': {
            'actions': [],
            'result': {'type':'form', 'arch':info, 'fields':{}, 'state':[('end','OK')]}
        },
        'endit': {
            'actions': [],
            'result': {'type':'action','action':_do_nothing , 'state':'end'} #FIXME: check
        },
    }
create_model('create.model')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

