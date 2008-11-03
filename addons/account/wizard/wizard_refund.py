# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
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

sur_form = '''<?xml version="1.0"?>
<form string="Credit Note">
    <label string="Are you sure you want to refund this invoice ?"/>
</form>'''

sur_fields = {
}

class wiz_refund(wizard.interface):
    def _invoice_refund(self, cr, uid, data, context):
        pool = pooler.get_pool(cr.dbname)
        ids = pool.get('account.invoice').refund(cr, uid, data['ids'])
        return {
            'domain': "[('id','in', ["+','.join(map(str,ids))+"])]",
            'name': 'Invoices',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.invoice',
            'view_id': False,
            'context': "{'type':'out_refund'}",
            'type': 'ir.actions.act_window'
        }
    states = {
        'init': {
            'actions': [],
            'result': {'type':'form', 'arch':sur_form, 'fields':sur_fields, 'state':[('end','Cancel'),('refund','Credit Note')]}
        },
        'refund': {
            'actions': [],
            'result': {'type':'action', 'action':_invoice_refund, 'state':'end'}
        }
    }
wiz_refund('account.invoice.refund')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

