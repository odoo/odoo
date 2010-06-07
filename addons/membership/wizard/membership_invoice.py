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
    _name = "membership.invoice"
    _description = "Membership Invoice From Partner"
    _columns ={
        'product_id': fields.many2one('product.product','Membership Product', required=True),
               }

    def membership_invoice(self, cr, uid, ids, context={}):
        invoice_obj = self.pool.get('account.invoice')
        partner_obj = self.pool.get('res.partner')
        product_obj = self.pool.get('product.product')
        invoice_line_obj = self.pool.get(('account.invoice.line'))
        invoice_tax_obj = self.pool.get(('account.invoice.tax'))
        partner_ids = context['active_ids']
        for data in self.read(cr, uid, ids, context=context):
            product_id = data['product_id']
            cr.execute('''
                        SELECT partner_id, id, type
                        FROM res_partner_address
                        WHERE partner_id =ANY(%s)''',(partner_ids,))
            fetchal = cr.fetchall()
            if not fetchal:
                raise osv.except_osv(_('Error !'), _('No Address defined for this partner'))
            partner_address_ids = {}
            for x in range(len(fetchal)):
                pid = fetchal[x][0]
                id = fetchal[x][1]
                type = fetchal[x][2]
                if partner_address_ids.has_key(pid) and partner_address_ids[pid]['type'] == 'invoice':
                        continue
                partner_address_ids[pid] = {'id': id, 'type': type}

            invoice_list= []
            product = product_obj.read(cr, uid, product_id, ['uom_id'], context=context)

            for partner_id in partner_ids:
                account_id = partner_obj.read(cr, uid, partner_id, ['property_account_receivable'], context=context)['property_account_receivable'][0]
                read_fpos = partner_obj.read(cr, uid, partner_id, ['property_account_position'], context=context)
                fpos_id = read_fpos['property_account_position'] and read_fpos['property_account_position'][0]
                line_value =  {
                    'product_id' : product_id,
                     }
                quantity = 1
                line_dict = invoice_line_obj.product_id_change(cr, uid, {}, product_id, product['uom_id'][0], quantity, '', 'out_invoice', partner_id, fpos_id, context=context)
                line_value.update(line_dict['value'])
                if line_value['invoice_line_tax_id']:
                    tax_tab = [(6, 0, line_value['invoice_line_tax_id'])]
                    line_value['invoice_line_tax_id'] = tax_tab
                invoice_id = invoice_obj.create(cr, uid, {
                    'partner_id' : partner_id,
                    'address_invoice_id': partner_address_ids[partner_id]['id'],
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
