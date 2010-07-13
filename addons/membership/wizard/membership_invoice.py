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
from tools.translate import _
import tools

class membership_invoice(osv.osv_memory):
    """Membership Invoice"""
    
    _name = "membership.invoice"
    _description = "Membership Invoice"
    _columns = {
        'product_id': fields.many2one('product.product','Membership Product', required=True),
    }

    def membership_invoice(self, cr, uid, ids, context=None):
        invoice_obj = self.pool.get('account.invoice')
        partner_obj = self.pool.get('res.partner')
        product_obj = self.pool.get('product.product')
        invoice_line_obj = self.pool.get('account.invoice.line')
        invoice_tax_obj = self.pool.get('account.invoice.tax')
        if not context:
            context={}
        partner_ids = context.get('active_ids', [])
        invoice_list = []
        for partner in partner_obj.browse(cr, uid, partner_ids, context=context):
            account_id = partner.property_account_receivable and partner.property_account_receivable.id or False
            fpos_id = partner.property_account_position and partner.property_account_position.id or False
            addr = partner_obj.address_get(cr, uid, [partner.id], ['invoice'])
            if not addr.get('invoice', False):
                continue
            for data in self.browse(cr, uid, ids, context=context):
                product_id = data.product_id and data.product_id.id or False
                product_uom_id = data.product_id and data.product_id.uom_id.id
                quantity = 1
                line_value =  {
                    'product_id' : product_id,
                }
                
                line_dict = invoice_line_obj.product_id_change(cr, uid, {}, 
                                product_id, product_uom_id, quantity, '', 'out_invoice', partner.id, fpos_id, context=context)
                line_value.update(line_dict['value'])
                if line_value.get('invoice_line_tax_id', False):
                    tax_tab = [(6, 0, line_value['invoice_line_tax_id'])]
                    line_value['invoice_line_tax_id'] = tax_tab

                invoice_id = invoice_obj.create(cr, uid, {
                    'partner_id' : partner.id,
                    'address_invoice_id': addr.get('invoice', False),
                    'account_id': account_id,
                    'fiscal_position': fpos_id or False
                    }
                )
                line_value['invoice_id'] = invoice_id
                invoice_line_id = invoice_line_obj.create(cr, uid, line_value, context=context)
                invoice_obj.write(cr, uid, invoice_id, {'invoice_line':[(6,0,[invoice_line_id])]}, context=context)
                invoice_list.append(invoice_id)
                if line_value['invoice_line_tax_id']:
                    tax_value = invoice_tax_obj.compute(cr, uid, invoice_id).values()
                    for tax in tax_value:
                           invoice_tax_obj.create(cr, uid, tax, context=context)  
           

        return  {
            'domain': [('id', 'in', invoice_list)],
            'name': 'Membership Invoice',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.invoice',
            'type': 'ir.actions.act_window',
            }

membership_invoice()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
