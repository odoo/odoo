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
import time

from osv import fields, osv

class member_unpaid_invoice(osv.osv_memory):
    _name = "membership.unpaid.invoice"
    _description = "List of Unpaid Partner"
    _columns ={
        'product': fields.many2one('product.product','Membership product', size=64,required=True, help='Select Membership product'),
               }

    def _invoice_membership(self, cr, uid, ids, context):
        model_obj = self.pool.get('ir.model.data')
        partners = []
        result = model_obj._get_id(cr, uid, 'base', 'view_res_partner_filter')
        res = model_obj.read(cr, uid, result, ['res_id'], context=context)
        for data in self.read(cr, uid, ids, context=context):
            cr.execute('''select p.id from res_partner as p \
                left join account_invoice as i on p.id=i.partner_id \
                left join account_invoice_line as il on i.id=il.invoice_id \
                left join product_product as pr on pr.id=il.product_id \
                where i.state = 'open' and pr.id=%s \
                group by p.id''' % (data['product']))
        map(lambda x: partners.append(x[0]),cr.fetchall())

        return {
            'domain': [('id', 'in', partners)],
            'name': 'Unpaid Partners',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'res.partner',
            'type': 'ir.actions.act_window',
            'res_id' : partners,
            'search_view_id' : res['res_id']
        }

member_unpaid_invoice()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: