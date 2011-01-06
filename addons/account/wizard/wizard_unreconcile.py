# -*- encoding: utf-8 -*-
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

_info_form = '''<?xml version="1.0"?>
<form string="Unreconciliation">
    <separator string="Unreconciliation transactions" colspan="4"/>
    <image name="gtk-dialog-info" colspan="2"/>
    <label string="If you unreconciliate transactions, you must also verify all the actions that are linked to those transactions because they will not be disable" colspan="2"/>
</form>'''

def _trans_unrec(self, cr, uid, data, context):
    pool = pooler.get_pool(cr.dbname)
    recs = pool.get('account.move.line').read(cr, uid, data['ids'], ['reconcile_id','reconcile_partial_id'])
    unlink_ids = []
    full_recs = filter(lambda x: x['reconcile_id'], recs)
    rec_ids = [rec['reconcile_id'][0] for rec in full_recs]
    
    part_recs = filter(lambda x: x['reconcile_partial_id'], recs)
    part_rec_ids = [rec['reconcile_partial_id'][0] for rec in part_recs]

    unlink_ids += rec_ids
    unlink_ids += part_rec_ids
    
    if len(unlink_ids):
        pooler.get_pool(cr.dbname).get('account.move.reconcile').unlink(cr, uid, unlink_ids)
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
wiz_unreconcile('account.move.line.unreconcile')


def _trans_unrec_reconcile(self, cr, uid, data, context):
    rec_ids = data['ids']
    if len(rec_ids):
        pooler.get_pool(cr.dbname).get('account.move.reconcile').unlink(cr, uid, rec_ids)
    return {}

class wiz_unreconcile_reconcile(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {'type': 'form', 'arch': _info_form, 'fields': {}, 'state':[('end', 'Cancel'), ('unrec', 'Unreconcile')]}
        },
        'unrec': {
            'actions': [_trans_unrec_reconcile],
            'result': {'type': 'state', 'state':'end'}
        }
    }
wiz_unreconcile_reconcile('account.reconcile.unreconcile')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

