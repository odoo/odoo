# -*- encoding: utf-8 -*-
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

asset_end_arch = '''<?xml version="1.0"?>
<form string="Modify asset">
    <separator string="Asset properties to modify" colspan="4"/>
    <field name="name" colspan="4"/>
    <field name="method_delay"/>
    <field name="method_period"/>
    <separator string="Notes" colspan="4"/>
    <field name="note" nolabel="1" colspan="4"/>
</form>'''

asset_end_fields = {
    'name': {'string':'Reason', 'type':'char', 'size':64, 'required':True},
    'method_delay': {'string':'Number of interval', 'type':'float'},
    'method_period': {'string':'Period per interval', 'type':'float'},
    'note': {'string':'Notes', 'type':'text'},
}

def _asset_default(self, cr, uid, data, context={}):
    pool = pooler.get_pool(cr.dbname)
    prop = pool.get('account.asset.property').browse(cr, uid, data['id'], context)
    return {
        'name': prop.name,
        'method_delay': prop.method_delay,
        'method_period': prop.method_period
    }

def _asset_modif(self, cr, uid, data, context={}):
    pool = pooler.get_pool(cr.dbname)
    prop = pool.get('account.asset.property').browse(cr, uid, data['id'], context)
    pool.get('account.asset.property.history').create(cr, uid, {
        'asset_property_id': data['id'],
        'name': prop.name,
        'method_delay': prop.method_delay,
        'method_period': prop.method_period,
        'note': data['form']['note'],
    }, context)
    pool.get('account.asset.property').write(cr, uid, [data['id']], {
        'name': data['form']['name'],
        'method_delay': data['form']['method_delay'],
        'method_period': data['form']['method_period'],
    }, context)
    return {}


class wizard_asset_modify(wizard.interface):
    states = {
        'init': {
            'actions': [_asset_default],
            'result': {'type':'form', 'arch':asset_end_arch, 'fields':asset_end_fields, 'state':[
                ('end','Cancel'),
                ('asset_modify','Modify asset')
            ]}
        },
        'asset_modify': {
            'actions': [_asset_modif],
            'result': {'type' : 'state', 'state': 'end'}
        }
    }
wizard_asset_modify('account.asset.modify')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

