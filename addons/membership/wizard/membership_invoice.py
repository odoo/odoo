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

from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp

class membership_invoice(osv.osv_memory):
    """Membership Invoice"""

    _name = "membership.invoice"
    _description = "Membership Invoice"
    _columns = {
        'product_id': fields.many2one('product.product','Membership', required=True),
        'member_price': fields.float('Member Price', digits_compute= dp.get_precision('Product Price'), required=True),
    }
    def onchange_product(self, cr, uid, ids, product_id=False):
        """This function returns value of  product's member price based on product id.
        """
        if not product_id:
            return {'value': {'member_price': False}}
        return {'value': {'member_price': self.pool.get('product.product').price_get(cr, uid, [product_id])[product_id]}}

    def membership_invoice(self, cr, uid, ids, context=None):
        mod_obj = self.pool.get('ir.model.data')
        partner_obj = self.pool.get('res.partner')
        datas = {}
        if context is None:
            context = {}
        data = self.browse(cr, uid, ids, context=context)
        if data:
            data = data[0]
            datas = {
                'membership_product_id': data.product_id.id,
                'amount': data.member_price
            }
        invoice_list = partner_obj.create_membership_invoice(cr, uid, context.get('active_ids', []), datas=datas, context=context)

        try:
            search_view_id = mod_obj.get_object_reference(cr, uid, 'account', 'view_account_invoice_filter')[1]
        except ValueError:
            search_view_id = False
        try:
            form_view_id = mod_obj.get_object_reference(cr, uid, 'account', 'invoice_form')[1]
        except ValueError:
            form_view_id = False

        return  {
            'domain': [('id', 'in', invoice_list)],
            'name': 'Membership Invoices',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.invoice',
            'type': 'ir.actions.act_window',
            'views': [(False, 'tree'), (form_view_id, 'form')],
            'search_view_id': search_view_id,
        }


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
