# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004 TINY SPRL. (http://tiny.be) All Rights Reserved.
#                    Fabien Pinckaers <fp@tiny.Be>
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
import netsvc

import pooler
from tools.misc import UpdateableStr


# Dossier

_lot_arch = """<?xml version="1.0"?>
<form string="Mark Lots" height="500" width="1000">
    <label string="Select lots which are Sold" colspan="4"/>
    <field name="lot_ids" nolabel="1" colspan="4" domain="[('state','=','sold')]"/>
</form>
"""
_lot_fields = {
    'lot_ids': {'string':'Lots Emportes','relation':'auction.lots','type':'many2many'}
}

def _to_xml(s):
    return s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')

def _process(self, cr, uid, data, context):
    pool = pooler.get_pool(cr.dbname)
    lot_obj = pool.get('auction.lots')
    if data['form']['lot_ids']:
        lot_obj.write(cr, uid, data['form']['lot_ids'][0][2], {'state':'taken_away'})
    return {'lot_ids': []}

class wizard_reprint(wizard.interface):
    states = {
        'valid': {
            'actions': [_process],
            'result': {'type':'state', 'state':'init'}
        },
        'init': {
            'actions': [],
            'result': {
                'type':'form', 
                'arch': _lot_arch,
                'fields': _lot_fields,
                'state': [
                    ('valid','       OK       ')
                ],
            }
        }
    }
wizard_reprint('auction.taken')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

