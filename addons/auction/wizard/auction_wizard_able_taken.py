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
import netsvc
import pooler
take_form = """<?xml version="1.0"?>
<form title="Confirm">
    <separator string="Confirmation set taken away" colspan="4"/>
    <newline/>
</form>
"""

take_fields = {
#   'confirm_en': {'string':'Catalog Number', 'type':'integer'},
}

def _confirm_able(self,cr,uid,data,context={}):
    res={}
    pool = pooler.get_pool(cr.dbname)
    pool.get('auction.lots').write(cr,uid,data['ids'],{'ach_emp':True})
    return {}

class able_take_away(wizard.interface):
    states = {
        'init' : {
            'actions' : [],
            'result' : {
                    'type' : 'form',
                    'arch' : take_form,
                    'fields' : take_fields,
                    'state' : [('end', 'Cancel'),('go', 'Able Taken away')]}
        },
            'go' : {
            'actions' : [_confirm_able],
            'result' : {'type' : 'state', 'state' : 'end'}
        },
}
able_take_away('auction.lots.able')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

