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
<form string="Close asset">
    <separator string="General information" colspan="4"/>
</form>'''

asset_end_fields = {
}

class wizard_asset_close(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {'type':'form', 'arch':asset_end_arch, 'fields':asset_end_fields, 'state':[
                ('end','Cancel'),
                ('asset_close','End of asset')
            ]}
        },
        'asset_close': {
            'actions': [],
            'result': {'type' : 'state', 'state': 'end'}
        }
    }
wizard_asset_close('account.asset.close')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

