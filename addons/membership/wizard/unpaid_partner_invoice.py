# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

wizard_arch= """<?xml version="1.0"?>
<form string="Choose invoice details">
    <field
        name="product"
        domain="[('membership','=','True')]"
        context="product='membership_product'"
        />
</form>"""

def _invoice_membership(self, cr, uid, data, context):
    pool = pooler.get_pool(cr.dbname)
    partners = []
    cr.execute('''select p.id from res_partner as p \
                left join account_invoice as i on p.id=i.partner_id \
                left join account_invoice_line as il on i.id=il.invoice_id \
                left join product_product as pr on pr.id=il.product_id \
                where i.state = 'open' and pr.id=%s \
                group by p.id''' % (data['form']['product']))
    map(lambda x: partners.append(x[0]),cr.fetchall())
    result = pool.get('ir.model.data')._get_id(cr, uid, 'base', 'view_res_partner_filter')
    res = pool.get('ir.model.data').read(cr, uid, result, ['res_id'])
    value = {
            'domain': [('id', 'in', partners)],
            'name': 'Unpaid Partners',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'res.partner',
            'type': 'ir.actions.act_window',
            'res_id' : partners,
            'search_view_id' : res['res_id']
        }
    return value

class wizard_unpaid_inv(wizard.interface):

    states = {
        'init' : {
            'actions' : [],
            'result' : {
                'type' : 'form',
                'arch' : wizard_arch,
                'fields' : {
                        'product': {
                            'string': 'Membership product',
                            'type': 'many2one',
                            'relation': 'product.product',
                            'help': 'Select Membership product',
                            'required': True
                        },
                },
                'state' : [('end', 'Cancel'),('ok', 'Unpaid Partners') ]}
        },
        'ok' : {
            'actions' : [],
            'result' : {'type' : 'action', 'action': _invoice_membership, 'state' : 'end'},
        },

    }

wizard_unpaid_inv("wizard.invoice.membership.unpaid")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
