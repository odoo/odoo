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

_info_form = '''<?xml version="1.0"?>
<form string="Unreconciliation">
    <separator string="Unreconciliation transactions" colspan="4"/>
    <image name="gtk-dialog-info" colspan="2"/>
    <label string="If you unreconciliate transactions, you must also verify all the actions that are linked to those transactions because they will not be disable" colspan="2"/>
</form>'''

def _trans_unrec(self, cr, uid, data, context):
    pool = pooler.get_pool(cr.dbname)
    voucher = pool.get('account.voucher').browse(cr, uid, data.get('id'))
    recs = None
    for line in voucher.move_ids:
        if line.reconcile_id:
            recs = [line.reconcile_id.id]
    
    for rec in recs:
        pool.get('account.move.reconcile').unlink(cr, uid, rec)
    return {}

class wiz_unreconcile(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {'type': 'form', 'arch': _info_form, 'fields': {}, 'state':[('end', 'Cancel'), ('unrec', 'Unreconcile')]}
        },
        'unrec': {
            'actions': [_trans_unrec],
            'result': {'type': 'state', 'state':'end'}
        }
    }
wiz_unreconcile('account.voucher.unreconcile')

